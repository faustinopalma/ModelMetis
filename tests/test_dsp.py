import numpy as np
import pytest
import soundfile as sf

from modelmetis.dsp import (
    DspConfig,
    analyze_segment,
    decode_recording,
    fft_spectrum,
    plotted_segment_indices,
    segment_slices,
)


def sine(frequency=1000, amplitude=0.1, seconds=1.0, rate=16000):
    clock = np.arange(round(seconds * rate)) / rate
    return amplitude * np.sin(2 * np.pi * frequency * clock)


def test_fft_coherent_gain_amplitude_resolution_and_level_change():
    frequencies, amplitude, parameters = fft_spectrum(sine(), 16000)
    assert frequencies[np.argmax(amplitude)] == 1000
    assert amplitude[1000] == pytest.approx(0.1)
    assert parameters["bin_spacing_hz"] == 1
    assert parameters["equivalent_noise_bandwidth_hz"] == pytest.approx(1.5)
    _, louder, _ = fft_spectrum(sine(amplitude=0.2), 16000)
    assert 20 * np.log10(louder[1000] / amplitude[1000]) == pytest.approx(6.020599913)


def test_fft_dc_and_nyquist_are_not_doubled():
    _, amplitude, _ = fft_spectrum(np.ones(1024) * 0.2, 16000)
    assert amplitude[0] == pytest.approx(0.2)
    _, amplitude, _ = fft_spectrum(0.3 * (-1.0) ** np.arange(1024), 16000)
    assert amplitude[-1] == pytest.approx(0.3)


def test_welch_power_bands_stft_and_rms_are_consistent():
    metrics, arrays = analyze_segment(sine(), 16000, DspConfig())
    assert metrics["rms_fs"] == pytest.approx(0.1 / np.sqrt(2))
    assert metrics["crest_factor_db"] == pytest.approx(3.0102999566)
    assert metrics["welch"]["integrated_power_fs_squared"] == pytest.approx(0.005)
    assert sum(band["power_fs_squared"] for band in metrics["bands"]) == pytest.approx(0.005)
    np.testing.assert_allclose(arrays["stft_psd"].mean(axis=1), arrays["welch_psd"], atol=1e-20)
    assert metrics["peaks"][0]["frequency_hz"] == 1000
    assert metrics["autocorrelation"]["strongest_positive_peak_lag_seconds"] == 0.001


def test_envelope_recovers_known_amplitude_modulation():
    clock = np.arange(32000) / 16000
    samples = 0.1 * (1 + 0.5 * np.cos(2 * np.pi * 40 * clock)) * np.sin(2 * np.pi * 2000 * clock)
    metrics, _ = analyze_segment(samples, 16000, DspConfig())
    assert metrics["envelope"]["status"] == "available"
    peak = metrics["envelope"]["modulation_peaks"][0]
    assert peak["frequency_hz"] == pytest.approx(40)
    assert peak["amplitude_fs_peak"] == pytest.approx(0.05, abs=1e-6)


def test_silence_and_short_tail_are_not_fake_spectral_evidence():
    metrics, arrays = analyze_segment(np.zeros(8000), 16000, DspConfig())
    assert metrics["silent"]
    assert metrics["rms_db_re_1_fs"] is None
    assert metrics["crest_factor_db"] is None
    assert metrics["peaks"] == []
    assert np.max(arrays["autocorrelation"]) == 0
    short, _ = analyze_segment(np.zeros(7), 16000, DspConfig(), start_sample=80000)
    assert short["spectral_status"] == "unavailable_fewer_than_32_samples"
    assert short["padding_samples"] == 0
    assert short["end_sample_exclusive"] == 80007


def test_level_changes_and_tail_remain_traceable():
    samples = np.concatenate([sine(seconds=0.2), sine(amplitude=0.4, seconds=0.2), np.zeros(17)])
    metrics, arrays = analyze_segment(samples, 16000, DspConfig(), start_sample=16000)
    assert any(abs(change["time_seconds"] - 1.2) < 0.021 for change in metrics["level_changes"])
    assert arrays["level_valid_samples"][-1] == 17
    assert metrics["regime"] == "unverified_may_be_mixed"
    assert segment_slices(160001, 16000, DspConfig()) == [
        (0, 80000), (80000, 160000), (160000, 160001),
    ]


def test_nonfinite_signal_is_rejected():
    with pytest.raises(ValueError, match="finite"):
        analyze_segment(np.array([1.0, np.nan]), 16000, DspConfig())


