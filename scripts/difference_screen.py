"""Screen raw, normal-subtracted and speed-aware spectra with nearest-reference rules; no model."""

import argparse
import json
import re
import time
from collections import defaultdict
from pathlib import Path

import numpy as np
import soundfile as sf
from scipy import signal
from scipy.io import loadmat

from modelmetis.speed_context import match_speed

BAND = (20.0, 20000.0)
COARSE = 1024
FINE = 32768
ORDERS = np.arange(0.5, 300.0, 0.05)
LOG_STEP = 1 / 96
LOG_GRID = 2 ** np.arange(np.log2(BAND[0]), np.log2(BAND[1]), LOG_STEP)
MAX_SHIFT = int(round(1.2 / LOG_STEP))
METHODS = ("raw", "delta", "order", "delta_order", "shift", "delta_shift", "matched")
SELECTED = list(METHODS)


def welch_db(samples, rate, nperseg):
    samples = np.asarray(samples, dtype=float)
    frequencies, power = signal.welch(samples - samples.mean(), rate, nperseg=nperseg)
    level = 10 * np.log10(np.maximum(power, power.max() * 1e-12))
    keep = (frequencies >= BAND[0]) & (frequencies <= min(BAND[1], rate / 2))
    return frequencies[keep], level[keep]


def centered(values):
    return values - np.nanmean(values)


def on_orders(frequencies, level, shaft_hz):
    orders = frequencies / shaft_hz
    return np.interp(ORDERS, orders, level, left=np.nan, right=np.nan)


def on_log_grid(frequencies, level):
    return np.interp(LOG_GRID, frequencies, level, left=np.nan, right=np.nan)


def rms(first, second):
    both = np.isfinite(first) & np.isfinite(second)
    if both.sum() < 0.2 * min(np.isfinite(first).sum(), np.isfinite(second).sum()):
        return np.inf
    difference = centered(first[both]) - centered(second[both])
    return float(np.sqrt(np.mean(difference ** 2)))


def shifted_rms(first, second, max_shift=MAX_SHIFT):
    best = np.inf
    for shift in range(-max_shift, max_shift + 1):
        if shift >= 0:
            value = rms(first[shift:], second[:len(second) - shift])
        else:
            value = rms(first[:shift], second[-shift:])
        best = min(best, value)
    return best


def features(samples, rate, shaft_hz):
    coarse_f, coarse = welch_db(samples, rate, COARSE)
    fine_f, fine = welch_db(samples, rate, FINE)
    return {"coarse_f": coarse_f, "coarse": coarse, "fine_f": fine_f, "fine": fine,
            "shaft_hz": shaft_hz}


def vectors(item, normal):
    """Representations of one recording; `normal` is the healthy recording of its regime."""
    out = {"raw": centered(item["coarse"]),
           "order": on_orders(item["fine_f"], item["fine"], item["shaft_hz"]),
           "shift": on_log_grid(item["fine_f"], item["fine"])}
    if normal is not None:
        delta_coarse = item["coarse"] - normal["coarse"]
        delta_fine = item["fine"] - normal["fine"]
        out["delta"] = centered(delta_coarse)
        out["delta_order"] = on_orders(item["fine_f"], delta_fine, item["shaft_hz"])
        out["delta_shift"] = on_log_grid(item["fine_f"], delta_fine)
    return out


def distance(method, first, second):
    if method.endswith("shift"):
        return shifted_rms(first[method], second[method])
    if method in {"raw", "delta"}:
        return float(np.sqrt(np.mean((centered(first[method]) - centered(second[method])) ** 2)))
    if method == "matched":
        return float(np.sqrt(np.mean((centered(first["raw"]) - centered(second[method])) ** 2)))
    return rms(first[method], second[method])


def matched_vector(samples, rate, reference_hz, query_hz):
    """Reference spectrum after resampling the recording to the query's shaft speed."""
    resampled, _ = match_speed(samples, rate, reference_hz, query_hz)
    return centered(welch_db(resampled, rate, COARSE)[1])


