import argparse
import base64
import hashlib
import io
import json
import time
from dataclasses import asdict
from importlib.metadata import version
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

from modelmetis import dsp, dsp_extensions, dsp_guide
from modelmetis.dsp_comparison import baseline_shape
from modelmetis.dsp_extensions import ExtensionConfig, analyze_extensions
from modelmetis.dsp_guide import VIEW_GUIDE, interpretation_prompt
from modelmetis.dsp_report import BLUE, GOLD, digest, figure_axes, save_figure
from modelmetis.visual_audio import canonical_json, pcm_sha256
from scripts.audio_comparison import ROOT, data_url, load_dataset, load_icons


def read_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def json_value(value):
    if isinstance(value, np.ndarray):
        return json_value(value.tolist())
    if isinstance(value, dict):
        return {key: json_value(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [json_value(item) for item in value]
    if isinstance(value, (float, np.floating)):
        return float(value) if np.isfinite(value) else None
    if isinstance(value, np.integer):
        return int(value)
    return value


def write_json(path, value):
    Path(path).write_bytes(canonical_json(json_value(value)))


def render_view(view, path, key):
    config = dsp.DspConfig()
    figure, axes = figure_axes(config)
    axis = axes[0]
    if view["status"] != "available":
        axis.axis("off")
        axis.text(0.5, 0.55, VIEW_GUIDE[key][0], ha="center", fontsize=18)
        axis.text(0.5, 0.4, "Unavailable", ha="center", fontsize=16)
        axis.text(0.5, 0.3, view["reason"], ha="center", fontsize=12, wrap=True)
    elif view["kind"] == "line":
        for (label, values), color in zip(view["series"].items(),
                                          (BLUE, GOLD, "#333333"), strict=False):
            axis.plot(view["x"], values, color=color, label=label, linewidth=1.1)
        axis.set(xlabel=view["x_label"], ylabel=view["y_label"], title=view["title"])
        axis.legend(fontsize=9)
    else:
        image = axis.pcolormesh(view["x"], view["y"], np.ma.masked_invalid(view["values"]),
                                shading="nearest", cmap="cividis")
        if key == "cyclic":
            image.set_clim(0, 1)
        figure.colorbar(image, ax=axis, label=view["value_label"])
        axis.set(xlabel=view["x_label"], ylabel=view["y_label"], title=view["title"])
        if key == "wavelet":
            axis.set_yscale("log")
    return save_figure(figure, path, VIEW_GUIDE[key][0], VIEW_GUIDE[key][1], config)


def signature(view):
    if view["status"] != "available":
        return None
    if view["kind"] == "line":
        return np.concatenate([np.interp(np.linspace(view["x"][0], view["x"][-1], 256),
                                         view["x"], values)
                               for values in view["series"].values()])
    values = np.asarray(view["values"])
    valid = np.isfinite(values)
    if not valid.any():
        return None
    summed = np.nansum(values, axis=1)
    count = valid.sum(axis=1)
    profile = np.divide(summed, count, out=np.zeros_like(summed), where=count > 0)
    return np.interp(np.linspace(0, 1, 256), np.linspace(0, 1, len(profile)), profile)


def distances_for(query, references, name):
    values = query["signatures"].get(name)
    if values is None:
        return None
    values = np.asarray(values)
    distances = {}
    for reference in references:
        other = reference["signatures"].get(name)
        if other is None or np.shape(other) != values.shape:
            return None
        distances[reference["id"]] = float(np.sqrt(np.mean((values - other) ** 2)))
    return distances


def numerical_trials(dataset):
    references = dataset["references"]
    predictions = []
    names = ["baseline", *list(VIEW_GUIDE)[7:]]
    for query in dataset["queries"]:
        for name in names:
            distances = distances_for(query, references, name)
            candidate = None
            if distances:
                ordered = sorted(distances, key=lambda key: (distances[key], key))
                if len(ordered) == 1 or distances[ordered[0]] != distances[ordered[1]]:
                    candidate = next(item["condition"] for item in references
                                     if item["id"] == ordered[0])
            predictions.append({"query_id": query["id"], "representation": name,
                                "candidate": candidate, "distances": distances,
                                "decision_kind": "forced_known_class_only"})
    return predictions


def score_trials(dataset, predictions, group_ids):
    truth = {item["id"]: item["truth"] for item in dataset["queries"]}
    scores = []
    for name in ["baseline", *list(VIEW_GUIDE)[7:]]:
        rows = [row for row in predictions if row["representation"] == name]
        if len(rows) != len(truth) or not rows:
            raise ValueError("Every registered query requires one result per representation.")
        groups = {group_ids[row["query_id"]] for row in rows}
        correct = sum(row["candidate"] == truth[row["query_id"]] for row in rows)
        wrong = sum(row["candidate"] is not None and row["candidate"] != truth[row["query_id"]]
                    for row in rows)
        scores.append({"representation": name, "queries": len(rows), "correct": correct,
                       "wrong": wrong, "unavailable_or_tied": len(rows) - correct - wrong,
                       "acquisitions": len(groups), "all_correct_acquisitions": sum(all(
                           row["candidate"] == truth[row["query_id"]] for row in rows
                           if group_ids[row["query_id"]] == group) for group in groups),
                       "rejection_correctness": "unmeasured"})
    return scores


def contact_sheets(record, directory):
    directory.mkdir(parents=True)
    sheets = []
    figures = list(record["figures"].items())
    for start in range(0, len(figures), 16):
        subset = figures[start:start + 16]
        sheet = Image.new("RGB", (2400, 4 * 380), "white")
        drawer = ImageDraw.Draw(sheet)
        cells = []
        for index, (key, url) in enumerate(subset):
            payload = base64.b64decode(url.split(",", 1)[1])
            with Image.open(io.BytesIO(payload)) as image:
                image = image.convert("RGB").resize((600, 350), Image.Resampling.LANCZOS)
                left, top = index % 4 * 600, index // 4 * 380
                sheet.paste(image, (left, top + 30))
                drawer.text((left + 10, top + 8), f"{record['id']}.{key}", fill="black")
            cells.append({"id": f"{record['id']}.{key}", "view": key,
                          "original_sha256": hashlib.sha256(payload).hexdigest(),
                          "cell": index, "original_pixels": [1200, 700],
                          "image_pixels": [600, 350]})
        path = directory / f"sheet-{len(sheets) + 1}.png"
        sheet.save(path)
        sheets.append({"path": path.as_posix(), "sha256": digest(path), "cells": cells,
                       "size": [2400, 1520], "transform": "Lanczos resize, all figures retained"})
    return sheets


def prepare(output):
    output = Path(output)
    output.mkdir(parents=True, exist_ok=False)
    write_json(output / "attempt.json", {"status": "started", "model_calls": 0})
    config = ExtensionConfig()
    code = {Path(module.__file__).relative_to(ROOT).as_posix(): digest(module.__file__)
            for module in (dsp, dsp_extensions, dsp_guide)}
    code["scripts/dsp_extended_experiment.py"] = digest(__file__)
    sources = [(ROOT / "outputs/dsp-jin-v1", "Jin"),
               (ROOT / "outputs/dsp-ottawa-v2", "Ottawa")]
    registration = {"schema": 1, "config": asdict(config), "code_sha256": code,
                    "protocol_hashes": {name: digest(folder / "protocol.json")
                                        for folder, name in sources},
                    "runtime": {name: version(name) for name in (
                        "numpy", "scipy", "PyWavelets", "matplotlib", "pillow")},
                    "scope": "consumed_project_acquisitions_exploratory",
                    "selection": "exact existing v8 evaluated queries and references",
                    "pruning": False, "threshold_fitting": False,
                    "signatures": "line curves resampled to 256 points; map row means to 256; "
                    "raw RMS distance within each view; descriptive screen, not a classifier gate",
                    "ai_spending_cap": None, "ai_execution": "separate registered stage"}
    write_json(output / "registration.json", registration)
    (output / "prompt.txt").write_text(interpretation_prompt(), encoding="utf-8")
    started = time.perf_counter()
    datasets, artifacts = [], {}
    try:
        for folder, name in sources:
            dataset = load_dataset(folder, name)
            protocol = read_json(folder / "protocol.json")
            originals = {item["id"]: item for item in [*protocol["known"], *protocol["queries"]]}
            query_ids = {item["id"] for item in dataset["queries"]}
            reference_ids = {item["id"] for item in dataset["references"]}
            if query_ids & reference_ids:
                raise ValueError("References overlap query identifiers.")
            content_hashes = set()
            groups = {item["id"]: item.get("group_id", item["id"])
                      for item in originals.values()}
            for record in [*dataset["references"], *dataset["queries"]]:
                item = originals[record["id"]]
                samples, rate, provenance = dsp.decode_recording(item["wav"], dsp.DspConfig())
                if provenance["source_sha256"] != item["audio_sha256"] or samples.shape[1] != 1:
                    raise ValueError("Registered mono source mismatch.")
                pcm_hash = pcm_sha256(samples[:, 0])
                if pcm_hash in content_hashes:
                    raise ValueError("Duplicate decoded audio in the registered dataset.")
                content_hashes.add(pcm_hash)
                result = analyze_extensions(samples[:, 0], rate, config)
                directory = output / name / record["id"]
                directory.mkdir(parents=True)
                write_json(directory / "evidence.json", result)
                record["signatures"] = {key: signature(view)
                                        for key, view in result["views"].items()}
                record["signatures"]["baseline"] = baseline_shape(
                    samples[:, 0], rate).get("shape_db")
                record["viewMetadata"] = {}
                for key, view in result["views"].items():
                    descriptor = render_view(view, directory / f"{key}.png", key)
                    record["figures"][key] = data_url((directory / f"{key}.png").read_bytes(),
                                                     "image/png")
                    record["figureHashes"][key] = descriptor["sha256"]
                    record["viewMetadata"][key] = {field: view[field] for field in (
                        "status", "reason", "metrics") if field in view}
                record["sheets"] = contact_sheets(record, directory / "sheets")
                record["measurementPath"] = (directory / "evidence.json").as_posix()
                print(f"{name} {record['id']}: {len(result['views'])} extension views", flush=True)
            predictions = numerical_trials(dataset)
            write_json(output / name / "predictions.json", predictions)
            scores = score_trials(dataset, predictions, groups)
            write_json(output / name / "scores.json", scores)
            for record in dataset["queries"]:
                record["models"] = [{"round": "numeric-" + row["representation"],
                                      "phase": "forced-known", "status": "completed"
                                      if row["candidate"] else "unavailable",
                                      "outcome": "forced", "condition": row["candidate"]}
                                     for row in predictions if row["query_id"] == record["id"]]
            write_json(output / name / "dataset.json", dataset)
            datasets.append(dataset)
        if any(digest(ROOT / name) != expected for name, expected in code.items()):
            raise ValueError("DSP implementation changed during preparation.")
        for path in output.rglob("*"):
            if path.is_file() and path.name != "attempt.json":
                artifacts[path.relative_to(output).as_posix()] = digest(path)
        write_json(output / "manifest.json", {"files": artifacts})
        write_json(output / "attempt.json", {"status": "completed", "model_calls": 0,
                                             "elapsed_seconds": time.perf_counter() - started})
        build_review(output, output / "review")
    except Exception as error:
        write_json(output / "attempt.json", {"status": "failed", "error_type": type(error).__name__,
                                             "model_calls": 0})
        raise


def build_review(source, output):
    from scripts.audio_comparison import TEMPLATE

    source, output = Path(source), Path(output)
    output.mkdir(parents=True, exist_ok=False)
    datasets = [read_json(source / name / "dataset.json") for name in ("Jin", "Ottawa")]
    for dataset in datasets:
        for record in [*dataset["references"], *dataset["queries"]]:
            record.pop("signatures", None)
    payload = {"schema": 2, "datasets": datasets, "icons": load_icons(),
               "views": [[key, value[0]] for key, value in VIEW_GUIDE.items()],
               "guide": {key: value[1] for key, value in VIEW_GUIDE.items()},
               "resultNoun": "Numerical control", "fingerprint": digest(source / "manifest.json")}
    from modelmetis.dsp_report import STYLE, THEME

    encoded = canonical_json(json_value(payload)).decode().replace("<", "\\u003c")
    page = TEMPLATE.read_text(encoding="utf-8").replace("__THEME__", THEME).replace(
        "__BASE_STYLE__", STYLE).replace("__DATA__", encoded)
    (output / "index.html").write_text(page, encoding="utf-8")
    write_json(output / "manifest.json", {"page_sha256": digest(output / "index.html"),
                                         "source_manifest_sha256": digest(source / "manifest.json"),
                                         "template_sha256": digest(TEMPLATE)})


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="All-view DSP and serial offline trials.")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--review-source", type=Path)
    args = parser.parse_args()
    if args.review_source:
        build_review(args.review_source, args.output)
    else:
        prepare(args.output)