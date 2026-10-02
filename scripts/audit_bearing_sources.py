"""Audit downloaded UORED v5 and FSTF bearing recordings: labels, regimes and signal quality."""

import argparse
import hashlib
import json
import re
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np
from scipy.io import loadmat

UORED_CLASSES = {"H": "healthy", "I": "inner_race", "O": "outer_race", "B": "ball", "C": "cage"}
UORED_STATES = {"0": "healthy", "1": "developing", "2": "faulty"}
FSTF_RATE = 44100


def array(path):
    variables = {key: value for key, value in loadmat(path).items() if not key.startswith("__")}
    if len(variables) != 1:
        raise ValueError(f"Expected one variable in {path}")
    return np.asarray(next(iter(variables.values())), dtype=float)


def signal_stats(values):
    return {"mean": float(values.mean()), "rms_ac": float(values.std()),
            "peak": float(np.abs(values).max()), "distinct": int(np.unique(values).size),
            "sha256": hashlib.sha256(np.ascontiguousarray(values).tobytes()).hexdigest()}


def single_value(column):
    nonzero = np.unique(column[column != 0])
    return float(nonzero[0]) if nonzero.size == 1 else (0.0 if nonzero.size == 0 else None)


def audit_uored(root):
    rows = []
    for path in sorted(Path(root).rglob("*.mat")):
        match = re.fullmatch(r"([HIOBC])_(\d+)_([012])", path.stem)
        data = array(path)
        rows.append({
            "file": path.name, "class": UORED_CLASSES[match[1]], "bearing": int(match[2]),
            "state": UORED_STATES[match[3]], "shape": list(data.shape),
            "finite": bool(np.isfinite(data).all()),
            "microphone": signal_stats(data[:, 1]),
            "speed_rpm_value": single_value(data[:, 2]), "load_n_value": single_value(data[:, 3]),
            "column5_mean": float(data[:, 4].mean()),
        })
    bearings = defaultdict(dict)
    for row in rows:
        bearings[row["bearing"]][row["state"]] = row["class"]
    complete = {bearing: states for bearing, states in bearings.items()
                if {"healthy", "developing", "faulty"} <= set(states)}
    per_class = Counter(states["faulty"] for states in complete.values())
    duplicates = Counter(row["microphone"]["sha256"] for row in rows)
    pairs = []
    for bearing in sorted(complete):
        states = {row["state"]: row for row in rows if row["bearing"] == bearing}
        healthy = states["healthy"]
        for state in ("developing", "faulty"):
            later = states[state]
            pairs.append({"bearing": bearing, "class": later["class"], "state": state,
                          "speed_delta_rpm": later["speed_rpm_value"]
                          - healthy["speed_rpm_value"],
                          "load_change": [healthy["load_n_value"], later["load_n_value"]]})
    deltas = np.abs([pair["speed_delta_rpm"] for pair in pairs])
    return {
        "files": len(rows), "shapes": dict(Counter(str(row["shape"]) for row in rows)),
        "nonfinite": [row["file"] for row in rows if not row["finite"]],
        "bearings_with_all_three_states": len(complete),
        "bearings_per_fault_class": dict(per_class),
        "healthy_only_bearings": sorted(b for b, s in bearings.items() if set(s) == {"healthy"}),
        "speed_rpm_values": dict(Counter(str(row["speed_rpm_value"]) for row in rows)),
        "load_n_values_by_class": {cls: dict(Counter(str(row["load_n_value"]) for row in rows
                                                     if row["class"] == cls))
                                   for cls in UORED_CLASSES.values()},
        "microphone_distinct_values": [min(r["microphone"]["distinct"] for r in rows),
                                       max(r["microphone"]["distinct"] for r in rows)],
        "microphone_rms_ac": [min(r["microphone"]["rms_ac"] for r in rows),
                              max(r["microphone"]["rms_ac"] for r in rows)],
        "duplicate_microphone_groups": sum(count > 1 for count in duplicates.values()),
        "column5_mean_range": [min(r["column5_mean"] for r in rows),
                               max(r["column5_mean"] for r in rows)],
        "records": rows,
        "healthy_to_later_state": pairs,
        "abs_speed_delta_rpm": {"median": float(np.median(deltas)), "max": float(deltas.max()),
                                "over_20_rpm": int((deltas > 20).sum()), "pairs": len(pairs)},
        "load_differs_from_healthy": sum(len(set(p["load_change"])) > 1 for p in pairs),
    }


def audit_fstf(root):
    rows = []
    for path in sorted(Path(root).rglob("*.mat")):
        setup = "air" if "without using the stethoscope" in str(path) else "stethoscope"
        case = re.match(r"Case (\d) - (.+)", path.parent.name)
        speed = re.search(r"(\d+)\s*rpm", path.stem)
        data = array(path).ravel()
        rows.append({"file": str(path.relative_to(root)), "setup": setup,
                     "case": int(case[1]), "class": case[2], "speed_rpm": int(speed[1]),
                     "samples": int(data.size), "seconds_at_44100": data.size / FSTF_RATE,
                     "finite": bool(np.isfinite(data).all()), "signal": signal_stats(data),
                     "at_extremes": float(np.mean((data == data.max()) | (data == data.min())))})
    cells = Counter((row["class"], row["setup"]) for row in rows)
    duplicates = Counter(row["signal"]["sha256"] for row in rows)
    return {
        "files": len(rows), "recordings_per_class_and_setup": {f"{c} | {s}": n
                                                               for (c, s), n in cells.items()},
        "samples": dict(Counter(row["samples"] for row in rows)),
        "nonfinite": [row["file"] for row in rows if not row["finite"]],
        "duplicate_signal_groups": sum(count > 1 for count in duplicates.values()),
        "rms_ac": [min(r["signal"]["rms_ac"] for r in rows),
                   max(r["signal"]["rms_ac"] for r in rows)],
        "records": rows,
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("dataset", choices=["uored", "fstf"])
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = (audit_uored if args.dataset == "uored" else audit_fstf)(args.root.resolve())
    manifest = json.loads((args.root / "manifest.json").read_text(encoding="utf-8"))
    result["source"] = {key: manifest[key] for key in ("dataset", "version", "folder_prefix")}
    result["publisher_sha256_verified_files"] = len(manifest["files"])
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=1), encoding="utf-8")
    print(json.dumps({k: v for k, v in result.items() if k != "records"}, indent=1))
