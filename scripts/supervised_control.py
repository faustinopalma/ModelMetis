import argparse
import hashlib
import json
import time
from pathlib import Path

import joblib
import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.svm import SVC

from modelmetis.audio_models import spectral_features, waveform
from modelmetis.learning import Sample, validate_split
from modelmetis.simulation import load_demonstrations, load_samples, write_json

KIND = "publisher-supervised-diagnostic-control-not-operational-silver"
METHODS = ("welch-logistic", "mfcc-svm")


def features(audio, method):
    if method == "welch-logistic":
        return spectral_features(audio)
    if method != "mfcc-svm":
        raise ValueError("Unknown fixed control method.")
    import librosa

    cepstra = librosa.feature.mfcc(y=waveform(audio, 16000), sr=16000, n_mfcc=20,
                                   n_fft=1024, hop_length=512, n_mels=64)
    components = (cepstra, librosa.feature.delta(cepstra), librosa.feature.delta(cepstra, order=2))
    return np.concatenate([statistic(component, axis=1)
                           for component in components for statistic in (np.mean, np.std)])


def fit_control(samples, references, method):
    validate_split(samples)
    if any(item.partition != "train" for item in samples):
        raise ValueError("Only training audio is permitted in the supervised control.")
    indexed = {row["sample_id"]: row for row in references}
    if (len(indexed) != len(references)
            or set(indexed) != {item.audio.sample_id for item in samples}
            or any(row["partition"] != "train" for row in references)):
        raise ValueError("References must exactly cover training inputs only.")
    labels = []
    for item in samples:
        row = indexed[item.audio.sample_id]
        if row["audio_sha256"] != hashlib.sha256(item.audio.wav_bytes).hexdigest():
            raise ValueError("Training reference/audio mismatch.")
        if not isinstance(row["label"], str) or not row["label"]:
            raise ValueError("Missing publisher label.")
        labels.append(row["label"])
    if len(set(labels)) < 2:
        raise ValueError("At least two publisher classes are required.")
    classifier = make_pipeline(StandardScaler(),
        LogisticRegression(max_iter=1000, random_state=17) if method == "welch-logistic"
        else SVC(C=10, kernel="rbf", gamma="scale", class_weight="balanced"))
    matrix = np.stack([features(item.audio, method) for item in samples])
    classifier.fit(matrix, labels)
    return {"kind": KIND, "method": method, "classifier": classifier,
            "training_samples": len(samples),
            "training_groups": len({item.group_id for item in samples}),
            "training_audio_sha256": [hashlib.sha256(item.audio.wav_bytes).hexdigest()
                                      for item in samples],
            "training_group_ids": sorted({item.group_id for item in samples})}


def predict_control(artifact, samples):
    validate_split(samples)
    if artifact.get("kind") != KIND:
        raise ValueError("Not a separately identified supervised control.")
    partitions = {item.partition for item in samples}
    if len(partitions) != 1 or not partitions <= {"development", "test"}:
        raise ValueError("Prediction requires one held-out partition.")
    rows = []
    for item in samples:
        if (item.group_id in artifact["training_group_ids"]
                or hashlib.sha256(item.audio.wav_bytes).hexdigest()
                in artifact["training_audio_sha256"]):
            raise ValueError("Held-out query overlaps control training.")
    for item in samples:
        started = time.monotonic()
        label = str(artifact["classifier"].predict(
            features(item.audio, artifact["method"])[None, :],
        )[0])
        rows.append({"sample_id": item.audio.sample_id, "label": label,
                     "status": "accepted", "seconds": time.monotonic() - started})
    return {"model": f"{KIND}:{artifact['method']}", "partition": samples[0].partition,
            "complete": True, "expected_count": len(samples), "predictions": rows,
            "load_seconds": 0.0, "training_samples": artifact["training_samples"],
            "training_groups": artifact["training_groups"], "promotion": "not_authorized"}


def main():
    parser = argparse.ArgumentParser()
    commands = parser.add_subparsers(dest="command", required=True)
    train = commands.add_parser("train")
    train.add_argument("--input", type=Path, required=True)
    origins = train.add_mutually_exclusive_group(required=True)
    origins.add_argument("--references", type=Path)
    origins.add_argument("--support-taxonomy", nargs="+")
    train.add_argument("--method", choices=METHODS, required=True)
    train.add_argument("--output", type=Path, required=True)
    predict = commands.add_parser("predict")
    predict.add_argument("--input", type=Path, required=True)
    predict.add_argument("--artifact", type=Path, required=True)
    predict.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise ValueError("Do not overwrite experimental evidence.")
    started = time.monotonic()
    if args.command == "train":
        if args.support_taxonomy:
            demonstrations, provenance = load_demonstrations(
                args.input, [], tuple(args.support_taxonomy),
            )
            package = json.loads((args.input / "manifest.json").read_text())
            references = [{**row, "partition": "train"} for row in package["examples"]]
            samples = [Sample(item.audio, row["group_id"], "train")
                       for item, row in zip(demonstrations, references, strict=True)]
        else:
            samples = load_samples(args.input)
            references = json.loads(args.references.read_text(encoding="utf-8"))
            provenance = {
                "reference_sha256": hashlib.sha256(args.references.read_bytes()).hexdigest(),
            }
        artifact = fit_control(samples, references, args.method)
        args.output.mkdir(parents=True)
        joblib.dump(artifact, args.output / "control.joblib")
        report = {key: artifact[key]
              for key in ("kind", "method", "training_samples", "training_groups")}
        report.update({"provenance": provenance, "elapsed_seconds": time.monotonic() - started,
                       "artifact_sha256": hashlib.sha256(
                           (args.output / "control.joblib").read_bytes()).hexdigest(),
                       "script_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                       "parameters": artifact["classifier"].steps[-1][1].get_params(),
                       "promotion": "not_authorized"})
        write_json(args.output / "training.json", report)
    else:
        artifact = joblib.load(args.artifact)
        report = predict_control(artifact, load_samples(args.input))
        report["artifact_sha256"] = hashlib.sha256(args.artifact.read_bytes()).hexdigest()
        report["elapsed_seconds"] = time.monotonic() - started
        args.output.parent.mkdir(parents=True, exist_ok=True)
        write_json(args.output, report)
    summary = {key: value for key, value in report.items() if key != "predictions"}
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()