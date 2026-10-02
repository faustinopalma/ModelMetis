"""Write the aggregate speed-normalization record published at examples/results/."""

import argparse
import json
from collections import defaultdict
from pathlib import Path

MODEL_ARMS = {
    "reports": "Reports only",
    "speed": "Reports plus stated speed and an order-axis figure",
    "matched": "Reference recordings resampled to the query speed",
    "normalized_known": "Speed-normalized reports, measured shaft speed",
    "normalized_estimated": "Speed-normalized reports, base frequency estimated from audio",
}
NUMERIC = {"raw": "Nearest Welch spectrum in hertz",
           "tool_known_100": "Nearest order spectrum, 0-100 orders, measured shaft speed"}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", type=Path, default=Path("outputs/speed-normalized-v1"))
    parser.add_argument("--numeric", type=Path, default=Path("outputs/order-tools-check-v1"))
    parser.add_argument("--output", type=Path,
                        default=Path("examples/results/speed-normalization-summary.json"))
    args = parser.parse_args()
    evaluation = json.loads((args.model / "evaluation.json").read_text(encoding="utf-8"))
    cells = defaultdict(lambda: [0, 0])
    for row in evaluation["rows"]:
        if row["arm"] in MODEL_ARMS:
            for key in (f"x{row['ratio']:g}", "all"):
                cells[(row["arm"], key)][0] += row["predicted"] == row["expected"]
                cells[(row["arm"], key)][1] += 1
    model = [{"arm": arm, "description": text,
              "correct": {key: f"{c}/{t}" for (a, key), (c, t) in sorted(cells.items())
                          if a == arm}} for arm, text in MODEL_ARMS.items()]
    summary = json.loads((args.numeric / "summary.json").read_text(encoding="utf-8"))
    numeric = [{"method": method, "description": text,
                "correct": {cell["scenario"].replace("speed ", ""):
                            f"{cell['correct']}/{cell['total']}"
                            for cell in summary["results"]["MAFAULDA"]
                            if cell["method"] == method}} for method, text in NUMERIC.items()]
    record = {
        "dataset": "MAFAULDA machinery fault database, microphone channel; 10 conditions "
                   "(normal, imbalance, two misalignments, three bearing defects in two "
                   "positions); one reference per condition at a speed 1.0-2.0 times the "
                   "query's; 167 recordings with microphone spikes excluded",
        "model": "GPT-5.6 Sol 2026-07-09, low reasoning effort, same prompt and decision "
                 "schema as the simple method",
        "model_cases": "72 seeded cases: 2 queries for each of 9 fault classes at speed ratios "
                       "1.0, 1.1, 1.3 and 2.0",
        "model_results": model,
        "numeric_queries": "400 seeded fault queries, each compared at every ratio where all "
                           "ten references exist",
        "numeric_results": numeric,
        "estimator_check": summary["estimator_check"],
        "chance": "1 in 10",
        "sources": ["scripts/speed_normalized_experiment.py", "scripts/order_tools_check.py",
                    "tools/audio_order_known", "tools/audio_order_estimated"],
    }
    args.output.write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(record, indent=2))


if __name__ == "__main__":
    main()
