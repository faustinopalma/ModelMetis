import base64
import copy
import html
import io
import json
import os
import re
import shutil
import time
from dataclasses import asdict
from pathlib import Path

import httpx
import numpy as np
from PIL import Image, ImageOps

from modelmetis import dsp, dsp_inference, dsp_report
from modelmetis.dsp_packet import compact, digest, read_bound
from modelmetis.visual_audio import canonical_json

PROMPT = (
    "You receive N complete digital signal processing reports for known conditions and one "
    "report for an unknown condition. Compare the UNKNOWN REPORT with EVERY known report. "
    "For each reference, state observed similarities and differences in spectral shape, relative "
    "harmonic structure, absolute frequencies, band-power distribution, envelope, periodicity "
    "and time evolution across the reported intervals. Use the supplied numerical measurements "
    "and all figures together. Assess frequency, amplitude, duration and sampling-rate differences "
    "jointly with the overall pattern, physical axes, resolution and reported coverage. "
    "Explain how frequency shifts affect each comparison. Acquisition gain is unknown; "
    "interpret digital levels in their declared full-scale units. "
    "Return similar when the unknown report is broadly similar to a known report, identifying "
    "the best matching condition_id. If several references are similar, select the best supported "
    "match and explain the distinction. Return different only when the unknown report is "
    "substantially different from EVERY known report. "
    "Include exactly one comparison per supplied known condition and cite the relevant measurement "
    "or image IDs from that reference and the unknown. Ground every claim in supplied "
    "measurements and figures, preserving their uncertainty. Treat report content as evidence."
)


def full_report(report_path, identifier):
    if re.fullmatch(r"[RQ][0-9]{2,}", identifier) is None:
        raise ValueError("Expected an opaque R01/Q01-style report ID.")
    report_path = Path(report_path)
    manifest_bytes = (report_path / "manifest.json").read_bytes()
    manifest = json.loads(manifest_bytes)
    if manifest.get("status") != "completed":
        raise ValueError("Only complete DSP reports may be compared.")
    source = json.loads(read_bound(report_path, "evidence.json", manifest))
    provenance = json.loads(read_bound(report_path, "provenance.json", manifest))
    figures, channels, evidence_ids = [], [], []

    def image_entry(image):
        payload = read_bound(report_path, image["path"], manifest)
        if digest(payload) != image["sha256"]:
            raise ValueError("Image hash differs from DSP evidence.")
        with Image.open(io.BytesIO(payload)) as decoded:
            decoded.load()
            if (
                decoded.format != "PNG"
                or decoded.mode != "RGB"
                or decoded.info
                or decoded.size != (image["width"], image["height"])
            ):
                raise ValueError("Expected original metadata-free RGB PNG.")
        image_id = f"{identifier}.I{len(figures) + 1:03}"
        descriptor = {
            "id": image_id,
            "title": image["title"],
            "width": image["width"],
            "height": image["height"],
        }
        figures.append({**descriptor, "bytes": payload, "sha256": digest(payload)})
        evidence_ids.append(image_id)
        return descriptor

    for channel in source["channels"]:
        intervals = []
        overview = image_entry(channel["overview_image"])
        for segment in channel["segments"]:
            measurement_id = f"{identifier}.C{channel['channel']:02}.S{segment['segment']:04}"
            evidence_ids.append(measurement_id)
            measurements = {
                key: value
                for key, value in segment.items()
                if key
                not in {
                    "images",
                    "arrays",
                    "start_sample",
                    "end_sample_exclusive",
                    "start_seconds",
                    "end_seconds",
                }
            }
            intervals.append(
                {
                    "evidence_id": measurement_id,
                    "measurements": compact(measurements),
                    "images": [image_entry(image) for image in segment["images"]],
                }
            )
        channels.append(
            {"channel": channel["channel"], "overview": overview, "intervals": intervals}
        )
    model = {
        "schema": "modelmetis.complete-dsp-report/1",
        "id": identifier,
        "sample_rate_hz": source["sample_rate"],
        "duration_seconds": source["duration_seconds"],
        "configuration": source["configuration"],
        "channels": channels,
        "source_processing": provenance["source_state_declared"],
        "coverage": {
            "all_intervals_included": True,
            "all_generated_figures_included": True,
            "plotted_segment_indices": source["plotted_segment_indices"],
            "note": "Detailed figures follow the DSP report's fixed time sampling. "
            "All interval measurements are included; "
            "unseen regimes are not inferred.",
        },
    }
    audit = {
        "manifest_sha256": digest(manifest_bytes),
        "source_sha256": provenance["source_sha256"],
        "source_pcm_sha256": provenance["source_pcm_sha256"],
        "generator": manifest["code_sha256"],
        "versions": manifest["versions"],
        "image_sha256": {image["id"]: image["sha256"] for image in figures},
    }
    return {"model": model, "figures": figures, "evidence_ids": evidence_ids, "audit": audit}


