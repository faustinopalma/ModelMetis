import argparse
import io
import json
import uuid
import wave
from pathlib import Path

import numpy as np

from modelmetis.simulation import infer_audio, load_samples, write_json


def prepare(directory: Path) -> None:
    directory.mkdir(parents=True, exist_ok=False)
    samples = 24000 * 3
    signals = {
        "steady_tone": 0.5 * np.sin(2 * np.pi * 440 * np.arange(samples) / 24000),
        "broadband_noise": np.clip(np.random.default_rng(17).normal(0, 0.2, samples), -1, 1),
    }
    manifest, expected = [], {}
    for label, signal in signals.items():
        identifier = uuid.uuid4().hex
        content = io.BytesIO()
        with wave.open(content, "wb") as recording:
            recording.setnchannels(1)
            recording.setsampwidth(2)
            recording.setframerate(24000)
            recording.writeframes((signal * 32767).astype("<i2").tobytes())
        (directory / f"{identifier}.wav").write_bytes(content.getvalue())
        manifest.append({"sample_id": identifier, "group_id": uuid.uuid4().hex,
                         "partition": "development"})
        expected[identifier] = label
    write_json(directory / "manifest.json", manifest)
    write_json(directory / "expected.json", expected)
    write_json(directory / "prompts.json", {"synthetic-capability-v1": {
        "taxonomy": {"steady_tone": "A steady narrowband musical or electronic tone.",
                     "broadband_noise": "Broadband random noise or hiss."},
        "instructions": "Listen to the supplied audio and classify the audible signal. "
                        "Use null if neither category is supported. Do not infer from metadata.",
        "response_contract": "Return only JSON with exactly label (taxonomy key or null), "
                             "score (number between 0 and 1), observations (list of strings).",
    }})
    assert len(load_samples(directory)) == 2


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--prepare-only", action="store_true")
    parser.add_argument("--output", type=Path)
    parser.add_argument("--endpoint")
    parser.add_argument("--deployment")
    parser.add_argument("--tenant-id")
    parser.add_argument("--subscription")
    parser.add_argument("--resource-group")
    parser.add_argument("--ledger", type=Path)
    parser.add_argument("--max-requests", type=int, default=160)
    parser.add_argument("--acknowledge-paid-requests", action="store_true")
    args = parser.parse_args()
    if args.prepare_only:
        prepare(args.input)
        print("Prepared and validated two synthetic audio inputs; no network requests.")
        return
    if any(getattr(args, name) is None for name in (
        "output", "endpoint", "deployment", "tenant_id", "subscription", "ledger",
        "resource_group",
    )):
        parser.error("A live probe requires output, endpoint, identity and ledger arguments.")
    args.prompts = args.input / "prompts.json"
    args.variant = "synthetic-capability-v1"
    args.minimum_score = 0
    args.deadline_seconds = 300
    infer_audio(args)
    report = json.loads((args.output / "predictions.json").read_text(encoding="utf-8"))
    expected = json.loads((args.input / "expected.json").read_text(encoding="utf-8"))
    correct = sum(row["status"] == "accepted" and row["label"] == expected[row["sample_id"]]
                  for row in report["predictions"])
    summary = {"samples": 2, "correct": correct, "passed": correct == 2,
               "meaning": "Synthetic audio transport/capability only, not motor diagnosis"}
    write_json(args.output / "capability.json", summary)
    print(json.dumps(summary))
    if correct != 2:
        raise RuntimeError("Synthetic capability check did not pass.")


if __name__ == "__main__":
    main()