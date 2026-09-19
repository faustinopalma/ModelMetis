import argparse
import hashlib
import io
import json
import uuid
import wave
import zipfile
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np

from modelmetis.audio import ModelAudioInput
from modelmetis.learning import Sample, validate_split
from modelmetis.simulation import load_demonstrations, load_samples, write_json

LABELS = {
    "normal engine inside cabin": "normal",
    "idling": "normal",
    "air leak engine inside cabin": "air_leak",
    "air leak": "air_leak",
    "oil cap off engine inside cabin": "oil_cap_open",
    "background noise": "background_noise",
}


def prepare(archive_path: Path, output: Path) -> dict:
    if output.exists():
        raise ValueError("Use a new output directory; never overwrite a frozen split.")
    grouped = defaultdict(list)
    unique_audio = {}
    duplicates = 0
    constant_windows = 0
    with zipfile.ZipFile(archive_path) as archive:
        metadata = json.loads(archive.read("ai-mechanic-export/info.labels"))
        if metadata["version"] != 1:
            raise ValueError("Unsupported annotation version.")
        for row in metadata["files"]:
            if row["category"] != "training":
                continue
            label = LABELS[row["label"]["label"].lower()]
            raw = archive.read("ai-mechanic-export/" + row["path"])
            with wave.open(io.BytesIO(raw), "rb") as recording:
                if recording.getparams()[:3] != (1, 2, 16000):
                    raise ValueError("Unexpected source audio format.")
                frames = recording.readframes(min(recording.getnframes(), 160000))
            signal = np.frombuffer(frames, dtype="<i2")
            if len(signal) == 0 or int(signal.max()) == int(signal.min()):
                constant_windows += 1
                continue
            content = io.BytesIO()
            with wave.open(content, "wb") as recording:
                recording.setparams((1, 2, 16000, len(frames) // 2, "NONE", "not compressed"))
                recording.writeframes(frames)
            digest = hashlib.sha256(content.getvalue()).hexdigest()
            if digest in unique_audio:
                if unique_audio[digest] != label:
                    raise ValueError("Identical audio has conflicting source labels.")
                duplicates += 1
                continue
            unique_audio[digest] = label
            grouped[label].append((hashlib.sha256(raw).hexdigest(), row["path"],
                                   content.getvalue()))
    if set(grouped) != set(LABELS.values()) or min(map(len, grouped.values())) < 3:
        raise ValueError("Need all four categories with at least three acquisitions each.")
    samples, references = [], []
    for label, sources in sorted(grouped.items()):
        for index, (source_hash, source_path, content) in enumerate(sorted(sources)):
            partition = "development" if index < 2 else "train"
            item = Sample(ModelAudioInput(uuid.uuid4().hex, content), uuid.uuid4().hex, partition)
            samples.append(item)
            references.append({
                "sample_id": item.audio.sample_id, "partition": partition, "label": label,
                "source_path": source_path, "source_sha256": source_hash,
                "audio_sha256": hashlib.sha256(content).hexdigest(),
            })
    validate_split(samples)
    if len({row["source_sha256"] for row in references}) != len(references):
        raise ValueError("Duplicate source recordings; grouping requires review.")
    output.mkdir(parents=True)
    (output / "sealed").mkdir()
    write_json(output / "sealed" / "references.json", references)
    for partition in ("development", "train"):
        directory = output / partition
        directory.mkdir()
        manifest = []
        for item in sorted(samples, key=lambda item: item.audio.sample_id):
            if item.partition != partition:
                continue
            (directory / f"{item.audio.sample_id}.wav").write_bytes(item.audio.wav_bytes)
            manifest.append({"sample_id": item.audio.sample_id, "group_id": item.group_id,
                             "partition": partition})
        write_json(directory / "manifest.json", manifest)
    with archive_path.open("rb") as source:
        archive_hash = hashlib.file_digest(source, "sha256").hexdigest()
    report = {
        "dataset": "eoinedge/ai-mechanic-engine-condition-audio-fault-finding", "version": 1,
        "license": "Apache-2.0", "attribution": "Eoin / AI Mechanic, Kaggle",
        "archive_sha256": archive_hash, "acquisitions": len(samples),
        "duplicate_canonical_windows_removed": duplicates,
        "constant_or_empty_windows_removed": constant_windows,
        "partitions": dict(Counter(item.partition for item in samples)),
        "source_class_counts": {label: len(sources) for label, sources in grouped.items()},
        "split": "Publisher training; two lowest source hashes per class development; rest train",
        "preprocessing": "First min(10s, duration) per source; PCM16/16kHz; metadata stripped",
        "limitation": "One car; session dependence unknown; not independent validation",
        "publisher_test": "Not imported, heard or evaluated; unknown/testing labels not remapped",
        "isolation": "Separate local inputs, not an OS-enforced security boundary",
    }
    write_json(output / "audit.json", report)
    return report


def prepare_support(frozen: Path, output: Path, taxonomy: tuple[str, ...]) -> dict:
    if output.exists():
        raise ValueError("Use a new output directory; never overwrite a frozen support set.")
    train = load_samples(frozen / "train")
    development = load_samples(frozen / "development")
    if (any(item.partition != "train" for item in train)
            or any(item.partition != "development" for item in development)):
        raise ValueError("Unexpected source partitions.")
    validate_split(train + development)
    reference_path = frozen / "sealed" / "references.json"
    references = json.loads(reference_path.read_text(encoding="utf-8"))
    indexed = {row["sample_id"]: row for row in references}
    if len(indexed) != len(references):
        raise ValueError("Duplicate reference identity.")
    grouped = defaultdict(list)
    for item in train:
        reference = indexed[item.audio.sample_id]
        digest = hashlib.sha256(item.audio.wav_bytes).hexdigest()
        if reference["partition"] != "train" or reference["audio_sha256"] != digest:
            raise ValueError("Training source reference mismatch.")
        grouped[reference["label"]].append((digest, item))
    if set(grouped) != set(taxonomy):
        raise ValueError("Training sources must cover the entire support taxonomy.")
    selected = [min(grouped[label], key=lambda pair: pair[0])[1] for label in sorted(taxonomy)]
    identifiers = {item.audio.sample_id for item in selected}
    remaining = [item for item in train if item.audio.sample_id not in identifiers]
    groups = {item.group_id for item in selected}
    contents = {item.audio.wav_bytes for item in selected}
    if (not remaining or len(groups) != len(selected) or len(contents) != len(selected)
            or any(item.group_id in groups or item.audio.wav_bytes in contents
                   for item in remaining + development)):
        raise ValueError("Support selection must leave disjoint query acquisitions.")
    package = {
        "schema": 1, "label_source": "simulated_human_from_publisher",
        "origin_partition": "train",
        "examples": [{"sample_id": item.audio.sample_id, "group_id": item.group_id,
                      "label": indexed[item.audio.sample_id]["label"],
                      "audio_sha256": hashlib.sha256(item.audio.wav_bytes).hexdigest()}
                     for item in selected],
    }
    (output / "support").mkdir(parents=True)
    write_json(output / "support" / "manifest.json", package)
    for item in selected:
        (output / "support" / f"{item.audio.sample_id}.wav").write_bytes(item.audio.wav_bytes)
    for partition, samples in (("train", remaining), ("development", development)):
        directory = output / partition
        directory.mkdir()
        write_json(directory / "manifest.json", [
            {"sample_id": item.audio.sample_id, "group_id": item.group_id, "partition": partition}
            for item in samples
        ])
        for item in samples:
            (directory / f"{item.audio.sample_id}.wav").write_bytes(item.audio.wav_bytes)
    (output / "sealed").mkdir()
    query_ids = {item.audio.sample_id for item in remaining + development}
    write_json(output / "sealed" / "references.json",
               [row for row in references if row["sample_id"] in query_ids])
    _, support = load_demonstrations(output / "support", remaining + development, taxonomy)
    report = {
        "protocol": "EXP-006-one-shot-v1", "support": support,
        "selection": "One lowest canonical-audio SHA256 per class from frozen train only",
        "partitions": {"support": len(selected), "train": len(remaining),
                       "development": len(development)},
        "source_manifest_sha256": {
            partition: hashlib.sha256(
                (frozen / partition / "manifest.json").read_bytes(),
            ).hexdigest()
            for partition in ("train", "development")
        },
        "reference_sha256": hashlib.sha256(reference_path.read_bytes()).hexdigest(),
        "source_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "limitation": "Publisher labels simulate human annotation, not actual independent review",
    }
    write_json(output / "audit.json", report)
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--archive", type=Path)
    source.add_argument("--support-from", type=Path)
    parser.add_argument("--prompts", type=Path)
    parser.add_argument("--variant")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.support_from:
        from modelmetis.audio_teacher import validate_prompt

        if args.prompts is None or args.variant is None:
            parser.error("Support preparation requires --prompts and --variant.")
        prompt = json.loads(args.prompts.read_text(encoding="utf-8"))[args.variant]
        report = prepare_support(args.support_from, args.output, validate_prompt(prompt))
    else:
        report = prepare(args.archive, args.output)
    print(json.dumps(report, indent=2))