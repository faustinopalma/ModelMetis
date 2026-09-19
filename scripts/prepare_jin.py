import argparse
import hashlib
import io
import json
import uuid
import wave
from collections import Counter
from pathlib import Path

import numpy as np
from scipy.io import wavfile

from modelmetis.audio import ModelAudioInput
from modelmetis.learning import Sample, validate_split
from modelmetis.simulation import load_demonstrations, write_json

LABELS = {"n": "healthy", "b1": "magnet_fracture", "b2": "excess_hall_adhesive",
          "b3": "tight_bearing"}
OFFSETS = {"f": (0,), "l": tuple(range(0, 300, 10)), "r": (0, 120, 240)}


def canonical_window(signal: np.ndarray, rate: int, offset: int) -> bytes:
    values = signal[offset * rate:(offset + 10) * rate].astype(np.float64)
    if len(values) != 10 * rate or not np.isfinite(values).all():
        raise ValueError("A complete finite ten-second window is required.")
    values -= values.mean()
    peak = float(np.max(np.abs(values)))
    if peak == 0:
        raise ValueError("Constant audio is not an experimental sample.")
    pcm = np.rint(values * (0.95 * 32767 / peak)).astype("<i2")
    output = io.BytesIO()
    with wave.open(output, "wb") as recording:
        recording.setparams((1, 2, rate, len(pcm), "NONE", "not compressed"))
        recording.writeframes(pcm.tobytes())
    return output.getvalue()


def prepare(source: Path, output: Path) -> dict:
    if output.exists():
        raise ValueError("Never overwrite a frozen dataset.")
    catalog = json.loads((source / "catalog.json").read_text(encoding="utf-8-sig"))
    entries = {row["entry"]["filename"]: row["entry"] for row in catalog}
    expected = {f"{code}{direction}10m{'_01' if code != 'n' else ''}.wav"
                for code in LABELS for direction in OFFSETS}
    if (len(entries) != len(catalog) or set(entries) != expected | {"readme.txt"}
            or {path.name for path in source.glob("*.wav")} != expected):
        raise ValueError("Expected the twelve original PCB microphone recordings and legend.")
    samples, references, support, sources = [], [], [], []
    hashes = set()
    for code, label in sorted(LABELS.items()):
        for direction, offsets in OFFSETS.items():
            name = f"{code}{direction}10m{'_01' if code != 'n' else ''}.wav"
            path = source / name
            with path.open("rb") as stream:
                digest = hashlib.file_digest(stream, "sha256").hexdigest()
            if digest != entries[name]["content_details"]["sha256_hash"]:
                raise ValueError("Source checksum mismatch.")
            rate, signal = wavfile.read(path, mmap=True)
            if (rate != 44100 or signal.ndim != 1 or len(signal) < 600 * rate
                    or not np.isfinite(signal).all()):
                raise ValueError("Unexpected source rate, channels, duration or nonfinite signal.")
            group = uuid.uuid4().hex
            partition = "development" if direction == "r" else "train"
            sources.append({"source_path": name, "source_sha256": digest,
                            "group_id": group, "direction": direction, "label": label,
                            "frames": len(signal), "rate": rate, "dtype": str(signal.dtype)})
            for offset in offsets:
                content = canonical_window(signal, rate, offset)
                audio_hash = hashlib.sha256(content).hexdigest()
                if audio_hash in hashes:
                    raise ValueError("Duplicate canonical audio requires source review.")
                hashes.add(audio_hash)
                item = Sample(ModelAudioInput(uuid.uuid4().hex, content), group, partition)
                reference = {"sample_id": item.audio.sample_id, "group_id": group,
                             "partition": partition, "label": label,
                             "audio_sha256": audio_hash, "source_sha256": digest,
                             "source_path": name, "offset_seconds": offset}
                if direction == "f":
                    support.append((item, reference))
                else:
                    samples.append(item)
                    references.append(reference)
    validate_split(samples + [item for item, _ in support])
    if len({row["source_sha256"] for row in sources}) != 12:
        raise ValueError("Duplicate original acquisitions.")
    for partition in ("train", "development"):
        directory = output / partition
        directory.mkdir(parents=True)
        chosen = sorted((item for item in samples if item.partition == partition),
                        key=lambda item: item.audio.sample_id)
        write_json(directory / "manifest.json", [
            {"sample_id": item.audio.sample_id, "group_id": item.group_id,
             "partition": partition} for item in chosen
        ])
        for item in chosen:
            (directory / f"{item.audio.sample_id}.wav").write_bytes(item.audio.wav_bytes)
    (output / "support").mkdir()
    support.sort(key=lambda pair: pair[1]["label"])
    write_json(output / "support" / "manifest.json", {
        "schema": 1, "label_source": "simulated_human_from_publisher",
        "origin_partition": "train", "examples": [
            {key: reference[key] for key in ("sample_id", "group_id", "label", "audio_sha256")}
            for _, reference in support
        ],
    })
    for item, _ in support:
        (output / "support" / f"{item.audio.sample_id}.wav").write_bytes(item.audio.wav_bytes)
    (output / "sealed").mkdir()
    write_json(output / "sealed" / "references.json", references)
    write_json(output / "sealed" / "supervised-train.json",
               [row for row in references if row["partition"] == "train"])
    write_json(output / "sealed" / "sources.json", sources)
    _, provenance = load_demonstrations(output / "support", samples, tuple(LABELS.values()))
    report = {
        "protocol": "EXP-007-jin-directions-v1", "doi": "10.17632/9dpmkgpncw.1",
        "license": "CC-BY-4.0", "attribution": "Linjie Jin, Mendeley Data, 2025",
        "source_url": "https://data.mendeley.com/datasets/9dpmkgpncw/1",
        "license_url": "https://creativecommons.org/licenses/by/4.0/",
        "source_catalog_sha256": hashlib.sha256((source / "catalog.json").read_bytes()).hexdigest(),
        "importer_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "original_recordings": len(sources), "source_groups_per_partition": 4,
        "source_seconds": sum(row["frames"] / row["rate"] for row in sources),
        "partitions": {**dict(Counter(item.partition for item in samples)),
                   "support": len(support)},
        "support": provenance, "taxonomy": sorted(LABELS.values()),
        "split": "Front: support at 0s; left: train at 0..290s by 10s; right: dev at 0/120/240s",
        "preprocessing": "10s mono 44.1kHz; DC removal, per-window peak 0.95, "
                 "PCM16, metadata removed",
        "limitations": ["Same motor population; unit/session independence not documented",
                        "Four held-out source recordings, not twelve independent queries",
                        "Direction transfer only; no independent-machine or final evaluation",
                        "Source healthy PCM16 versus fault FLOAT encoding is a potential confound",
                        "Local file separation, not an OS-enforced security boundary"],
    }
    write_json(output / "audit.json", report)
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(prepare(args.source, args.output), indent=2))