def zero_delta(item):
    """Healthy reference in the difference methods: no change from its own normal."""
    return {"delta": np.zeros_like(item["coarse"]),
            "delta_order": np.where(np.isfinite(on_orders(item["fine_f"], item["fine"],
                                                          item["shaft_hz"])), 0.0, np.nan),
            "delta_shift": np.zeros_like(LOG_GRID)}


def decide(query, references, method):
    scores = {}
    for label, candidates in references.items():
        values = [distance(method, query, candidate) for candidate in candidates
                  if method in candidate]
        if values:
            scores[label] = min(values)
    ranked = sorted(scores, key=lambda label: (scores[label], label))
    return ranked, scores


def score(rows):
    table = defaultdict(lambda: {"correct": 0, "total": 0, "rank_sum": 0})
    for row in rows:
        cell = table[(row["scenario"], row["method"])]
        cell["total"] += 1
        cell["correct"] += row["ranked"][0] == row["expected"]
        cell["rank_sum"] += row["ranked"].index(row["expected"]) + 1
    return [{"scenario": scenario, "method": method, "correct": cell["correct"],
             "total": cell["total"], "mean_rank": round(cell["rank_sum"] / cell["total"], 2)}
            for (scenario, method), cell in sorted(table.items())]


# MAFAULDA: same rig, references taken at another rotation speed.

def mafaulda_class(member):
    parts = member.split("/")
    return f"{parts[0]}-{parts[1]}" if parts[0] in {"underhang", "overhang"} else parts[0]


