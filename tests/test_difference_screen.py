import numpy as np

from scripts import difference_screen as screen

RATE = 16000


def machine(shaft_hz, fault_order=None, tilt_db=0.0, seed=0):
    rng = np.random.default_rng(seed)
    t = np.arange(RATE * 4) / RATE
    x = 0.02 * rng.standard_normal(t.size)
    for harmonic in range(1, 8):
        x += 0.3 / harmonic * np.sin(2 * np.pi * harmonic * shaft_hz * t)
    if fault_order is not None:
        for multiple in range(1, 6):
            x += 0.2 * np.sin(2 * np.pi * multiple * fault_order * shaft_hz * t)
    if tilt_db:
        spectrum = np.fft.rfft(x)
        frequencies = np.fft.rfftfreq(x.size, 1 / RATE)
        spectrum *= 10 ** (tilt_db * np.log2(np.maximum(frequencies, 20) / 20) / 20)
        x = np.fft.irfft(spectrum, x.size)
    return x


def item(shaft_hz, fault_order=None, tilt_db=0.0):
    return screen.features(machine(shaft_hz, fault_order, tilt_db), RATE, shaft_hz)


def bank(shaft_hz, tilt_db=0.0):
    normal = item(shaft_hz, None, tilt_db)
    references = {"normal": [{**screen.vectors(normal, None), **screen.zero_delta(normal)}]}
    for label, order in (("a", 3.3), ("b", 5.7)):
        references[label] = [screen.vectors(item(shaft_hz, order, tilt_db), normal)]
    return references


def test_identical_vectors_have_zero_distance_and_shift_is_recovered():
    values = np.sin(np.linspace(0, 20, screen.LOG_GRID.size))
    assert screen.rms(values, values) == 0
    shifted = np.roll(values, 12)
    shifted[:12] = np.nan
    assert screen.shifted_rms(shifted, values) < 1e-9


def test_order_axis_recognizes_classes_after_a_speed_change():
    references = bank(25.0)
    query_item = item(40.0, 5.7)
    query = screen.vectors(query_item, item(40.0))
    assert screen.decide(query, references, "order")[0][0] == "b"
    assert screen.decide(query, references, "delta_order")[0][0] == "b"


def test_difference_cancels_a_filter_shared_by_sample_and_normal():
    references = bank(25.0)
    query_item = item(25.0, 3.3, tilt_db=-6.0)
    query = screen.vectors(query_item, item(25.0, None, tilt_db=-6.0))
    raw_scores = screen.decide(query, references, "raw")[1]
    delta_ranked, delta_scores = screen.decide(query, references, "delta")
    assert delta_ranked[0] == "a"
    assert delta_scores["a"] < raw_scores["a"]
