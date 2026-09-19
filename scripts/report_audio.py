import argparse
import hashlib
import json
from collections import Counter
from pathlib import Path

from modelmetis.simulation import write_json

RUN_FIELDS = (
    "model", "variant", "partition", "complete", "termination", "expected_count",
    "prompt_sha256", "manifest_sha256", "source_sha256", "started_utc", "ended_utc", "seconds",
)
METRIC_FIELDS = (
    "model", "variant", "partition", "samples", "accepted", "failed", "coverage", "accuracy",
    "macro_f1", "per_class_recall", "confusion_labels", "confusion_matrix",
    "inference_seconds_total", "inference_seconds_median", "inference_seconds_p95",
    "load_seconds", "prediction_sha256", "prompt_sha256",
)
SUPPORT_FIELDS = (
    "manifest_sha256", "support_set_sha256", "example_count", "shots_per_class", "label_source",
)


def read(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def bundle(roots: list[Path]) -> dict:
    runs, ledgers, evaluations, curves = [], [], [], []
    seen = set()
    for root in roots:
        root = root.resolve()
        if root in seen:
            raise ValueError("Duplicate report root.")
        seen.add(root)
        ledger = read(root / "usage.json")
        attempts = []
        for path in sorted(root.rglob("predictions.json")):
            report = read(path)
            if "usage_ledger" not in report:
                continue
            if Path(report["usage_ledger"]).resolve() != root / "usage.json":
                raise ValueError("Prediction ledger does not match report root.")
            rows = report["predictions"]
            summary = {key: report[key] for key in RUN_FIELDS if key in report}
            if "support" in report:
                summary["support"] = {key: report["support"][key] for key in SUPPORT_FIELDS
                                      if key in report["support"]}
            summary.update(
                artifact=f"{root.name}/{path.relative_to(root).as_posix()}",
                artifact_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
                attempted=len(rows), statuses=dict(Counter(row["status"] for row in rows)),
                accepted_class_counts=dict(Counter(row["label"] for row in rows
                                                   if row["status"] == "accepted")),
                http_responses=sum("http_status" in row.get("metadata", {}) for row in rows),
                known_usage_requests=sum("estimated_usd" in row.get("metadata", {})
                                         for row in rows),
                known_estimated_usd=sum(row.get("metadata", {}).get("estimated_usd", 0)
                                        for row in rows),
            )
            attempts.append(summary)
        if not attempts or sum(row["attempted"] for row in attempts) != ledger["requests"]:
            raise ValueError("Zero attempts or ledger/request reconciliation failed.")
        runs.extend(attempts)
        ledgers.append({"campaign": root.name, "requests": ledger["requests"],
                        "accounted_usd": ledger["accounted_usd"]})
        for path in sorted(root.glob("development*.json")):
            report = read(path)
            evaluations.append({
                "artifact": f"{root.name}/{path.name}",
                "selected_variant": report["selected_variant"],
                "runs": [{key: row[key] for key in METRIC_FIELDS if key in row}
                         for row in report["runs"]],
            })
        for path in sorted(root.rglob("curve.json")):
            report = read(path)
            snapshots = []
            for row in report["snapshots"]:
                snapshot = {key: row[key] for key in ("observed_examples", "status", "seconds")}
                snapshot["class_counts"] = row.get("training", {}).get("class_counts", {})
                snapshot["metrics"] = {key: row["metrics"][key] for key in METRIC_FIELDS
                                       if key in row.get("metrics", {})}
                snapshots.append(snapshot)
            curves.append({"artifact": f"{root.name}/{path.relative_to(root).as_posix()}",
                           "complete": report["complete"], "snapshots": snapshots})
    if not runs:
        raise ValueError("No experiment evidence.")
    return {
        "schema": 1, "promotion": "not_authorized", "ledgers": ledgers, "runs": runs,
        "evaluations": evaluations, "learning_curves": curves,
        "reserved_requests": sum(row["requests"] for row in ledgers),
        "http_responses": sum(row["http_responses"] for row in runs),
        "known_usage_requests": sum(row["known_usage_requests"] for row in runs),
        "known_estimated_usd": sum(row["known_estimated_usd"] for row in runs),
        "conservative_accounted_usd": sum(row["accounted_usd"] for row in ledgers),
        "cost_note": "List-price token estimates, not invoices; unknown usage retains reservations",
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--roots", type=Path, nargs="+", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise ValueError("Use a new report path; never overwrite experiment evidence.")
    write_json(args.output, bundle(args.roots))