def test_native_stereo_channels_are_preserved_even_when_the_mean_cancels(tmp_path):
    samples = np.column_stack([sine(rate=44100), -sine(rate=44100)])
    path = tmp_path / "source.wav"
    sf.write(path, samples, 44100, subtype="FLOAT")
    decoded, rate, provenance = decode_recording(path, DspConfig())
    assert rate == 44100
    np.testing.assert_allclose(decoded, samples, atol=1e-8)
    assert np.max(np.abs(decoded[:, 0])) == pytest.approx(np.max(np.abs(samples[:, 0])), abs=1e-8)
    assert provenance["analysis_transformations"] == []
    assert provenance["analysis_channel_policy"] == "preserve_each_native_channel"


def test_plot_schedule_is_fixed_time_sampling_with_first_and_last():
    config = DspConfig()
    assert plotted_segment_indices(2, config) == [0, 1]
    assert plotted_segment_indices(120, config) == [0, 39, 79, 119]


def test_report_generates_seven_views_numbers_and_separate_provenance(tmp_path):
    import json

    from modelmetis.dsp_report import generate_report

    path = tmp_path / "hidden-diagnosis.wav"
    sf.write(path, sine(seconds=0.5), 16000, subtype="PCM_24")
    output = tmp_path / "report"
    report = generate_report(path, output)
    segment = report["channels"][0]["segments"][0]
    assert len(segment["images"]) == 7
    assert len(list((output / "images").glob("*.png"))) == 8
    assert segment["fft"]["bin_spacing_hz"] == 2
    assert segment["peaks"][0]["frequency_hz"] == 1000
    for name in ("report.html", "report.md", "evidence.json"):
        text = (output / name).read_text()
        assert "hidden-diagnosis" not in text
    json.dumps(json.loads((output / "evidence.json").read_text()), allow_nan=False)
    provenance = json.loads((output / "provenance.json").read_text())
    assert "hidden-diagnosis" in provenance["source_path"]
    manifest = json.loads((output / "manifest.json").read_text())
    assert manifest["status"] == "completed"
    assert "report.html" in manifest["files"]
    with pytest.raises(FileExistsError):
        generate_report(path, output)


def test_report_preserves_failed_attempt(tmp_path):
    import json

    from modelmetis.dsp_report import generate_report

    output = tmp_path / "failed"
    with pytest.raises(FileNotFoundError):
        generate_report(tmp_path / "missing.wav", output)
    manifest = json.loads((output / "manifest.json").read_text())
    assert manifest["status"] == "failed"
    assert manifest["error_type"] == "FileNotFoundError"
    assert (output / "attempts.jsonl").exists()


def test_fixed_segments_retain_final_sample_and_image_budget(tmp_path):
    from dataclasses import replace

    from PIL import Image

    from modelmetis.dsp_report import generate_report

    path = tmp_path / "source.wav"
    sf.write(path, np.concatenate([sine(seconds=0.15), [0.0]]), 16000, subtype="PCM_24")
    config = replace(DspConfig(), segment_seconds=0.05, max_plot_segments=2)
    report = generate_report(path, tmp_path / "report", config)
    segments = report["channels"][0]["segments"]
    assert len(segments) == 4
    assert sum(segment["valid_samples"] for segment in segments) == 2401
    assert [segment["segment"] for segment in segments if segment["images"]] == [1, 4]
    assert segments[-1]["valid_samples"] == 1
    assert segments[-1]["spectral_status"] == "unavailable_fewer_than_32_samples"
    stft = next(image for image in segments[0]["images"] if image["title"] == "STFT spectrogram")
    with Image.open(tmp_path / "report" / stft["path"]) as picture:
        assert min(picture.getpixel((600, 350))) < 240


def test_optional_bandpass_envelope_and_invalid_band():
    from dataclasses import replace

    config = replace(DspConfig(), envelope_band_hz=(1500, 2500))
    metrics, _ = analyze_segment(sine(frequency=2000, seconds=0.5), 16000, config)
    assert metrics["envelope"]["filter"] == "butterworth_order4_zero_phase_sos"
    with pytest.raises(ValueError, match="Envelope band"):
        replace(config, envelope_band_hz=(1500, 9000)).validate(16000)


