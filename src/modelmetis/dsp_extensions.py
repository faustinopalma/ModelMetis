from dataclasses import asdict, dataclass

import numpy as np
import pywt
from scipy import signal
from scipy.integrate import cumulative_trapezoid

from modelmetis.dsp import fft_spectrum
from modelmetis.dsp_guide import VIEW_GUIDE


@dataclass(frozen=True)
class ExtensionConfig:
    frame_seconds: float = 0.1
    envelope_bands_hz: tuple = ((100, 500), (500, 1500), (1500, 4000),
                               (4000, 8000), (8000, 16000))
    modulation_max_hz: float = 500.0
    edge_seconds: float = 0.1
    cepstrum_max_seconds: float = 0.1
    relative_floor_db: float = -80.0
    multitaper_nw: float = 3.0
    multitaper_count: int = 5
    map_frequency_bins: int = 256
    map_time_bins: int = 200
    wavelet_frequencies: int = 48
    cyclic_max_hz: float = 300.0
    max_seconds: float = 30.0

    def validate(self, rate):
        if (type(rate) is not int or not 8000 <= rate <= 192000
                or not 0.02 <= self.frame_seconds <= 1
                or not 0 < self.modulation_max_hz <= rate / 2
                or not 0 < self.edge_seconds <= 1
                or not 0 < self.cepstrum_max_seconds <= 1
                or not -160 <= self.relative_floor_db < 0
                or not 1 <= self.multitaper_nw <= 8
                or type(self.multitaper_count) is not int
                or not 1 <= self.multitaper_count <= 2 * self.multitaper_nw
                or not 0 < self.cyclic_max_hz <= 1000
                or not 0 < self.max_seconds <= 30):
            raise ValueError("Invalid extension configuration.")
        for dimension in (self.map_frequency_bins, self.map_time_bins,
                          self.wavelet_frequencies):
            if type(dimension) is not int or not 16 <= dimension <= 512:
                raise ValueError("Invalid map dimension.")
        if not self.envelope_bands_hz or any(
            len(band) != 2 or not np.isfinite(band).all() or not 0 < band[0] < band[1]
            for band in self.envelope_bands_hz
        ):
            raise ValueError("Invalid envelope bands.")


def unavailable(reason):
    return {"status": "unavailable", "reason": reason}


def log_power(power, floor_db=-80):
    maximum = float(np.max(power))
    return 10 * np.log10(np.maximum(power, max(
        maximum * 10 ** (floor_db / 10), np.finfo(float).tiny)))


def curve(title, x, series, x_label, y_label, **metrics):
    return {"status": "available", "title": title, "kind": "line", "x": np.asarray(x),
            "series": {name: np.asarray(values) for name, values in series.items()},
            "x_label": x_label, "y_label": y_label, "metrics": metrics}


def map_view(title, x, y, values, x_label, y_label, value_label, **metrics):
    return {"status": "available", "title": title, "kind": "map", "x": np.asarray(x),
            "y": np.asarray(y), "values": np.asarray(values), "x_label": x_label,
            "y_label": y_label, "value_label": value_label, "metrics": metrics}


def reduce_map(values, max_rows, max_columns, reducer=np.mean):
    rows = np.array_split(np.arange(values.shape[0]), min(max_rows, values.shape[0]))
    columns = np.array_split(np.arange(values.shape[1]), min(max_columns, values.shape[1]))
    reduced = np.stack([reducer(values[index], axis=0) for index in rows])
    reduced = np.stack([reducer(reduced[:, index], axis=1) for index in columns], axis=1)
    return reduced, rows, columns


def spectral_matrix(samples, rate, seconds):
    frame = round(rate * seconds)
    if len(samples) < frame:
        return None
    frequencies, times, spectrum = signal.spectrogram(
        samples, rate, window="hann", nperseg=frame, noverlap=frame - frame // 4,
        detrend=False, scaling="density", mode="complex",
    )
    power = np.abs(spectrum) ** 2
    power[1:-1 if frame % 2 == 0 else None] *= 2
    return frequencies, times, power, spectrum


