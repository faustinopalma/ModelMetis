"""MAFAULDA model test of speed-normalized reports on the cases of outputs/speed-context-v1.

Every reference and query recording is analysed by tools/audio_order_known with its tachometer
shaft speed, or by tools/audio_order_estimated with an acoustic base estimated from the audio, so
all reports share an order axis. The request otherwise follows the simple method.

Commands: calibrate (estimator thresholds against the tachometer on recordings outside the
cases; no fault labels used), prepare, run, evaluate.
"""

import argparse
import json
from dataclasses import asdict, replace
from pathlib import Path

import numpy as np

from modelmetis.dsp_packet import compact, digest
from modelmetis.dsp_similarity import (
    PROMPT,
    contact_sheet,
    decision_schema,
    file_hash,
    messages_for,
    write_json,
)
from modelmetis.visual_audio import canonical_json
from scripts import speed_context_experiment as base
from tools.audio_order_estimated.estimator import EstimatorConfig, estimate_base
from tools.audio_order_known import cli as known_cli
from tools.audio_order_known.analysis import OrderConfig, order_analysis
from tools.audio_order_known.report import read_audio, write_report

ARMS = ("normalized_known", "normalized_estimated")
CALIBRATION_FILES = 200
SCORES = (0.65, 0.6, 0.5, 0.4, 0.3, 0.2)
MARGINS = (0.08, 0.05, 0.02, 0.0)
MIN_PRECISION = 0.97
GUIDANCE = {
    "normalized_known": (
        "Every report was produced by angular resampling to its own shaft rotation, using the "
        "measured shaft speed shown in its normalization reference figure. Normalized figures "
        "use shaft order, frequency divided by shaft frequency, so components locked to "
        "rotation, such as shaft harmonics, imbalance, misalignment and bearing defect "
        "frequencies, sit at the same order in every report whatever the speed. The original "
        "figures in hertz show components fixed in hertz, such as structural resonances, "
        "electrical lines and the microphone response. Recorded gain is preserved, so overall "
        "level and broadband shape can still change with speed. Compare rotation-locked "
        "structure on the order figures and fixed-frequency structure on the hertz figures."
    ),
    "normalized_estimated": (
        "Every report was produced by angular resampling to an acoustic base frequency "
        "estimated from harmonic peaks of its own audio, without a tachometer. When estimation "
        "succeeded, normalized figures use acoustic relative order, frequency divided by that "
        "base, so components locked to the same periodicity align across reports whatever the "
        "speed; the base can be the shaft frequency or another periodicity. When estimation "
        "failed, the report states the reason and contains only the original figures. The "
        "original figures in hertz show components fixed in hertz, such as structural "
        "resonances, electrical lines and the microphone response. Recorded gain is preserved, "
        "so overall level and broadband shape can still change with speed."
    ),
}


def case_members(cases):
    return sorted({case["query"] for case in cases}
                  | {member for case in cases for member in case["references"].values()})


def accepted(frames, score, margin):
    path = [frame for frame in frames if "base_hz" in frame]
    if len(path) != len(frames) or not path:
        return None
    if any(frame["score"] < score or frame["margin"] < margin for frame in path):
        return None
    values = np.array([frame["base_hz"] for frame in path])
    if len(values) > 1 and np.max(np.abs(np.diff(np.log(values)))) > np.log(1.2):
        return None
    return float(np.median(values))