def test_physical_shape_resolution_gain_invariance_and_band_accounting():
    from modelmetis.dsp_comparison import compare_shapes, shape_features

    samples = sine(frequency=1000, seconds=2) + sine(frequency=1040, seconds=2)
    original = shape_features(samples, 16000)
    louder = shape_features(samples * 3, 16000)
    for comparison in compare_shapes(original, louder):
        assert comparison["distance_db"] < 1e-9
        assert sum(band["squared_distance_contribution_db2"] for band in comparison["bands"]) == (
            pytest.approx(comparison["distance_db"] ** 2, abs=1e-18))
    assert louder["quality"]["rms_fs"] == pytest.approx(original["quality"]["rms_fs"] * 3)
    for rate in (8000, 42000, 44100):
        other = shape_features(sine(frequency=1000, seconds=2, rate=rate)
                               + sine(frequency=1040, seconds=2, rate=rate), rate)
        for view, comparison in zip(other["resolutions"], compare_shapes(original, other),
                                    strict=True):
            assert view["bin_spacing_hz"] == pytest.approx(1 / view["requested_frame_seconds"])
            assert view["hann_enbw_hz"] == pytest.approx(1.5 * view["bin_spacing_hz"])
            assert comparison["distance_db"] < 0.15
        fine = other["resolutions"][-1]
        from scipy.signal import find_peaks

        peaks, _ = find_peaks(fine["median_db"], prominence=10)
        assert {fine["frequencies_hz"][position] for position in peaks} == {1000, 1040}


def test_shape_unavailable_tails_silence_and_temporal_transition():
    from modelmetis.dsp_comparison import compare_shapes, shape_features

    quiet = shape_features(np.zeros(16000), 16000)
    assert all(view["status"] == "unavailable" for view in quiet["resolutions"])
    assert all(row["status"] == "unavailable" for row in compare_shapes(quiet, quiet))
    samples = np.concatenate([sine(frequency=1000), sine(frequency=2000), [0.0]])
    changing = shape_features(samples, 16000)
    for view in changing["resolutions"]:
        assert view["available_segments"] == 2
        assert view["total_segments"] == 3
        assert view["segments"][-1]["status"] == "unavailable"
        assert view["segments"][-1]["end_sample_exclusive"] == 32001
        assert min(view["temporal_distance_db"]) > 1
        assert np.max(np.subtract(view["q90_db"], view["q10_db"])) > 10
    with pytest.raises(ValueError, match="finite"):
        shape_features([float("nan")], 16000)


def test_comparison_baseline_matches_existing_labeled_calculation():
    from modelmetis.dsp_comparison import shape_features

    samples = sine(seconds=2) + np.random.default_rng(13).normal(0, 0.01, 32000)
    _, arrays = analyze_segment(samples, 16000, DspConfig())
    expected = 10 * np.log10(np.maximum(arrays["welch_psd"], 1e-30))
    expected -= expected.mean()
    np.testing.assert_allclose(shape_features(samples, 16000)["baseline"]["shape_db"], expected)
    controls = shape_features(samples, 16000)["controls"]
    selected = (arrays["welch_frequencies"] >= 20) & (arrays["welch_frequencies"] <= 4000)
    band = expected[selected]
    np.testing.assert_allclose(controls["band_1024"]["shape_db"], band - band.mean())
    gain_controls = shape_features(samples * 2, 16000)["controls"]
    for name in controls:
        np.testing.assert_allclose(controls[name]["shape_db"], gain_controls[name]["shape_db"],
                                   atol=1e-10)


def test_multi_reference_regimes_groups_duplicates_and_unavailable():
    from modelmetis.dsp_comparison import compare_bank, shape_features

    def recording(identifier, frequency, class_id, regime="M01", group=None):
        return {"id": identifier, "class_id": class_id, "regime_id": regime,
                "group_id": group or identifier, "content_sha256": identifier,
                "features": shape_features(sine(frequency=frequency), 16000)}

    references = [recording("R01", 900, "C01"), recording("R02", 1100, "C01", "M02"),
                  recording("R03", 2000, "C02"), recording("R04", 2200, "C02", "M02")]
    query = recording("Q01", 1101, None)
    result = compare_bank(query, references)
    assert result["decision"] is None
    assert result["diagnostic_correctness"] == "unmeasured"
    assert not result["unequal_bank_sizes"]
    for ranking in result["rankings"]:
        assert ranking["forced_candidate"] == "C01"
        assert ranking["classes"][0]["closest_regime"] == "M02"
        assert ranking["margin_db"] > 0
    assert all(row["pairs"] == 1 for row in result["within_class_variability"]
               if row["scope"] == "across_regimes")
    duplicated_window = {**references[0], "id": "R05", "content_sha256": "different_window"}
    repeated = compare_bank(query, [*references, duplicated_window])
    assert [row["margin_db"] for row in repeated["rankings"]] == [
        row["margin_db"] for row in result["rankings"]]
    assert compare_bank(query, references[:-1])["unequal_bank_sizes"]
    with pytest.raises(ValueError, match="Duplicate"):
        compare_bank(query, [*references, references[0]])
    with pytest.raises(ValueError, match="overlap"):
        compare_bank({**query, "group_id": "R01"}, references)
    quiet = {**query, "features": shape_features(np.zeros(16000), 16000)}
    missing = compare_bank(quiet, references)
    assert missing["incomplete_rankings"]
    assert all(row["forced_candidate"] is None for row in missing["rankings"])


