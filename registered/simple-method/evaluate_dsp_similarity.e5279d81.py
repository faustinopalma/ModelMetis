import argparse
import base64
import hashlib
import html
import json
import shutil
import time
from dataclasses import asdict, replace
from pathlib import Path

import numpy as np

from modelmetis.dsp import DspConfig
from modelmetis.dsp_report import STYLE, THEME, generate_report
from modelmetis.dsp_similarity import file_hash, prepare_comparison, write_json
from scripts.compare_dsp import run_isolated
from scripts.prepare_ottawa import CLASSES

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data/ottawa-simulation-v1"
SOURCE_STATE = "derived_peak_normalized"


def read_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def numeric_control(folder):
    protocol = checked_protocol(folder)
    truth = read_json(folder / "sealed/truth.json")
    reference_labels = [item["label"] for item in protocol["known"]]
    results = {}
    for lower_hz in (0, 500, 2000):
        vectors = {}
        for item in [
            *protocol["known"],
            *[query for query in protocol["queries"] if query["role"] == "development"],
        ]:
            report = folder / "reports" / item["id"]
            evidence = read_json(report / "evidence.json")
            with np.load(
                report / evidence["channels"][0]["segments"][0]["arrays"], allow_pickle=False
            ) as arrays:
                selected = arrays["welch_frequencies"] >= lower_hz
                spectrum = 10 * np.log10(np.maximum(arrays["welch_psd"][selected], 1e-30))
                vectors[item["id"]] = spectrum - np.mean(spectrum)
        references = np.stack([vectors[item["id"]] for item in protocol["known"]])
        rows = []
        for query in protocol["queries"]:
            if query["role"] != "development":
                continue
            distances = np.sqrt(np.mean((references - vectors[query["id"]]) ** 2, axis=1))
            rows.append(
                {
                    "id": query["id"],
                    "expected_label": truth[query["id"]]["label"],
                    "predicted_label": reference_labels[int(np.argmin(distances))],
                    "distances_db": distances.tolist(),
                }
            )
        results[str(lower_hz)] = {**score_rows(rows, reference_labels), "rows": rows}
    write_json(folder / "numeric-control.json", results)
    return {
        key: {"correct": value["correct"], "queries": value["queries"]}
        for key, value in results.items()
    }


def score_rows(rows, labels):
    if not rows:
        raise ValueError("Evaluation requires at least one registered query.")
    confusion = {
        label: {value: 0 for value in [*labels, "different", "technical_failure"]}
        for label in labels
    }
    for row in rows:
        confusion[row["expected_label"]][row["predicted_label"]] += 1
    per_class = {}
    for label in labels:
        true_positive = confusion[label][label]
        count = sum(confusion[label].values())
        predicted = sum(confusion[other][label] for other in labels)
        per_class[label] = {
            "correct": true_positive,
            "queries": count,
            "recall": true_positive / count if count else None,
            "f1": 2 * true_positive / (count + predicted) if count + predicted else 0.0,
        }
    correct = sum(row["predicted_label"] == row["expected_label"] for row in rows)
    return {
        "queries": len(rows),
        "correct": correct,
        "accuracy": correct / len(rows),
        "technical_failures": sum(row["predicted_label"] == "technical_failure" for row in rows),
        "false_rejections": sum(row["predicted_label"] == "different" for row in rows),
        "wrong_known_labels": sum(
            row["predicted_label"] in labels and row["predicted_label"] != row["expected_label"]
            for row in rows
        ),
        "macro_f1": sum(value["f1"] for value in per_class.values()) / len(labels),
        "per_class": per_class,
        "confusion": confusion,
    }


