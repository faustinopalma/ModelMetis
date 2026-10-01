import numpy as np
import pytest

from modelmetis.dsp_extensions import ExtensionConfig, analyze_extensions


def tone(frequency, rate=16000, seconds=2, amplitude=0.1):
    return amplitude * np.sin(2 * np.pi * frequency * np.arange(round(rate * seconds)) / rate)


def test_envelope_recovers_modulation_and_preserves_gain_ratios():
    clock = np.arange(32000) / 16000
    samples = tone(2500) * (1 + 0.5 * np.cos(2 * np.pi * 40 * clock))
    first = analyze_extensions(samples, 16000)["views"]["envelope_3"]
    louder = analyze_extensions(samples * 2, 16000)["views"]["envelope_3"]
    assert first["metrics"]["strongest_modulation_hz"] == pytest.approx(40)
    assert max(first["series"]["envelope / mean"]) == pytest.approx(0.5, abs=0.003)
    np.testing.assert_allclose(
        first["series"]["envelope / mean"], louder["series"]["envelope / mean"], atol=1e-10
    )
    assert louder["metrics"]["mean_envelope_fs"] == pytest.approx(
        2 * first["metrics"]["mean_envelope_fs"]
    )


def test_multitaper_power_persistence_accounting_and_cepstrum_spacing():
    result = analyze_extensions(tone(1000), 16000)["views"]
    assert result["estimators"]["metrics"]["integrated_multitaper_power"] == pytest.approx(
        0.005, rel=0.01
    )
    np.testing.assert_allclose(result["persistence"]["values"].sum(axis=0), 100)
    harmonic = sum(tone(100 * order, amplitude=0.05) for order in range(1, 31))
    cepstrum = analyze_extensions(harmonic, 16000)["views"]["cepstrum"]
    selected = (cepstrum["x"] >= 0.008) & (cepstrum["x"] <= 0.012)
    maximum = cepstrum["x"][selected][np.argmax(cepstrum["series"]["cepstrum"][selected])]
    assert maximum == pytest.approx(0.01, abs=1 / 16000)


def test_extension_missing_short_silent_and_invalid_inputs():
    quiet = analyze_extensions(np.zeros(16000), 16000)["views"]
    assert len(quiet) == 19
    assert all(view["status"] == "unavailable" for view in quiet.values())
    short = analyze_extensions(tone(1000, seconds=0.05), 16000)["views"]
    assert short["envelope_3"]["status"] == "unavailable"
    assert short["estimators"]["status"] == "unavailable"
    assert short["envelope_5"]["status"] == "unavailable"
    with pytest.raises(ValueError, match="finite"):
        analyze_extensions([float("nan")], 16000)
    with pytest.raises(ValueError, match="configuration"):
        analyze_extensions(tone(1000), 16000, ExtensionConfig(frame_seconds=0))


def test_advanced_maps_detect_periodicity_and_keep_invalid_cells_masked():
    samples = tone(2000) + tone(2040)
    views = analyze_extensions(samples, 16000)["views"]
    cyclic = views["cyclic"]
    row = np.flatnonzero(np.isclose(cyclic["y"], 40))[0]
    column = np.argmin(abs(cyclic["x"] - 2020))
    assert cyclic["values"][row, column] > 0.99
    assert np.isnan(cyclic["values"]).any()
    assert np.nanmax(cyclic["values"]) <= 1
    assert views["orders"]["status"] == "unavailable"
    wavelet = views["wavelet"]
    assert np.isnan(wavelet["values"]).any()
    assert np.isfinite(wavelet["values"]).any()
    assert len(views["kurtosis_bank"]["metrics"]["bands"]) == 30
    assert views["reassigned"]["metrics"]["retained_weight_fraction"] > 0.99


def test_reassignment_localizes_tone_and_kurtosis_distinguishes_impulses():
    rng = np.random.default_rng(33)
    stationary = rng.normal(0, 0.02, 32000)
    impulsive = stationary.copy()
    impulsive[10000:10010] += 0.8
    clean = analyze_extensions(stationary, 16000)["views"]
    transient = analyze_extensions(impulsive, 16000)["views"]
    assert np.median(clean["spectral_kurtosis"]["series"]["kurtosis"]) == pytest.approx(0, abs=0.3)
    assert np.max(transient["spectral_kurtosis"]["series"]["kurtosis"]) > 5
    reassigned = analyze_extensions(tone(1033), 16000)["views"]["reassigned"]
    peak_frequency = reassigned["y"][np.argmax(np.sum(10 ** (reassigned["values"] / 10), axis=1))]
    assert peak_frequency == pytest.approx(1033, abs=8000 / 256)


