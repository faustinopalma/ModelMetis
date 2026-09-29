import hashlib
import io
from dataclasses import replace

import numpy as np
import pytest
import soundfile as sf
from PIL import Image

from modelmetis.visual_audio import (
    RenderConfig,
    decode_audio,
    evaluate_predictions,
    image_messages,
    numerical_decision,
    parse_decision,
    render_png,
    render_recordings,
    stft_power,
    welch_features,
    windows,
)


def tone(config, frequency=1000, amplitude=0.1):
    times = np.arange(config.window_samples) / config.sample_rate
    return amplitude * np.sin(2 * np.pi * frequency * times)


def test_stft_frequency_power_and_absolute_level():
    config = RenderConfig()
    frequencies, _, decibels = stft_power(tone(config), config)
    assert frequencies[np.argmax(decibels.mean(axis=1))] == 1000
    power = 10 ** (decibels / 10)
    np.testing.assert_allclose(power.sum(axis=0) * config.sample_rate / config.nfft, 0.005)
    _, _, louder = stft_power(tone(config, amplitude=0.2), config)
    np.testing.assert_allclose(louder[32] - decibels[32], 20 * np.log10(2))


def test_transient_remains_localized_in_time():
    config = RenderConfig()
    samples = np.zeros(config.window_samples)
    samples[4000] = 0.5
    _, times, decibels = stft_power(samples, config)
    active = times[np.max(decibels, axis=0) > -100]
    assert len(active) > 0
    assert active.min() >= 0.23
    assert active.max() <= 0.27


def test_windows_keep_offsets_transition_tail_and_silence():
    config = RenderConfig()
    samples = np.concatenate([np.zeros(4000), np.full(4300, 0.25)])
    result = list(windows(samples, config))
    assert len(result) == 2
    assert result[0][1]["end_sample_exclusive"] == 8000
    assert result[0][1]["regime"] == "unverified_may_include_transitions"
    assert result[1][1]["start_sample"] == 8000
    assert result[1][1]["valid_samples"] == 300
    assert result[1][1]["padding_samples"] == 7700
    assert result[1][1]["rms"] == 0.25
    assert list(windows(np.zeros(30), config))[0][1]["silence"]


def test_overlap_does_not_make_redundant_tail():
    config = replace(RenderConfig(), overlap_seconds=0.25)
    result = list(windows(np.ones(12000), config))
    assert [metadata["start_sample"] for _, metadata in result] == [0, 4000]


@pytest.mark.parametrize("changes", [
    {"overlap_seconds": 0.5}, {"reference_power": 0}, {"db_max": -120},
    {"frequency_max": 9000}, {"window_seconds": 0.0001}, {"hop": 513},
    {"window_seconds": float("nan")}, {"channel_policy": "implicit"},
])
def test_invalid_render_config_is_rejected(changes):
    with pytest.raises(ValueError):
        replace(RenderConfig(), **changes).validate()


def test_nonfinite_audio_is_rejected():
    with pytest.raises(ValueError):
        list(windows(np.array([np.nan]), RenderConfig()))


@pytest.mark.parametrize("container", ["WAV", "FLAC"])
def test_content_decode_preserves_levels_and_detects_truncation(tmp_path, container):
    config = RenderConfig()
    path = tmp_path / "neutral.wav"
    sf.write(path, tone(config), config.sample_rate, format=container, subtype="PCM_24")
    samples, metadata = decode_audio(path, config)
    np.testing.assert_allclose(samples, tone(config), atol=2 ** -22)
    assert metadata["container"] == container
    assert metadata["transformations"] == []
    path.write_bytes(path.read_bytes()[:-30])
    with pytest.raises((ValueError, sf.LibsndfileError)):
        decode_audio(path, config)


def test_channel_and_sample_rate_changes_require_explicit_policy(tmp_path):
    config = RenderConfig()
    path = tmp_path / "neutral.wav"
    sf.write(path, np.column_stack([tone(config), -tone(config)]), 32000, subtype="FLOAT")
    with pytest.raises(ValueError, match="channel"):
        decode_audio(path, config)
    with pytest.raises(ValueError, match="Sample-rate"):
        decode_audio(path, replace(config, channel_policy="mean"))
    samples, metadata = decode_audio(
        path, replace(config, channel_policy="mean", resample_policy="polyphase"),
    )
    assert len(samples) == 4000
    assert np.max(np.abs(samples)) == 0
    assert len(metadata["transformations"]) == 2