def test_shape_modulation_impulse_filter_noise_and_clipping_controls():
    from scipy import signal

    from modelmetis.dsp_comparison import compare_shapes, shape_features

    clock = np.arange(32000) / 16000
    modulated = 0.1 * (1 + 0.5 * np.cos(2 * np.pi * 40 * clock)) * np.sin(2 * np.pi * 2000 * clock)
    features = shape_features(modulated, 16000)
    fine = features["resolutions"][-1]
    peaks, _ = signal.find_peaks(fine["median_db"], prominence=10)
    assert {fine["frequencies_hz"][position] for position in peaks} == {1960, 2000, 2040}
    impulse = sine(seconds=2)
    impulse[8000] += 0.8
    transient = shape_features(impulse, 16000)
    assert transient["resolutions"][0]["segments"][0]["transient_frame_fraction"] > 0
    noisy = shape_features(modulated + np.random.default_rng(14).normal(0, 0.01, 32000), 16000)
    assert all(row["distance_db"] > 1 for row in compare_shapes(features, noisy))
    broadband = np.random.default_rng(15).normal(0, 0.1, 32000)
    filtered = signal.sosfilt(signal.butter(4, 700, fs=16000, output="sos"), broadband)
    assert compare_shapes(shape_features(broadband, 16000), shape_features(filtered, 16000))[
        -1]["distance_db"] > 5
    clipped = shape_features(np.clip(modulated * 20, -1, 1), 16000)
    assert clipped["quality"]["near_full_scale_fraction"] > 0.1


def test_offline_comparison_report_integrity_privacy_and_failed_attempt(tmp_path):
    import hashlib
    import json

    from scripts.dsp_compare_offline import execute

    records = []
    for identifier, frequency in (("R01", 1000), ("R02", 1200), ("Q01", 1010)):
        path = tmp_path / f"hidden-label-{identifier}.wav"
        sf.write(path, sine(frequency=frequency), 16000, subtype="PCM_24")
        records.append({"id": identifier, "wav": path.name, "group_id": f"private-{identifier}",
                        "audio_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                        "channel": 0})
    spec = {"schema": 1, "references": [
        {**records[0], "class_id": "C01", "regime_id": "M01"},
        {**records[1], "class_id": "C01", "regime_id": "M02"}], "query": records[2]}
    output = tmp_path / "report"
    evidence = execute(spec, output, tmp_path)
    assert len(evidence["comparisons"]) == 2
    assert len(list((output / "images").glob("*.png"))) == 6
    for name in ("report.html", "evidence.json", "features.json"):
        text = (output / name).read_text(encoding="utf-8")
        assert "hidden-label" not in text
        assert "private-" not in text
        if name.endswith(".json"):
            json.dumps(json.loads(text), allow_nan=False)
    manifest = json.loads((output / "manifest.json").read_text())
    assert manifest["files"]
    for name, expected in manifest["files"].items():
        assert hashlib.sha256((output / name).read_bytes()).hexdigest() == expected
    with pytest.raises(FileExistsError):
        execute(spec, output, tmp_path)
    bad = {**spec, "query": {**spec["query"], "audio_sha256": "wrong"}}
    with pytest.raises(ValueError, match="hash mismatch"):
        execute(bad, tmp_path / "failed", tmp_path)
    assert json.loads((tmp_path / "failed/attempt.json").read_text())["status"] == "failed"


def test_shape_invalid_configuration_and_unavailable_frequency_grid():
    from dataclasses import replace

    from modelmetis.dsp_comparison import ShapeConfig, compare_shapes, shape_features

    for config in (replace(ShapeConfig(), band_edges_hz=()),
                   replace(ShapeConfig(), frame_seconds=()),
                   replace(ShapeConfig(), relative_floor_db=0)):
        with pytest.raises(ValueError, match="configuration"):
            shape_features(sine(), 16000, config)
    config = replace(ShapeConfig(), frame_seconds=(0.023,))
    first = shape_features(sine(), 16000, config)
    second = shape_features(sine(rate=44100), 44100, config)
    assert compare_shapes(first, second)[0]["reason"] == "physical_frequency_grid_mismatch"
    outside = shape_features(sine(frequency=6000), 16000)
    assert outside["resolutions"][-1]["status"] == "unavailable"