import argparse
import json
import shutil
import subprocess
import sys
import time
from pathlib import Path

import httpx
import numpy as np

from modelmetis import dsp_inference, dsp_similarity
from modelmetis.dsp_guide import VIEW_GUIDE, interpretation_prompt
from modelmetis.dsp_packet import compact
from modelmetis.dsp_report import digest
from modelmetis.dsp_similarity import decision_schema, full_report, validate_result
from modelmetis.visual_audio import canonical_json
from scripts.audio_comparison import ROOT, data_url
from scripts.dsp_extended_experiment import read_json, write_json


def numerical_metadata(value):
    if isinstance(value, dict):
        return {key: numerical_metadata(item) for key, item in value.items()
                if not isinstance(item, str) or key in {"status", "reason", "evidence_id"}}
    if isinstance(value, list):
        return [numerical_metadata(item) for item in value]
    return value


def summarize_view(view):
    result = {
        key: view[key]
        for key in (
            "status",
            "reason",
            "title",
            "kind",
            "x_label",
            "y_label",
            "value_label",
            "metrics",
        )
        if key in view
    }
    if view["status"] != "available":
        return result
    if view["kind"] == "line":
        result["series_summary"] = {}
        for name, values in view["series"].items():
            array = np.asarray(values, dtype=float)
            positions = np.argsort(array)[-6:][::-1]
            result["series_summary"][name] = {
                "min": float(array.min()),
                "median": float(np.median(array)),
                "max": float(array.max()),
                "samples": len(array),
                "largest_bins": [
                    [view["x"][int(index)], float(array[index])] for index in positions
                ],
            }
    else:
        array = np.asarray(view["values"], dtype=float)
        valid = np.isfinite(array)
        if valid.any():
            result["map_summary"] = {
                "min": float(array[valid].min()),
                "median": float(np.median(array[valid])),
                "max": float(array[valid].max()),
                "valid_cells": int(valid.sum()),
                "total_cells": array.size,
            }
    return compact(numerical_metadata(result))


def model_record(record, source_folder, extended_root, dataset_name, is_query=False):
    identifier = "Q01" if is_query else record["id"]
    original = full_report(source_folder / "reports" / record["id"], identifier)
    evidence = read_json(extended_root / dataset_name / record["id"] / "evidence.json")
    summaries = {
        key: {"evidence_id": record["id"] + "." + key, **summarize_view(view)}
        for key, view in evidence["views"].items()
    }
    identifiers = [*original["evidence_ids"], *[record["id"] + "." + key for key in VIEW_GUIDE]]
    original_summary = {key: original["model"][key] for key in (
        "id", "sample_rate_hz", "duration_seconds", "source_processing")}
    original_summary["channels"] = [{"channel": channel["channel"], "intervals": [
        {"evidence_id": interval["evidence_id"],
         "measurements": numerical_metadata(interval["measurements"])}
        for interval in channel["intervals"]]} for channel in original["model"]["channels"]]
    text = {
        "report": original_summary,
        "extension_configuration": evidence["config"],
        "extensions": summaries,
        "numerical_summary": "All view metadata and original interval measurements; "
        "new curves summarized by extrema/largest bins; full arrays retained locally.",
        "figure_prefix": record["id"],
    }
    return {"text": text, "evidence_ids": identifiers, "sheets": record["sheets"]}


