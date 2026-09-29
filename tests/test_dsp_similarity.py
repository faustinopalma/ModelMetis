import copy
import json
from dataclasses import replace

import numpy as np
import pytest
import soundfile as sf

from modelmetis.dsp import DspConfig
from modelmetis.dsp_report import generate_report
from modelmetis.dsp_similarity import (
    full_report,
    messages_for,
    prepare_comparison,
    validate_result,
    verify_bundle,
)


def stub_report(identifier):
    return {"model": {"id": identifier, "configuration": {}}, "figures": []}


@pytest.mark.parametrize("count", [1, 4, 8])
def test_variable_known_condition_count(count):
    known = {f"C{index:02}": stub_report(f"R{index:02}") for index in range(1, count + 1)}
    messages = messages_for(known, stub_report("Q01"))
    context = json.loads(messages[1]["content"][0]["text"])
    assert len(context["known_conditions"]) == count
    assert context["unknown_report"] == "Q01"


def test_all_eight_classes_and_figures_with_explicit_low_detail():
    reports = [stub_report(f"R{index:02}") for index in range(1, 10)]
    for report in reports:
        report["figures"] = [{"id": f"I{index}", "bytes": b"fixture"} for index in range(8)]
    known = {f"C{index:02}": report for index, report in enumerate(reports[:8], 1)}
    labels = {identifier: f"Class {identifier}" for identifier in known}
    with pytest.raises(ValueError, match="none omitted"):
        messages_for(known, reports[8])
    messages = messages_for(
        known, reports[8], max_images=72, image_detail="low", condition_labels=labels
    )
    images = [part for part in messages[1]["content"] if part["type"] == "image_url"]
    assert len(images) == 72
    assert all(part["image_url"]["detail"] == "low" for part in images)
    assert json.loads(messages[1]["content"][0]["text"])["known_condition_labels"] == labels


def test_complete_report_keeps_all_intervals_and_all_generated_figures(tmp_path):
    source = tmp_path / "hidden-condition.wav"
    clock = np.arange(1280) / 16000
    sf.write(source, 0.1 * np.sin(2 * np.pi * 1000 * clock), 16000, subtype="PCM_24")
    report_path = tmp_path / "report"
    report = generate_report(
        source, report_path, replace(DspConfig(), segment_seconds=0.04, max_plot_segments=1)
    )
    packed = full_report(report_path, "Q01")
    assert len(packed["model"]["channels"][0]["intervals"]) == 2
    assert len(packed["figures"]) == len(report["channels"][0]["segments"][0]["images"]) + 1
    text = json.dumps(packed["model"])
    assert "hidden-condition" not in text and "source_sha256" not in text
    assert "start_sample" not in text and "end_sample_exclusive" not in text
    assert '"arrays"' not in text
    known = copy.deepcopy(packed)
    known["model"]["id"] = "R01"
    with pytest.raises(ValueError, match="none omitted"):
        messages_for({"C01": known}, packed, max_images=1)


def valid_result():
    return {
        "outcome": "similar",
        "condition_id": "C01",
        "explanation": "Shared pattern.",
        "comparisons": [
            {
                "condition_id": "C01",
                "similar": True,
                "similarities": ["Harmonic structure"],
                "differences": ["Level"],
                "evidence_ids": ["R01.M01", "Q01.M01"],
            }
        ],
    }


def test_binary_response_requires_each_reference_and_consistent_choice():
    result = valid_result()
    assert validate_result(result, {"C01": ["R01.M01"]}, ["Q01.M01"]) == result
    with pytest.raises(ValueError, match="Different requires"):
        validate_result(
            {**result, "outcome": "different", "condition_id": None},
            {"C01": ["R01.M01"]},
            ["Q01.M01"],
        )
    result["comparisons"][0]["similar"] = False
    result.update(outcome="different", condition_id=None)
    assert validate_result(result, {"C01": ["R01.M01"]}, ["Q01.M01"]) == result
    result["comparisons"][0]["evidence_ids"] = ["Q01.M01"]
    with pytest.raises(ValueError, match="reference and the query"):
        validate_result(result, {"C01": ["R01.M01"]}, ["Q01.M01"])
    result["comparisons"][0]["evidence_ids"] = ["COMPARISON.WELCH"]
    with pytest.raises(ValueError, match="reference and the query"):
        validate_result(
            result, {"C01": ["R01.M01", "COMPARISON.WELCH"]}, ["Q01.M01", "COMPARISON.WELCH"]
        )


def test_labeled_score_distinguishes_wrong_class_rejection_and_failure():
    from scripts.evaluate_dsp_similarity import score_rows

    rows = [
        {"expected_label": "healthy", "predicted_label": predicted}
        for predicted in ("healthy", "fault", "different", "technical_failure")
    ]
    result = score_rows(rows, ["healthy", "fault"])
    assert result["queries"] == 4 and result["correct"] == 1
    assert result["accuracy"] == 0.25
    assert result["wrong_known_labels"] == 1
    assert result["false_rejections"] == 1
    assert result["technical_failures"] == 1
    with pytest.raises(ValueError, match="at least one"):
        score_rows([], ["healthy"])


def test_paired_figures_preserve_every_original_pixel():
    import io

    from PIL import Image

    from modelmetis.dsp_similarity import pair_figures

    report = {"model": {"id": "R01"}, "figures": [], "evidence_ids": []}
    for index, color in enumerate(("blue", "yellow", "gray")):
        stream = io.BytesIO()
        Image.new("RGB", (20, 10), color).save(stream, format="PNG")
        report["figures"].append(
            {"id": f"R01.I{index}", "title": color, "bytes": stream.getvalue()}
        )
    originals = list(report["figures"])
    packed = pair_figures(report)
    assert len(packed["figures"]) == 2
    for pair in packed["figures"]:
        canvas = Image.open(io.BytesIO(pair["bytes"]))
        for part in pair["components"]:
            original = next(figure for figure in originals if figure["id"] == part["id"])
            image = Image.open(io.BytesIO(original["bytes"]))
            assert (
                canvas.crop((0, part["y"], part["width"], part["y"] + part["height"])).tobytes()
                == image.tobytes()
            )