def envelope_views(samples, rate, config):
    trim = round(config.edge_seconds * rate)
    views, modulation_rows, available_bands = {}, [], []
    for index, (lower, upper) in enumerate(config.envelope_bands_hz):
        key = f"envelope_{index + 1}"
        if upper >= rate / 2:
            views[key] = unavailable("Declared carrier band reaches or exceeds Nyquist.")
            continue
        if len(samples) - 2 * trim < 32:
            views[key] = unavailable("Insufficient samples after filter/Hilbert edge exclusion.")
            continue
        sections = signal.butter(4, (lower, upper), fs=rate, btype="bandpass", output="sos")
        filtered = signal.sosfiltfilt(sections, samples)
        envelope = np.abs(signal.hilbert(filtered))[trim:len(samples) - trim]
        mean = float(envelope.mean())
        if mean < 1e-10:
            views[key] = unavailable("Carrier band has insufficient energy.")
            continue
        frequencies, amplitude, parameters = fft_spectrum(envelope - mean, rate)
        _, squared, _ = fft_spectrum(envelope ** 2 - np.mean(envelope ** 2), rate)
        selected = frequencies <= min(config.modulation_max_hz, (upper - lower) / 2)
        frequencies, amplitude, squared = (values[selected] for values in (
            frequencies, amplitude, squared))
        normalized = amplitude / mean
        views[key] = curve(
            f"Envelope / {lower:g}-{upper:g} Hz", frequencies,
            {"envelope / mean": normalized,
             "squared envelope / mean square": squared / np.mean(envelope ** 2)},
            "Modulation frequency (Hz)", "Relative amplitude",
            carrier_band_hz=[lower, upper], mean_envelope_fs=mean,
            excluded_edge_samples_each=trim, valid_samples=len(envelope),
            bin_spacing_hz=parameters["bin_spacing_hz"],
            strongest_modulation_hz=float(frequencies[np.argmax(normalized)]),
        )
        grid = np.linspace(0, config.modulation_max_hz, 251)
        modulation_rows.append(np.interp(grid, frequencies, normalized, right=np.nan))
        available_bands.append([lower, upper])
    views["modulation_map"] = map_view(
        "Carrier-band modulation", grid, np.arange(len(available_bands)),
        np.stack(modulation_rows), "Modulation frequency (Hz)", "Available carrier band index",
        "Envelope amplitude / mean", carrier_bands_hz=available_bands,
        unsupported_modulation_cells="masked; inspect per-band valid range",
    ) if modulation_rows else unavailable("No carrier band has usable envelope evidence.")
    return views