def register(folder):
    records = read_json(DATA / "sealed/references.json")
    labels = list(CLASSES.values())
    if len(records) != 128 or set(record["label"] for record in records) != set(labels):
        raise ValueError("Ottawa inventory or taxonomy differs from the audited dataset.")
    by_cell = {}
    for record in records:
        condition, suffix, profile, load = Path(record["source_path"]).stem.split("_")
        if CLASSES[f"{condition}_{suffix}"] != record["label"]:
            raise ValueError("Publisher condition and stored truth disagree.")
        key = (record["label"], int(profile), int(load))
        if key in by_cell:
            raise ValueError("Repeated acquisition cell.")
        by_cell[key] = record
    expected = {
        (label, profile, load) for label in labels for profile in range(1, 9) for load in (0, 1)
    }
    if set(by_cell) != expected:
        raise ValueError("Incomplete class, speed-profile or load coverage.")
    folder.mkdir(parents=True, exist_ok=False)
    (folder / "sealed").mkdir()
    (folder / "reports").mkdir()
    known, queries, truth, source_hashes = [], [], {}, set()
    for role, profile in (("reference", 1), ("development", 2), ("final", 8)):
        ordinal = 0
        for class_index, label in enumerate(labels, 1):
            for load in (0,) if role == "reference" else (0, 1):
                ordinal += 1
                record = by_cell[label, profile, load]
                source = DATA / record["partition"] / f"{record['sample_id']}.wav"
                if file_hash(source) != record["audio_sha256"]:
                    raise ValueError("Registered WAV hash changed.")
                if record["audio_sha256"] in source_hashes:
                    raise ValueError("Audio overlaps between reference and evaluation roles.")
                source_hashes.add(record["audio_sha256"])
                identifier = (
                    f"{ {'reference': 'R', 'development': 'D', 'final': 'T'}[role] }{ordinal:02}"
                )
                item = {
                    "id": identifier,
                    "wav": str(source.resolve()),
                    "role": role,
                    "audio_sha256": record["audio_sha256"],
                    "profile": profile,
                    "load": load,
                }
                if role == "reference":
                    item.update(
                        condition_id=f"C{class_index:02}",
                        label=label,
                        source_acquisition=Path(record["source_path"]).stem,
                    )
                    known.append(item)
                else:
                    queries.append(item)
                    truth[identifier] = {
                        "label": label,
                        "condition_id": f"C{class_index:02}",
                        "source_acquisition": Path(record["source_path"]).stem,
                    }
    protocol = {
        "schema": 1,
        "dataset": "10.17632/msxs4vj48g.2",
        "license": "CC BY 4.0",
        "known": known,
        "queries": queries,
        "max_development_iterations": 3,
        "max_total_http_attempts": 72,
        "criteria": {
            "known_correct_min": 14,
            "known_queries": 16,
            "minimum_correct_per_class": 1,
            "novel_correct_min": 7,
            "novel_queries": 8,
        },
        "scope": "Acquisition and operating-profile transfer within eight existing motors",
        "holdout": "Profile 8 is reserved here; prior project experiments consumed it",
        "code_sha256": file_hash(__file__),
    }
    write_json(folder / "protocol.json", protocol)
    write_json(folder / "sealed/truth.json", truth)
    write_json(
        folder / "registration.json",
        {
            "protocol_sha256": file_hash(folder / "protocol.json"),
            "truth_sha256": file_hash(folder / "sealed/truth.json"),
        },
    )
    rows = [
        "# Ottawa Reference Cases",
        "",
        "Every model request includes one labeled example of each visible known condition.",
        "",
        "| Condition | Publisher class | Acquisition | WAV SHA-256 |",
        "| --- | --- | --- | --- |",
    ]
    rows.extend(
        f"| {item['condition_id']} | {item['label']} | {item['source_acquisition']} | "
        f"{item['audio_sha256']} |"
        for item in known
    )
    (folder / "reference-cases.md").write_text("\n".join(rows) + "\n", encoding="utf-8")
    export_reference_audio(folder, known)
    return {"references": len(known), "development_queries": 16, "final_queries": 16}


def export_reference_audio(folder, known):
    jin = read_json(folder / "protocol.json")["dataset"] == "10.17632/9dpmkgpncw.1"
    name = "Jin" if jin else "Ottawa"
    rate = "44.1 kHz" if jin else "42 kHz"
    context = "Four labeled conditions / front microphone" if jin else (
        "Eight labeled motor conditions / speed profile 1 / unloaded"
    )
    url = "https://data.mendeley.com/datasets/" + ("9dpmkgpncw/1" if jin else "msxs4vj48g/2")
    attribution = "Linjie Jin" if jin else "Mert Sehri and Patrick Dumond"
    output = folder / "reference-audio"
    output.mkdir(exist_ok=True)
    sections, manifest = [], []
    for item in known:
        filename = f"{item['condition_id']}-{item['label']}.wav"
        target = output / filename
        if not target.exists():
            shutil.copyfile(item["wav"], target)
        if file_hash(target) != item["audio_sha256"]:
            raise ValueError("Listening copy differs from the model's source WAV.")
        title = f"{item['condition_id']} / {item['label'].replace('_', ' ').title()}"
        audio_url = "data:audio/wav;base64," + base64.b64encode(target.read_bytes()).decode()
        sections.append(
            f"<section><h2>{html.escape(title)}</h2>"
            f'<audio controls preload="metadata" src="{audio_url}" '
            f'aria-label="{html.escape(title)}"></audio>'
            f"<p>Acquisition: {html.escape(item['source_acquisition'])} / "
            f'10 seconds / {rate} / mono / <a href="{filename}">WAV</a></p></section>'
        )
        manifest.append(
            {
                "condition_id": item["condition_id"],
                "label": item["label"],
                "path": filename,
                "sha256": item["audio_sha256"],
                "source_acquisition": item["source_acquisition"],
            }
        )
    page = (
        '<!doctype html><html lang="en"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width,initial-scale=1">'
        f"<title>{name} / Reference recordings</title>{THEME}<style>{STYLE}"
        "audio{display:block;width:100%;max-width:420px}"
        "section{padding:16px 0;border-bottom:1px solid var(--cp-border)}"
        f"</style></head><body><header><h1>{name} reference recordings</h1>"
        f"<p>{context}.</p>"
        "<p>Microphone recordings, peak-normalized to 0.95 during import.</p>"
        f'<p><a href="{url}">{name} dataset</a> / {attribution} / CC BY 4.0.</p>'
        '<nav><a href="../reference-cases.md">Reference case list</a></nav>'
        f"</header><main>{''.join(sections)}</main></body></html>"
    )
    (output / "index.html").write_text(page, encoding="utf-8")
    write_json(output / "manifest.json", manifest)


