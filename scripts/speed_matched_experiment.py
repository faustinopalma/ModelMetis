"""MAFAULDA model test of speed-matched references on the cases of outputs/speed-context-v1.

Every reference recording is resampled so its shaft frequency equals the query's before its DSP
report is generated; the request otherwise follows the simple method.
"""

import argparse
from dataclasses import asdict, replace
from pathlib import Path

import numpy as np
import soundfile as sf

from modelmetis.dsp import DspConfig
from modelmetis.dsp_packet import digest
from modelmetis.dsp_report import generate_report
from modelmetis.dsp_similarity import (
    PROMPT,
    contact_sheet,
    decision_schema,
    file_hash,
    full_report,
    messages_for,
    write_json,
)
from modelmetis.speed_context import MATCHED_GUIDANCE, match_speed
from modelmetis.visual_audio import canonical_json
from scripts import speed_context_experiment as base

ARM = "matched"
# Long enough for every matched reference (ratio 2 doubles the duration) to stay one interval.
SEGMENT_SECONDS = 12.0


def matched_wav(item, target_hz, folder):
    key = item["member"].replace("/", "__")[:-4] + f"__to_{target_hz:.4f}Hz"
    path = folder / "wav" / f"{key}.wav"
    if not path.exists():
        path.parent.mkdir(parents=True, exist_ok=True)
        samples, factor = match_speed(np.load(item["cache"]), base.RATE, item["shaft_hz"],
                                      target_hz)
        sf.write(path, samples.astype(np.float32), base.RATE, subtype="FLOAT")
        write_json(path.with_suffix(".json"), {"member": item["member"],
                                               "source_shaft_hz": item["shaft_hz"],
                                               "target_shaft_hz": target_hz,
                                               "frequency_factor": factor})
    return path


def report(path, folder, config, identifier):
    target = folder / "reports" / path.stem
    if not target.exists():
        generate_report(path, target, config, "R0001", "derived")
    packed = contact_sheet(full_report(target, identifier))
    if packed["audit"]["source_sha256"] != file_hash(path):
        raise ValueError("Report belongs to another WAV.")
    return packed


def build_request(case, items, folder, settings, config):
    query_item = items[case["query"]]
    query_hz = query_item["shaft_hz"]
    known, context = {}, {}
    for index, label in enumerate(base.CLASSES, 1):
        item = items[case["references"][label]]
        identifier = f"R{index:02d}"
        known[f"C{index:02d}"] = report(matched_wav(item, query_hz, folder), folder, config,
                                        identifier)
        context[identifier] = {"original_shaft_hz": round(item["shaft_hz"], 3),
                               "matched_shaft_hz": round(query_hz, 3),
                               "frequency_factor": round(query_hz / item["shaft_hz"], 4)}
    query_wav = base.write_wav(query_item, folder)
    unknown = report(query_wav, folder, config, "Q01")
    context["Q01"] = {"original_shaft_hz": round(query_hz, 3)}
    labels = {f"C{i:02d}": base.LABELS[label] for i, label in enumerate(base.CLASSES, 1)}
    messages = messages_for(known, unknown, image_detail="high", condition_labels=labels)
    messages[0]["content"] += " " + MATCHED_GUIDANCE
    messages[1]["content"].insert(1, {"type": "text", "text": canonical_json(
        {"operating_context": context}).decode()})
    body = {"model": settings["deployment"], "messages": messages,
            "reasoning_effort": settings["reasoning_effort"],
            "max_completion_tokens": settings["max_completion_tokens"],
            "response_format": decision_schema(list(known))}
    evidence = {"known": {cid: rep["evidence_ids"] for cid, rep in known.items()},
                "unknown": unknown["evidence_ids"]}
    return body, evidence


def prepare(folder, source):
    folder, source = Path(folder), Path(source)
    folder.mkdir(parents=True, exist_ok=False)
    settings = base.read_json(source / "settings.json")
    write_json(folder / "settings.json", settings)
    config = replace(DspConfig(), segment_seconds=SEGMENT_SECONDS, max_plot_segments=1)
    write_json(folder / "dsp-config.json", asdict(config))
    cases = base.read_json(source / "cases.json")
    write_json(folder / "cases.json", cases)
    sources = base.read_json(source / "sources.json")
    write_json(folder / "sources.json", sources)
    items, _ = base.mafaulda_inventory(*sources)
    write_json(folder / "registration.json", {
        "arms": [ARM], "source_experiment": str(source), "cases": len(cases),
        "cases_sha256": file_hash(folder / "cases.json"),
        "settings_sha256": file_hash(folder / "settings.json"),
        "code_sha256": {"experiment": file_hash(__file__),
                        "speed_context": file_hash(Path(match_speed.__code__.co_filename))},
        "prompt_base_sha256": digest(PROMPT.encode()),
        "scope": "Same 72 MAFAULDA cases as the source experiment; references speed-matched",
    })
    for case in cases:
        target = folder / "requests" / ARM / case["id"]
        target.mkdir(parents=True)
        body, evidence = build_request(case, items, folder, settings, config)
        payload = canonical_json(body)
        (target / "request.json").write_bytes(payload)
        write_json(target / "evidence.json", evidence)
        write_json(target / "binding.json", {"request_sha256": digest(payload),
                                             "bytes": len(payload)})
        print(case["id"], case["ratio"], len(payload), flush=True)


def evaluate(folder, source):
    folder, source = Path(folder), Path(source)
    previous = base.read_json(source / "evaluation.json")["rows"]
    rows = list(previous)
    cost = 0.0
    for case in base.read_json(folder / "cases.json"):
        expected = next(row["expected"] for row in previous if row["case"] == case["id"])
        path = folder / "requests" / ARM / case["id"] / "attempt.json"
        attempt = base.read_json(path) if path.exists() else {"status": "missing"}
        cost += attempt.get("estimated_cost_usd") or 0
        predicted = (attempt.get("condition_id") or "different"
                     if attempt["status"] == "completed" else None)
        rows.append({"case": case["id"], "ratio": case["ratio"], "arm": ARM,
                     "expected": expected, "predicted": predicted, "status": attempt["status"]})
    write_json(folder / "evaluation.json", {"rows": rows, "estimated_cost_usd": cost})
    return rows, cost


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("command", choices=["prepare", "run", "evaluate"])
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--source", type=Path, default=Path("outputs/speed-context-v1"))
    parser.add_argument("--workers", type=int, default=3)
    args = parser.parse_args()
    if args.command == "prepare":
        prepare(args.output, args.source)
    elif args.command == "run":
        base.run(args.output, args.workers, [ARM])
    else:
        rows, cost = evaluate(args.output, args.source)
        table = {}
        for row in rows:
            cell = table.setdefault((row["arm"], row["ratio"]), [0, 0])
            cell[0] += row["predicted"] == row["expected"]
            cell[1] += 1
        for (arm, ratio), (correct, total) in sorted(table.items()):
            print(f"{arm:15s} x{ratio:<4g} {correct}/{total}")
        print("matched-arm estimated cost USD", round(cost, 4))
