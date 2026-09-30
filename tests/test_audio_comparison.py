import base64
import json
import subprocess
from pathlib import Path

import numpy as np
import pytest
import soundfile as sf

from modelmetis.dsp_report import generate_report
from scripts.audio_comparison import load_dataset, pack_record, sha256


def test_audio_and_figures_match_registered_report(tmp_path):
    source = tmp_path / "source.wav"
    clock = np.arange(800) / 16000
    sf.write(source, 0.1 * np.sin(2 * np.pi * 500 * clock), 16000)
    report = tmp_path / "reports/R01"
    generate_report(source, report)
    item = {"id": "R01", "wav": str(source), "audio_sha256": sha256(source.read_bytes())}
    packed = pack_record(tmp_path, item)
    assert base64.b64decode(packed["audio"].split(",", 1)[1]) == source.read_bytes()
    assert packed["duration"] == 0.05 and packed["rate"] == 16000
    assert {"levels", "fft", "welch", "stft"}.issubset(packed["figures"])
    assert "source.wav" not in json.dumps(packed)
    for key, image in packed["figures"].items():
        assert sha256(base64.b64decode(image.split(",", 1)[1])) == packed["figureHashes"][key]
    with pytest.raises(ValueError, match="registered WAV"):
        pack_record(tmp_path, {**item, "audio_sha256": "modified"})


def test_changed_registration_is_rejected_before_loading_audio(tmp_path):
    (tmp_path / "sealed").mkdir()
    (tmp_path / "protocol.json").write_text("{}")
    (tmp_path / "sealed/truth.json").write_text("{}")
    (tmp_path / "registration.json").write_text(
        json.dumps(
            {
                "protocol_sha256": "changed",
                "truth_sha256": sha256(b"{}"),
            }
        )
    )
    with pytest.raises(ValueError, match="registration changed"):
        load_dataset(tmp_path, "Fixture")


def test_model_comparison_uses_the_same_reference_set(tmp_path, monkeypatch):
    from scripts import audio_comparison

    (tmp_path / "sealed").mkdir()
    protocol = {
        "known": [{"id": "R01", "condition_id": "C01", "label": "healthy"}],
        "queries": [{"id": "T01", "role": "final"}],
    }
    protocol_bytes = json.dumps(protocol).encode()
    truth_bytes = json.dumps({"T01": {"condition_id": "C01"}}).encode()
    (tmp_path / "protocol.json").write_bytes(protocol_bytes)
    (tmp_path / "sealed/truth.json").write_bytes(truth_bytes)
    (tmp_path / "registration.json").write_text(
        json.dumps(
            {
                "protocol_sha256": sha256(protocol_bytes),
                "truth_sha256": sha256(truth_bytes),
            }
        )
    )
    monkeypatch.setattr(
        audio_comparison,
        "pack_record",
        lambda folder, item: {"id": item["id"], "audioHash": item["id"]},
    )
    for phase in ("final", "novelty", "replay-known", "replay-novelty"):
        path = tmp_path / "round-02" / phase / "T01/03_response"
        path.mkdir(parents=True)
        (path / "attempt.json").write_text(
            json.dumps(
                {
                    "status": "completed",
                    "decision": {"condition_id": "C01", "outcome": "similar"},
                }
            )
        )
    packed = load_dataset(tmp_path, "Fixture")
    assert [model["phase"] for model in packed["queries"][0]["models"]] == ["final", "replay-known"]


def test_generated_page_is_direct_reference_review(tmp_path, monkeypatch):
    from scripts import audio_comparison

    monkeypatch.setattr(
        audio_comparison,
        "load_dataset",
        lambda folder, name: {
            "name": name,
            "key": name,
            "protocolHash": "fixture",
            "references": [{"audioHash": "reference"}],
            "queries": [{"audioHash": "query"}],
        },
    )
    monkeypatch.setattr(audio_comparison, "load_icons", lambda: {})
    output = tmp_path / "review"
    audio_comparison.build(output)
    manifest = json.loads((output / "manifest.json").read_text())
    page = (output / "index.html").read_text()
    assert manifest["mode"] == "reference-review"
    assert "always visible" in manifest["labels"]
    assert 'id="correct-reference"' in page
    assert 'id="reference-match"' in page
    assert all(f'id="{identifier}"' not in page for identifier in ("choice", "record", "reveal"))
    assert "modelmetis-reference-review-" in page
    assert "modelmetis-human-comparison-" not in page
    assert 'id="model-status"' in page
    assert 'id="errors-only"' in page
    assert 'id="trial"' in page


def test_model_error_categories_exclude_technical_failures():
    from scripts.audio_comparison import TEMPLATE

    source = TEMPLATE.read_text(encoding="utf-8")
    helpers = source.split("function modelResult(model,truth) {", 1)[1].split("const trialKey", 1)[
        0
    ]
    program = (
        "function modelResult(model,truth) {"
        + helpers
        + """
const assert = require('node:assert/strict');
const cases = [
    [{status:'completed',outcome:'similar',condition:'C01'}, 'correct', false],
    [{status:'completed',outcome:'similar',condition:'C02'}, 'wrong_class', true],
    [{status:'completed',outcome:'different',condition:null}, 'false_rejection', true],
    [{status:'technical_failure',outcome:'similar',condition:'C02'}, 'technical_failure', false],
    [{status:'completed',outcome:null,condition:null}, 'technical_failure', false],
];
for(const [model, expected, error] of cases){
    assert.equal(modelResult(model,'C01'),expected);
    assert.equal(isModelError(model,'C01'),error);
}
"""
    )
    subprocess.run(["node", "-e", program], cwd=Path(__file__).resolve().parents[1], check=True)