def cepstrum_view(samples, rate, config):
    windowed = samples * signal.windows.hann(len(samples), sym=False)
    magnitude = np.abs(np.fft.rfft(windowed))
    log_magnitude = np.log(np.maximum(magnitude, max(
        magnitude.max() * 10 ** (config.relative_floor_db / 20), np.finfo(float).tiny)))
    cepstrum = np.fft.irfft(log_magnitude, n=len(samples))
    count = min(len(samples) // 2, round(config.cepstrum_max_seconds * rate))
    return curve("Real cepstrum", np.arange(1, count) / rate, {"cepstrum": cepstrum[1:count]},
                 "Quefrency (s)", "Real cepstral coefficient",
                 zero_quefrency_excluded=True, log_magnitude_floor_db=config.relative_floor_db)


def persistence_view(frequencies, power, config):
    reduced, groups, _ = reduce_map(power, config.map_frequency_bins, power.shape[1])
    decibels = log_power(reduced, config.relative_floor_db)
    bins = np.linspace(float(decibels.min()), float(decibels.max()) + 1e-9, 65)
    counts = np.stack([np.histogram(row, bins)[0] for row in decibels], axis=1)
    return map_view("Spectral persistence", [frequencies[group].mean() for group in groups],
                    (bins[1:] + bins[:-1]) / 2, 100 * counts / power.shape[1],
                    "Frequency (Hz)", "PSD (dB re 1 FS squared/Hz)", "Frames (%)",
                    frames=power.shape[1], frequency_pooling="mean PSD before log",
                    chronological_order_retained=False)


def multitaper_view(samples, rate, config):
    frame = round(config.frame_seconds * rate)
    if len(samples) < frame:
        return unavailable("Insufficient data for declared multitaper frame.")
    tapers, eigenvalues = signal.windows.dpss(
        frame, config.multitaper_nw, Kmax=config.multitaper_count, return_ratios=True,
    )
    estimates = []
    for taper in tapers:
        frequencies, power = signal.welch(
            samples, rate, window=taper, nperseg=frame, noverlap=frame // 2,
            detrend=False, scaling="density",
        )
        estimates.append(power)
    average = np.average(estimates, axis=0, weights=eigenvalues)
    _, welch_mean = signal.welch(samples, rate, nperseg=frame, noverlap=frame // 2,
                                 detrend=False, window="hann", average="mean")
    _, welch_median = signal.welch(samples, rate, nperseg=frame, noverlap=frame // 2,
                                   detrend=False, window="hann", average="median")
    return curve("PSD estimators", frequencies,
                 {"DPSS multitaper": log_power(average), "Welch mean": log_power(welch_mean),
                  "Welch median": log_power(welch_median)},
                 "Frequency (Hz)", "PSD (dB re 1 FS squared/Hz)",
                 integrated_multitaper_power=float(average.sum() * rate / frame),
                 smoothing_bandwidth_hz=2 * config.multitaper_nw / config.frame_seconds,
                 tapers=config.multitaper_count, taper_eigenvalues=eigenvalues.tolist())


def harmonic_view(samples, rate, config):
    frequencies, amplitude, parameters = fft_spectrum(samples, rate)
    decibels = 20 * np.log10(np.maximum(amplitude, amplitude.max() * 1e-4))
    positions, _ = signal.find_peaks(decibels, prominence=8)
    positions = positions[frequencies[positions] >= 20]
    positions = sorted(positions, key=lambda position: -amplitude[position])[:24]
    peaks = sorted(float(frequencies[position]) for position in positions)
    candidates = []
    tolerance = max(2 * parameters["bin_spacing_hz"], 1.0)
    for fundamental in peaks:
        multiples = [peak for peak in peaks if peak >= fundamental and abs(
            peak - round(peak / fundamental) * fundamental) <= tolerance]
        if len(multiples) >= 3:
            candidates.append({"spacing_hz": fundamental, "matched_peaks_hz": multiples})
    spacings = sorted(abs(first - second) for index, first in enumerate(peaks)
                      for second in peaks[index + 1:] if abs(first - second) <= 1000)
    bands = np.arange(0, 1002, 2)
    counts, _ = np.histogram(spacings, bands)
    return curve("Peak-spacing evidence", (bands[1:] + bands[:-1]) / 2,
                 {"peak-pair count": counts}, "Peak spacing (Hz)", "Peak pairs",
                 peaks_hz=peaks, harmonic_candidates=candidates,
                 tolerance_hz=tolerance, peak_count_limit=24,
                 interpretation="Candidate spacings; missing fundamentals and sidebands ambiguous.")


def kurtosis_views(samples, rate, spectral, config):
    frequencies, _, power, _ = spectral
    average = power.mean(axis=1)
    valid = average > average.max() * 10 ** (config.relative_floor_db / 10)
    valid[[0, -1]] = False
    kurtosis = np.zeros_like(average)
    kurtosis[valid] = np.mean(power[valid] ** 2, axis=1) / average[valid] ** 2 - 2
    rows, band_metrics = [], []
    trim = round(config.edge_seconds * rate)
    grid = np.linspace(0, rate / 2, config.map_frequency_bins)
    for level in (1, 2, 3, 4):
        row = np.full(len(grid), np.nan)
        edges = np.linspace(20, 0.95 * rate / 2, 2 ** level + 1)
        for lower, upper in zip(edges[:-1], edges[1:], strict=True):
            if len(samples) - 2 * trim < 32:
                continue
            sections = signal.butter(4, (lower, upper), btype="bandpass", fs=rate, output="sos")
            analytic = signal.hilbert(signal.sosfiltfilt(sections, samples))[
                trim:len(samples) - trim]
            squared = np.abs(analytic) ** 2
            if squared.mean() < 1e-20:
                continue
            value = float(np.mean(squared ** 2) / np.mean(squared) ** 2 - 2)
            row[(grid >= lower) & (grid < upper)] = value
            band_metrics.append({"level": level, "band_hz": [float(lower), float(upper)],
                                 "complex_excess_kurtosis": value})
        rows.append(row)
    return {
        "spectral_kurtosis": curve(
            "STFT spectral kurtosis", frequencies[valid], {"kurtosis": kurtosis[valid]},
            "Frequency (Hz)", "E[P squared] / E[P] squared - 2",
            frames=power.shape[1], gaussian_reference=0, finite_sample_bias_corrected=False,
            low_energy_bins_excluded=int((~valid).sum()),
        ) if np.any(valid) and power.shape[1] >= 8 else unavailable("Too few active frames/bins."),
        "kurtosis_bank": map_view(
            "Filter-bank impulsiveness", grid, [1, 2, 3, 4], np.stack(rows),
            "Carrier frequency (Hz)", "Dyadic bank level", "Complex excess kurtosis",
            bands=band_metrics, algorithm="Butterworth band bank; not the Fast Kurtogram",
            gaussian_reference=0, selection="All declared bands retained; no label-based tuning",
        ) if band_metrics else unavailable("Insufficient samples for filtered-band moments."),
    }


def cyclic_view(spectral, rate, config):
    frequencies, times, _, spectrum = spectral
    if len(times) < 16:
        return unavailable("Cyclic estimates require at least sixteen STFT frames.")
    spacing = frequencies[1] - frequencies[0]
    max_shift = min(len(frequencies) - 2, int(config.cyclic_max_hz / spacing))
    if max_shift < 1:
        return unavailable("Cyclic frequency range is narrower than the configured grid.")
    cyclic_frequencies, rows = [], []
    energy = np.mean(np.abs(spectrum) ** 2, axis=1)
    for shift in range(1, max_shift + 1):
        cyclic = shift * spacing
        product = spectrum[shift:] * spectrum[:-shift].conj()
        correlation = np.mean(product * np.exp(-2j * np.pi * cyclic * times), axis=1)
        denominator = energy[shift:] * energy[:-shift]
        valid = ((energy[shift:] > energy.max() * 1e-8)
                 & (energy[:-shift] > energy.max() * 1e-8))
        coherence = np.full(len(frequencies), np.nan)
        coherence[shift // 2:shift // 2 + len(product)][valid] = np.minimum(
            1.0, np.abs(correlation[valid]) ** 2 / denominator[valid])
        rows.append(coherence)
        cyclic_frequencies.append(cyclic)
    return map_view(
        "Cyclic spectral coherence", frequencies, cyclic_frequencies, np.stack(rows),
        "Carrier frequency (Hz)", "Cyclic frequency (Hz)", "Squared coherence (0-1)",
        frames=len(times), cyclic_grid_hz=spacing, carrier_quantization_hz=spacing / 2,
        estimator="STFT bin-pair average with cyclic phase correction; not Fast-SC",
        limitation="Deterministic tones also correlate; no fault specificity or significance test.",
    )


def time_frequency_views(samples, rate, spectral, config):
    frequencies, times, power, _ = spectral
    reduced, rows, columns = reduce_map(power, config.map_frequency_bins, config.map_time_bins)
    frequency_axis = np.array([frequencies[group].mean() for group in rows])
    time_axis = np.array([times[group].mean() for group in columns])
    views = {"stft_detail": map_view(
        "Physical-resolution STFT", time_axis, frequency_axis, log_power(reduced),
        "Time (s)", "Frequency (Hz)", "PSD (dB re 1 FS squared/Hz)",
        frame_seconds=config.frame_seconds, bin_spacing_hz=1 / config.frame_seconds,
        display_pooling="mean linear PSD; all frames contribute",
    )}
    selected = frequencies >= 20
    ridge = frequencies[selected][np.argmax(power[selected], axis=0)]
    views["ridge"] = curve("Dominant spectral ridge", times, {"dominant bin": ridge},
                           "Time (s)", "Frequency (Hz)",
                           limitation="Per-frame maximum; no RPM or continuity constraint.")
    frame = round(config.frame_seconds * rate)
    starts = np.arange(0, len(samples) - frame + 1, frame // 4)
    blocks = np.lib.stride_tricks.sliding_window_view(samples, frame)[::frame // 4]
    window = signal.windows.hann(frame, sym=False)
    coordinate = np.arange(frame)
    derivative = np.pi * rate / frame * np.sin(2 * np.pi * coordinate / frame)
    transformed = np.fft.rfft(blocks * window, axis=1)
    derivative_fft = np.fft.rfft(blocks * derivative, axis=1)
    timed_fft = np.fft.rfft(blocks * window * ((coordinate - frame / 2) / rate), axis=1)
    valid = np.abs(transformed) ** 2 > np.max(np.abs(transformed) ** 2) * 1e-8
    ratio_derivative = np.divide(derivative_fft, transformed, out=np.zeros_like(transformed),
                                 where=valid)
    ratio_time = np.divide(timed_fft, transformed, out=np.zeros_like(transformed), where=valid)
    reassigned_frequency = frequencies[None, :] - ratio_derivative.imag / (2 * np.pi)
    reassigned_time = (starts[:, None] + frame / 2) / rate + ratio_time.real
    valid &= (reassigned_frequency >= 0) & (reassigned_frequency <= rate / 2)
    valid &= (reassigned_time >= 0) & (reassigned_time <= len(samples) / rate)
    weights = np.abs(transformed) ** 2
    weights[:, 1:-1 if frame % 2 == 0 else None] *= 2
    weights /= rate * np.sum(window ** 2)
    histogram, frequency_edges, time_edges = np.histogram2d(
        reassigned_frequency[valid], reassigned_time[valid],
        bins=(config.map_frequency_bins, config.map_time_bins),
        range=((0, rate / 2), (0, len(samples) / rate)), weights=weights[valid],
    )
    views["reassigned"] = map_view(
        "Reassigned STFT energy", (time_edges[1:] + time_edges[:-1]) / 2,
        (frequency_edges[1:] + frequency_edges[:-1]) / 2, log_power(histogram),
        "Time (s)", "Frequency (Hz)", "Pooled spectral weight (dB; not PSD)",
        retained_weight_fraction=float(weights[valid].sum() / weights.sum()),
        threshold_relative_power=1e-8, window="periodic Hann with analytic derivative",
    )
    return views


def wavelet_view(samples, rate, config):
    divisor = max(1, int(np.ceil(rate / 16000)))
    working = signal.resample_poly(samples, 1, divisor) if divisor > 1 else samples
    working_rate = rate / divisor
    frequencies = np.geomspace(40, 0.3 * working_rate, config.wavelet_frequencies)
    scales = pywt.frequency2scale("cmor1.5-1.0", frequencies / working_rate)
    coefficients, actual_frequencies = pywt.cwt(
        working, scales, "cmor1.5-1.0", sampling_period=1 / working_rate, method="fft",
    )
    power = np.abs(coefficients) ** 2 / working_rate
    for index, scale in enumerate(scales):
        edge = min(len(working) // 2, int(np.ceil(8 * scale)))
        power[index, :edge] = np.nan
        power[index, len(working) - edge:] = np.nan
    reduced, _, columns = reduce_map(np.nan_to_num(power), len(frequencies), config.map_time_bins)
    coverage, _, _ = reduce_map(np.isfinite(power).astype(float), len(frequencies),
                                config.map_time_bins)
    values = log_power(reduced)
    values[coverage < 1] = np.nan
    return map_view(
        "Morlet wavelet scalogram", [np.mean(group) / working_rate for group in columns],
        actual_frequencies, values, "Time (s)", "Frequency (Hz)",
        "Coefficient power (dB; physical-time scaling, not PSD)",
        wavelet="cmor1.5-1.0", analysis_sample_rate=working_rate, resample_divisor=divisor,
        edge_mask="Full +/-8 scale support excluded; pooled cells require full coverage",
        frequency_max_hz=float(actual_frequencies.max()),
    )


def order_views(samples, rate, rpm):
    if rpm is None:
        return {key: unavailable("Independent RPM trace was not supplied.")
                for key in ("orders", "synchronous")}
    speed = np.asarray(rpm, dtype=float)
    if speed.shape != samples.shape or not np.isfinite(speed).all() or np.any(speed <= 0):
        raise ValueError("RPM requires one finite positive value per native sample.")
    cycles = cumulative_trapezoid(speed / 60, dx=1 / rate, initial=0)
    rotations = int(cycles[-1])
    if rotations < 3:
        return {key: unavailable("At least three complete rotations are required.")
                for key in ("orders", "synchronous")}
    per_rotation = min(2048, int(rate / (speed.max() / 60)))
    if per_rotation < 32:
        return {key: unavailable("Insufficient samples per rotation.")
                for key in ("orders", "synchronous")}
    cutoff = min(0.45 * rate, 0.4 * per_rotation * speed.min() / 60)
    filtered = signal.sosfiltfilt(signal.butter(6, cutoff, fs=rate, output="sos"), samples)
    angles = np.arange(rotations * per_rotation) / per_rotation
    angular = np.interp(angles, cycles, filtered)
    orders, power = signal.welch(angular, fs=per_rotation, nperseg=per_rotation * 2,
                                  noverlap=per_rotation, detrend=False)
    rotation_blocks = angular.reshape(rotations, per_rotation)
    return {
        "orders": curve("Order spectrum", orders, {"power": log_power(power)},
                        "Order (cycles per rotation)", "Angular PSD (dB)",
                        rpm_min=float(speed.min()), rpm_max=float(speed.max()),
                        rotations=rotations, samples_per_rotation=per_rotation,
                        anti_alias_lowpass_hz=cutoff, angular_interpolation="linear"),
        "synchronous": curve(
            "Time-synchronous average", np.arange(per_rotation) / per_rotation,
            {"rotation mean": rotation_blocks.mean(axis=0)}, "Rotation phase (cycles)",
            "Amplitude (FS)", rotations=rotations,
            limitation="Asynchronous impacts can be attenuated; not a general bearing filter.",
        ),
    }


def analyze_extensions(samples, rate, config=None, rpm=None):
    config = config or ExtensionConfig()
    config.validate(rate)
    samples = np.asarray(samples, dtype=np.float64)
    if (samples.ndim != 1 or not len(samples) or not np.isfinite(samples).all()
            or len(samples) > rate * config.max_seconds):
        raise ValueError("Expected finite mono input within the explicit duration limit.")
    centered = samples - samples.mean()
    if np.sqrt(np.mean(centered ** 2)) < 1e-10:
        return {"config": asdict(config), "sample_rate": rate, "sample_count": len(samples),
            "views": {key: unavailable("Low AC energy.") for key in list(VIEW_GUIDE)[7:]}}
    views = envelope_views(centered, rate, config)
    views["cepstrum"] = cepstrum_view(centered, rate, config)
    views["estimators"] = multitaper_view(centered, rate, config)
    spectral = spectral_matrix(centered, rate, config.frame_seconds)
    views["persistence"] = persistence_view(spectral[0], spectral[2], config) if spectral else (
        unavailable("Insufficient samples for persistence frame."))
    views["harmonics"] = harmonic_view(centered, rate, config)
    if spectral:
        views.update(kurtosis_views(centered, rate, spectral, config))
        views["cyclic"] = cyclic_view(spectral, rate, config)
        views.update(time_frequency_views(centered, rate, spectral, config))
    else:
        views.update({key: unavailable("Insufficient samples for declared STFT frame.")
                      for key in ("spectral_kurtosis", "kurtosis_bank", "cyclic",
                                  "stft_detail", "ridge", "reassigned")})
    views["wavelet"] = wavelet_view(centered, rate, config)
    views.update(order_views(centered, rate, rpm))
    return {"config": asdict(config), "sample_rate": rate, "sample_count": len(samples),
            "views": views}