def build_body(known, unknown, labels, settings):
    prompt = interpretation_prompt() + (
        "\nEXPERIMENT RESPONSE CONTRACT: Return similar and its condition_id when one or more "
        "known conditions are supported, choosing the best supported. Return different with "
        "null condition_id when all known conditions are substantially different. Include "
        "exactly one comparison for each supplied condition and cite both its reference "
        "and the query. Explain uncertainty and conflicting diagnostics. Use concise prose. "
        "No calibrated distance threshold is supplied. This is an exploratory binary judgment."
    )
    parts = [
        {
            "type": "text",
            "text": canonical_json(
                {
                    "known_condition_labels": labels,
                    "references": {
                        key: value["text"]["report"]["id"] for key, value in known.items()
                    },
                    "query": unknown["text"]["report"]["id"],
                }
            ).decode(),
        }
    ]
    if "comparison_distances" in unknown:
        visible = {value["text"]["report"]["id"] for value in known.values()}
        parts.append(
            {
                "type": "text",
                "text": canonical_json(
                    {
                        "numerical_control": {
                            name: {key: value for key, value in distances.items() if key in visible}
                            if distances
                            else None
                            for name, distances in unknown["comparison_distances"].items()
                        },
                        "method": "baseline: mean-centered full-band log Welch RMS distance in dB; "
                        "other views: raw RMS distance between declared descriptive signatures; "
                        "different units/scales, no thresholds; compare only within each view",
                    }
                ).decode(),
            }
        )
    count = 0
    for report in [*known.values(), unknown]:
        parts.append({"type": "text", "text": canonical_json(report["text"]).decode()})
        for sheet in report["sheets"]:
            payload = Path(sheet["path"]).read_bytes()
            if digest(sheet["path"]) != sheet["sha256"]:
                raise ValueError("Contact sheet changed after offline preparation.")
            parts.append(
                {
                    "type": "text",
                    "text": canonical_json(
                        {
                            "cell_evidence_ids_row_major": [cell["id"] for cell in sheet["cells"]],
                            "transform": sheet["transform"],
                            "size": sheet["size"],
                        }
                    ).decode(),
                }
            )
            parts.append(
                {
                    "type": "image_url",
                    "image_url": {"url": data_url(payload, "image/png"), "detail": "high"},
                }
            )
            count += 1
    if count > 50:
        raise ValueError("Image admission limit exceeded; no view may be silently omitted.")
    body = {
        "model": settings["deployment"],
        "max_completion_tokens": settings["max_completion_tokens"],
        "reasoning_effort": settings["reasoning_effort"],
        "messages": [{"role": "system", "content": prompt}, {"role": "user", "content": parts}],
        "response_format": decision_schema(known),
    }
    if len(canonical_json(body)) > 64_000_000:
        raise ValueError("Request byte limit exceeded.")
    return body, count


def prepare(source, output, settings_path, resume_source=None):
    source, output = Path(source), Path(output)
    manifest = read_json(source / "manifest.json")
    for name, expected in manifest["files"].items():
        if digest(source / name) != expected:
            raise ValueError("Offline preparation hash mismatch.")
    output.mkdir(parents=True, exist_ok=False)
    settings = read_json(settings_path)
    settings["max_completion_tokens"] = 8192
    settings["request_process_timeout_seconds"] = 240
    settings["expected_capacity"] = 100
    write_json(output / "settings.json", settings)
    code = {
        Path(module.__file__).relative_to(ROOT).as_posix(): digest(module.__file__)
        for module in (dsp_inference, dsp_similarity)
    }
    code["scripts/dsp_extended_ai.py"] = digest(__file__)
    cases, expected_answers, sizes = [], {}, []
    for dataset_name, folder_name in (("Jin", "dsp-jin-v1"), ("Ottawa", "dsp-ottawa-v2")):
        dataset = read_json(source / dataset_name / "dataset.json")
        numerical = read_json(source / dataset_name / "predictions.json")
        folder = ROOT / "outputs" / folder_name
        protocol = read_json(folder / "protocol.json")
        candidates = [
            item
            for item in protocol["queries"]
            if item["load"] == 0
            and item["role"] == ("final" if dataset_name == "Jin" else "development")
        ]
        available = {item["id"]: item for item in dataset["queries"]}
        references = {
            item["condition"]: model_record(item, folder, source, dataset_name)
            for item in dataset["references"]
        }
        labels = {item["condition"]: item["label"] for item in dataset["references"]}
        for candidate in candidates:
            query = available[candidate["id"]]
            unknown = model_record(query, folder, source, dataset_name, is_query=True)
            unknown["comparison_distances"] = {
                row["representation"]: row["distances"]
                for row in numerical
                if row["query_id"] == query["id"]
            }
            for phase in ("known", "excluded"):
                name = f"{dataset_name}-{phase}-{query['id']}"
                selected = {
                    key: value
                    for key, value in references.items()
                    if phase == "known" or key != query["truth"]
                }
                body, count = build_body(
                    selected, unknown, {key: labels[key] for key in selected}, settings
                )
                case = output / name
                case.mkdir()
                write_json(case / "request.json", body)
                write_json(
                    case / "contract.json",
                    {
                        "known_evidence": {
                            key: value["evidence_ids"] for key, value in selected.items()
                        },
                        "unknown_evidence": unknown["evidence_ids"],
                    },
                )
                cases.append(
                    {
                        "name": name,
                        "dataset": dataset_name,
                        "phase": phase,
                        "query_id": query["id"],
                        "request_sha256": digest(case / "request.json"),
                        "contract_sha256": digest(case / "contract.json"),
                    }
                )
                expected_answers[name] = query["truth"] if phase == "known" else "different"
                sizes.append(
                    {
                        "case": name,
                        "images": count,
                        "bytes": (case / "request.json").stat().st_size,
                        "text_bytes": len(body["messages"][0]["content"].encode())
                        + sum(
                            len(part["text"].encode())
                            for part in body["messages"][1]["content"]
                            if part["type"] == "text"
                        ),
                    }
                )
    if len(cases) != 24:
        raise ValueError("Expected twelve paired known/excluded trials.")
    (output / "sealed").mkdir()
    write_json(output / "sealed/truth.json", expected_answers)
    reused = []
    if resume_source is not None:
        resume_source = Path(resume_source)
        prior = read_json(resume_source / "registration.json")
        prior_cases = {item["name"]: item for item in prior["cases"]}
        for case in cases:
            prior_path = resume_source / case["name"] / "attempt.json"
            if not prior_path.exists() or read_json(prior_path)["status"] != "completed":
                continue
            if (prior_cases[case["name"]]["request_sha256"] != case["request_sha256"]
                    or digest(resume_source / case["name"] / "request.json")
                    != case["request_sha256"]):
                raise ValueError("A reused decision requires an identical registered request.")
            for filename in ("attempt.json", "response.json"):
                shutil.copyfile(resume_source / case["name"] / filename,
                                output / case["name"] / filename)
            reused.append({
                "case": case["name"], "attempt_sha256": digest(prior_path),
                "source_registration_sha256": digest(resume_source / "registration.json")})
    write_json(
        output / "registration.json",
        {
            "schema": 1,
            "cases": cases,
            "max_attempts": 24,
            "spending_cap_usd": None,
            "authorization": "User explicitly requests experiments without spending limit",
            "code_sha256": code,
            "settings_sha256": digest(output / "settings.json"),
            "truth_sha256": digest(output / "sealed/truth.json"),
            "source_manifest_sha256": digest(source / "manifest.json"),
            "scope": "consumed_acquisitions_exploratory; paired reference removal only",
            "stop_rule": "Stop on technical failure; no automatic retries or prompt tuning",
            "request_byte_admission_limit": 64000000,
            "sizes": sizes,
            "reused_completed_attempts": reused,
            "capacity_change": "50 to 100 kTPM; same model/version/SKU and same request bytes",
        },
    )
    return sizes