def checked_protocol(folder):
    binding = read_json(folder / "registration.json")
    if binding["protocol_sha256"] != file_hash(folder / "protocol.json") or binding[
        "truth_sha256"
    ] != file_hash(folder / "sealed/truth.json"):
        raise ValueError("Frozen registration changed.")
    return read_json(folder / "protocol.json")


def register_jin(folder):
    source = ROOT / "data/jin-directions-v1"
    supports = read_json(source / "support/manifest.json")["examples"]
    references = read_json(source / "sealed/references.json")
    sources = read_json(source / "sealed/sources.json")
    folder.mkdir(parents=True, exist_ok=False)
    (folder / "sealed").mkdir()
    (folder / "reports").mkdir()
    known, queries, truth, hashes = [], [], {}, set()
    reference_groups, query_groups = set(), set()
    for ordinal, record in enumerate(supports, 1):
        original = next(item for item in sources
                        if item["label"] == record["label"] and item["direction"] == "f")
        item = {"id": f"R{ordinal:02}", "condition_id": f"C{ordinal:02}",
                "label": record["label"], "role": "reference", "direction": "front",
                "wav": str((source / "support" / f"{record['sample_id']}.wav").resolve()),
                "audio_sha256": record["audio_sha256"],
                "source_acquisition": original["source_path"] + " at 0 s"}
        known.append(item)
        reference_groups.add(record["group_id"])
        for role, partition, offsets in (("development", "train", (0, 120)),
                                         ("final", "development", (0, 120, 240))):
            for offset in offsets:
                selected = [row for row in references if row["label"] == record["label"]
                            and row["partition"] == partition and row["offset_seconds"] == offset]
                if len(selected) != 1:
                    raise ValueError("Expected exactly one Jin acquisition window per cell.")
                row = selected[0]
                index = sum(query["role"] == role for query in queries) + 1
                identifier = f"{'D' if role == 'development' else 'T'}{index:02}"
                query = {"id": identifier, "role": role, "load": int(offset != 0),
                         "direction": "left" if role == "development" else "right",
                         "wav": str((source / partition / f"{row['sample_id']}.wav").resolve()),
                         "audio_sha256": row["audio_sha256"], "group_id": row["group_id"]}
                queries.append(query)
                query_groups.add(row["group_id"])
                truth[identifier] = {"label": row["label"], "condition_id": f"C{ordinal:02}",
                                     "source_acquisition": row["source_path"],
                                     "offset_seconds": offset}
    if len(known) != 4 or reference_groups.intersection(query_groups):
        raise ValueError("Jin class coverage or source-group separation failed.")
    for item in [*known, *queries]:
        actual = file_hash(item["wav"])
        if actual != item["audio_sha256"] or actual in hashes:
            raise ValueError("Jin input hash mismatch or duplicate across roles.")
        hashes.add(actual)
    protocol = {"schema": 1, "dataset": "10.17632/9dpmkgpncw.1", "license": "CC BY 4.0",
                "known": known, "queries": queries, "max_development_iterations": 3,
                "max_total_http_attempts": 48,
                "criteria": {"known_correct_min": 11, "known_queries": 12,
                             "development_correct_min": 7, "development_queries": 8,
                             "minimum_correct_per_class": 1, "novel_correct_min": 4,
                             "novel_queries": 4},
                "scope": "Four labeled conditions; front-to-left/right microphone direction transfer",
                "holdout": "Right acquisitions reserved in this run; previously consumed by project",
                "dependence": "12 final windows share four acquisitions; unit/session IDs unknown",
                "encoding_confound": "Original healthy PCM16/fault FLOAT; exports are PCM16",
                "code_sha256": file_hash(__file__)}
    write_json(folder / "protocol.json", protocol)
    write_json(folder / "sealed/truth.json", truth)
    write_json(folder / "registration.json", {"protocol_sha256": file_hash(folder / "protocol.json"),
                                             "truth_sha256": file_hash(folder / "sealed/truth.json")})
    rows = ["# Jin Reference Cases", "", "| Condition | Publisher class | Reference window |",
            "| --- | --- | --- |"]
    rows.extend(f"| {item['condition_id']} | {item['label']} | {item['source_acquisition']} |"
                for item in known)
    (folder / "reference-cases.md").write_text("\n".join(rows) + "\n", encoding="utf-8")
    export_reference_audio(folder, known)
    return {"references": 4, "development_queries": 8, "final_queries": 12,
            "final_original_acquisitions": 4}


