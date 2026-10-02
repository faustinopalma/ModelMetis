import json

import numpy as np
import pytest
import soundfile as sf

from tools.audio_order_estimated.cli import main as estimated_main
from tools.audio_order_known.cli import main, rpm_trace
from tools.audio_order_known.report import digest, read_audio


def test_known_report_is_complete_and_does_not_overwrite(tmp_path):
    rate = 8000
    clock = np.arange(rate * 2) / rate
    source = tmp_path / "synthetic & tone.wav"
    samples = 0.5 * np.cos(2 * np.pi * 60 * clock)
    sf.write(source, np.column_stack([samples, -samples]), rate, subtype="FLOAT")
    source_hash = digest(source)
    output = tmp_path / "known"
    assert main([str(source), "--rpm", "1800", "--output", str(output)]) == 0
    report = json.loads((output / "measurements.json").read_text())
    assert len(report["figures"]) == 9
    assert report["source"]["source_channels"] == 2
    assert report["raw_metrics"]["rms_fs"] == pytest.approx(0.5 / np.sqrt(2))
    assert "synthetic &amp; tone.wav" in (output / "report.html").read_text()
    manifest = json.loads((output / "manifest.json").read_text())
    assert len(manifest) == 12
    assert all(digest(output / path) == expected for path, expected in manifest.items())
    with pytest.raises(SystemExit) as exit_info:
        main([str(source), "--rpm", "1800", "--output", str(output)])
    assert exit_info.value.code == 2
    assert digest(source) == source_hash


def test_unreliable_estimate_still_writes_original_report(tmp_path):
    source = tmp_path / "silence.wav"
    sf.write(source, np.zeros(16000), 8000)
    output = tmp_path / "unreliable"
    assert estimated_main([str(source), "--output", str(output)]) == 3
    report = json.loads((output / "measurements.json").read_text())
    assert report["normalization"]["status"] == "unavailable"
    assert len(report["figures"]) == 4
    with np.load(output / "arrays.npz") as arrays:
        assert "order_psd" not in arrays


def test_rpm_csv_uses_recording_clock_and_rejects_extrapolation():
    payload = b"time_seconds,rpm\n0,600\n10,1200\n"
    assert rpm_trace(payload, np.array([5, 6])) == pytest.approx([15, 16])
    with pytest.raises(ValueError, match="cover"):
        rpm_trace(payload, np.array([9, 11]))
    with pytest.raises(ValueError, match="increase"):
        rpm_trace(b"time_seconds,rpm\n0,600\n0,1200\n", np.array([0]))


@pytest.mark.parametrize("payload", [b"time,rpm\n0,600", b"time_seconds,rpm\n0,600\n1,",
                                     b"time_seconds,rpm\n0,600\n1,0\n"])
def test_invalid_rpm_csv(payload):
    with pytest.raises(ValueError):
        rpm_trace(payload, np.array([0, 1]))


def test_selection_preserves_channel_and_rate(tmp_path):
    source = tmp_path / "channels.wav"
    sf.write(source, np.column_stack([np.zeros(8000), np.ones(8000) * 0.2]), 8000)
    samples, rate, audit = read_audio(source, start=0.5, duration=0.25, channel=2)
    assert rate == 8000 and len(samples) == 2000
    assert np.mean(samples) == pytest.approx(0.2, abs=1e-4)
    assert audit["start_seconds"] == 0.5


def test_single_frame_map_has_nonzero_area():
    from tools.audio_order_known.report import axes_figure, draw_map

    figure, axes = axes_figure()
    mesh = draw_map(axes[0], np.array([0.2]), np.array([0, 1, 2]),
                    np.ones((3, 1)), (0.1, 0.3), -100, 10)
    coordinates = mesh.get_coordinates()
    assert np.ptp(coordinates[:, :, 0]) == pytest.approx(0.2)
    assert np.ptp(coordinates[:, :, 1]) > 0
    figure.clear()