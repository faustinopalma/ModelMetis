import numpy as np
import pytest
from scipy.integrate import cumulative_trapezoid

from tools.audio_order_known.analysis import OrderConfig, order_analysis


@pytest.mark.parametrize("accelerating", [False, True])
def test_harmonics_remain_at_their_orders(accelerating):
    rate = 8000
    clock = np.arange(rate * 4) / rate
    speed = 20 + (10 * clock if accelerating else np.zeros_like(clock))
    phase = 2 * np.pi * cumulative_trapezoid(speed, dx=1 / rate, initial=0)
    samples = 0.5 * np.cos(3 * phase) + 0.2 * np.cos(7 * phase)
    metadata, arrays = order_analysis(samples, rate, speed)
    assert abs(metadata["peak_orders"][0] - 3) <= 0.125
    assert any(abs(order - 7) <= 0.125 for order in metadata["peak_orders"][:3])
    assert np.all(np.diff(arrays["angular_times_seconds"]) > 0)
    assert metadata["integrated_full_order_psd"] == pytest.approx(0.145, rel=0.04)


@pytest.mark.parametrize("speed", [0, -1, float("nan"), float("inf")])
def test_invalid_speed_is_rejected(speed):
    with pytest.raises(ValueError, match="positive frequency"):
        order_analysis(np.ones(8000), 8000, speed)


def test_bandwidth_cannot_be_silently_exceeded():
    with pytest.raises(ValueError, match="reliable bandwidth"):
        order_analysis(np.ones(8000), 8000, 500, OrderConfig(max_order=20))


def test_short_and_silent_audio():
    with pytest.raises(ValueError, match="four complete"):
        order_analysis(np.ones(800), 8000, 20, OrderConfig(edge_seconds=0))
    _, arrays = order_analysis(np.zeros(8000), 8000, 20)
    assert np.isfinite(arrays["autocorrelation"]).all()
    assert not arrays["order_psd"].any()


def test_antialias_filter_rejects_folded_high_frequency_tone():
    rate = 8000
    clock = np.arange(rate * 4) / rate
    samples = 0.5 * np.cos(2 * np.pi * 60 * clock) + np.cos(2 * np.pi * 1200 * clock)
    _, arrays = order_analysis(samples, rate, 20, OrderConfig(samples_per_cycle=64))
    folded = arrays["order_psd"][np.abs(arrays["orders"] - 4) < 0.2].sum()
    retained = arrays["order_psd"][np.abs(arrays["orders"] - 3) < 0.2].sum()
    assert folded < retained * 1e-6


def test_max_order_must_span_a_spectral_bin():
    with pytest.raises(ValueError, match="spectral bin"):
        order_analysis(np.zeros(8000), 8000, 20, OrderConfig(max_order=0.01))