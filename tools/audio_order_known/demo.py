import argparse
import csv
import json
from pathlib import Path

import numpy as np
import soundfile as sf
from scipy.integrate import cumulative_trapezoid

from tools.audio_order_estimated.cli import main as estimated_main

from .cli import main as known_main


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Build isolated synthetic examples for both tools.")
    parser.add_argument("--name", default="demo-v1")
    args = parser.parse_args(argv)
    if not args.name or any(character not in "abcdefghijklmnopqrstuvwxyz0123456789-_"
                            for character in args.name):
        parser.error("Use a lowercase name containing letters, digits, '-' or '_'.")
    known_folder = Path(__file__).resolve().parent
    estimated_folder = known_folder.parent / "audio_order_estimated"
    inputs = known_folder / "runs" / (args.name + "-inputs")
    known_output = known_folder / "runs" / args.name
    estimated_output = estimated_folder / "runs" / args.name
    if any(path.exists() for path in (inputs, known_output, estimated_output)):
        parser.error("A demo directory already exists; use a new --name.")
    inputs.mkdir(parents=True)
    rate = 8000
    clock = np.arange(rate * 6) / rate
    base = 30 + 2 * clock
    phase = 2 * np.pi * cumulative_trapezoid(base, dx=1 / rate, initial=0)
    samples = sum(amplitude * np.cos(order * phase)
                  for order, amplitude in ((1, 0.12), (2, 0.5), (3, 0.22), (5, 0.08)))
    samples += np.random.default_rng(731).normal(0, 0.015, len(samples))
    source = inputs / "synthetic-runup.wav"
    sf.write(source, samples, rate, subtype="FLOAT")
    trace = inputs / "synthetic-rpm.csv"
    with trace.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.writer(stream)
        writer.writerow(["time_seconds", "rpm"])
        for instant in np.linspace(0, 6, 61):
            writer.writerow([float(instant), float((30 + 2 * instant) * 60)])
    known_main([str(source), "--rpm-trace", str(trace), "--output", str(known_output)])
    result = estimated_main([str(source), "--output", str(estimated_output)])
    if result != 0:
        raise RuntimeError("The synthetic estimator demo was not accepted.")
    with np.load(estimated_output / "arrays.npz") as arrays:
        truth = 30 + 2 * arrays["base_times_seconds"]
        error = np.abs(arrays["base_hz"] / truth - 1)
        maximum = float(error.max())
        median = float(np.median(error))
    known = json.loads((known_output / "measurements.json").read_text(encoding="utf-8"))
    estimated = json.loads((estimated_output / "measurements.json").read_text(encoding="utf-8"))
    summary = {"fixture": "synthetic run-up with four harmonics and seeded Gaussian noise",
               "duration_seconds": 6, "sample_rate": rate, "seed": 731,
               "shaft_hz_start": 30, "shaft_hz_end": 42,
               "known_dominant_order": known["normalization"]["peak_orders"][0],
               "estimated_dominant_order": estimated["normalization"]["peak_orders"][0],
               "max_relative_base_error": maximum, "median_relative_base_error": median,
               "scope": "Synthetic implementation check; no real-machine accuracy claim."}
    assert maximum < 0.025, summary
    assert summary["known_dominant_order"] == 2, summary
    assert summary["estimated_dominant_order"] == 2, summary
    (inputs / "validation.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())