def test_bundle_exposes_reports_prompt_exact_data_and_response_location(tmp_path, monkeypatch):
    import httpx

    from modelmetis import dsp_similarity

    for name, frequency in (("hidden-known", 500), ("hidden-query", 700)):
        clock = np.arange(800) / 16000
        sf.write(tmp_path / f"{name}.wav", 0.1 * np.sin(2 * np.pi * frequency * clock), 16000)
    spec = {
        "known_conditions": [{"condition_id": "C01", "wav": "hidden-known.wav"}],
        "unknown": {"wav": "hidden-query.wav"},
    }
    (tmp_path / "spec.json").write_text(json.dumps(spec))
    (tmp_path / "settings.json").write_text(
        json.dumps(
            {
                "deployment": "deployment",
                "reasoning_effort": "low",
                "max_completion_tokens": 2048,
                "endpoint": "https://fixture.openai.azure.com/",
                "subscription": "fixture-subscription",
                "model": "gpt-5.6-sol",
                "version": "2026-07-09",
                "prices_usd_per_million": {"input": 4.4, "cached_input": 0.44, "output": 22},
            }
        )
    )
    output = tmp_path / "bundle"
    manifest = prepare_comparison(tmp_path / "spec.json", tmp_path / "settings.json", output)
    assert verify_bundle(output) == manifest
    assert (output / "01_dsp/R01/report.html").exists()
    assert (output / "01_dsp/Q01/report.html").exists()
    assert (output / "03_response").is_dir()
    assert not (output / "03_response/response.json").exists()
    body = json.loads((output / "02_model/request.json").read_text())
    assert body["response_format"]["json_schema"]["schema"]["properties"]["outcome"]["enum"] == [
        "similar",
        "different",
    ]
    assert "hidden-known" not in json.dumps(body) and "hidden-query" not in json.dumps(body)
    assert manifest["image_count"] == 14
    assert len(list((output / "02_model/images").glob("*.png"))) == 14
    from modelmetis.dsp_similarity import contact_sheet

    packed = full_report(output / "01_dsp/R01", "R01")
    from modelmetis.dsp_similarity import spectral_distances

    spectral = spectral_distances(
        [output / "01_dsp/R01", output / "01_dsp/Q01", output / "01_dsp/R01"],
        ["C01", "C02"],
    )
    assert spectral["query_distance_db"]["C01"] == 0
    assert spectral["query_distance_db"]["C02"] > 0
    original_ids = [figure["id"] for figure in packed["figures"]]
    sheet = contact_sheet(packed)
    assert len(sheet["figures"]) == 1
    assert [part["id"] for part in sheet["figures"][0]["components"]] == original_ids
    assert all(
        part["width"] <= 600 and part["height"] <= 350 for part in sheet["figures"][0]["components"]
    )
    spec["known_conditions"][0]["report"] = "bundle/01_dsp/R01"
    spec["unknown"]["report"] = "bundle/01_dsp/Q01"
    (tmp_path / "cached-spec.json").write_text(json.dumps(spec))
    cached_output = tmp_path / "cached-bundle"
    reused = prepare_comparison(
        tmp_path / "cached-spec.json", tmp_path / "settings.json", cached_output
    )
    assert reused["request_sha256"] == manifest["request_sha256"]
    assert verify_bundle(cached_output) == reused
    decision = valid_result()
    decision["comparisons"][0]["evidence_ids"] = [
        manifest["known_evidence"]["C01"][0],
        manifest["unknown_evidence"][0],
    ]
    sent = []

    def handle(request):
        sent.append(request.content)
        assert request.headers["Authorization"] == "Bearer fixture"
        return httpx.Response(
            200,
            json={
                "model": "gpt-5.6-sol-2026-07-09",
                "id": "fixture-response",
                "usage": {"prompt_tokens": 100, "completion_tokens": 10},
                "choices": [
                    {"finish_reason": "stop", "message": {"content": json.dumps(decision)}}
                ],
            },
        )

    original_client = httpx.Client
    monkeypatch.setattr(dsp_similarity.dsp_inference, "verify_target", lambda settings: {})
    monkeypatch.setattr(
        dsp_similarity.dsp_inference,
        "azure_json",
        lambda arguments, settings: {"accessToken": "fixture"},
    )
    monkeypatch.setattr(
        dsp_similarity.httpx,
        "Client",
        lambda **kwargs: original_client(transport=httpx.MockTransport(handle), **kwargs),
    )
    result = dsp_similarity.invoke_once(output)
    assert result["status"] == "completed" and result["http_attempts"] == 1
    assert sent == [(output / "02_model/request.json").read_bytes()]
    assert json.loads((output / "03_response/decision.json").read_text()) == decision
    assert (output / "03_response/result.html").exists()
    assert all(
        b"Bearer fixture" not in path.read_bytes() and b'"accessToken"' not in path.read_bytes()
        for path in output.rglob("*")
        if path.is_file()
    )
    with pytest.raises(FileExistsError):
        dsp_similarity.invoke_once(output)
    assert len(sent) == 1
    (output / "02_model/prompt.txt").write_text("changed")
    with pytest.raises(ValueError, match="content mismatch"):
        verify_bundle(output)
