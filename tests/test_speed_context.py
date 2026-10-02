import numpy as np
from scipy import signal

from modelmetis.speed_context import match_speed, order_figure

RATE = 16000


def peak_hz(samples):
    frequencies, power = signal.welch(samples, RATE, nperseg=8192)
    return frequencies[np.argmax(power)]


def test_speed_matching_moves_a_rotation_line_to_the_target_speed():
    t = np.arange(RATE * 4) / RATE
    reference = np.sin(2 * np.pi * 3 * 20.0 * t)
    matched, factor = match_speed(reference, RATE, 20.0, 26.0)
    assert abs(factor - 1.3) < 1e-3
    assert abs(peak_hz(matched) - 78.0) < 2.5
    assert abs(len(matched) - len(reference) / 1.3) < 2


def test_speed_matching_lowers_frequencies_without_aliasing():
    t = np.arange(RATE * 4) / RATE
    reference = np.sin(2 * np.pi * 7000.0 * t) + np.sin(2 * np.pi * 300.0 * t)
    matched, _ = match_speed(reference, RATE, 30.0, 15.0)
    frequencies, power = signal.welch(matched, RATE, nperseg=8192)
    strongest = sorted(frequencies[np.argsort(power)[-2:]])
    assert abs(strongest[0] - 150.0) < 2.5 and abs(strongest[1] - 3500.0) < 2.5


def test_order_figure_is_a_metadata_free_png():
    payload = order_figure(np.random.default_rng(0).standard_normal(RATE * 2), RATE, 25.0, 4096)
    assert payload.startswith(b"\x89PNG")


def test_speed_context_adds_cited_order_figures_and_guidance():
    from modelmetis.speed_context import SPEED_GUIDANCE, add_speed_context
    from modelmetis.visual_audio import canonical_json

    messages = [{"role": "system", "content": "Compare."}, {"role": "user", "content": []}]
    reports = {"R01": {"evidence_ids": []}, "Q01": {"evidence_ids": []}}
    noise = np.random.default_rng(1).standard_normal(RATE * 3)
    add_speed_context(messages, reports, {"R01": 20.0, "Q01": 22.0},
                      {"R01": noise, "Q01": noise}, RATE, canonical_json)
    assert messages[0]["content"].endswith(SPEED_GUIDANCE)
    assert reports["Q01"]["evidence_ids"] == ["Q01.O001"]
    images = [part for part in messages[1]["content"] if part["type"] == "image_url"]
    assert len(images) == 2 and '"shaft_hz":22.0' in messages[1]["content"][0]["text"]