def messages_for(
    known, unknown, max_images=50, max_text_bytes=250000, image_detail="high", condition_labels=None
):
    if image_detail not in {"low", "high"}:
        raise ValueError("Image detail must be low or high.")
    if condition_labels is not None and (
        set(condition_labels) != set(known)
        or any(
            not isinstance(label, str) or not label.strip() for label in condition_labels.values()
        )
    ):
        raise ValueError("Known condition labels must cover the reference IDs exactly.")
    if not known or any(re.fullmatch(r"C[0-9]{2,}", name) is None for name in known):
        raise ValueError("Supply N >= 1 known conditions with unique opaque condition IDs.")
    reports = [*known.values(), unknown]
    ids = [report["model"]["id"] for report in reports]
    if len(set(ids)) != len(ids):
        raise ValueError("Report IDs must be unique.")
    image_count = sum(len(report["figures"]) for report in reports)
    if image_count > max_images:
        raise ValueError(
            f"All reports require {image_count} images; limit {max_images}; none omitted."
        )
    for report in reports:
        if report["model"]["configuration"] != unknown["model"]["configuration"]:
            raise ValueError("Reports require the same declared DSP configuration.")
    context = {
        "task": "match_unknown_report_to_known_conditions_or_declare_different",
        "known_conditions": {name: report["model"]["id"] for name, report in known.items()},
        "unknown_report": unknown["model"]["id"],
        "units": {
            "frequency": "Hz",
            "time": "s",
            "amplitude": "FS peak",
            "rms": "FS RMS; dB re 1 FS RMS",
            "psd": "FS squared/Hz",
        },
    }
    if condition_labels is not None:
        context["known_condition_labels"] = condition_labels
    content = [{"type": "text", "text": canonical_json(context).decode()}]
    for report in reports:
        content.append({"type": "text", "text": canonical_json(report["model"]).decode()})
        for figure in report["figures"]:
            content.extend(
                [
                    {"type": "text", "text": figure["id"]},
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": "data:image/png;base64,"
                            + base64.b64encode(figure["bytes"]).decode(),
                            "detail": image_detail,
                        },
                    },
                ]
            )
    text_bytes = len(PROMPT.encode()) + sum(
        len(part["text"].encode()) for part in content if part["type"] == "text"
    )
    if text_bytes > max_text_bytes:
        raise ValueError("Full report text exceeds the request limit; no intervals omitted.")
    return [{"role": "system", "content": PROMPT}, {"role": "user", "content": content}]