def test_order_spectrum_and_synchronous_average_with_independent_rpm():
    from scipy.integrate import cumulative_trapezoid

    rate = 16000
    rpm = np.linspace(1200, 1800, 32000)
    phase = 2 * np.pi * cumulative_trapezoid(rpm / 60, dx=1 / rate, initial=0)
    samples = 0.1 * np.sin(4 * phase)
    result = analyze_extensions(samples, rate, rpm=rpm)["views"]
    orders = result["orders"]
    assert orders["x"][np.argmax(orders["series"]["power"])] == pytest.approx(4, abs=0.5)
    assert np.max(result["synchronous"]["series"]["rotation mean"]) > 0.095
    with pytest.raises(ValueError, match="RPM"):
        analyze_extensions(samples, rate, rpm=[0])


def test_every_diagram_has_interpretation_and_unavailable_semantics():
    from modelmetis.dsp_guide import VIEW_GUIDE, interpretation_prompt

    prompt = interpretation_prompt()
    views = analyze_extensions(tone(1000), 16000)["views"]
    assert len(VIEW_GUIDE) == 26
    assert set(views) == set(list(VIEW_GUIDE)[7:])
    assert all(key in prompt and VIEW_GUIDE[key][1] in prompt for key in VIEW_GUIDE)
    assert "masked cells as missing data" in prompt
    assert "forced ranking" in prompt


def test_extension_rendering_json_and_signatures_preserve_missing_values(tmp_path):
    import json

    from PIL import Image

    from scripts.dsp_extended_experiment import json_value, render_view, signature

    result = analyze_extensions(tone(2000), 16000)
    encoded = json.dumps(json_value(result), allow_nan=False)
    assert "NaN" not in encoded
    assert signature(result["views"]["orders"]) is None
    for key in ("cepstrum", "cyclic", "orders", "wavelet"):
        descriptor = render_view(result["views"][key], tmp_path / f"{key}.png", key)
        assert descriptor["sha256"]
        with Image.open(tmp_path / f"{key}.png") as image:
            assert image.size == (1200, 700)
            assert np.asarray(image).std() > 5


def test_ai_contract_transmits_exact_bytes_and_enforces_one_attempt(tmp_path, monkeypatch):
    import json

    import httpx

    from scripts import dsp_extended_ai as runner
    from scripts.dsp_extended_experiment import write_json

    case = tmp_path / "case"
    case.mkdir()
    payload = b'{"model":"pinned","messages":[]}'
    (case / "request.json").write_bytes(payload)
    write_json(
        case / "contract.json",
        {"known_evidence": {"C01": ["R01.fft"]}, "unknown_evidence": ["Q01.fft"]},
    )
    settings = {
        "subscription": "fixture",
        "endpoint": "https://fixture.openai.azure.com",
        "model": "pinned",
        "version": "v1",
        "max_completion_tokens": 8192,
        "prices_usd_per_million": {"input": 1, "cached_input": 0.1, "output": 2},
    }
    write_json(tmp_path / "settings.json", settings)
    monkeypatch.setattr(runner, "verify", lambda output: {"cases": [{"name": "case"}]})
    monkeypatch.setattr(
        runner.dsp_inference, "verify_target", lambda settings: {"state": "fixture"}
    )
    monkeypatch.setattr(
        runner.dsp_inference, "azure_json", lambda *args: {"accessToken": "secret-marker"}
    )
    decision = {
        "outcome": "similar",
        "condition_id": "C01",
        "explanation": "Observed match.",
        "comparisons": [
            {
                "condition_id": "C01",
                "similar": True,
                "similarities": ["Measured frequency"],
                "differences": [],
                "evidence_ids": ["R01.fft", "Q01.fft"],
            }
        ],
    }

    def respond(request):
        assert request.content == payload
        assert request.headers["Authorization"] == "Bearer secret-marker"
        return httpx.Response(
            200,
            json={
                "model": "pinned-v1",
                "usage": {"prompt_tokens": 10, "completion_tokens": 10},
                "choices": [
                    {"finish_reason": "stop", "message": {"content": json.dumps(decision)}}
                ],
            },
        )

    receipt = runner.execute_one(
        tmp_path,
        "case",
        lambda **kwargs: httpx.Client(transport=httpx.MockTransport(respond), **kwargs),
    )
    assert receipt["status"] == "completed"
    assert receipt["http_attempts"] == 1
    assert "secret-marker" not in (case / "attempt.json").read_text()
    with pytest.raises(FileExistsError):
        runner.execute_one(tmp_path, "case")