def mafaulda(cache, audit, ratios, query_limit):
    index = json.loads((Path(cache) / "index.json").read_text(encoding="utf-8"))
    records = {row["member"]: row for row in json.loads(Path(audit).read_text(encoding="utf-8"))}
    spikes = {member for member, row in records.items() if row["microphone"]["peak"] > 5}
    normal_speeds = sorted(float(m.split("/")[-1][:-4]) for m in index if m.startswith("normal/"))
    items = {}
    for member, name in index.items():
        if member in spikes:
            continue
        nominal = float(member.split("/")[-1][:-4])
        measured = records[member]["rotation_hz"]
        shaft = measured if measured and abs(measured / nominal - 0.977) < 0.03 else 0.977 * nominal
        speed_index = int(np.argmin([abs(nominal - value) for value in normal_speeds]))
        items[member] = {"class": mafaulda_class(member), "speed_index": speed_index,
                         "severity": member.split("/")[-2], "cache": Path(cache) / name,
                         "shaft_hz": shaft}
    loaded = {}

    def load(member):
        if member not in loaded:
            item = items[member]
            loaded[member] = {**features(np.load(item["cache"]), 50000, item["shaft_hz"]),
                              **{k: item[k] for k in ("class", "speed_index", "severity")}}
        return loaded[member]

    normals = {items[m]["speed_index"]: m for m in items if items[m]["class"] == "normal"}
    by_cell = defaultdict(list)
    for member, item in items.items():
        by_cell[(item["class"], item["speed_index"])].append(member)
    classes = sorted({item["class"] for item in items.values()})
    queries = sorted(m for m, item in items.items() if item["class"] != "normal")
    rng = np.random.default_rng(20261001)
    if query_limit and len(queries) > query_limit:
        queries = sorted(rng.choice(queries, query_limit, replace=False).tolist())
    rows = []
    for member in queries:
        query_item = items[member]
        for ratio in ratios:
            target = normal_speeds[query_item["speed_index"]] * ratio
            ref_index = int(np.argmin([abs(target - value) for value in normal_speeds]))
            if abs(normal_speeds[ref_index] / target - 1) > 0.03:
                continue
            references = {}
            for label in classes:
                pool = sorted(m for m in by_cell.get((label, ref_index), []) if m != member)
                if not pool:
                    break
                references[label] = pool[len(pool) // 2]
            if len(references) != len(classes):
                continue
            query = load(member)
            query_vectors = vectors(query, load(normals[query_item["speed_index"]]))
            reference_vectors = {}
            for label, ref in references.items():
                ref_loaded = load(ref)
                if label == "normal":
                    base = vectors(ref_loaded, None)
                    base.update(zero_delta(ref_loaded))
                else:
                    base = vectors(ref_loaded, load(normals[ref_index]))
                if "matched" in SELECTED:
                    base["matched"] = matched_vector(np.load(items[ref]["cache"]), 50000,
                                                     items[ref]["shaft_hz"],
                                                     query_item["shaft_hz"])
                reference_vectors[label] = [base]
            for method in SELECTED:
                ranked, _ = decide(query_vectors, reference_vectors, method)
                rows.append({"dataset": "MAFAULDA", "scenario": f"speed x{ratio:g}",
                             "method": method, "query": member, "expected": query_item["class"],
                             "ranked": ranked})
    return rows


# UORED: references from other bearings; each bearing's own healthy state is its normal.

UORED_CLASSES = {"I": "inner_race", "O": "outer_race", "B": "ball", "C": "cage"}


def uored(root):
    items = {}
    for path in sorted(Path(root).rglob("*.mat")):
        letter, bearing, state = re.fullmatch(r"([HIOBC])_(\d+)_([012])", path.stem).groups()
        data = next(v for k, v in loadmat(path).items() if not k.startswith("__"))
        rpm = float(np.unique(data[:, 2][data[:, 2] != 0])[0])
        items[path.stem] = {**features(data[:, 1], 42000, rpm / 60), "bearing": int(bearing),
                            "state": state, "class": UORED_CLASSES.get(letter, "healthy"),
                            "samples": data[:, 1]}
    healthy = {item["bearing"]: key for key, item in items.items() if item["state"] == "0"}
    fault_class = {item["bearing"]: item["class"] for item in items.values()
                   if item["state"] != "0"}
    rows = []
    for key, item in items.items():
        if item["state"] == "0":
            continue
        query = vectors(item, items[healthy[item["bearing"]]])
        references = defaultdict(list)
        for other in items.values():
            if other["bearing"] == item["bearing"] or other["state"] != item["state"]:
                continue
            base = vectors(other, items[healthy[other["bearing"]]])
            if "matched" in SELECTED:
                base["matched"] = matched_vector(other["samples"], 42000, other["shaft_hz"],
                                                 item["shaft_hz"])
            references[other["class"]].append(base)
        healthy_refs = []
        for bearing, healthy_key in healthy.items():
            if bearing == item["bearing"]:
                continue
            base = vectors(items[healthy_key], None)
            base.update(zero_delta(items[healthy_key]))
            if "matched" in SELECTED:
                base["matched"] = matched_vector(items[healthy_key]["samples"], 42000,
                                                 items[healthy_key]["shaft_hz"], item["shaft_hz"])
            healthy_refs.append(base)
        references["healthy"] = healthy_refs
        for method in SELECTED:
            ranked, _ = decide(query, references, method)
            rows.append({"dataset": "UORED", "scenario": f"other bearings, state {item['state']}",
                         "method": method, "query": key, "expected": fault_class[item["bearing"]],
                         "ranked": ranked})
    return rows


# Ottawa: profile-1 unloaded references (15 Hz), profile-2 queries (30 Hz), healthy per cell.

OTTAWA = {"H_H": "healthy", "R_U": "rotor_unbalance", "R_M": "rotor_misalignment",
          "S_W": "stator_winding", "V_U": "voltage_unbalance", "B_R": "bowed_rotor",
          "K_A": "broken_rotor_bars", "F_B": "faulty_bearing"}
DRIVE_HZ = {1: 15.0, 2: 30.0}


def ottawa(source):
    source = Path(source)
    items = {}
    for entry in json.loads((source / "sealed/references.json").read_text(encoding="utf-8")):
        stem = Path(entry["source_path"]).stem
        code, profile, load = re.fullmatch(r"([A-Z]_[A-Z])_([1-8])_([01])", stem).groups()
        if int(profile) not in DRIVE_HZ:
            continue
        samples, rate = sf.read(source / entry["partition"] / f"{entry['sample_id']}.wav")
        items[stem] = {**features(samples, rate, DRIVE_HZ[int(profile)]), "class": OTTAWA[code],
                       "profile": int(profile), "load": int(load), "samples": samples,
                       "rate": rate}
    references = {}
    sources = {}
    for item in items.values():
        if item["profile"] == 1 and item["load"] == 0:
            if item["class"] == "healthy":
                base = vectors(item, None)
                base.update(zero_delta(item))
            else:
                base = vectors(item, items["H_H_1_0"])
            references[item["class"]] = [base]
            sources[item["class"]] = item
    rows = []
    for key, item in items.items():
        if item["profile"] != 2 or item["class"] == "healthy":
            continue
        query = vectors(item, items[f"H_H_2_{item['load']}"])
        if "matched" in SELECTED:
            for label, source_item in sources.items():
                references[label][0]["matched"] = matched_vector(
                    source_item["samples"], source_item["rate"], source_item["shaft_hz"],
                    item["shaft_hz"])
        for method in SELECTED:
            ranked, _ = decide(query, references, method)
            rows.append({"dataset": "Ottawa", "scenario": "profile 1 -> 2, faults",
                         "method": method, "query": key, "expected": item["class"],
                         "ranked": ranked})
    return rows


def run(args):
    started = time.perf_counter()
    output = Path(args.output)
    output.mkdir(parents=True, exist_ok=False)
    rows = []
    if "ottawa" in args.datasets:
        rows += ottawa(args.ottawa)
    if "uored" in args.datasets:
        rows += uored(args.uored)
    if "mafaulda" in args.datasets:
        rows += mafaulda(args.mafaulda_cache, args.mafaulda_audit, args.ratios, args.query_limit)
    summary = {name: score([row for row in rows if row["dataset"] == name])
               for name in ("Ottawa", "UORED", "MAFAULDA")
               if any(row["dataset"] == name for row in rows)}
    (output / "decisions.json").write_text(json.dumps(rows), encoding="utf-8")
    (output / "summary.json").write_text(json.dumps({
        "summary": summary, "methods": SELECTED, "elapsed_seconds": time.perf_counter() - started,
        "settings": {"band_hz": BAND, "coarse_nperseg": COARSE, "fine_nperseg": FINE,
                     "orders": [float(ORDERS[0]), float(ORDERS[-1]), 0.05],
                     "log_step_octave": LOG_STEP, "max_shift_octave": MAX_SHIFT * LOG_STEP,
                     "ratios": args.ratios, "query_limit": args.query_limit,
                     "datasets": args.datasets}}, indent=1),
        encoding="utf-8")
    return summary


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--ottawa", type=Path, default=Path("data/ottawa-simulation-v1"))
    parser.add_argument("--uored", type=Path, default=Path("data/raw/uored-v5"))
    parser.add_argument("--mafaulda-cache", type=Path,
                        default=Path("data/derived/mafaulda-microphone"))
    parser.add_argument("--mafaulda-audit", type=Path,
                        default=Path("outputs/mafaulda-audit-v1/files.json"))
    parser.add_argument("--ratios", type=float, nargs="+", default=[1.0, 1.1, 1.3, 1.6, 2.0])
    parser.add_argument("--query-limit", type=int, default=400)
    parser.add_argument("--datasets", nargs="+", default=["ottawa", "uored", "mafaulda"])
    parser.add_argument("--methods", nargs="+", default=list(METHODS), choices=METHODS)
    arguments = parser.parse_args()
    SELECTED[:] = arguments.methods
    summary = run(arguments)
    for dataset, table in summary.items():
        for row in table:
            print(dataset, row)