def test_png_is_deterministic_fixed_scale_and_metadata_free():
    config = RenderConfig()
    first = render_png(tone(config), config.window_samples, config)
    second = render_png(tone(config), config.window_samples, config)
    assert first == second
    quieter = render_png(tone(config, amplitude=0.01), config.window_samples, config)
    with Image.open(io.BytesIO(first)) as image, Image.open(io.BytesIO(quieter)) as low:
        assert image.size == (1024, 768)
        assert image.mode == "RGB"
        assert image.info == {}
        assert np.std(np.asarray(image)) > 20
        assert not np.array_equal(np.asarray(image), np.asarray(low))


def test_manifest_binds_parent_offsets_config_pcm_and_png(tmp_path):
    config = RenderConfig()
    path = tmp_path / "answer-bearing.wav"
    sf.write(path, np.concatenate([tone(config), np.zeros(100)]), 16000, subtype="PCM_24")
    records = [{"path": str(path), "recording_id": "opaque", "group_id": "unit",
                "split": "support"}]
    report = render_recordings(records, tmp_path / "render", config)
    assert report["status"] == "completed"
    assert report["config_sha256"] == config.sha256
    assert len(report["recordings"][0]["windows"]) == 2
    for window in report["recordings"][0]["windows"]:
        png = (tmp_path / "render" / window["image"]).read_bytes()
        assert hashlib.sha256(png).hexdigest() == window["image_sha256"]
        assert b"answer-bearing" not in png


def test_split_group_check_precedes_decode(tmp_path):
    records = [{"path": "absent", "recording_id": str(index), "group_id": "same",
                "split": split} for index, split in enumerate(["support", "query"])]
    with pytest.raises(ValueError, match="group crosses"):
        render_recordings(records, tmp_path / "render", RenderConfig())


def test_model_input_contains_only_neutral_ids_and_stft_pngs():
    config = RenderConfig()
    png = render_png(tone(config), config.window_samples, config)
    messages = image_messages([("C01", png), ("C02", png)], png, config)
    content = messages[1]["content"]
    assert [item["text"] for item in content if item["type"] == "text"] == [
        "Reference C01", "Reference C02", "Query",
    ]
    assert all(item["image_url"]["detail"] == "high" for item in content
               if item["type"] == "image_url")
    with pytest.raises(ValueError, match="opaque"):
        image_messages([("healthy", png)], png, config)


@pytest.mark.parametrize("decision", [
    {"outcome": "known", "condition_id": "C03", "explanation": "same"},
    {"outcome": "outside_reference", "condition_id": "C01", "explanation": "different"},
    {"outcome": "indeterminate", "condition_id": None, "explanation": ""},
    {"outcome": "known", "condition_id": "C01", "explanation": "same", "extra": 1},
    {"outcome": [], "condition_id": None, "explanation": "invalid"},
    {"outcome": "known", "condition_id": {}, "explanation": "invalid"},
])
def test_strict_response_contract(decision):
    with pytest.raises(ValueError):
        parse_decision(decision, ["C01", "C02"])


def test_welch_matches_time_averaged_stft_without_extra_normalization():
    config = RenderConfig()
    samples = tone(config)
    _, _, decibels = stft_power(samples, config)
    expected = np.clip(10 * np.log10(np.mean(10 ** (decibels / 10), axis=1)), -110, -10)
    np.testing.assert_allclose(welch_features(samples, config), expected)
    reference = {"C01": np.zeros(5), "C02": np.full(5, 20)}
    assert numerical_decision(np.zeros(5), reference)["outcome"] == "known"
    assert numerical_decision(np.full(5, 50), reference)["outcome"] == "outside_reference"
    assert numerical_decision(np.full(5, 10), reference)["outcome"] == "indeterminate"


def test_evaluation_distinguishes_errors_abstention_and_failure():
    outcomes = [("C01", "known", "C01"), ("C01", "known", "C02"),
                ("C01", "outside_reference", None), ("C03", "known", "C01"),
                ("C03", "outside_reference", None), ("C03", "indeterminate", None)]
    rows = [{"truth": truth, "visible_ids": ["C01", "C02"],
             "group_id": "unit", "recording_id": "same",
             "decision": {"outcome": outcome, "condition_id": identifier,
                          "explanation": "evidence"}} for truth, outcome, identifier in outcomes]
    rows.append({"truth": "C01", "visible_ids": ["C01", "C02"], "group_id": "unit",
                 "recording_id": "same", "technical_failure": True})
    result = evaluate_predictions(rows)
    assert set(result["counts"].values()) == {1}
    assert result["known_trials"] == 4
    assert result["unknown_trials"] == 3
    assert result["accepted_label_error"] == 2 / 3
    assert result["query_physical_groups"] == result["query_recordings"] == 1
    assert result["independent_acquisitions"] is None
    empty = evaluate_predictions([])
    assert empty["accepted_label_error"] is None
    assert empty["known_label_coverage"] is None


