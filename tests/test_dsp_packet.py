import json

import numpy as np
import pytest
import soundfile as sf

from modelmetis.dsp_packet import (
    compact,
    comparison_messages,
    make_packet,
    response_schema,
    validate_decision,
)
from modelmetis.dsp_report import generate_report


def test_compact_preserves_small_nonzero_measurements():
    assert compact(1.23456789e-12) == 1.234568e-12
    assert compact({"count": 123456789, "empty": None}) == {"count": 123456789, "empty": None}


def test_packet_uses_original_images_and_excludes_provenance(tmp_path):
    source = tmp_path / "secret-diagnosis.wav"
    clock = np.arange(8000) / 16000
    sf.write(source, 0.1 * np.sin(2 * np.pi * 1000 * clock), 16000, subtype="PCM_24")
    report = tmp_path / "report"
    generate_report(source, report, source_state="original")
    packet = make_packet(report, "R01")
    model_text = json.dumps(packet["model"])
    for forbidden in ("secret-diagnosis", "source_sha256", "start_sample", "path", "R0001"):
        assert forbidden not in model_text
    assert len(packet["figures"]) == 2
    assert packet["model"]["measurement"]["peaks"][0]["frequency_hz"] == 1000
    assert packet["audit"]["start_sample"] == 0
    image = next((report / "images").glob("*-fft.png"))
    assert packet["figures"][0]["bytes"] == image.read_bytes()
    image.write_bytes(b"corrupted")
    with pytest.raises(ValueError, match="integrity"):
        make_packet(report, "R01")


def small_packet(identifier, rate=16000):
    return {"model": {"id": identifier}, "compatibility": {"sample_rate": rate,
            "configuration": {}}, "audit": {"source_pcm_sha256": identifier}, "figures": []}


def test_comparison_rejects_incompatible_or_duplicate_sources():
    references = {"C01": small_packet("R01"), "C02": small_packet("R02")}
    with pytest.raises(ValueError, match="Incompatible"):
        comparison_messages(references, small_packet("Q01", 44100))
    with pytest.raises(ValueError, match="unique"):
        comparison_messages(references, small_packet("R01"))
    query = small_packet("Q01")
    query["audit"]["source_pcm_sha256"] = "R01"
    with pytest.raises(ValueError, match="Repeated"):
        comparison_messages(references, query)


def test_output_schema_and_validation_require_visible_evidence():
    schema = response_schema(["C01", "C02"])
    assert schema["json_schema"]["strict"]
    decision = {"outcome": "known", "condition_id": "C01", "evidence_ids": ["Q01.M01"],
                "explanation": "Measured spectral comparison.", "limitations": []}
    assert validate_decision(decision, ["C01", "C02"], ["Q01.M01"]) == decision
    with pytest.raises(ValueError, match="visible condition"):
        validate_decision({**decision, "condition_id": "C03"}, ["C01", "C02"], ["Q01.M01"])
    with pytest.raises(ValueError, match="fabricated"):
        validate_decision({**decision, "evidence_ids": ["hidden"]}, ["C01"], ["Q01.M01"])


def test_completion_accounting_includes_reasoning_and_validates_identity():
    from modelmetis.dsp_inference import estimate_cost, parse_completion

    settings = {"model": "gpt-5.6-sol", "version": "2026-07-09", "max_completion_tokens": 4096,
                "prices_usd_per_million": {"input": 4.4, "cached_input": 0.44, "output": 22}}
    usage = {"prompt_tokens": 1000, "completion_tokens": 100,
             "prompt_tokens_details": {"cached_tokens": 200},
             "completion_tokens_details": {"reasoning_tokens": 80}}
    assert estimate_cost(usage, settings) == pytest.approx(0.005808)
    decision = {"outcome": "indeterminate", "condition_id": None,
                "evidence_ids": ["Q01.M01"], "explanation": "Ambiguous measured features.",
                "limitations": ["Acquisition gain unknown."]}
    choices = [{"finish_reason": "stop", "message": {"content": json.dumps(decision)}}]
    response = {"model": "gpt-5.6-sol", "usage": usage, "id": "test", "choices": choices}
    job = {"allowed_ids": ["C01", "C02"], "evidence_ids": ["Q01.M01"]}
    assert parse_completion(response, job, settings)["decision"] == decision
    with pytest.raises(ValueError, match="identity"):
        parse_completion({**response, "model": "another-model"}, job, settings)
    with pytest.raises(ValueError, match="incomplete"):
        parse_completion({**response, "choices": [{"finish_reason": "length"}]}, job, settings)
    with pytest.raises(ValueError, match="accounting"):
        estimate_cost({**usage, "prompt_tokens": True}, settings)


def test_request_building_keeps_shared_units_and_strict_output():
    from scripts.dsp_experiment import job_for

    packets = [small_packet(identifier) for identifier in ("R01", "R02", "Q01")]
    for packet in packets:
        packet["model"].update(measurement_id=packet["model"]["id"] + ".M01", images=[])
    settings = {"deployment": "modelmetis-dsp-sol", "reasoning_effort": "low",
                "max_completion_tokens": 4096}
    job = job_for({"C01": packets[0], "C02": packets[1]}, packets[2], settings)
    assert job["allowed_ids"] == ["C01", "C02"]
    assert job["evidence_ids"] == ["R01.M01", "R02.M01", "Q01.M01"]
    assert job["body"]["response_format"]["json_schema"]["strict"]
    assert "packet_audit" not in json.dumps(job["body"])
    assert "source_pcm_sha256" not in json.dumps(job["body"])
    assert job["body"]["messages"][1]["content"][0]["type"] == "text"


def test_publication_check_rejects_secrets_without_returning_values():
    from scripts.check_publication import findings

    assert findings(".azure/msal_token_cache.bin", b"opaque") == ["forbidden_artifact_path"]
    assert findings("artifacts/receipt.json", b"{}") == ["forbidden_artifact_path"]
    assert findings("data/README.md", b"Dataset instructions.") == []
    token = "ghp_" + "A" * 36
    result = findings("config.json", json.dumps({"api_key": token}).encode())
    assert set(result) == {"github_token", "literal_secret"}
    assert token not in json.dumps(result)
    assert findings("private.txt", ("-----BEGIN " + "PRIVATE KEY-----").encode()) == ["private_key"]
    public_metadata = b'{"subscription":"e2cb999b-d471-4148-9b22-1c4c8019cb4e"}'
    assert findings("settings.json", public_metadata) == []