def test_ai_review_rejects_mutated_response_and_keeps_excluded_results_separate(tmp_path):
    import json

    from scripts.dsp_extended_experiment import write_json
    from scripts.dsp_extended_review import validated_decisions

    folder = tmp_path / "case"
    folder.mkdir()
    (tmp_path / "sealed").mkdir()
    write_json(folder / "request.json", {"model": "fixture"})
    write_json(
        folder / "contract.json",
        {"known_evidence": {"C01": ["R01.fft"]}, "unknown_evidence": ["Q01.fft"]},
    )
    decision = {
        "outcome": "similar",
        "condition_id": "C01",
        "explanation": "Match.",
        "comparisons": [
            {
                "condition_id": "C01",
                "similar": True,
                "similarities": ["Observed"],
                "differences": [],
                "evidence_ids": ["R01.fft", "Q01.fft"],
            }
        ],
    }
    write_json(
        folder / "response.json", {"choices": [{"message": {"content": json.dumps(decision)}}]}
    )
    from modelmetis.dsp_report import digest

    write_json(
        folder / "attempt.json",
        {
            "status": "completed",
            "decision": decision,
            "request_sha256": digest(folder / "request.json"),
            "response_sha256": digest(folder / "response.json"),
        },
    )
    write_json(tmp_path / "sealed/truth.json", {"case": "different"})
    write_json(
        tmp_path / "registration.json",
        {
            "truth_sha256": digest(tmp_path / "sealed/truth.json"),
            "cases": [
                {
                    "name": "case",
                    "phase": "excluded",
                    "dataset": "Fixture",
                    "query_id": "Q01",
                    "request_sha256": digest(folder / "request.json"),
                    "contract_sha256": digest(folder / "contract.json"),
                }
            ],
        },
    )
    assert validated_decisions(tmp_path)[0]["category"] == "Wrong acceptance"
    write_json(folder / "response.json", {})
    with pytest.raises(ValueError, match="output binding"):
        validated_decisions(tmp_path)


def test_error_direction_summary_distinguishes_review_from_wrong_assignments():
    from scripts.dsp_extended_review import error_direction, error_direction_summary

    rows = [
        {"category": category}
        for category in [
            "Correct class",
            "Correct rejection",
            "Wrong class",
            "Wrong acceptance",
            "False rejection",
        ]
    ]
    summary = error_direction_summary(rows)
    assert summary["total"] == 5
    assert summary["unsafeErrors"] == 2
    assert summary["reviewErrors"] == 1
    assert summary["correct"] == 2
    assert summary["errors"] == 3
    assert summary["reviewDirected"] == 2
    assert summary["accepted"] == 3
    assert error_direction("Wrong acceptance") == "wrong"
    assert error_direction("False rejection") == "review"
    assert error_direction("Correct rejection") == "correct"
    with pytest.raises(ValueError, match="nonempty validated"):
        error_direction_summary([])
    with pytest.raises(ValueError, match="nonempty validated"):
        error_direction_summary([{"category": "Technical failure"}])