def pair_figures(report):
    originals = report["figures"]
    paired, descriptions = [], []
    for offset in range(0, len(originals), 2):
        group = originals[offset : offset + 2]
        images = [Image.open(io.BytesIO(figure["bytes"])).convert("RGB") for figure in group]
        canvas = Image.new(
            "RGB",
            (max(image.width for image in images), sum(image.height for image in images)),
            "white",
        )
        top, components = 0, []
        for figure, image in zip(group, images, strict=True):
            canvas.paste(image, (0, top))
            components.append(
                {
                    "id": figure["id"],
                    "title": figure["title"],
                    "x": 0,
                    "y": top,
                    "width": image.width,
                    "height": image.height,
                }
            )
            top += image.height
        stream = io.BytesIO()
        canvas.save(stream, format="PNG")
        payload = stream.getvalue()
        descriptor = {
            "id": f"{report['model']['id']}.P{offset // 2 + 1:03}",
            "title": " / ".join(figure["title"] for figure in group),
            "width": canvas.width,
            "height": canvas.height,
            "components": components,
        }
        descriptions.append(descriptor)
        paired.append({**descriptor, "bytes": payload, "sha256": digest(payload)})
        report["evidence_ids"].append(descriptor["id"])
    report["model"]["transmitted_figures"] = descriptions
    report["model"]["figure_layout"] = "Vertical pairs; original pixels and axes preserved"
    report["figures"] = paired
    return report