def calibrate(folder, source):
    folder, source = Path(folder), Path(source)
    folder.mkdir(parents=True, exist_ok=True)
    sources = base.read_json(source / "sources.json")
    items, _ = base.mafaulda_inventory(*sources)
    excluded = set(case_members(base.read_json(source / "cases.json")))
    pool = sorted(member for member in items if member not in excluded)
    rng = np.random.default_rng(base.SEED)
    chosen = sorted(pool[i] for i in rng.choice(len(pool), CALIBRATION_FILES, replace=False))
    files = []
    for member in chosen:
        result, _ = estimate_base(np.load(items[member]["cache"]).astype(float), base.RATE)
        frames = [{key: frame[key] for key in ("base_hz", "score", "margin") if key in frame}
                  for frame in result["frames"]]
        files.append({"member": member, "shaft_hz": items[member]["shaft_hz"], "frames": frames})
    grid = []
    for score in SCORES:
        for margin in MARGINS:
            estimates = [(accepted(f["frames"], score, margin), f["shaft_hz"]) for f in files]
            hits = [abs(value / shaft - 1) < 0.03 for value, shaft in estimates if value]
            grid.append({"min_score": score, "min_margin": margin, "accepted": len(hits),
                         "within_3_percent_of_shaft": sum(hits)})
    eligible = [row for row in grid if row["accepted"]
                and row["within_3_percent_of_shaft"] / row["accepted"] >= MIN_PRECISION]
    best = max(eligible, key=lambda row: (row["accepted"], row["min_score"], row["min_margin"]))
    write_json(folder / "calibration.json", {
        "purpose": "Estimator acceptance thresholds checked against the tachometer speed",
        "files": len(files), "excluded": "every recording used by a case", "seed": base.SEED,
        "rule": f"most accepted recordings with precision >= {MIN_PRECISION} within 3% of shaft",
        "grid": grid, "chosen": best, "per_file": files})
    for row in grid:
        print(row)
    print("chosen", best)
    return best


def estimator_config(folder):
    chosen = base.read_json(Path(folder) / "calibration.json")["chosen"]
    return replace(EstimatorConfig(), min_score=chosen["min_score"],
                   min_margin=chosen["min_margin"])


def tool_report(item, arm, folder, config):
    wav = base.write_wav(item, folder)
    target = folder / "reports" / arm / wav.stem
    if target.exists():
        return target
    target.parent.mkdir(parents=True, exist_ok=True)
    if arm == "normalized_known":
        argv = [str(wav), "--rpm", repr(60 * item["shaft_hz"]), "--output", str(target)]
        if known_cli.main(argv) != 0:
            raise ValueError(f"Known-speed tool failed on {wav.name}.")
        return target
    # Same path as tools/audio_order_estimated/cli.py, with calibrated acceptance thresholds.
    samples, rate, audit = read_audio(wav)
    estimation, trace = estimate_base(samples, rate, config)
    reference = {"kind": "estimated_acoustic_base", "estimation": estimation}
    metadata, arrays = {"status": "unavailable", "reason": estimation["reason"]}, {}
    if trace is not None:
        start, end = estimation["valid_start_sample"], estimation["valid_end_sample_exclusive"]
        try:
            metadata, arrays = order_analysis(samples[start:end], rate, trace, OrderConfig())
            metadata.update({"status": "available", "analysis_start_seconds": start / rate,
                             "analysis_end_seconds": end / rate})
            arrays["map_times_seconds"] += start / rate
            arrays["angular_times_seconds"] += start / rate
            arrays.update({"base_hz": trace, "base_times_seconds": np.arange(start, end) / rate})
        except ValueError as error:
            metadata = {"status": "unavailable", "reason": str(error)}
    write_report(target, samples, rate, audit, reference, metadata, arrays)
    return target