def test_diagram_audit_requires_all_views_and_rejects_false_citations():
    import copy

    import jsonschema

    from modelmetis.dsp_guide import VIEW_GUIDE
    from scripts.dsp_diagram_audit import validate_audit

    contract = {
        "known_evidence": {"C01": ["R01." + key for key in VIEW_GUIDE]},
        "unknown_evidence": ["Q01." + key for key in VIEW_GUIDE],
    }
    survey = {
        "diagram_review": {
            key: {
                "priority": "unavailable" if key in {"orders", "synchronous"} else "medium",
                "finding": "Observed or explicitly unavailable.",
                "evidence_ids": ["R01." + key],
            }
            for key in VIEW_GUIDE
        },
        "most_informative": ["welch"],
        "limitations": "One per class.",
    }
    assert validate_audit(survey, contract, "survey") == survey
    contract["known_evidence"]["C01"].append("R01.C01.S0001")
    survey["diagram_review"]["fft"]["evidence_ids"].append("R01.C01.S0001")
    survey["diagram_review"]["fft"]["evidence_ids"].append("R01.welch")
    assert validate_audit(survey, contract, "survey") == survey
    missing = copy.deepcopy(survey)
    del missing["diagram_review"]["fft"]
    with pytest.raises(jsonschema.ValidationError):
        validate_audit(missing, contract, "survey")
    invalid = copy.deepcopy(survey)
    invalid["diagram_review"]["fft"]["evidence_ids"] = ["R01.welch"]
    with pytest.raises(ValueError, match="citations"):
        validate_audit(invalid, contract, "survey")
    invalid = copy.deepcopy(survey)
    invalid["diagram_review"]["orders"]["priority"] = "high"
    with pytest.raises(ValueError, match="RPM"):
        validate_audit(invalid, contract, "survey")


def test_reference_only_survey_removes_query_and_query_distances():
    import copy
    import json

    from scripts.dsp_diagram_audit import reference_only_body

    original = {
        "messages": [
            {"role": "system", "content": "Guide"},
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": json.dumps({"query": "Q01", "references": {"C01": "R01"}}),
                    },
                    {
                        "type": "text",
                        "text": json.dumps({"numerical_control": "secret-query-distance"}),
                    },
                    {"type": "text", "text": json.dumps({"report": {"id": "R01"}})},
                    {"type": "image_url", "image_url": {"url": "reference-figure"}},
                    {"type": "text", "text": json.dumps({"report": {"id": "Q01"}})},
                    {"type": "image_url", "image_url": {"url": "secret-query-figure"}},
                ],
            },
        ]
    }
    snapshot = copy.deepcopy(original)
    survey = reference_only_body(original, {"known_evidence": {"C01": ["R01.fft"]}})
    assert original == snapshot
    encoded = json.dumps(survey)
    assert "secret-query" not in encoded and '"Q01"' not in encoded
    assert "reference-figure" in encoded
    assert len(survey["messages"][1]["content"]) == 3


def test_diagram_audit_transport_preserves_exact_request_and_no_secret(tmp_path, monkeypatch):
    import json

    import httpx

    from modelmetis.dsp_guide import VIEW_GUIDE
    from modelmetis.dsp_report import digest
    from scripts import dsp_diagram_audit as audit
    from scripts.dsp_extended_experiment import write_json

    folder = tmp_path / "survey"
    folder.mkdir()
    write_json(
        tmp_path / "settings.json",
        {
            "endpoint": "https://fixture.openai.azure.com",
            "subscription": "fixture",
            "expected_capacity": 100,
            "model": "pinned",
            "version": "v1",
        },
    )
    write_json(folder / "request.json", {"model": "fixture"})
    contract = {
        "known_evidence": {"C01": ["R01." + key for key in VIEW_GUIDE]},
        "unknown_evidence": [],
    }
    write_json(folder / "contract.json", contract)
    result = {
        "diagram_review": {
            key: {
                "priority": "unavailable" if key in {"orders", "synchronous"} else "medium",
                "finding": "Observed.",
                "evidence_ids": ["R01." + key],
            }
            for key in VIEW_GUIDE
        },
        "most_informative": ["welch"],
        "limitations": "Uncalibrated.",
    }
    monkeypatch.setattr(
        audit, "verify", lambda output: {"jobs": [{"name": "survey", "stage": "survey"}]}
    )
    monkeypatch.setattr(
        audit.dsp_inference, "verify_target", lambda settings: {"sku": {"capacity": 100}}
    )
    monkeypatch.setattr(
        audit.dsp_inference, "azure_json", lambda *args: {"accessToken": "secret-marker"}
    )
    monkeypatch.setattr(audit.dsp_inference, "estimate_cost", lambda *args: 0.01)

    def respond(request):
        assert request.content == (folder / "request.json").read_bytes()
        assert request.headers["Authorization"] == "Bearer secret-marker"
        return httpx.Response(
            200,
            json={
                "model": "pinned-v1",
                "usage": {},
                "choices": [{"finish_reason": "stop", "message": {"content": json.dumps(result)}}],
            },
        )

    receipt = audit.execute_one(
        tmp_path,
        "survey",
        lambda **kwargs: httpx.Client(transport=httpx.MockTransport(respond), **kwargs),
    )
    assert receipt["status"] == "completed" and receipt["http_attempts"] == 1
    assert receipt["response_sha256"] == digest(folder / "response.json")
    assert "secret-marker" not in (folder / "attempt.json").read_text()
    assert audit.completed_result(folder, contract, "survey") == result
    with pytest.raises(FileExistsError):
        audit.execute_one(tmp_path, "survey")
    previous = json.loads((folder / "attempt.json").read_text())
    previous.update(status="technical_failure", error="Synthetic overstrict validator")
    write_json(folder / "attempt.json", previous)
    original_receipt = (folder / "attempt.json").read_bytes()
    recovered = tmp_path / "recovered"
    recovered.mkdir()
    write_json(recovered / "request.json", {"model": "fixture"})
    write_json(recovered / "contract.json", contract)
    audit.adopt_result(folder, recovered, {"model": "pinned", "version": "v1"}, "survey")
    restored = json.loads((recovered / "attempt.json").read_text())
    assert restored["status"] == "completed" and restored["http_attempts"] == 0
    assert "error" not in restored
    assert (folder / "attempt.json").read_bytes() == original_receipt
    assert (recovered / "source-attempt.json").read_bytes() == original_receipt
    assert audit.completed_result(recovered, contract, "survey") == result
    write_json(recovered / "request.json", {"model": "changed"})
    with pytest.raises(ValueError, match="identical bound inputs"):
        audit.adopt_result(folder, recovered, {"model": "pinned", "version": "v1"}, "survey")


