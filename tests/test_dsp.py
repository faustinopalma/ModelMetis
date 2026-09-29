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