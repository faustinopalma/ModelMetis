"""Audit the MAFAULDA archive in place: structure, labels, regimes and signal quality."""

import argparse
import hashlib
import json
import time
import zipfile
from collections import Counter, defaultdict
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np

SOURCE_URL = "https://www02.smt.ufrj.br/~offshore/mfs/database/mafaulda/full.zip"
RATE = 50000
SAMPLES = 250000
COLUMNS = ("tachometer", "underhang_axial", "underhang_radial", "underhang_tangential",
           "overhang_axial", "overhang_radial", "overhang_tangential", "microphone")
PUBLISHED = {"normal": 49, "imbalance": 333, "horizontal-misalignment": 197,
             "vertical-misalignment": 301, "underhang": 558, "overhang": 513}


def download(path, url=SOURCE_URL, chunk=1 << 22):
    from urllib.request import Request, urlopen

    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with urlopen(Request(url, method="HEAD")) as response:
        total = int(response.headers["Content-Length"])
    done = path.stat().st_size if path.exists() else 0
    if done < total:
        request = Request(url, headers={"Range": f"bytes={done}-"})
        with urlopen(request) as response, open(path, "ab") as target:
            if response.status != 206:
                raise ValueError("The server ignored the resume request.")
            while block := response.read(chunk):
                target.write(block)
    if path.stat().st_size != total:
        raise ValueError("Downloaded size differs from the published Content-Length.")
    return path


def digest_file(path, chunk=1 << 24):
    value = hashlib.sha256()
    with open(path, "rb") as handle:
        while block := handle.read(chunk):
            value.update(block)
    return value.hexdigest()


def label(member):
    parts = [part for part in member.split("/") if part]
    if parts and parts[0] == "full":
        parts = parts[1:]
    family = parts[0]
    position = None
    if family in {"underhang", "overhang"}:
        position, family, severity = parts[0], f"bearing-{parts[1]}", parts[2]
    elif family == "normal":
        severity = None
    else:
        severity = parts[1]
    return {"family": family, "position": position, "severity": severity,
            "file_value": Path(parts[-1]).stem}


def rotation_hz(tach):
    level = (np.percentile(tach, 99) + np.percentile(tach, 1)) / 2
    above = tach > level
    edges = np.flatnonzero(~above[:-1] & above[1:])
    if len(edges) < 3:
        return None, len(edges)
    period = np.median(np.diff(edges)) / RATE
    return float(1 / period), int(len(edges))


def inspect(task):
    archive, member = task
    # ZipFile.read verifies the member CRC.
    with zipfile.ZipFile(archive) as source:
        payload = source.read(member)
    text = payload.decode("ascii").replace("\r", "").strip()
    rows = text.count("\n") + 1
    values = np.fromstring(text.replace("\n", ","), sep=",")
    record = {"member": member, **label(member), "bytes": len(payload),
              "sha256": hashlib.sha256(payload).hexdigest(), "rows": rows}
    if values.size != rows * len(COLUMNS):
        return {**record, "status": "malformed", "values": int(values.size)}
    data = values.reshape(rows, len(COLUMNS))
    mic = data[:, 7]
    speed, edges = rotation_hz(data[:, 0])
    return {
        **record, "status": "ok", "finite": bool(np.isfinite(data).all()),
        "rotation_hz": speed, "tachometer_edges": edges,
        "microphone_sha256": hashlib.sha256(np.ascontiguousarray(mic).tobytes()).hexdigest(),
        "microphone": {"mean": float(mic.mean()), "rms_ac": float(mic.std()),
                       "peak": float(np.abs(mic).max()), "min": float(mic.min()),
                       "max": float(mic.max()), "distinct": int(np.unique(mic).size),
                       "at_extremes": float(np.mean((mic == mic.max()) | (mic == mic.min())))},
        "channel_rms_ac": {name: float(data[:, i].std()) for i, name in enumerate(COLUMNS)},
    }


