import argparse
import base64
import hashlib
import html
import json
import shutil
import time
from dataclasses import asdict, replace
from pathlib import Path

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
            f'10 seconds / 42 kHz / mono / <a href="{filename}">WAV</a></p></section>'
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
        f"<title>Ottawa / Reference recordings</title>{THEME}<style>{STYLE}"
        "audio{display:block;width:100%;max-width:420px}"
        "section{padding:16px 0;border-bottom:1px solid var(--cp-border)}"
        "</style></head><body><header><h1>Ottawa reference recordings</h1>"
        "<p>Eight labeled motor conditions / speed profile 1 / unloaded.</p>"
        "<p>Microphone recordings, peak-normalized to 0.95 during import.</p>"
        '<p><a href="https://data.mendeley.com/datasets/msxs4vj48g/2">'
        "UOEMD-VAFCVS v2</a> / Mert Sehri and Patrick Dumond / CC BY 4.0.</p>"
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
        result["passed"] = len(rows) == 8 and result["correct_rejections"] >= 7
    else:
        result = score_rows(rows, labels)
        result["passed"] = (
            len(rows) == 16
            and result["correct"] >= 14
            and all(value["correct"] >= 1 for value in result["per_class"].values())
        )
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
        "command", choices=["register", "audio", "new-round", "run", "evaluate", "select"]
    )
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--round", default="01")
    parser.add_argument(
        "--phase", choices=["development", "final", "novelty"], default="development"
    )
    parser.add_argument("--limit", type=int, default=16)
    parser.add_argument("--guidance", default="")
    parser.add_argument("--image-detail", choices=["low", "high"], default="high")
    args = parser.parse_args()
    if args.command == "register":
        result = register(args.output)
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
