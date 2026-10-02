import numpy as np
import pytest
from scipy.integrate import cumulative_trapezoid

from tools.audio_order_estimated.estimator import EstimatorConfig, estimate_base
from tools.audio_order_known.analysis import order_analysis


@pytest.mark.parametrize("harmonics", [(1, 2, 3), (2, 3, 4)])
@pytest.mark.parametrize("accelerating", [False, True])
def test_recovers_base_with_stronger_overtone_or_missing_fundamental(harmonics, accelerating):
    rate = 8000
    clock = np.arange(rate * 4) / rate
    base = 30 + (3 * clock if accelerating else 0 * clock)
    phase = 2 * np.pi * cumulative_trapezoid(base, dx=1 / rate, initial=0)
    samples = sum(amplitude * np.cos(order * phase)
                  for order, amplitude in zip(harmonics, (0.1, 0.5, 0.25), strict=True))
    samples += np.random.default_rng(412).normal(0, 0.01, len(samples))
    result, trace = estimate_base(samples, rate)
    assert result["status"] == "accepted_acoustic_reference", result
    start, end = result["valid_start_sample"], result["valid_end_sample_exclusive"]
    assert np.max(np.abs(trace / base[start:end] - 1)) < 0.025
    metadata, _ = order_analysis(samples[start:end], rate, trace)
    assert abs(metadata["peak_orders"][0] - harmonics[1]) <= 0.125
    assert result["shaft_rpm"] is None


@pytest.mark.parametrize("kind", ["silence", "noise", "single-tone", "gap"])
def test_unreliable_audio_does_not_produce_normalization(kind):
    rate = 8000
    clock = np.arange(rate * 3) / rate
    samples = np.zeros_like(clock)
    if kind == "noise":
        samples = np.random.default_rng(92).normal(0, 0.2, len(clock))
    elif kind == "single-tone":
        samples = np.cos(2 * np.pi * 60 * clock)
    elif kind == "gap":
        samples = sum(np.cos(2 * np.pi * 30 * order * clock) for order in (1, 2, 3))
        samples[rate:2 * rate] = 0
    result, trace = estimate_base(samples, rate)
    assert result["status"] == "unreliable"
    assert trace is None


def test_invalid_range_is_rejected():
    with pytest.raises(ValueError, match="Invalid estimator"):
        estimate_base(np.zeros(8000), 8000, EstimatorConfig(min_hz=0))