def make_round(folder, name, guidance="", image_detail="high"):
    protocol = checked_protocol(folder)
    iterations = list(folder.glob("round-*/settings.json"))
    if len(iterations) >= protocol["max_development_iterations"]:
        raise ValueError("Registered iteration limit reached.")
    target = folder / f"round-{name}"
    target.mkdir(exist_ok=False)
    settings = read_json(ROOT / "configs/dsp-sol-reuse-v1.json")
    settings.update(
        image_detail=image_detail,
        max_report_images=50,
        figure_layout="contact-sheet",
        max_request_bytes=20_000_000,
        comparison_guidance=guidance,
        max_completion_tokens=8192,
    )
    write_json(target / "settings.json", settings)
    config = replace(DspConfig(), segment_seconds=10.0, max_plot_segments=1)
    write_json(target / "dsp-config.json", asdict(config))
    write_json(
        target / "round.json",
        {
            "settings_sha256": file_hash(target / "settings.json"),
            "config_sha256": file_hash(target / "dsp-config.json"),
            "protocol_sha256": file_hash(folder / "protocol.json"),
        },
    )
    return target


def report_item(folder, item, config, report_id):
    source = Path(item["wav"])
    if file_hash(source) != item["audio_sha256"]:
        raise ValueError("Source WAV changed after registration.")
    report = folder / "reports" / item["id"]
    if not report.exists():
        generate_report(source, report, config, report_id, SOURCE_STATE)
    result = {"wav": str(source), "report": str(report.resolve()), "source_state": SOURCE_STATE}
    if "condition_id" in item:
        result.update(condition_id=item["condition_id"], label=item["label"])
    return result


def run_cases(folder, name, phase, limit):
    protocol = checked_protocol(folder)
    target = folder / f"round-{name}"
    binding = read_json(target / "round.json")
    if binding["settings_sha256"] != file_hash(target / "settings.json") or binding[
        "config_sha256"
    ] != file_hash(target / "dsp-config.json"):
        raise ValueError("Frozen iteration settings changed.")
    if phase != "development":
        winner = read_json(folder / "selected-round.json")
        if winner["round"] != name:
            raise ValueError("Final evaluation requires the selected frozen iteration.")
    config = DspConfig(**read_json(target / "dsp-config.json"))
    selection = [
        item
        for item in protocol["queries"]
        if item["role"] == ("development" if phase == "development" else "final")
        and (phase != "novelty" or item["load"] == 0)
    ]
    completed = []
    for ordinal, query in enumerate(selection):
        case = target / phase / query["id"]
        if (case / "03_response/attempt.json").exists():
            continue
        attempts = sum(
            read_json(path).get("http_attempts", 0)
            for path in folder.glob("round-*/*/*/03_response/attempt.json")
        )
        if attempts >= protocol["max_total_http_attempts"]:
            raise ValueError("Registered HTTP attempt limit reached.")
        excluded = f"C{ordinal + 1:02}" if phase == "novelty" else None
        known = [
            report_item(folder, item, config, f"R{index:04}")
            for index, item in enumerate(protocol["known"], 1)
            if item["condition_id"] != excluded
        ]
        unknown = report_item(folder, query, config, "R0009")
        spec_path = target / f"{phase}-{query['id']}-spec.json"
        write_json(spec_path, {"known_conditions": known, "unknown": unknown})
        prepare_comparison(spec_path, target / "settings.json", case, config)
        result = run_isolated(case)
        row = {
            "case": query["id"],
            "status": result["status"],
            "outcome": result.get("decision", {}).get("outcome"),
            "condition_id": result.get("decision", {}).get("condition_id"),
            "cost_usd": result.get("estimated_cost_usd"),
            "usage": result.get("usage"),
        }
        completed.append(row)
        print(json.dumps(row), flush=True)
        if result["status"] != "completed":
            raise RuntimeError("Technical failure retained; stop this batch before another call.")
        if len(completed) >= limit:
            break
    return completed