def verify(output):
    output = Path(output)
    registration = read_json(output / "registration.json")
    for name, expected in registration["code_sha256"].items():
        if digest(ROOT / name) != expected:
            raise ValueError("Frozen inference implementation changed.")
    if digest(output / "settings.json") != registration["settings_sha256"]:
        raise ValueError("Frozen inference settings changed.")
    for case in registration["cases"]:
        for filename, field in (
            ("request.json", "request_sha256"),
            ("contract.json", "contract_sha256"),
        ):
            if digest(output / case["name"] / filename) != case[field]:
                raise ValueError("Frozen inference input changed.")
    return registration


def execute_one(output, case_name, client_factory=httpx.Client):
    output = Path(output)
    registration = verify(output)
    if case_name not in {case["name"] for case in registration["cases"]}:
        raise ValueError("Unregistered case.")
    case = output / case_name
    attempt_path = case / "attempt.json"
    with attempt_path.open("xb") as stream:
        stream.write(canonical_json({"status": "reserved", "http_attempts": 0}))
    settings = read_json(output / "settings.json")
    contract = read_json(case / "contract.json")
    receipt = {"status": "reserved", "http_attempts": 0, "estimated_cost_usd": None}
    started = time.perf_counter()
    try:
        receipt["target"] = dsp_inference.verify_target(settings)
        expected_capacity = settings.get("expected_capacity")
        if (expected_capacity is not None
            and receipt["target"]["sku"]["capacity"] != expected_capacity):
            raise ValueError("Deployment capacity differs from this campaign registration.")
        token = dsp_inference.azure_json(
            [
                "account",
                "get-access-token",
                "--resource",
                "https://ai.azure.com",
                "--subscription",
                settings["subscription"],
            ],
            settings,
        )["accessToken"]
        payload = (case / "request.json").read_bytes()
        receipt.update(status="http_started", http_attempts=1, request_sha256=hashlib_sha(payload))
        write_json(attempt_path, receipt)
        with client_factory(
            timeout=httpx.Timeout(180, connect=15, write=30, pool=5), follow_redirects=False
        ) as client:
            response = client.post(
                settings["endpoint"].rstrip("/") + "/openai/v1/chat/completions",
                content=payload,
                headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
            )
        del token
        (case / "response.json").write_bytes(response.content)
        receipt.update(
            http_status=response.status_code, response_sha256=hashlib_sha(response.content)
        )
        if response.status_code != 200:
            raise ValueError(f"HTTP {response.status_code}; response retained.")
        result = response.json()
        receipt["usage"] = result.get("usage")
        try:
            receipt["estimated_cost_usd"] = dsp_inference.estimate_cost(
                result.get("usage"), settings)
        except ValueError as error:
            receipt["cost_unestablished_reason"] = str(error)
        if result.get("model") not in {
            settings["model"],
            settings["model"] + "-" + settings["version"],
        }:
            raise ValueError("Returned model identity mismatch.")
        choices = result.get("choices", [])
        if len(choices) != 1 or choices[0].get("finish_reason") != "stop":
            raise ValueError("Incomplete model completion.")
        message = choices[0]["message"]
        if message.get("refusal"):
            raise ValueError("Model refusal.")
        decision = validate_result(
            json.loads(message["content"]), contract["known_evidence"], contract["unknown_evidence"]
        )
        receipt.update(status="completed", decision=decision, returned_model=result["model"])
    except Exception as error:
        receipt.update(
            status="technical_failure", error_type=type(error).__name__, error=str(error)
        )
    finally:
        receipt["elapsed_seconds"] = time.perf_counter() - started
        write_json(attempt_path, receipt)
    return receipt