def test_family_separation_distinguishes_class_signal_from_regime_signal():
    from scripts.dsp_family_separation import separation_metrics

    records = [
        {"id": str(index), "class": label, "group": str(index), "regime": regime}
        for index, (label, regime) in enumerate(
            [("A", "r1"), ("A", "r2"), ("B", "r1"), ("B", "r2")]
        )
    ]
    separated = separation_metrics(records, [[0], [0.1], [10], [10.1]])
    assert separated["forced_correct"] == 4
    assert separated["complete_gap_classes"] == 2
    assert separated["median_within_over_between"] < 0.02
    nuisance = separation_metrics(records, [[0], [10], [0], [10]])
    assert nuisance["forced_correct"] == 0 and nuisance["tied_or_unavailable"] == 4
    assert nuisance["median_within_over_between"] == 2
    assert nuisance["complete_gap_classes"] == 0
    constant = separation_metrics(records, [[1], [1], [1], [1]])
    assert constant["median_within_over_between"] is None
    assert constant["tied_or_unavailable"] == 4


def test_family_separation_groups_windows_and_preserves_missing_support():
    from scripts.dsp_family_separation import separation_metrics

    records = [
        {"id": str(index), "class": label, "group": group, "regime": regime}
        for index, (label, group, regime) in enumerate(
            [
                ("A", "a1", "r1"),
                ("A", "a1", "r1"),
                ("A", "a2", "r2"),
                ("B", "b1", "r1"),
                ("B", "b2", "r2"),
            ]
        )
    ]
    values = [[0, np.nan], [0.2, 3], [0.1, 4], [10, 3], [10.1, 4]]
    result = separation_metrics(records, values)
    assert result["recordings"] == 5 and result["acquisitions"] == 4
    assert result["forced_correct"] == 4
    assert result["common_coordinates"] == 1 and result["common_fraction"] == 0.5
    assert result["per_class"][0]["within"]["pairs"] == 1
    assert result["within_session"]["pairs"] == 1
    assert separation_metrics(records, [None] * 5)["status"] == "unavailable"
    with pytest.raises(ValueError, match="Duplicate"):
        separation_metrics(records + records[:1], values + values[:1])


def test_family_features_keep_carrier_axis_and_ignore_arbitrary_time_origin():
    from scripts.dsp_family_separation import extension_vector, temporal_quantiles

    mapping = {"status": "available", "kind": "map", "values": [[1, 2], [4, None]]}
    vector = extension_vector("kurtosis_bank", mapping, 8000)
    assert vector.shape == (4,) and np.isnan(vector[-1])
    temporal = np.array([[1, 3, 2, 4], [5, 6, 8, 7]], dtype=float)
    np.testing.assert_allclose(temporal_quantiles(temporal), temporal_quantiles(temporal[:, ::-1]))
    persistence = {
        "status": "available",
        "kind": "map",
        "y": [-20, -10, 0],
        "values": [[10, 30], [30, 60], [60, 10]],
    }
    shifted = {**persistence, "y": [20, 30, 40]}
    np.testing.assert_allclose(
        extension_vector("persistence", persistence, 8000),
        extension_vector("persistence", shifted, 8000),
        atol=1e-12,
    )