def pack(target, identifier, arm, config):
    document = json.loads((target / "measurements.json").read_text(encoding="utf-8"))
    reference = document["reference"]
    if reference["kind"] == "known_rpm":
        shown = {"kind": "measured shaft speed", "rpm": round(reference["rpm"], 1),
                 "shaft_hz": round(reference["rpm"] / 60, 3)}
    else:
        estimation = reference["estimation"]
        shown = {"kind": "acoustic base estimated from the audio",
                 "status": estimation["status"], "reason": estimation["reason"],
                 "base_hz_median": estimation.get("base_hz_median"),
                 "reliable_frames": estimation.get("reliable_frames"),
                 "total_frames": estimation.get("total_frames")}
    normalization = {key: value for key, value in document["normalization"].items()
                     if key != "config"}
    measurement_id = f"{identifier}.M001"
    configuration = {"tool": arm, "order": asdict(OrderConfig())}
    if arm == "normalized_estimated":
        configuration["estimator"] = asdict(config)
    model = {
        "schema": "modelmetis.order-normalized-report/1", "id": identifier,
        "configuration": configuration,
        "source": {"sample_rate_hz": document["source"]["sample_rate"],
                   "duration_seconds": document["source"]["duration_seconds"],
                   "channel": document["source"]["selected_channel"]},
        "measurements": {"evidence_id": measurement_id, "reference": compact(shown),
                         "normalization": compact(normalization),
                         "original_metrics": compact(document["raw_metrics"])},
    }
    figures, evidence_ids = [], [measurement_id]
    for number, figure in enumerate(document["figures"], 1):
        payload = (target / figure["path"]).read_bytes()
        if digest(payload) != figure["sha256"]:
            raise ValueError("Tool figure hash differs from its measurements.")
        image_id = f"{identifier}.I{number:03}"
        figures.append({"id": image_id, "title": figure["title"], "bytes": payload,
                        "sha256": figure["sha256"]})
        evidence_ids.append(image_id)
    return contact_sheet({"model": model, "figures": figures, "evidence_ids": evidence_ids,
                          "audit": {"measurements_sha256": file_hash(
                              target / "measurements.json")}})


def build_request(case, arm, items, folder, settings, config):
    labels, known = {}, {}
    for index, label in enumerate(base.CLASSES, 1):
        target = tool_report(items[case["references"][label]], arm, folder, config)
        known[f"C{index:02d}"] = pack(target, f"R{index:02d}", arm, config)
        labels[f"C{index:02d}"] = base.LABELS[label]
    unknown = pack(tool_report(items[case["query"]], arm, folder, config), "Q01", arm, config)
    messages = messages_for(known, unknown, image_detail="high", condition_labels=labels)
    messages[0]["content"] += " " + GUIDANCE[arm]
    body = {"model": settings["deployment"], "messages": messages,
            "reasoning_effort": settings["reasoning_effort"],
            "max_completion_tokens": settings["max_completion_tokens"],
            "response_format": decision_schema(list(known))}
    evidence = {"known": {cid: report["evidence_ids"] for cid, report in known.items()},
                "unknown": unknown["evidence_ids"]}
    return body, evidence


def prepare(folder, source):
    folder, source = Path(folder), Path(source)
    if (folder / "registration.json").exists():
        raise ValueError("Experiment already prepared.")
    config = estimator_config(folder)
    settings = base.read_json(source / "settings.json")
    write_json(folder / "settings.json", settings)
    cases = base.read_json(source / "cases.json")
    write_json(folder / "cases.json", cases)
    sources = base.read_json(source / "sources.json")
    write_json(folder / "sources.json", sources)
    items, _ = base.mafaulda_inventory(*sources)
    tools = Path(base.ROOT) / "tools"
    write_json(folder / "registration.json", {
        "arms": ARMS, "source_experiment": str(source), "cases": len(cases),
        "cases_sha256": file_hash(folder / "cases.json"),
        "settings_sha256": file_hash(folder / "settings.json"),
        "calibration_sha256": file_hash(folder / "calibration.json"),
        "estimator": asdict(config), "order": asdict(OrderConfig()),
        "code_sha256": {"experiment": file_hash(__file__),
                        **{str(p.relative_to(tools)): file_hash(p) for p in
                           sorted(tools.glob("audio_order_*/*.py"))}},
        "prompt_base_sha256": digest(PROMPT.encode()),
        "scope": "Same 72 MAFAULDA cases as the source experiment; every report normalized",
    })
    for case in cases:
        for arm in ARMS:
            target = folder / "requests" / arm / case["id"]
            target.mkdir(parents=True)
            body, evidence = build_request(case, arm, items, folder, settings, config)
            payload = canonical_json(body)
            (target / "request.json").write_bytes(payload)
            write_json(target / "evidence.json", evidence)
            write_json(target / "binding.json", {"request_sha256": digest(payload),
                                                 "bytes": len(payload)})
        print(case["id"], case["ratio"], flush=True)
    coverage = {}
    for target in sorted((folder / "reports" / "normalized_estimated").iterdir()):
        status = base.read_json(target / "measurements.json")["normalization"]["status"]
        coverage[status] = coverage.get(status, 0) + 1
    print("estimated-base normalization", coverage)