def test_failed_decode_preserves_attempt_and_refuses_overwrite(tmp_path):
    records = [{"path": str(tmp_path / "absent.wav"), "recording_id": "opaque",
                "group_id": "unit", "split": "query"}]
    with pytest.raises(FileNotFoundError):
        render_recordings(records, tmp_path / "run", RenderConfig())
    from scripts.visual_audio import read_json

    report = read_json(tmp_path / "run/manifest.json")
    assert report["status"] == "failed"
    assert report["error_type"] == "FileNotFoundError"
    with pytest.raises(FileExistsError):
        render_recordings(records, tmp_path / "run", RenderConfig())


def test_runner_rejects_changed_frozen_code_or_config(tmp_path):
    from scripts.visual_audio import digest, verify_prepared, write_json

    write_json(tmp_path / "registration.json", {
        "config_sha256": "changed", "runner_sha256": "old", "renderer_sha256": "old",
    })
    write_json(tmp_path / "audit.json", {
        "status": "completed", "registration_sha256": digest(tmp_path / "registration.json"),
    })
    with pytest.raises(ValueError, match="Frozen"):
        verify_prepared(tmp_path, RenderConfig())


def test_pcm_positive_full_scale_is_counted_as_clipping(tmp_path):
    path = tmp_path / "clipped.wav"
    sf.write(path, np.array([-32768, 0, 32767], dtype=np.int16), 16000, subtype="PCM_16")
    samples, metadata = decode_audio(path, RenderConfig())
    assert metadata["source_clipped_samples"] == 2
    result = list(windows(samples, RenderConfig(), metadata["positive_clip_threshold"]))
    assert result[0][1]["clipped_samples"] == 2


def test_offline_pipeline_holds_out_whole_conditions_and_seals_answers(tmp_path):
    from modelmetis import visual_audio
    from scripts import visual_audio as runner

    config = RenderConfig()
    prepared = tmp_path / "prepared"
    (prepared / "audio").mkdir(parents=True)
    (prepared / "sealed").mkdir()
    records, sources, supports, queries = [], [], [], []
    for split in ("support", "query"):
        for number, frequency in enumerate((750, 1750, 3750), 1):
            identifier = f"{split}-{number}"
            relative = f"audio/{identifier}.wav"
            samples = tone(config, frequency, amplitude=0.1 if split == "support" else 0.11)
            sf.write(prepared / relative, samples, 16000, subtype="PCM_24")
            row = {"recording_id": identifier, "group_id": split, "split": split,
                   "path": relative}
            records.append(row)
            sources.append({**row, "condition_id": f"C{number:02}",
                            "source_sha256": runner.digest(prepared / relative)})
            if split == "support":
                supports.append({"recording_id": identifier, "condition_id": f"C{number:02}"})
            else:
                queries.append(identifier)
    runner.write_json(prepared / "manifest.json", records)
    runner.write_json(prepared / "inputs.json", {"supports": supports, "queries": queries})
    runner.write_json(prepared / "sealed/sources.json", sources)
    runner.write_json(prepared / "registration.json", {
        "config_sha256": config.sha256, "runner_sha256": runner.digest(runner.__file__),
        "renderer_sha256": runner.digest(visual_audio.__file__),
        "numeric": {"max_distance_db": 12.0, "min_margin_db": 2.0},
        "schedule": ["all_known", "without_C01", "without_C02", "without_C03"],
    })
    runner.write_json(prepared / "audit.json", {
        "status": "completed", "registration_sha256": runner.digest(prepared / "registration.json"),
        "files": {name: runner.digest(prepared / name) for name in
                  ("manifest.json", "inputs.json", "sealed/sources.json")},
    })
    run = tmp_path / "run"
    predictions = runner.compare_offline(prepared, run, config)
    assert len(predictions) == 12
    assert all("truth" not in prediction for prediction in predictions)
    for condition in ("C01", "C02", "C03"):
        for query in queries:
            message = runner.read_json(run / "messages" / f"without_{condition}-{query}.json")
            titles = [part["text"] for part in message["messages"][1]["content"]
                      if part["type"] == "text"]
            assert f"Reference {condition}" not in titles
            assert titles[-1] == "Query"
            assert len(titles) == 3
    aggregate = runner.evaluate(prepared, run, tmp_path / "evaluation", config)
    assert aggregate["numeric"]["known_trials"] == 9
    assert aggregate["numeric"]["unknown_trials"] == 3
    assert aggregate["visual"]["submitted_requests"] == 0
    assert aggregate["numeric"]["query_recordings"] == 3
    assert aggregate["verdict"] == "inconclusive_no_real_visual_comparison"