def hashlib_sha(payload):
    import hashlib

    return hashlib.sha256(payload).hexdigest()


def run(output, limit):
    output = Path(output)
    registration = verify(output)
    attempted = 0
    for case in registration["cases"]:
        path = output / case["name"] / "attempt.json"
        if path.exists():
            if read_json(path)["status"] != "completed":
                raise ValueError("An earlier unresolved technical attempt blocks continuation.")
            continue
        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "scripts.dsp_extended_ai",
                "one",
                "--output",
                str(output),
                "--case",
                case["name"],
            ],
            timeout=240,
            check=False,
            capture_output=True,
            text=True,
        )
        receipt = read_json(path) if path.exists() else {"status": "worker_failed"}
        print(
            json.dumps(
                {
                    "case": case["name"],
                    "status": receipt["status"],
                    "decision": receipt.get("decision", {}).get("outcome"),
                    "cost": receipt.get("estimated_cost_usd"),
                }
            ),
            flush=True,
        )
        if result.returncode or receipt["status"] != "completed":
            raise RuntimeError("Technical failure retained; campaign stopped.")
        attempted += 1
        if attempted >= limit:
            break


def evaluate(output):
    output = Path(output)
    registration = verify(output)
    if digest(output / "sealed/truth.json") != registration["truth_sha256"]:
        raise ValueError("Evaluator truth changed.")
    truth = read_json(output / "sealed/truth.json")
    rows = []
    for case in registration["cases"]:
        path = output / case["name"] / "attempt.json"
        if not path.exists():
            continue
        receipt = read_json(path)
        row = {
            **case,
            "expected": truth[case["name"]],
            "status": receipt["status"],
            "cost_usd": receipt.get("estimated_cost_usd"),
            "outcome": "technical_failure",
        }
        if receipt["status"] == "completed":
            decision = receipt["decision"]
            predicted = (
                decision["condition_id"] if decision["outcome"] == "similar" else "different"
            )
            row["predicted"] = predicted
            row["outcome"] = (
                "correct_known"
                if predicted == row["expected"]
                else "false_rejection"
                if predicted == "different"
                else "wrong_class"
            )
            if case["phase"] == "excluded":
                row["outcome"] = (
                    "correct_rejection" if predicted == "different" else "wrong_acceptance"
                )
        rows.append(row)
    write_json(
        output / "evaluation.json",
        {
            "rows": rows,
            "registered_trials": len(truth),
            "attempted_trials": len(rows),
            "known_cost_usd": sum(row["cost_usd"] or 0 for row in rows),
            "unknown_cost_attempts": sum(row["cost_usd"] is None for row in rows),
        },
    )
    return rows


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Registered all-view AI experiment.")
    parser.add_argument("action", choices=("prepare", "run", "one", "evaluate"))
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--source", type=Path)
    parser.add_argument("--resume-source", type=Path)
    parser.add_argument("--settings", type=Path, default=Path("configs/dsp-sol-reuse-v1.json"))
    parser.add_argument("--case")
    parser.add_argument("--limit", type=int, default=24)
    args = parser.parse_args()
    if args.action == "prepare":
        try:
            print(json.dumps(prepare(args.source, args.output, args.settings, args.resume_source)))
        except Exception as error:
            if args.output.exists():
                write_json(args.output / "preparation-failure.json", {
                    "status": "failed", "error_type": type(error).__name__,
                    "error": str(error), "http_attempts": 0})
            raise
    elif args.action == "run":
        run(args.output, args.limit)
    elif args.action == "one":
        result = execute_one(args.output, args.case)
        raise SystemExit(0 if result["status"] == "completed" else 1)
    else:
        print(json.dumps(evaluate(args.output)))
