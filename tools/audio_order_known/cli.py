import argparse
import csv
import io
from pathlib import Path

import numpy as np

from .analysis import OrderConfig, order_analysis
from .report import read_audio, write_report


def common_arguments(parser, directory):
    parser.add_argument("audio", type=Path)
    parser.add_argument("--output", type=Path, required=True,
                        help=f"New report directory, for example {directory}/runs/example")
    parser.add_argument("--start", type=float, default=0)
    parser.add_argument("--duration", type=float, default=10)
    parser.add_argument("--channel", type=int, default=1, help="1-based native channel")
    parser.add_argument("--max-order", type=float, default=20)
    parser.add_argument("--samples-per-cycle", type=int, default=512)
    parser.add_argument("--cycles-per-frame", type=int, default=8)


def rpm_trace(payload, clock):
    reader = csv.DictReader(io.StringIO(payload.decode("utf-8-sig")))
    if reader.fieldnames != ["time_seconds", "rpm"]:
        raise ValueError("RPM CSV requires exactly time_seconds,rpm headers.")
    rows = list(reader)
    if len(rows) < 2 or any(None in row or None in row.values() for row in rows):
        raise ValueError("RPM CSV requires at least two complete rows.")
    values = np.asarray([[float(row["time_seconds"]), float(row["rpm"])] for row in rows])
    if (not np.isfinite(values).all() or np.any(values[:, 1] <= 0)
            or np.any(np.diff(values[:, 0]) <= 0) or values[0, 0] > clock[0]
            or values[-1, 0] < clock[-1]):
        raise ValueError("RPM times must increase and cover the selection; "
                 "speeds must be positive.")
    return np.interp(clock, values[:, 0], values[:, 1]) / 60


def normalization_config(args):
    return OrderConfig(samples_per_cycle=args.samples_per_cycle,
                       cycles_per_frame=args.cycles_per_frame, max_order=args.max_order)


def main(argv=None):
    import hashlib

    parser = argparse.ArgumentParser(description="Normalize audio using supplied shaft RPM.")
    common_arguments(parser, "tools/audio_order_known")
    speed = parser.add_mutually_exclusive_group(required=True)
    speed.add_argument("--rpm", type=float, help="Constant shaft RPM during selected interval")
    speed.add_argument("--rpm-trace", type=Path, help="CSV in absolute recording seconds")
    args = parser.parse_args(argv)
    try:
        if args.output.exists():
            raise ValueError("Output already exists; choose a new directory.")
        samples, rate, audit = read_audio(args.audio, args.start, args.duration, args.channel)
        clock = np.arange(len(samples)) / rate
        reference = {"kind": "known_rpm", "source": "user_supplied", "rpm": args.rpm,
                     "constant_speed_assumption": args.rpm is not None}
        if args.rpm_trace:
            payload = args.rpm_trace.read_bytes()
            base = rpm_trace(payload, clock + audit["start_seconds"])
            reference.update({"trace_sha256": hashlib.sha256(payload).hexdigest(),
                               "trace_interpolation": "linear; no extrapolation"})
        else:
            base = np.full(len(samples), args.rpm / 60)
        metadata, arrays = order_analysis(samples, rate, base, normalization_config(args))
        metadata["status"] = "available"
        arrays.update({"base_times_seconds": clock, "base_hz": base})
        write_report(args.output, samples, rate, audit, reference, metadata, arrays)
    except (ValueError, OSError) as error:
        parser.exit(2, f"Error: {error}\n")
    print(args.output / "report.html")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())