def evaluate(folder, previous):
    folder, previous = Path(folder), Path(previous)
    rows = list(base.read_json(previous / "evaluation.json")["rows"])
    expected = {row["case"]: row["expected"] for row in rows}
    cost = 0.0
    for arm in ARMS:
        for case in base.read_json(folder / "cases.json"):
            path = folder / "requests" / arm / case["id"] / "attempt.json"
            attempt = base.read_json(path) if path.exists() else {"status": "missing"}
            cost += attempt.get("estimated_cost_usd") or 0
            predicted = (attempt.get("condition_id") or "different"
                         if attempt["status"] == "completed" else None)
            rows.append({"case": case["id"], "ratio": case["ratio"], "arm": arm,
                         "expected": expected[case["id"]], "predicted": predicted,
                         "status": attempt["status"]})
    rows.extend(numeric_rows(folder, expected))
    write_json(folder / "evaluation.json", {"rows": rows, "estimated_cost_usd": cost})
    return rows, cost


def numeric_rows(folder, expected):
    """Nearest reference by RMS distance of mean-centered dB order PSDs from the tool arrays."""
    rows = []
    for arm in ARMS:
        cache = {}

        def curve(member, arm=arm, cache=cache):
            if member not in cache:
                stem = member.replace("/", "__")[:-4]
                path = folder / "reports" / arm / stem / "arrays.npz"
                with np.load(path, allow_pickle=False) as arrays:
                    if "order_psd" not in arrays:
                        cache[member] = None
                    else:
                        level = 10 * np.log10(np.maximum(arrays["order_psd"], 1e-30))
                        cache[member] = level - level.mean()
            return cache[member]

        for case in base.read_json(folder / "cases.json"):
            query = curve(case["query"])
            references = {f"C{i:02d}": curve(case["references"][label])
                          for i, label in enumerate(base.CLASSES, 1)}
            usable = {cid: ref for cid, ref in references.items()
                      if ref is not None and query is not None and len(ref) == len(query)}
            predicted = (min(usable, key=lambda cid: np.sqrt(np.mean(
                (usable[cid] - query) ** 2))) if usable else None)
            rows.append({"case": case["id"], "ratio": case["ratio"],
                         "arm": f"numeric-{arm}", "expected": expected[case["id"]],
                         "predicted": predicted, "status": "completed" if predicted
                         else "unavailable", "references_available": len(usable)})
    return rows


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("command", choices=["calibrate", "prepare", "run", "evaluate"])
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--source", type=Path, default=Path("outputs/speed-context-v1"))
    parser.add_argument("--previous", type=Path, default=Path("outputs/speed-matched-v1"))
    parser.add_argument("--workers", type=int, default=3)
    args = parser.parse_args()
    if args.command == "calibrate":
        calibrate(args.output, args.source)
    elif args.command == "prepare":
        prepare(args.output, args.source)
    elif args.command == "run":
        base.run(args.output, args.workers, list(ARMS))
    else:
        rows, cost = evaluate(args.output, args.previous)
        table = {}
        for row in rows:
            cell = table.setdefault((row["arm"], row["ratio"]), [0, 0])
            cell[0] += row["predicted"] == row["expected"]
            cell[1] += 1
        for (arm, ratio), (correct, total) in sorted(table.items()):
            print(f"{arm:22s} x{ratio:<4g} {correct}/{total}")
        print("normalized arms estimated cost USD", round(cost, 4))