def evaluate(folder, name, phase):
    protocol = checked_protocol(folder)
    criteria = protocol["criteria"]
    truth = read_json(folder / "sealed/truth.json")
    labels = [item["label"] for item in protocol["known"]]
    mapping = {item["condition_id"]: item["label"] for item in protocol["known"]}
    target = folder / f"round-{name}"
    rows = []
    for query in protocol["queries"]:
        if query["role"] != ("development" if phase == "development" else "final"):
            continue
        if phase == "novelty" and query["load"] != 0:
            continue
        path = target / phase / query["id"] / "03_response/attempt.json"
        if not path.exists():
            continue
        receipt = read_json(path)
        predicted = "technical_failure"
        if receipt["status"] == "completed":
            decision = receipt["decision"]
            predicted = (
                mapping[decision["condition_id"]]
                if decision["outcome"] == "similar"
                else "different"
            )
        rows.append(
            {
                "id": query["id"],
                "expected_label": truth[query["id"]]["label"],
                "predicted_label": predicted,
                "cost_usd": receipt.get("estimated_cost_usd"),
                "request_sha256": receipt.get("request_sha256"),
                "receipt_sha256": file_hash(path),
            }
        )
    if phase == "novelty":
        result = {
            "queries": len(rows),
            "correct_rejections": sum(row["predicted_label"] == "different" for row in rows),
        }
        result["passed"] = (len(rows) == criteria["novel_queries"]
                    and result["correct_rejections"] >= criteria["novel_correct_min"])
    else:
        result = score_rows(rows, labels)
        result["passed"] = (
            len(rows) == criteria.get("development_queries", criteria["known_queries"])
            if phase == "development" else len(rows) == criteria["known_queries"]
        )
        minimum = criteria.get("development_correct_min", criteria["known_correct_min"]) \
            if phase == "development" else criteria["known_correct_min"]
        result["passed"] = (result["passed"] and result["correct"] >= minimum
                            and all(value["correct"] >= criteria["minimum_correct_per_class"]
                                    for value in result["per_class"].values()))
    result.update(
        phase=phase,
        round=name,
        rows=rows,
        estimated_cost_usd=sum(row["cost_usd"] or 0 for row in rows),
        unknown_cost_receipts=sum(row["cost_usd"] is None for row in rows),
    )
    write_json(target / f"{phase}-evaluation.json", result)
    return result


def main():
    parser = argparse.ArgumentParser(
        description="Bounded labeled DSP reference-comparison evaluation."
    )
    parser.add_argument(
        "command",
        choices=["register", "audio", "control", "new-round", "run", "evaluate", "select"],
    )
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--round", default="01")
    parser.add_argument(
        "--phase", choices=["development", "final", "novelty"], default="development"
    )
    parser.add_argument("--limit", type=int, default=16)
    parser.add_argument("--guidance", default="")
    parser.add_argument("--image-detail", choices=["low", "high"], default="high")
    parser.add_argument("--dataset", choices=["ottawa", "jin"], default="ottawa")
    args = parser.parse_args()
    if args.command == "register":
        result = register_jin(args.output) if args.dataset == "jin" else register(args.output)
    elif args.command == "control":
        result = numeric_control(args.output)
    elif args.command == "audio":
        export_reference_audio(args.output, checked_protocol(args.output)["known"])
        result = {"reference_audio": str(args.output / "reference-audio/index.html")}
    elif args.command == "new-round":
        result = {
            "round": str(make_round(args.output, args.round, args.guidance, args.image_detail))
        }
    elif args.command == "run":
        result = run_cases(args.output, args.round, args.phase, args.limit)
    elif args.command == "select":
        evaluation = evaluate(args.output, args.round, "development")
        if not evaluation["passed"]:
            raise ValueError("Development acceptance criterion has not been met.")
        with (args.output / "selected-round.json").open("x", encoding="utf-8") as stream:
            json.dump(
                {
                    "round": args.round,
                    "evaluation_sha256": hashlib.sha256(
                        json.dumps(evaluation, sort_keys=True).encode()
                    ).hexdigest(),
                },
                stream,
            )
        result = {"selected_round": args.round}
    else:
        result = evaluate(args.output, args.round, args.phase)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    started = time.perf_counter()
    try:
        main()
    finally:
        print(f"ElapsedSeconds={time.perf_counter() - started:.3f}", flush=True)