def summarize(records, archive, elapsed):
    ok = [row for row in records if row["status"] == "ok"]
    counts = Counter(row["family"] if row["position"] is None else row["position"]
                     for row in records)
    cells = defaultdict(int)
    for row in records:
        cells[(row["family"], row["position"], row["severity"])] += 1
    duplicates = Counter(row["microphone_sha256"] for row in ok)
    folder = lambda row: row["member"].rsplit("/", 1)[0]  # noqa: E731
    normal = sorted(float(row["file_value"]) for row in ok if row["family"] == "normal")
    gaps = [min(abs(float(row["file_value"]) - value) for value in normal)
            for row in ok if row["family"] != "normal" and normal]
    mic_rms = [row["microphone"]["rms_ac"] for row in ok]
    named = [(row["rotation_hz"], float(row["file_value"])) for row in ok if row["rotation_hz"]]
    ratio = np.array([measured / value for measured, value in named])
    typical = float(np.median(ratio)) if ratio.size else None
    failed = [row for row in ok if row["rotation_hz"]
              and abs(row["rotation_hz"] / float(row["file_value"]) - typical) > 0.03]
    spikes = [row for row in ok if row["microphone"]["peak"] > 5]
    return {
        "dataset": "MAFAULDA, SpectraQuest MFS-ABVT, Universidade Federal do Rio de Janeiro",
        "source": "https://www02.smt.ufrj.br/~offshore/mfs/page_01.html",
        "archive": {"name": Path(archive).name, "bytes": Path(archive).stat().st_size,
                    "sha256": digest_file(archive)},
        "license": "No license statement on the publisher page; reuse rights unresolved.",
        "files": len(records), "ok": len(ok),
        "malformed": [row["member"] for row in records if row["status"] != "ok"],
        "nonfinite": [row["member"] for row in ok if not row["finite"]],
        "wrong_length": [row["member"] for row in ok if row["rows"] != SAMPLES],
        "family_counts": dict(counts), "published_counts": PUBLISHED,
        "cells": [{"family": f, "position": p, "severity": s, "files": n}
                  for (f, p, s), n in sorted(cells.items(), key=lambda x: tuple(map(str, x[0])))],
        "duplicate_microphone_groups": sum(count > 1 for count in duplicates.values()),
        "filename_rotation_hz_normal": {"count": len(normal), "min": min(normal, default=None),
                                        "max": max(normal, default=None)},
        "fault_to_nearest_normal_filename_hz": {
            "count": len(gaps), "median": float(np.median(gaps)) if gaps else None,
            "p95": float(np.percentile(gaps, 95)) if gaps else None,
            "max": float(max(gaps)) if gaps else None,
            "exact": sum(gap == 0 for gap in gaps)},
        "missing_rotation": [row["member"] for row in ok if row["rotation_hz"] is None],
        "tachometer_estimator_failures_by_folder": dict(Counter(map(folder, failed))),
        "microphone_peak_over_5_by_folder": dict(Counter(map(folder, spikes))),
        "microphone_peak_values_over_5": dict(Counter(str(round(row["microphone"]["peak"], 2))
                                                      for row in spikes).most_common(3)),
        "tachometer_over_filename": {"count": int(ratio.size),
                                     "quantiles": np.quantile(ratio, [0, 0.05, 0.5, 0.95, 1])
                                     .round(4).tolist() if ratio.size else None},
        "microphone_rms_ac": {"min": min(mic_rms), "median": float(np.median(mic_rms)),
                              "max": max(mic_rms)},
        "microphone_constant": [row["member"] for row in ok if row["microphone"]["rms_ac"] == 0],
        "elapsed_seconds": elapsed,
    }


def run(archive, output, workers):
    started = time.perf_counter()
    archive, output = Path(archive).resolve(), Path(output).resolve()
    output.mkdir(parents=True, exist_ok=False)
    with zipfile.ZipFile(archive) as source:
        members = sorted(name for name in source.namelist() if name.lower().endswith(".csv"))
        others = sorted(name for name in source.namelist()
                        if not name.endswith("/") and not name.lower().endswith(".csv"))
    with ProcessPoolExecutor(workers) as pool:
        records = list(pool.map(inspect, [(str(archive), name) for name in members], chunksize=4))
    (output / "files.json").write_text(json.dumps(records, indent=1), encoding="utf-8")
    summary = summarize(records, archive, time.perf_counter() - started)
    summary["non_csv_members"] = others
    (output / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    return summary


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--archive", type=Path, default=Path("data/raw/mafaulda/full.zip"))
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--workers", type=int, default=8)
    parser.add_argument("--download", action="store_true",
                        help="Fetch or resume the archive from the UFRJ site first.")
    parser.add_argument("--from-files", type=Path,
                        help="Rebuild the summary from an existing files.json.")
    args = parser.parse_args()
    if args.from_files:
        records = json.loads(args.from_files.read_text(encoding="utf-8"))
        args.output.mkdir(parents=True, exist_ok=False)
        summary = summarize(records, args.archive, None)
        (args.output / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
        print(json.dumps({k: v for k, v in summary.items() if k != "cells"}, indent=2))
        raise SystemExit
    if args.download:
        download(args.archive)
    print(json.dumps(run(args.archive, args.output, args.workers), indent=2))
