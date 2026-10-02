from dataclasses import asdict, dataclass

import numpy as np
from scipy import signal
from scipy.integrate import cumulative_trapezoid


@dataclass(frozen=True)
class OrderConfig:
    samples_per_cycle: int = 512
    cycles_per_frame: int = 8
    max_order: float = 20.0
    edge_seconds: float = 0.05


def order_analysis(samples, sample_rate, base_hz, config=None):
    config = config or OrderConfig()
    samples = np.asarray(samples, dtype=float)
    base_hz = np.asarray(base_hz, dtype=float)
    if base_hz.ndim == 0:
        base_hz = np.full(samples.shape, float(base_hz))
    if (samples.ndim != 1 or len(samples) < 64 or base_hz.shape != samples.shape
            or not np.isfinite(samples).all() or not np.isfinite(base_hz).all()
            or np.any(base_hz <= 0) or not np.isfinite(sample_rate) or sample_rate <= 0):
        raise ValueError("Expected finite mono audio and positive frequency at every sample.")
    if (type(config.samples_per_cycle) is not int or config.samples_per_cycle < 32
            or config.samples_per_cycle > 4096 or type(config.cycles_per_frame) is not int
            or not 2 <= config.cycles_per_frame <= 64
            or not np.isfinite([config.max_order, config.edge_seconds]).all()
            or config.max_order <= 0 or config.edge_seconds < 0):
        raise ValueError("Invalid angular sampling configuration.")
    per_cycle = config.samples_per_cycle
    cutoff = min(0.45 * sample_rate, 0.4 * per_cycle * float(base_hz.min()))
    usable_order = 0.8 * cutoff / float(base_hz.max())
    if config.max_order > usable_order:
        raise ValueError(f"Requested order exceeds reliable bandwidth ({usable_order:.3f}).")
    clock = np.arange(len(samples)) / sample_rate
    cycles = cumulative_trapezoid(base_hz, dx=1 / sample_rate, initial=0)
    trim = max(1, round(config.edge_seconds * sample_rate))
    if 2 * trim >= len(samples):
        raise ValueError("Audio is too short after filter-edge exclusion.")
    first_cycle = int(np.ceil(cycles[trim]))
    last_cycle = int(np.floor(cycles[-trim - 1]))
    count = last_cycle - first_cycle
    if count < 4:
        raise ValueError("At least four complete interior cycles are required.")
    if count * per_cycle > 16_000_000:
        raise ValueError("Angular sample limit exceeded; shorten the selected interval.")
    centered = samples - samples.mean()
    sections = signal.butter(8, cutoff, fs=sample_rate, output="sos")
    filtered = signal.sosfiltfilt(sections, centered)
    positions = first_cycle + np.arange(count * per_cycle) / per_cycle
    angular = np.interp(positions, cycles, filtered)
    angular_times = np.interp(positions, cycles, clock)
    frame = min(config.cycles_per_frame, count) * per_cycle
    if config.max_order < per_cycle / frame:
        raise ValueError("Maximum order must span at least one spectral bin.")
    orders, power = signal.welch(angular, fs=per_cycle, nperseg=frame,
                                 noverlap=frame // 2, detrend="constant")
    map_orders, map_cycles, order_map = signal.spectrogram(
        angular, fs=per_cycle, window="hann", nperseg=frame,
        noverlap=frame // 2, detrend="constant", scaling="density")
    map_times = np.interp(first_cycle + map_cycles, cycles, clock)
    selected = orders <= config.max_order
    map_selected = map_orders <= config.max_order
    envelope = np.abs(signal.hilbert(angular))
    _, envelope_power = signal.welch(envelope, fs=per_cycle, nperseg=frame,
                                     noverlap=frame // 2, detrend="constant")
    blocks = angular.reshape(count, per_cycle)
    autocorrelation = signal.correlate(angular, angular, mode="full", method="fft")
    autocorrelation = autocorrelation[len(angular) - 1:len(angular) + 2 * per_cycle]
    if autocorrelation[0] > 0:
        autocorrelation = autocorrelation / autocorrelation[0]
    window = signal.windows.hann(len(angular), sym=False)
    fft_amplitude = np.abs(np.fft.rfft(angular * window)) / window.sum()
    fft_amplitude[1:] *= 2
    if len(angular) % 2 == 0:
        fft_amplitude[-1] /= 2
    fft_orders = np.fft.rfftfreq(len(angular), 1 / per_cycle)
    fft_selected = fft_orders <= config.max_order
    peaks, _ = signal.find_peaks(power[selected])
    peaks = sorted(peaks, key=lambda index: -power[selected][index])[:10]
    metadata = {
        "config": asdict(config), "complete_cycles": count,
        "first_cycle": first_cycle, "phase_origin": "arbitrary recording origin",
        "base_hz_min": float(base_hz.min()), "base_hz_max": float(base_hz.max()),
        "base_hz_median": float(np.median(base_hz)),
        "anti_alias_lowpass_hz": cutoff, "reliable_max_order": usable_order,
        "filter": "eighth-order Butterworth, forward-backward, before linear resampling",
        "order_bin_spacing": float(orders[1] - orders[0]),
        "density_unit": "FS^2 per order", "amplitude_normalization": "none",
        "cycle_weighting": "equal angle; faster intervals contribute more cycles",
        "angular_mean_square": float(np.mean(angular ** 2)),
        "integrated_full_order_psd": float(np.sum(power) * (orders[1] - orders[0])),
        "peak_orders": [float(orders[selected][index]) for index in peaks],
    }
    arrays = {
        "angular_samples": angular, "angular_times_seconds": angular_times,
        "orders": orders[selected], "order_psd": power[selected],
        "fft_orders": fft_orders[fft_selected], "fft_amplitude": fft_amplitude[fft_selected],
        "map_orders": map_orders[map_selected], "map_times_seconds": map_times,
        "order_map_psd": order_map[map_selected], "envelope_order_psd": envelope_power[selected],
        "cycle_phase": np.arange(per_cycle) / per_cycle,
        "synchronous_mean": blocks.mean(axis=0), "synchronous_std": blocks.std(axis=0),
        "autocorrelation_lag_cycles": np.arange(len(autocorrelation)) / per_cycle,
        "autocorrelation": autocorrelation,
    }
    return metadata, arrays