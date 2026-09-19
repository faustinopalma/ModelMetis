import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
from sklearn.metrics import accuracy_score, confusion_matrix, f1_score, recall_score


def evaluate(predictions: dict, references: list[dict], partition: str) -> dict:
    if partition not in ("development", "test") or predictions["partition"] != partition:
        raise ValueError("Evaluation requires the declared held-out partition.")
    rows = predictions["predictions"]
    expected_rows = [row for row in references if row["partition"] == partition]
    expected = {row["sample_id"]: row["label"] for row in expected_rows}
    if not expected or len(expected) != len(expected_rows):
        raise ValueError("Empty or duplicate reference data.")
    if not predictions["complete"] or predictions["expected_count"] != len(expected):
        raise ValueError("Incomplete prediction run.")
    if len(rows) != len(expected) or {row["sample_id"] for row in rows} != set(expected):
        raise ValueError("Prediction/reference sample mismatch.")
    labels = sorted(set(expected.values()))
    for row in rows:
        if row["status"] not in ("accepted", "abstained", "failed"):
            raise ValueError("Unknown prediction status.")
        if row["status"] == "accepted" and row["label"] not in labels:
            raise ValueError("Unknown predicted class.")
    truth = [expected[row["sample_id"]] for row in rows]
    predicted = [row["label"] if row["status"] == "accepted" else "__abstained__" for row in rows]
    accepted = sum(row["status"] == "accepted" for row in rows)
    seconds = [row["seconds"] for row in rows]
    recall = recall_score(truth, predicted, labels=labels, average=None, zero_division=0)
    macro_f1 = f1_score(truth, predicted, labels=labels, average="macro", zero_division=0)
    return {
        "model": predictions["model"], "partition": partition, "samples": len(rows),
        "accepted": accepted, "failed": sum(row["status"] == "failed" for row in rows),
        "coverage": accepted / len(rows),
        "accuracy": float(accuracy_score(truth, predicted)),
        "macro_f1": float(macro_f1),
        "per_class_recall": dict(zip(labels, recall.tolist(), strict=True)),
        "confusion_labels": labels + ["__abstained__"],
        "confusion_matrix": confusion_matrix(truth, predicted,
                                              labels=labels + ["__abstained__"]).tolist(),
        "inference_seconds_total": float(sum(seconds)),
        "inference_seconds_median": float(np.median(seconds)),
        "inference_seconds_p95": float(np.percentile(seconds, 95)),
        "load_seconds": predictions["load_seconds"],
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--references", type=Path, required=True)
    parser.add_argument("--predictions", type=Path, nargs="+", required=True)
    parser.add_argument("--partition", choices=["development", "test"], required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise ValueError("Evaluation report exists; do not overwrite experiment evidence.")
    references = json.loads(args.references.read_text(encoding="utf-8"))
    runs = []
    for path in args.predictions:
        predictions = json.loads(path.read_text(encoding="utf-8"))
        metrics = evaluate(predictions, references, args.partition)
        metrics["prediction_sha256"] = hashlib.sha256(path.read_bytes()).hexdigest()
        metrics["variant"] = predictions.get("variant")
        metrics["prompt_sha256"] = predictions.get("prompt_sha256")
        runs.append(metrics)
    report = {"partition": args.partition, "runs": runs, "promotion": "not_authorized"}
    if args.partition == "development":
        best = max(runs, key=lambda run: run["macro_f1"])
        report["selected_variant"] = best["variant"]
        report["selected_prompt_sha256"] = best["prompt_sha256"]
        report["selection_rule"] = "Highest development macro-F1; input order breaks ties"
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
