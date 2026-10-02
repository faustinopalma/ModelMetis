import argparse

import numpy as np

from tools.audio_order_known.analysis import order_analysis
from tools.audio_order_known.cli import common_arguments, normalization_config
from tools.audio_order_known.report import read_audio, write_report

from .estimator import EstimatorConfig, estimate_base


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Normalize audio using an estimated acoustic base.")
    common_arguments(parser, "tools/audio_order_estimated")
    parser.add_argument("--min-hz", type=float, default=10)
    parser.add_argument("--max-hz", type=float, default=300)
    parser.add_argument("--frame-seconds", type=float, default=0.5)
    parser.add_argument("--hop-seconds", type=float, default=0.1)
    args = parser.parse_args(argv)
    try:
        if args.output.exists():
            raise ValueError("Output already exists; choose a new directory.")
        samples, rate, audit = read_audio(args.audio, args.start, args.duration, args.channel)
        config = EstimatorConfig(min_hz=args.min_hz, max_hz=args.max_hz,
                                 frame_seconds=args.frame_seconds, hop_seconds=args.hop_seconds)
        estimation, base = estimate_base(samples, rate, config)
        reference = {"kind": "estimated_acoustic_base", "estimation": estimation}
        metadata, arrays = {"status": "unavailable", "reason": estimation["reason"]}, {}
        if base is not None:
            start = estimation["valid_start_sample"]
            end = estimation["valid_end_sample_exclusive"]
            try:
                metadata, arrays = order_analysis(samples[start:end], rate, base,
                                                   normalization_config(args))
                metadata.update({"status": "available", "analysis_start_seconds": start / rate,
                                  "analysis_end_seconds": end / rate})
                arrays["map_times_seconds"] += start / rate
                arrays["angular_times_seconds"] += start / rate
                arrays.update({"base_hz": base,
                               "base_times_seconds": np.arange(start, end) / rate})
            except ValueError as error:
                metadata = {"status": "unavailable", "reason": str(error)}
        write_report(args.output, samples, rate, audit, reference, metadata, arrays)
    except (ValueError, OSError) as error:
        parser.exit(2, f"Error: {error}\n")
    print(args.output / "report.html")
    return 0 if metadata["status"] == "available" else 3


if __name__ == "__main__":
    raise SystemExit(main())