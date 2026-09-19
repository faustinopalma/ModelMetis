import argparse
import hashlib
import json
import subprocess
import sys
import time
from datetime import UTC, datetime
from pathlib import Path

from modelmetis.learning import validate_split
from modelmetis.simulation import load_samples, write_json


def execute(command: list[str], *, allow_blocked: bool = False) -> bool:
    result = subprocess.run(command, capture_output=True, text=True, timeout=120, check=False)
    if result.returncode == 0:
        return True
    expected = (
        "ValueError: Fewer than two teacher classes; training must not run.",
        "ValueError: No accepted teacher labels; training must not run.",
    )
    if allow_blocked and result.stderr.rstrip().endswith(expected):
        return False
    raise RuntimeError("Learning-curve worker failed; no candidate may be promoted.")


def run(args) -> dict:
    training = load_samples(args.input)
    development = load_samples(args.development)
    if training[0].partition != "train" or development[0].partition != "development":
        raise ValueError("Learning curves use train and development only.")
    validate_split(training + development)
    if (not args.sizes or sorted(set(args.sizes)) != args.sizes
            or args.sizes[0] < 1 or args.sizes[-1] > len(training)):
        raise ValueError("Provide increasing distinct snapshot sizes within the training set.")
    args.output.mkdir(parents=True, exist_ok=False)
    report_path = args.output / "curve.json"
    report = {
        "started_utc": datetime.now(UTC).isoformat(), "complete": False,
        "partition": "development", "promotion": "not_authorized", "snapshots": [],
        "silver_sha256": hashlib.sha256(args.silver.read_bytes()).hexdigest(),
        "worker_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "arrival_order": "sorted opaque sample IDs, Python Random(17).shuffle",
        "limitation": "Exploratory development curve, not independent final validation",
    }
    write_json(report_path, report)
    started = time.perf_counter()
    try:
        for size in args.sizes:
            row = {"observed_examples": size, "status": "running"}
            report["snapshots"].append(row)
            write_json(report_path, report)
            snapshot_started = time.perf_counter()
            directory = args.output / f"student-{size}"
            command = [sys.executable, "-m", "modelmetis.simulation", "train",
                       "--input", str(args.input), "--silver", str(args.silver),
                       "--sample-count", str(size), "--output", str(directory)]
            if not execute(command, allow_blocked=True):
                row.update(status="blocked", reason="fewer_than_two_accepted_teacher_classes")
            else:
                training_report = json.loads((directory / "training.json").read_text())
                row["training"] = training_report
                prediction_dir = args.output / f"development-{size}"
                execute([sys.executable, "-m", "modelmetis.simulation", "predict",
                         "--input", str(args.development), "--model",
                         str(directory / "specialist.joblib"), "--output", str(prediction_dir)])
                evaluation_path = args.output / f"evaluation-{size}.json"
                execute([sys.executable, str(Path(__file__).with_name("evaluate_audio.py")),
                         "--references", str(args.references), "--predictions",
                         str(prediction_dir / "predictions.json"), "--partition", "development",
                         "--output", str(evaluation_path)])
                evaluation = json.loads(evaluation_path.read_text())
                row.update(status="evaluated", metrics=evaluation["runs"][0])
            row["seconds"] = time.perf_counter() - snapshot_started
            write_json(report_path, report)
            print(f"snapshot {size}: {row['status']} ({row['seconds']:.2f}s)", flush=True)
        report["complete"] = True
    except Exception:
        if report["snapshots"]:
            report["snapshots"][-1]["status"] = "failed"
        raise RuntimeError("Learning curve stopped; inspect its checkpoint report.") from None
    finally:
        report["seconds"] = time.perf_counter() - started
        report["ended_utc"] = datetime.now(UTC).isoformat()
        write_json(report_path, report)
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    for name in ("input", "silver", "development", "references", "output"):
        parser.add_argument(f"--{name}", type=Path, required=True)
    parser.add_argument("--sizes", type=int, nargs="+", required=True)
    run(parser.parse_args())