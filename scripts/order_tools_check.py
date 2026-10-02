"""Check the parallel-session order tools on the difference-screen scenarios; no model calls.

Adds four representations to the screen's raw and order spectra, all from
tools/audio_order_known.analysis.order_analysis with mean-centered decibel distances:
tool_known (order PSD, 0-20 orders, measured shaft speed), tool_known_100 (0-100 orders),
tool_envelope (angular envelope spectrum, 0-20 orders) and tool_estimated (order PSD with the
base from tools/audio_order_estimated, calibrated thresholds; absent when no base is accepted).
Also records every estimated base against the dataset's declared shaft speed.
"""

import argparse
import json
import time
from collections import defaultdict
from dataclasses import replace
from pathlib import Path

import numpy as np

from scripts import difference_screen as screen
from tools.audio_order_estimated.estimator import EstimatorConfig, estimate_base
from tools.audio_order_known.analysis import OrderConfig, order_analysis

TOOL_METHODS = ("tool_known", "tool_known_100", "tool_envelope", "tool_estimated")
ESTIMATOR = replace(EstimatorConfig(), min_score=0.2, min_margin=0.0)
ESTIMATES = []
_features = screen.features
_vectors = screen.vectors
_decide = screen.decide


def level(power):
    values = 10 * np.log10(np.maximum(power, 1e-30))
    return values - values.mean()


def tool_features(samples, rate, shaft_hz):
    samples = np.asarray(samples, dtype=float)
    out = _features(samples, rate, shaft_hz)
    _, narrow = order_analysis(samples, rate, shaft_hz)
    out.update(tool_known=level(narrow["order_psd"]),
               tool_envelope=level(narrow["envelope_order_psd"]))
    try:
        _, wide = order_analysis(samples, rate, shaft_hz, OrderConfig(max_order=100.0))
        out["tool_known_100"] = level(wide["order_psd"])
    except ValueError:
        pass
    result, trace = estimate_base(samples, rate, ESTIMATOR)
    record = {"declared_hz": shaft_hz, "status": result["status"],
              "estimated_hz": result.get("base_hz_median")}
    if trace is not None:
        start, end = result["valid_start_sample"], result["valid_end_sample_exclusive"]
        try:
            _, estimated = order_analysis(samples[start:end], rate, trace)
            out["tool_estimated"] = level(estimated["order_psd"])
        except ValueError as error:
            record["status"] = f"order analysis failed: {error}"
    ESTIMATES.append(record)
    return out


def tool_vectors(item, normal):
    out = _vectors(item, normal)
    out.update({key: item[key] for key in TOOL_METHODS if key in item})
    return out


def tool_decide(query, references, method):
    if method in TOOL_METHODS and method not in query:
        return ["unavailable"], {}
    return _decide(query, references, method)


def tool_distance(method, first, second):
    if method in TOOL_METHODS:
        return float(np.sqrt(np.mean((first[method] - second[method]) ** 2)))
    return _distance(method, first, second)


_distance = screen.distance
screen.features = tool_features
screen.vectors = tool_vectors
screen.decide = tool_decide
screen.distance = tool_distance
screen.SELECTED[:] = ["raw", "order", *TOOL_METHODS]


def estimator_summary():
    groups = defaultdict(lambda: {"recordings": 0, "accepted": 0, "within_3_percent": 0,
                                  "ratios": defaultdict(int)})
    for record in ESTIMATES:
        cell = groups[record["dataset"]]
        cell["recordings"] += 1
        if record["estimated_hz"] is not None and record["status"].startswith("accepted"):
            cell["accepted"] += 1
            ratio = record["estimated_hz"] / record["declared_hz"]
            cell["within_3_percent"] += abs(ratio - 1) < 0.03
            cell["ratios"][f"{round(ratio * 4) / 4:g}"] += 1
    return {name: {**cell, "ratios": dict(cell["ratios"])} for name, cell in groups.items()}


def main():
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--ottawa", default="data/ottawa-simulation-v1")
    parser.add_argument("--uored", default="data/raw/uored-v5")
    parser.add_argument("--mafaulda-cache", default="data/derived/mafaulda-microphone")
    parser.add_argument("--mafaulda-audit", default="outputs/mafaulda-audit-v1/files.json")
    parser.add_argument("--ratios", type=float, nargs="+", default=[1.0, 1.1, 1.3, 1.6, 2.0])
    parser.add_argument("--query-limit", type=int, default=400)
    parser.add_argument("--datasets", nargs="+", default=["ottawa", "uored", "mafaulda"])
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=False)
    started = time.perf_counter()
    rows = []
    loaders = {"ottawa": lambda: screen.ottawa(args.ottawa),
               "uored": lambda: screen.uored(args.uored),
               "mafaulda": lambda: screen.mafaulda(args.mafaulda_cache, args.mafaulda_audit,
                                                   args.ratios, args.query_limit)}
    for name in args.datasets:
        first = len(ESTIMATES)
        rows += loaders[name]()
        for record in ESTIMATES[first:]:
            record["dataset"] = name
        print(name, "done", round(time.perf_counter() - started), "s", flush=True)
    summary = {}
    for name in sorted({row["dataset"] for row in rows}):
        cells = defaultdict(lambda: [0, 0, 0])
        for row in rows:
            if row["dataset"] != name:
                continue
            cell = cells[(row["scenario"], row["method"])]
            cell[0] += row["ranked"][0] == row["expected"]
            cell[1] += 1
            cell[2] += row["ranked"] == ["unavailable"]
        summary[name] = [{"scenario": s, "method": m, "correct": c, "total": t,
                          "unavailable": u} for (s, m), (c, t, u) in sorted(cells.items())]
    (args.output / "decisions.json").write_text(json.dumps(rows), encoding="utf-8")
    (args.output / "summary.json").write_text(json.dumps({
        "methods": screen.SELECTED, "estimator": ESTIMATOR.__dict__,
        "estimator_check": estimator_summary(), "results": summary,
        "seconds": round(time.perf_counter() - started, 1)}, indent=2), encoding="utf-8")
    for name, cells in summary.items():
        for cell in cells:
            print(name, cell["scenario"], cell["method"], f"{cell['correct']}/{cell['total']}",
                  f"unavailable {cell['unavailable']}" if cell["unavailable"] else "")
    print(json.dumps(estimator_summary(), indent=1))


if __name__ == "__main__":
    main()
