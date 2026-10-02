"""Recompute the Ottawa distance geometry quoted in docs/RESULTS.md from the published record.

Distances keep each representation's units: dB for the Welch views.
"""

import argparse
import json
from collections import Counter
from pathlib import Path

DEFAULT = Path(__file__).resolve().parents[1] / "examples/archive/results/family-separation.json"


def geometry(rows, view):
    row = next(item for item in rows if item["dataset"] == "Ottawa" and item["view"] == view)
    groups, distances = row["groups"], row["group_distances"]
    references = [i for i, group in enumerate(groups) if group["regime"] == "profile1-load0"]
    queries = [i for i, group in enumerate(groups) if group["regime"].startswith("profile2")]
    spreads, leads, nearest, cross_speed, same_speed = [], [], Counter(), 0, 0
    for query in queries:
        ranked = sorted((distances[query][ref], groups[ref]["class"]) for ref in references)
        spreads.append(ranked[-1][0] - ranked[0][0])
        leads.append(ranked[1][0] - ranked[0][0])
        nearest[ranked[0][1]] += 1
        cross_speed += ranked[0][1] == groups[query]["class"]
        other_load = [i for i in queries if groups[i]["regime"] != groups[query]["regime"]]
        closest = min(other_load, key=lambda i: distances[query][i])
        same_speed += groups[closest]["class"] == groups[query]["class"]
    return {
        "view": view,
        "queries": len(queries),
        "profile1_reference_correct": cross_speed,
        "reference_spread": [round(min(spreads), 2), round(max(spreads), 2)],
        "nearest_lead": [round(min(leads), 2), round(max(leads), 2)],
        "nearest_reference_classes": dict(nearest),
        "same_speed_other_load_correct": same_speed,
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=DEFAULT)
    parser.add_argument("--view", action="append",
                        help="Representation; default: baseline, welch, cepstrum, stft.")
    args = parser.parse_args()
    rows = json.loads(args.source.read_text(encoding="utf-8"))
    for view in args.view or ["baseline", "welch", "cepstrum", "stft"]:
        print(json.dumps(geometry(rows, view)))