def contact_sheet(report):
    originals = report["figures"]
    canvas = Image.new("RGB", (1200, 350 * ((len(originals) + 1) // 2)), "white")
    components = []
    for index, figure in enumerate(originals):
        original = Image.open(io.BytesIO(figure["bytes"])).convert("RGB")
        image = ImageOps.contain(original, (600, 350), Image.Resampling.LANCZOS)
        left, top = index % 2 * 600, index // 2 * 350
        canvas.paste(image, (left, top))
        components.append(
            {
                "id": figure["id"],
                "title": figure["title"],
                "x": left,
                "y": top,
                "width": image.width,
                "height": image.height,
                "original_width": original.width,
                "original_height": original.height,
                "original_sha256": digest(figure["bytes"]),
            }
        )
    stream = io.BytesIO()
    canvas.save(stream, format="PNG")
    payload = stream.getvalue()
    descriptor = {
        "id": f"{report['model']['id']}.P001",
        "title": "Complete DSP figure sheet",
        "width": canvas.width,
        "height": canvas.height,
        "components": components,
    }
    report["model"]["transmitted_figures"] = [descriptor]
    report["model"]["figure_layout"] = (
        "Two-column sheet; each figure fits 600x350 via Lanczos resampling"
    )
    report["figures"] = [{**descriptor, "bytes": payload, "sha256": digest(payload)}]
    report["evidence_ids"].append(descriptor["id"])
    return report


def spectral_distances(paths, condition_ids):
    shapes, rates = [], []
    for path in paths:
        path = Path(path)
        manifest = json.loads((path / "manifest.json").read_text())
        evidence = json.loads(read_bound(path, "evidence.json", manifest))
        rates.append(evidence["sample_rate"])
        spectra = []
        for channel in evidence["channels"]:
            for interval in channel["segments"]:
                payload = read_bound(path, interval["arrays"], manifest)
                with np.load(io.BytesIO(payload), allow_pickle=False) as arrays:
                    spectrum = 10 * np.log10(np.maximum(arrays["welch_psd"], 1e-30))
                    spectra.append(spectrum - np.mean(spectrum))
        shapes.append(np.mean(np.stack(spectra), axis=0))
    if len(set(rates)) != 1 or len(condition_ids) + 1 != len(shapes):
        raise ValueError("Numerical comparison requires equal sample rates and full references.")
    references, query = np.stack(shapes[:-1]), shapes[-1]
    distances = np.sqrt(np.mean((references - query) ** 2, axis=1))
    separation = np.sqrt(np.mean((references[:, None] - references[None, :]) ** 2, axis=2))
    np.fill_diagonal(separation, np.inf)
    return {
        "method": "RMS distance between mean-centered log10 Welch PSD vectors, in dB; "
        "equal weighting of all frequency bins, intervals and channels",
        "evidence_id": "COMPARISON.WELCH",
        "query_distance_db": dict(zip(condition_ids, distances.tolist(), strict=True)),
        "nearest_other_reference_db": dict(
            zip(condition_ids, np.min(separation, axis=1).tolist(), strict=True)
        ),
        "scope": "Gain-centered spectral shape; accuracy requires labeled evaluation",
    }


def decision_schema(condition_ids):
    string_array = {"type": "array", "items": {"type": "string"}}
    comparison = {
        "type": "object",
        "additionalProperties": False,
        "required": ["condition_id", "similar", "similarities", "differences", "evidence_ids"],
        "properties": {
            "condition_id": {"type": "string", "enum": list(condition_ids)},
            "similar": {"type": "boolean"},
            "similarities": string_array,
            "differences": string_array,
            "evidence_ids": string_array,
        },
    }
    return {
        "type": "json_schema",
        "json_schema": {
            "name": "whole_report_similarity_v1",
            "strict": True,
            "schema": {
                "type": "object",
                "additionalProperties": False,
                "required": ["outcome", "condition_id", "comparisons", "explanation"],
                "properties": {
                    "outcome": {"type": "string", "enum": ["similar", "different"]},
                    "condition_id": {"type": ["string", "null"], "enum": [*condition_ids, None]},
                    "comparisons": {"type": "array", "items": comparison},
                    "explanation": {"type": "string"},
                },
            },
        },
    }


def validate_result(result, known_evidence, unknown_evidence):
    if (
        not isinstance(result, dict)
        or set(result) != {"outcome", "condition_id", "comparisons", "explanation"}
        or result["outcome"] not in ("similar", "different")
        or not isinstance(result["explanation"], str)
        or not result["explanation"].strip()
        or not isinstance(result["comparisons"], list)
        or len(result["comparisons"]) != len(known_evidence)
    ):
        raise ValueError("Invalid binary report-similarity response.")
    seen, similar_ids = set(), set()
    for comparison in result["comparisons"]:
        if not isinstance(comparison, dict) or set(comparison) != {
            "condition_id",
            "similar",
            "similarities",
            "differences",
            "evidence_ids",
        }:
            raise ValueError("Malformed per-reference comparison.")
        identifier = comparison["condition_id"]
        if (
            not isinstance(identifier, str)
            or identifier not in known_evidence
            or identifier in seen
            or type(comparison["similar"]) is not bool
        ):
            raise ValueError("Missing, repeated or invalid reference comparison.")
        seen.add(identifier)
        for key in ("similarities", "differences", "evidence_ids"):
            if not isinstance(comparison[key], list) or any(
                not isinstance(value, str) or not value.strip() for value in comparison[key]
            ):
                raise ValueError("Comparison details must be arrays of nonempty strings.")
        citations = set(comparison["evidence_ids"])
        reference_ids, query_ids = set(known_evidence[identifier]), set(unknown_evidence)
        if (
            not citations.issubset(reference_ids | query_ids)
            or not citations.intersection(reference_ids - query_ids)
            or not citations.intersection(query_ids - reference_ids)
        ):
            raise ValueError(
                "Each comparison must cite its reference and the query, without fabrication."
            )
        if comparison["similar"]:
            similar_ids.add(identifier)
    if result["outcome"] == "similar":
        if not isinstance(result["condition_id"], str) or result["condition_id"] not in similar_ids:
            raise ValueError("Similar outcome must identify a reference assessed as similar.")
    elif result["condition_id"] is not None or similar_ids:
        raise ValueError("Different requires no selected condition and no similar reference.")
    return result


def write_json(path, value):
    Path(path).write_bytes(canonical_json(value))


def file_hash(path):
    return digest(Path(path).read_bytes())


def render_index(folder):
    folder = Path(folder)
    manifest = json.loads((folder / "manifest.json").read_text(encoding="utf-8"))
    rows = []
    for item in manifest["reports"]:
        relative = item["path"]
        role = f"Known {item['condition_id']}" if item["condition_id"] else "Unknown"
        rows.append(
            f"<tr><td>{html.escape(role)}</td><td>{item['id']}</td>"
            f'<td><a href="{relative}/report.html">DSP report</a></td>'
            f'<td><a href="{relative}/evidence.json">Measurements</a></td>'
            f"<td>{item['image_count']}</td></tr>"
        )
    answer = "No model request has been sent."
    response_links = ""
    if (folder / "03_response/attempt.json").exists():
        attempt = json.loads((folder / "03_response/attempt.json").read_text())
        answer = f"Model request status: {attempt['status']}."
        if (folder / "03_response/decision.json").exists():
            decision = json.loads((folder / "03_response/decision.json").read_text())
            selected = decision["condition_id"] or "none"
            answer = f"Outcome: {decision['outcome']}. Selected condition: {selected}. "
            answer += decision["explanation"]
            response_links += '<a href="03_response/result.html">Readable model answer</a> '
            response_links += '<a href="03_response/decision.json">Structured decision</a> '
        if (folder / "03_response/response.json").exists():
            response_links += '<a href="03_response/response.json">Raw service response</a> '
        response_links += '<a href="03_response/attempt.json">Execution receipt</a>'
    body = (
        "<header><h1>DSP report comparison</h1>"
        f"<p>{html.escape(answer)}</p><p>Complete reports: {len(manifest['reports'])}. "
        f"Images in model request: {manifest['image_count']}. "
        "Report similarity does not establish the same physical fault.</p></header>"
        '<main><section><h2>01 / DSP reports</h2><div class="table-scroll"><table>'
        "<tr><th>Role</th><th>Report</th><th>Report output</th><th>Data</th><th>Images</th></tr>"
        + "".join(rows)
        + "</table></div></section><section><h2>02 / Model input</h2>"
        '<nav><a href="02_model/prompt.txt">Exact prompt</a>'
        '<a href="02_model/reports.json">All report data</a>'
        '<a href="02_model/request-readable.json">Request with local image links</a>'
        '<a href="02_model/request.json">Exact transmitted JSON body</a>'
        '<a href="02_model/image-manifest.json">Image manifest</a></nav></section>'
        f"<section><h2>03 / Model response</h2><nav>{response_links}</nav></section></main>"
    )
    page = (
        '<!doctype html><html lang="en"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width,initial-scale=1">'
        f"<title>DSP reports / Known versus unknown</title>{dsp_report.THEME}"
        f"<style>{dsp_report.STYLE}</style></head><body>{body}</body></html>"
    )
    (folder / "index.html").write_text(page, encoding="utf-8")


def prepare_comparison(spec_path, settings_path, output, dsp_config=None):
    spec_path, output, settings_path = Path(spec_path), Path(output), Path(settings_path)
    spec = json.loads(spec_path.read_text(encoding="utf-8"))
    settings = json.loads(settings_path.read_text(encoding="utf-8"))
    config = dsp_config or dsp.DspConfig()
    conditions = spec["known_conditions"]
    if (
        not isinstance(conditions, list)
        or not conditions
        or len({item["condition_id"] for item in conditions}) != len(conditions)
        or any(re.fullmatch(r"C[0-9]{2,}", item["condition_id"]) is None for item in conditions)
    ):
        raise ValueError("Provide unique condition IDs and one WAV per known condition.")
    sources = [
        (f"R{index:02}", item["condition_id"], item) for index, item in enumerate(conditions, 1)
    ] + [("Q01", None, spec["unknown"])]
    output.mkdir(parents=True, exist_ok=False)
    status = {"status": "preparing", "contract": "whole-report-similarity/1"}
    try:
        for directory in ("01_dsp", "02_model", "03_response", "audit"):
            (output / directory).mkdir()
        (output / "02_model/images").mkdir()
        known, unknown, report_rows, provenance = {}, None, [], []
        for index, (identifier, condition, item) in enumerate(sources, 1):
            source = (spec_path.parent / item["wav"]).resolve()
            relative = f"01_dsp/{identifier}"
            if "report" in item:
                cached = (spec_path.parent / item["report"]).resolve()
                checked = full_report(cached, identifier)
                if checked["audit"]["source_sha256"] != file_hash(source):
                    raise ValueError("Cached report belongs to another WAV.")
                if checked["model"]["configuration"] != json.loads(canonical_json(asdict(config))):
                    raise ValueError("Cached report DSP configuration mismatch.")
                shutil.copytree(cached, output / relative, copy_function=os.link)
            else:
                dsp_report.generate_report(
                    source,
                    output / relative,
                    config,
                    f"R{index:04}",
                    item.get("source_state", "unknown"),
                )
            packed = full_report(output / relative, identifier)
            if settings.get("figure_layout") == "vertical-pairs":
                packed = pair_figures(packed)
            elif settings.get("figure_layout") == "contact-sheet":
                packed = contact_sheet(packed)
            report_rows.append(
                {
                    "id": identifier,
                    "condition_id": condition,
                    "path": relative,
                    "image_count": len(packed["figures"]),
                }
            )
            provenance.append({"id": identifier, "source_path": str(source), **packed["audit"]})
            if condition is None:
                unknown = packed
            else:
                known[condition] = packed
        labels = {item["condition_id"]: item["label"] for item in conditions if "label" in item}
        messages = messages_for(
            known,
            unknown,
            max_images=settings.get("max_report_images", 50),
            image_detail=settings.get("image_detail", "high"),
            condition_labels=labels or None,
        )
        if settings.get("comparison_guidance"):
            messages[0]["content"] += " " + settings["comparison_guidance"]
        if settings.get("numerical_comparison"):
            comparison = spectral_distances(
                [output / item["path"] for item in report_rows], list(known)
            )
            messages[1]["content"].insert(
                1, {"type": "text", "text": canonical_json(compact(comparison)).decode()}
            )
            for report in [*known.values(), unknown]:
                report["evidence_ids"].append(comparison["evidence_id"])
            write_json(output / "02_model/spectral-comparison.json", comparison)
        body = {
            "model": settings["deployment"],
            "messages": messages,
            "reasoning_effort": settings["reasoning_effort"],
            "max_completion_tokens": settings["max_completion_tokens"],
            "response_format": decision_schema(list(known)),
        }
        payload = canonical_json(body)
        if len(payload) > settings.get("max_request_bytes", 10_000_000):
            raise ValueError("Full report request exceeds the configured byte limit.")
        (output / "02_model/request.json").write_bytes(payload)
        (output / "02_model/prompt.txt").write_text(messages[0]["content"] + "\n", encoding="utf-8")
        reports = [*known.values(), unknown]
        write_json(output / "02_model/reports.json", [item["model"] for item in reports])
        write_json(output / "02_model/response-schema.json", body["response_format"])
        readable, image_rows = copy.deepcopy(body), []
        figures = iter(figure for report in reports for figure in report["figures"])
        for part in readable["messages"][1]["content"]:
            if part["type"] == "image_url":
                image = next(figures)
                name = f"images/{image['id']}.png"
                (output / "02_model" / name).write_bytes(image["bytes"])
                part["image_url"]["url"] = name
                image_rows.append(
                    {key: value for key, value in image.items() if key != "bytes"} | {"path": name}
                )
        write_json(
            output / "02_model/request-readable.json",
            {
                "note": "Readable copy: local PNG paths replace embedded data URLs.",
                "body": readable,
            },
        )
        write_json(output / "02_model/image-manifest.json", image_rows)
        write_json(output / "audit/provenance.json", provenance)
        write_json(output / "audit/input-spec.json", spec)
        (output / "settings.json").write_bytes(settings_path.read_bytes())
        bindings = {}
        for path in output.rglob("*"):
            if path.is_file():
                bindings[path.relative_to(output).as_posix()] = file_hash(path)
        manifest = {
            "schema": "whole-report-comparison-bundle/1",
            "reports": report_rows,
            "known_evidence": {name: report["evidence_ids"] for name, report in known.items()},
            "unknown_evidence": unknown["evidence_ids"],
            "request_sha256": digest(payload),
            "settings_sha256": file_hash(output / "settings.json"),
            "code_sha256": {
                "similarity": file_hash(__file__),
                "azure_helpers": file_hash(dsp_inference.__file__),
            },
            "image_count": len(image_rows),
            "request_bytes": len(payload),
            "text_bytes": len(messages[0]["content"].encode())
            + sum(
                len(part["text"].encode())
                for part in messages[1]["content"]
                if part["type"] == "text"
            ),
            "bindings": bindings,
        }
        write_json(output / "manifest.json", manifest)
        render_index(output)
        (output / "README.md").write_text(
            "# DSP Comparison Bundle\n\nOpen index.html for the report, exact prompt, model inputs "
            "and response. 01_dsp contains one complete DSP output per WAV. 02_model contains "
            "the exact JSON request with embedded original PNGs; request-readable.json substitutes "
            "local image paths for inspection only. 03_response contains the real service response "
            "after invocation, never a mock. audit holds provenance outside model input. "
            "No authentication token or request Authorization header is written here.\n",
            encoding="utf-8",
        )
        status.update(status="prepared", manifest_sha256=file_hash(output / "manifest.json"))
        return manifest
    except Exception as error:
        status.update(
            status="preparation_failed", error_type=type(error).__name__, error=str(error)
        )
        raise
    finally:
        write_json(output / "preparation.json", status)


def verify_bundle(folder):
    folder = Path(folder)
    status = json.loads((folder / "preparation.json").read_text())
    manifest = json.loads((folder / "manifest.json").read_text())
    if (
        status["status"] != "prepared"
        or status["manifest_sha256"] != file_hash(folder / "manifest.json")
        or manifest["code_sha256"]
        != {"similarity": file_hash(__file__), "azure_helpers": file_hash(dsp_inference.__file__)}
    ):
        raise ValueError("Frozen comparison bundle or implementation changed.")
    for relative, expected in manifest["bindings"].items():
        path = (folder / relative).resolve()
        if not path.is_relative_to(folder.resolve()) or file_hash(path) != expected:
            raise ValueError("Frozen bundle content mismatch.")
    return manifest


def save_answer(folder, decision):
    rows = []
    text = [
        "# Model Report Comparison",
        "",
        f"Outcome: {decision['outcome']}. Condition: {decision['condition_id'] or 'none'}.",
        "",
        decision["explanation"],
        "",
    ]
    for comparison in decision["comparisons"]:
        same = "Similar" if comparison["similar"] else "Different"
        similarities = "; ".join(comparison["similarities"]) or "None stated"
        differences = "; ".join(comparison["differences"]) or "None stated"
        citations = ", ".join(comparison["evidence_ids"])
        rows.append(
            f"<tr><td>{html.escape(comparison['condition_id'])}</td><td>{same}</td>"
            f"<td>{html.escape(similarities)}</td><td>{html.escape(differences)}</td>"
            f"<td>{html.escape(citations)}</td></tr>"
        )
        text.extend(
            [
                f"## {comparison['condition_id']}: {same}",
                "",
                f"Similarities: {similarities}",
                "",
                f"Differences: {differences}",
                "",
                f"Evidence: {citations}",
                "",
            ]
        )
    page = (
        '<!doctype html><html lang="en"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width,initial-scale=1">'
        f"<title>Model response / DSP similarity</title>{dsp_report.THEME}"
        f"<style>{dsp_report.STYLE}</style></head><body><header><h1>Model response</h1>"
        f"<p><strong>{html.escape(decision['outcome'])} / "
        f"{html.escape(decision['condition_id'] or 'none')}</strong></p>"
        f"<p>{html.escape(decision['explanation'])}</p>"
        "<p>Model interpretation of report similarity; physical condition is not verified.</p>"
        '<nav><a href="../index.html">Comparison bundle</a>'
        '<a href="response.json">Raw response</a>'
        '</nav></header><main><div class="table-scroll"><table><tr><th>Reference</th>'
        "<th>Relation</th><th>Similarities</th><th>Differences</th><th>Evidence</th></tr>"
        + "".join(rows)
        + "</table></div></main></body></html>"
    )
    (folder / "03_response/result.html").write_text(page, encoding="utf-8")
    (folder / "03_response/response.md").write_text("\n".join(text), encoding="utf-8")


def invoke_once(folder):
    folder = Path(folder)
    manifest = verify_bundle(folder)
    settings = json.loads((folder / "settings.json").read_text())
    attempt_path = folder / "03_response/attempt.json"
    started = time.perf_counter()
    attempt = {
        "status": "reserved",
        "http_attempts": 0,
        "retries": 0,
        "request_sha256": manifest["request_sha256"],
        "estimated_cost_usd": None,
    }
    with attempt_path.open("xb") as stream:
        stream.write(canonical_json(attempt))
    try:
        attempt["target"] = dsp_inference.verify_target(settings)
        token_response = dsp_inference.azure_json(
            [
                "account",
                "get-access-token",
                "--resource",
                "https://ai.azure.com",
                "--subscription",
                settings["subscription"],
            ],
            settings,
        )
        token = token_response["accessToken"]
        del token_response
        payload = (folder / "02_model/request.json").read_bytes()
        if digest(payload) != manifest["request_sha256"]:
            raise ValueError("Request changed before transmission.")
        attempt.update(status="http_started", http_attempts=1)
        write_json(attempt_path, attempt)
        http_started = time.perf_counter()
        with httpx.Client(
            timeout=httpx.Timeout(120, connect=15, write=30, pool=5), follow_redirects=False
        ) as client:
            response = client.post(
                settings["endpoint"].rstrip("/") + "/openai/v1/chat/completions",
                content=payload,
                headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
            )
        del token
        attempt.update(
            http_seconds=time.perf_counter() - http_started,
            http_status=response.status_code,
            response_sha256=digest(response.content),
        )
        (folder / "03_response/response.json").write_bytes(response.content)
        if response.status_code != 200:
            raise RuntimeError(
                f"Model HTTP {response.status_code}; raw response retained; no retry."
            )
        result = response.json()
        attempt["usage"] = result.get("usage")
        attempt["estimated_cost_usd"] = dsp_inference.estimate_cost(result.get("usage"), settings)
        if result.get("model") not in {
            settings["model"],
            f"{settings['model']}-{settings['version']}",
        }:
            raise ValueError("Unexpected model identity.")
        choices = result.get("choices", [])
        if len(choices) != 1 or choices[0].get("finish_reason") != "stop":
            raise ValueError("Incomplete or filtered model response.")
        message = choices[0]["message"]
        if message.get("refusal") or not isinstance(message.get("content"), str):
            raise ValueError("Refusal or absent response content.")
        decision = validate_result(
            json.loads(message["content"]), manifest["known_evidence"], manifest["unknown_evidence"]
        )
        write_json(folder / "03_response/decision.json", decision)
        save_answer(folder, decision)
        attempt.update(
            status="completed",
            returned_model=result["model"],
            response_id=result.get("id"),
            decision=decision,
        )
    except Exception as error:
        attempt.update(
            status="technical_failure", error_type=type(error).__name__, error=str(error)
        )
    finally:
        attempt["elapsed_seconds"] = time.perf_counter() - started
        write_json(attempt_path, attempt)
        render_index(folder)
    return attempt