def test_pruning_removes_all_explicit_channels_and_preserves_other_pixels():
    import copy
    import io
    import json

    from PIL import Image

    from scripts.audio_comparison import data_url
    from scripts.dsp_pruning_experiment import prune_body, pruned_contract, variants

    image = Image.new("RGB", (2400, 1520), (40, 90, 180))
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    original = {
        "messages": [
            {"role": "system", "content": "Original"},
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": json.dumps(
                            {
                                "numerical_control": {
                                    "bands": {"R01": 123.456},
                                    "ridge": {"R01": 789.012},
                                    "welch": {"R01": 2},
                                }
                            }
                        ),
                    },
                    {
                        "type": "text",
                        "text": json.dumps(
                            {
                                "report": {
                                    "channels": [
                                        {
                                            "intervals": [
                                                {
                                                    "measurements": {
                                                        "bands": [123.456],
                                                        "autocorrelation": {"peak": 987.654},
                                                        "welch": {"power": 1},
                                                    }
                                                }
                                            ]
                                        }
                                    ]
                                },
                                "extensions": {"ridge": {"max": 789.012}, "wavelet": {"max": 3}},
                            }
                        ),
                    },
                    {
                        "type": "text",
                        "text": json.dumps(
                            {
                                "cell_evidence_ids_row_major": [
                                    "R01.bands",
                                    "R01.welch",
                                    "R01.ridge",
                                    "R01.autocorrelation",
                                ]
                            }
                        ),
                    },
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": data_url(buffer.getvalue(), "image/png"),
                            "detail": "high",
                        },
                    },
                ],
            },
        ]
    }
    snapshot = copy.deepcopy(original)
    removed = {"bands", "ridge", "autocorrelation"}
    pruned = prune_body(original, removed)
    assert original == snapshot
    parts = pruned["messages"][1]["content"]
    text = " ".join(part["text"] for part in parts if part["type"] == "text")
    assert not any(marker in text for marker in ("123.456", "789.012", "987.654"))
    assert '"welch"' in text and '"wavelet"' in text
    import base64

    with Image.open(
        io.BytesIO(base64.b64decode(parts[-1]["image_url"]["url"].split(",")[1]))
    ) as result:
        assert result.size == image.size
        np.testing.assert_array_equal(
            np.asarray(result)[:380, 600:1200], np.asarray(image)[:380, 600:1200]
        )
        assert np.all(np.asarray(result)[:380, :600] == 255)
    contract = pruned_contract(
        {
            "known_evidence": {"C01": ["R01.bands", "R01.welch"]},
            "unknown_evidence": ["Q01.bands", "Q01.welch"],
        },
        removed,
    )
    assert contract["known_evidence"]["C01"] == ["R01.welch"]
    assert contract["unknown_evidence"] == ["Q01.welch"]
    assert len(variants()) == 8 and len({tuple(item["removed"]) for item in variants()}) == 8


def test_crossed_pruning_schedule_is_balanced_and_has_exact_repeat_cells():
    from collections import Counter

    from scripts.dsp_pruning_experiment import schedule

    jobs = schedule()
    assert len(jobs) == 46 and len({job["name"] for job in jobs}) == 46
    assert Counter(job["block"] for job in jobs) == {
        "factorial": 32,
        "regression": 8,
        "targeted": 2,
        "replicate": 4,
    }
    factorial = [job for job in jobs if job["block"] == "factorial"]
    assert set(Counter(job["arm"] for job in factorial).values()) == {4}
    assert set(Counter(job["source_case"] for job in factorial).values()) == {8}
    for job in [job for job in jobs if job["block"] == "replicate"]:
        matches = [
            other
            for other in factorial
            if other["source_case"] == job["source_case"]
            and other["arm"] == job["arm"]
            and other["removed"] == job["removed"]
        ]
        assert len(matches) == 1
