import argparse
import hashlib
import io
import json
import re
import uuid
import wave
import zipfile
from collections import Counter
from pathlib import Path

import numpy as np
from scipy.io import loadmat

from modelmetis.audio import ModelAudioInput
from modelmetis.learning import Sample, validate_split

CLASSES = {
    "H_H": "healthy",
    "R_U": "rotor_unbalance",
    "R_M": "rotor_misalignment",
    "S_W": "stator_winding",
    "V_U": "voltage_unbalance",
    "B_R": "bowed_rotor",
    "K_A": "broken_rotor_bars",
    "F_B": "faulty_bearing",
}


def prepare(archive_path: Path, output: Path) -> dict:
    if output.exists():
        raise ValueError("Use a new output directory; never overwrite a frozen split.")
    samples = []
    references = []
    hashes = set()
    with zipfile.ZipFile(archive_path) as archive:
        names = [name for name in archive.namelist() if name.endswith(".mat")]
        if len(names) != 128:
            raise ValueError("Unexpected Ottawa v2 acquisition count.")
        csv_names = {Path(name).stem: name for name in archive.namelist()
                     if name.endswith(".csv") and "2_CSV_Data_Files/" in name}
        if len(csv_names) != 128:
            raise ValueError("CSV/MAT pairing count mismatch.")
        for name in sorted(names):
            stem = Path(name).stem
            match = re.fullmatch(r"([A-Z]_[A-Z])_([1-8])_([01])", stem)
            if not match or match[1] not in CLASSES:
                raise ValueError("Unknown source condition; audit taxonomy before importing.")
            raw = archive.read(name)
            matrix = loadmat(io.BytesIO(raw))["data"]
            if matrix.shape != (420000, 5) or not np.isfinite(matrix).all():
                raise ValueError("Unexpected acquisition shape or nonfinite values.")
            with archive.open(csv_names[stem]) as source:
                csv_audio = np.loadtxt(source, delimiter=",", skiprows=1, usecols=1)
            if not np.allclose(matrix[:, 1], csv_audio, rtol=0, atol=0.000001):
                raise ValueError("CSV and MAT acoustic channels disagree.")
            signal = matrix[:, 1]
            peak = float(np.max(np.abs(signal)))
            if peak <= 0:
                raise ValueError("Silent source acquisition.")
            pcm = np.rint(signal / peak * 0.95 * 32767).astype("<i2")
            stream = io.BytesIO()
            with wave.open(stream, "wb") as audio:
                audio.setparams((1, 2, 42000, len(pcm), "NONE", "not compressed"))
                audio.writeframes(pcm.tobytes())
            digest = hashlib.sha256(stream.getvalue()).hexdigest()
            if digest in hashes:
                raise ValueError("Duplicate acoustic acquisition; split needs review.")
            hashes.add(digest)
            partition = {"1": "development", "8": "test"}.get(match[2], "train")
            sample = Sample(ModelAudioInput(uuid.uuid4().hex, stream.getvalue()),
                            uuid.uuid4().hex, partition)
            samples.append(sample)
            references.append({
                "sample_id": sample.audio.sample_id, "label": CLASSES[match[1]],
                "partition": partition, "source_path": name,
                "source_sha256": hashlib.sha256(raw).hexdigest(),
                "audio_sha256": digest, "peak_microphone_volts": peak,
                "csv_mat_acoustic_match": True,
            })
    validate_split(samples)
    output.mkdir(parents=True)
    sealed = output / "sealed"
    sealed.mkdir()
    (sealed / "references.json").write_text(json.dumps(references, indent=2), encoding="utf-8")
    for partition in ("development", "train", "test"):
        directory = output / partition
        directory.mkdir()
        manifest = []
        for sample in sorted(samples, key=lambda item: item.audio.sample_id):
            if sample.partition != partition:
                continue
            identifier = sample.audio.sample_id
            (directory / f"{identifier}.wav").write_bytes(sample.audio.wav_bytes)
            manifest.append({"sample_id": identifier, "group_id": sample.group_id,
                             "partition": partition})
        (directory / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    with archive_path.open("rb") as source:
        archive_hash = hashlib.file_digest(source, "sha256").hexdigest()
    report = {
        "dataset": "10.17632/msxs4vj48g.2", "license": "CC BY 4.0",
        "attribution": "Mert Sehri and Patrick Dumond, University of Ottawa, 2026",
        "archive_sha256": archive_hash, "acquisitions": len(samples),
        "csv_mat_pairs_verified": len(samples), "classes": list(CLASSES.values()),
        "partitions": dict(Counter(sample.partition for sample in samples)),
        "split": "Speed profile 1 development, 8 final test, 2-7 train; both loads",
        "preprocessing": "Microphone column 2 only; per-record peak normalization to 0.95; PCM16",
        "limitation": "Same physical motors across splits; no unseen-motor generalization claim",
        "isolation": "Separate local inputs, not an OS-enforced security boundary",
    }
    (output / "audit.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--archive", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(prepare(args.archive, args.output), indent=2))
