import hashlib
import io
import math
from dataclasses import asdict, dataclass
from pathlib import Path

import numpy as np
import soundfile as sf
from scipy import signal, stats

from modelmetis.visual_audio import RenderConfig, decode_audio, pcm_sha256


@dataclass(frozen=True)
class DspConfig:
    schema: int = 1
    segment_seconds: float = 5.0
    spectral_frame_samples: int = 1024
    spectral_hop_samples: int = 256
    level_frame_seconds: float = 0.02
    level_change_db: float = 6.0
    amplitude_db_min: float = -120.0
    amplitude_db_max: float = 6.0
    psd_db_min: float = -130.0
    psd_db_max: float = 0.0
    peak_prominence_db: float = 8.0
    peak_count: int = 8
    fft_zoom_max_hz: float = 500.0
    envelope_band_hz: tuple[float, float] | None = None
    envelope_trim_seconds: float = 0.05
    envelope_max_hz: float = 500.0
    autocorrelation_max_seconds: float = 0.1
    max_file_bytes: int = 134217728
    max_decoded_samples: int = 40000000
    max_segments: int = 128
    max_plot_segments: int = 4
    max_channels: int = 8
    image_width: int = 1200
    image_height: int = 700
    image_dpi: int = 120

    def validate(self, sample_rate):
        numeric = [value for value in asdict(self).values() if isinstance(value, int | float)]
        integers = (self.schema, self.spectral_frame_samples, self.spectral_hop_samples,
                    self.peak_count, self.max_file_bytes, self.max_decoded_samples,
                    self.max_segments, self.max_plot_segments, self.max_channels, self.image_width,
                    self.image_height, self.image_dpi)
        if not all(np.isfinite(numeric)) or any(type(value) is not int for value in integers):
            raise ValueError("DSP parameters require finite values and integer dimensions.")
        if (self.schema != 1 or not 8000 <= sample_rate <= 192000
                or self.segment_seconds <= 0 or self.level_frame_seconds <= 0
                or self.level_change_db <= 0 or self.spectral_frame_samples < 32
                or not 0 < self.spectral_hop_samples <= self.spectral_frame_samples
                or self.amplitude_db_min >= self.amplitude_db_max
                or self.psd_db_min >= self.psd_db_max or self.peak_prominence_db <= 0
                or self.fft_zoom_max_hz <= 0
                or not 1 <= self.peak_count <= 32 or self.envelope_trim_seconds < 0
                or self.envelope_max_hz <= 0 or self.autocorrelation_max_seconds <= 0
                or min(self.max_file_bytes, self.max_decoded_samples, self.max_segments,
                      self.max_plot_segments, self.max_channels) <= 0
                or self.image_width < 800 or self.image_height < 500 or self.image_dpi < 72):
            raise ValueError("Unsupported DSP configuration.")
        for seconds in (self.segment_seconds, self.level_frame_seconds):
            if round(seconds * sample_rate) < 1:
                raise ValueError("Configured windows must contain at least one sample.")
        if self.envelope_band_hz is not None:
            if (len(self.envelope_band_hz) != 2 or not np.isfinite(self.envelope_band_hz).all()
                    or not 0 < self.envelope_band_hz[0]
                    < self.envelope_band_hz[1] < sample_rate / 2):
                raise ValueError("Envelope band must be strictly inside (0, Nyquist).")


def amplitude_db(value):
    return float(20 * np.log10(value)) if value > 0 else None


def power_db(value):
    return float(10 * np.log10(value)) if value > 0 else None


def decode_recording(path, config):
    path = Path(path)
    if path.stat().st_size > config.max_file_bytes:
        raise ValueError("Source exceeds the explicit byte limit; no truncation performed.")
    info = sf.info(path)
    config.validate(info.samplerate)
    if (info.frames == 0 or info.channels > config.max_channels
            or info.frames * info.channels > config.max_decoded_samples):
        raise ValueError("Empty recording or decoded sample/channel limit exceeded.")
    segment_slices(info.frames, info.samplerate, config)
    mono, audit = decode_audio(path, RenderConfig(
        sample_rate=info.samplerate, frequency_max=info.samplerate / 2, channel_policy="mean",
    ))
    if info.channels == 1:
        samples = mono[:, None]
    else:
        payload = path.read_bytes()
        if hashlib.sha256(payload).hexdigest() != audit["source_sha256"]:
            raise ValueError("Source changed during decoding.")
        try:
            samples, rate = sf.read(io.BytesIO(payload), dtype="float64", always_2d=True)
            if rate != info.samplerate:
                raise ValueError("Sample rate changed during decoding.")
        except sf.LibsndfileError:
            import av

            with av.open(io.BytesIO(payload)) as source:
                blocks = list(source.decode(audio=0))
            if not blocks or any(
                block.format.name != "s32" or block.sample_rate != info.samplerate
                or len(block.layout.channels) != info.channels for block in blocks
            ):
                raise ValueError("Unsupported multichannel fallback format.") from None
            samples = np.concatenate([block.to_ndarray().reshape(-1, info.channels)
                                      for block in blocks]).astype(np.float64) / 2 ** 31
        if (samples.shape != (info.frames, info.channels) or not np.isfinite(samples).all()
                or pcm_sha256(samples.mean(axis=1)) != audit["analysis_pcm_sha256"]):
            raise ValueError("Native channels differ from the verified decoder projection.")
    provenance = {
        **audit, "source_path": str(path.resolve()),
        "decoded_channels_pcm_sha256": pcm_sha256(samples),
        "decoder_validation_projection": audit["transformations"], "analysis_transformations": [],
        "analysis_channel_policy": "preserve_each_native_channel", "sample_rate_policy": "native",
    }
    provenance.pop("analysis_pcm_sha256")
    provenance.pop("transformations")
    return samples, info.samplerate, provenance


def plotted_segment_indices(segment_count, config):
    count = min(segment_count, config.max_plot_segments)
    return sorted(set(np.linspace(0, segment_count - 1, count, dtype=int).tolist()))


def fft_spectrum(samples, sample_rate):
    samples = np.asarray(samples, dtype=np.float64)
    if samples.ndim != 1 or len(samples) < 4 or not np.isfinite(samples).all():
        raise ValueError("FFT requires at least four finite mono samples.")
    window = signal.windows.hann(len(samples), sym=False)
    amplitude = np.abs(np.fft.rfft(samples * window)) / window.sum()
    amplitude[1:] *= 2
    if len(samples) % 2 == 0:
        amplitude[-1] /= 2
    return np.fft.rfftfreq(len(samples), 1 / sample_rate), amplitude, {
        "samples": len(samples), "bin_spacing_hz": sample_rate / len(samples),
        "equivalent_noise_bandwidth_hz": float(sample_rate * np.sum(window ** 2)
                                               / window.sum() ** 2),
        "window": "periodic_hann", "zero_padding": False,
        "scaling": "one_sided_peak_amplitude_coherent_gain_corrected",
        "limitation": "Peak amplitude is exact for bin-centered isolated tones; "
                      "leakage and scalloping affect off-bin or unresolved tones.",
    }


def spectral_peaks(frequencies, amplitude, config):
    decibels = 20 * np.log10(np.maximum(amplitude, 1e-15))
    positions, properties = signal.find_peaks(decibels, prominence=config.peak_prominence_db,
                                              distance=2)
    eligible = [(position, float(prominence)) for position, prominence in
                zip(positions, properties["prominences"], strict=True)
                if amplitude[position] > 10 ** (config.amplitude_db_min / 20)]
    strongest = sorted(eligible, key=lambda item: (-amplitude[item[0]], item[0]))[
        :config.peak_count
    ]
    return [{"frequency_hz": float(frequencies[position]),
             "amplitude_fs_peak": float(amplitude[position]),
             "amplitude_db_re_1_fs_peak": amplitude_db(amplitude[position]),
             "prominence_db": prominence} for position, prominence in strongest]


def level_series(samples, sample_rate, config, start_sample):
    frame_size = max(1, round(config.level_frame_seconds * sample_rate))
    starts = np.arange(0, len(samples), frame_size)
    counts = np.minimum(frame_size, len(samples) - starts)
    rms = np.sqrt(np.add.reduceat(samples ** 2, starts) / counts)
    peaks = np.maximum.reduceat(np.abs(samples), starts)
    minimum = np.minimum.reduceat(samples, starts)
    maximum = np.maximum.reduceat(samples, starts)
    db = 20 * np.log10(np.maximum(rms, 1e-15))
    change_positions = np.flatnonzero(np.abs(np.diff(db)) >= config.level_change_db) + 1
    changes = [{"time_seconds": float((start_sample + starts[position]) / sample_rate),
                "delta_db": float(db[position] - db[position - 1]),
                "kind": "level_change_candidate_not_regime_boundary"}
               for position in change_positions]
    return {
        "times": (start_sample + starts + counts / 2) / sample_rate,
        "rms": rms, "peak": peaks, "minimum": minimum, "maximum": maximum,
        "valid_samples": counts, "changes": changes,
    }


def envelope_analysis(centered, sample_rate, config):
    trim = round(config.envelope_trim_seconds * sample_rate)
    if len(centered) - 2 * trim < 32:
        return {"status": "unavailable", "reason": "Insufficient samples after edge exclusion."}, {}
    filtered = centered
    if config.envelope_band_hz is not None:
        sections = signal.butter(4, config.envelope_band_hz, btype="bandpass",
                                 fs=sample_rate, output="sos")
        try:
            filtered = signal.sosfiltfilt(sections, centered)
        except ValueError:
            return {"status": "unavailable", "reason": "Insufficient samples for bandpass."}, {}
    envelope = np.abs(signal.hilbert(filtered))
    end = len(envelope) - trim
    envelope = envelope[trim:end]
    frequencies, amplitude, parameters = fft_spectrum(envelope - envelope.mean(), sample_rate)
    selected = frequencies <= min(config.envelope_max_hz, sample_rate / 2)
    frequencies, amplitude = frequencies[selected], amplitude[selected]
    peaks = spectral_peaks(frequencies, amplitude, config)
    return {
        "status": "available", "band_hz": config.envelope_band_hz,
        "filter": "butterworth_order4_zero_phase_sos" if config.envelope_band_hz else None,
        "excluded_edge_samples_each": trim, "valid_samples": len(envelope),
        "mean_envelope_fs": float(envelope.mean()), "spectrum": parameters,
        "modulation_peaks": peaks,
        "limitation": "Broadband beating and filter/Hilbert edge effects can create modulation; "
                      "this is not a bearing diagnosis or a calibrated modulation index.",
    }, {"envelope_times": np.arange(trim, end) / sample_rate, "envelope": envelope,
        "envelope_frequencies": frequencies, "envelope_amplitude": amplitude}


def analyze_segment(samples, sample_rate, config, start_sample=0, positive_clip_threshold=1.0):
    config.validate(sample_rate)
    samples = np.asarray(samples, dtype=np.float64)
    if samples.ndim != 1 or len(samples) == 0 or not np.isfinite(samples).all():
        raise ValueError("Expected nonempty finite mono samples.")
    mean = float(samples.mean())
    centered = samples - mean
    rms = float(np.sqrt(np.mean(samples ** 2)))
    ac_rms = float(np.sqrt(np.mean(centered ** 2)))
    peak = float(np.abs(samples).max())
    levels = level_series(samples, sample_rate, config, start_sample)
    clipping = int(np.count_nonzero((samples <= -1) | (samples >= positive_clip_threshold)))
    metrics = {
        "start_sample": start_sample, "end_sample_exclusive": start_sample + len(samples),
        "start_seconds": start_sample / sample_rate,
        "end_seconds": (start_sample + len(samples)) / sample_rate,
        "valid_samples": len(samples), "padding_samples": 0,
        "duration_seconds": len(samples) / sample_rate,
        "dc_offset_fs": mean, "rms_fs": rms, "rms_db_re_1_fs": amplitude_db(rms),
        "ac_rms_fs": ac_rms, "peak_fs": peak, "peak_db_re_1_fs": amplitude_db(peak),
        "crest_factor_db": amplitude_db(peak / rms) if rms > 0 else None,
        "pearson_kurtosis_ac": float(stats.kurtosis(centered, fisher=False, bias=False))
        if len(samples) >= 4 and ac_rms > 1e-15 else None,
        "zero_crossings_per_second_ac": float(np.count_nonzero(
            np.diff(np.signbit(centered)),
        ) * sample_rate / (len(samples) - 1)) if len(samples) > 1 else None,
        "clipped_samples": clipping, "clipped_fraction": clipping / len(samples),
        "silent": peak == 0, "constant": ac_rms == 0,
        "level_changes": levels.pop("changes"), "regime": "unverified_may_be_mixed",
        "spectral_preprocessing": "subtract_segment_mean; no_gain_normalization_or_resampling",
    }
    arrays = {f"level_{key}": value for key, value in levels.items()}
    if len(samples) < 32:
        metrics.update(spectral_status="unavailable_fewer_than_32_samples",
                       envelope={"status": "unavailable", "reason": "Segment too short."})
        return metrics, arrays
    frequencies, amplitude, fft_parameters = fft_spectrum(centered, sample_rate)
    frame_size = min(config.spectral_frame_samples, len(samples))
    hop = min(config.spectral_hop_samples, frame_size)
    window = signal.windows.hann(frame_size, sym=False)
    welch_frequencies, psd = signal.welch(
        centered, fs=sample_rate, window=window, nperseg=frame_size, noverlap=frame_size - hop,
        nfft=frame_size, detrend=False, scaling="density", average="mean",
    )
    _, stft_times, stft_psd = signal.spectrogram(
        centered, fs=sample_rate, window=window, nperseg=frame_size, noverlap=frame_size - hop,
        nfft=frame_size, detrend=False, scaling="density", mode="psd",
    )
    spacing = sample_rate / frame_size
    total_power = float(psd.sum() * spacing)
    edges = sorted({0.0, sample_rate / 2, *(edge for edge in
                   (100, 500, 1000, 2000, 4000, 8000, 16000, 32000, 64000)
                   if edge < sample_rate / 2)})
    bands = []
    for index, (lower, upper) in enumerate(zip(edges[:-1], edges[1:], strict=True)):
        selected = (welch_frequencies >= lower) & (
            (welch_frequencies <= upper) if index == len(edges) - 2 else (welch_frequencies < upper)
        )
        power = float(psd[selected].sum() * spacing)
        bands.append({"low_hz": lower, "high_hz": upper, "bin_count": int(selected.sum()),
                      "power_fs_squared": power, "db_re_1_fs_squared": power_db(power),
                      "fraction_of_welch_power": power / total_power if total_power > 0 else None})
    centroid = float(np.sum(welch_frequencies * psd) / psd.sum()) if psd.sum() > 0 else None
    flatness = float(np.exp(np.mean(np.log(np.maximum(psd, 1e-30)))) / psd.mean()) \
        if psd.mean() > 0 else None
    correlation = signal.correlate(centered, centered, mode="full", method="fft")[len(centered)-1:]
    correlation = correlation[:min(len(samples), round(config.autocorrelation_max_seconds
                                                       * sample_rate) + 1)]
    correlation = correlation / correlation[0] if correlation[0] > 0 else np.zeros_like(correlation)
    lag_positions, _ = signal.find_peaks(correlation)
    lag_positions = lag_positions[correlation[lag_positions] > 0]
    strongest = int(lag_positions[np.argmax(correlation[lag_positions])]) \
        if lag_positions.size else None
    envelope, envelope_arrays = envelope_analysis(centered, sample_rate, config)
    metrics.update(
        spectral_status="available", fft=fft_parameters,
        peaks=spectral_peaks(frequencies, amplitude, config),
        welch={"frame_samples": frame_size, "hop_samples": hop, "window": "periodic_hann",
               "bin_spacing_hz": spacing, "equivalent_noise_bandwidth_hz": 1.5 * spacing,
               "frame_count": stft_psd.shape[1], "overlapping_frames_are_not_independent": True,
               "integrated_power_fs_squared": total_power,
               "spectral_centroid_hz": centroid, "spectral_flatness": flatness,
               "covered_samples": (stft_psd.shape[1] - 1) * hop + frame_size,
               "tail_samples_not_in_complete_frame": len(samples)
               - ((stft_psd.shape[1] - 1) * hop + frame_size)},
        bands=bands, envelope=envelope,
        autocorrelation={"normalization": "biased_lag_zero_energy",
                         "strongest_positive_peak_lag_seconds": strongest / sample_rate
                         if strongest is not None else None,
                         "coefficient": float(correlation[strongest])
                         if strongest is not None else None,
                         "limitation": "A repeated waveform interval does not identify shaft RPM."},
    )
    arrays.update(fft_frequencies=frequencies, fft_amplitude=amplitude,
                  welch_frequencies=welch_frequencies, welch_psd=psd,
                  stft_times=stft_times + start_sample / sample_rate, stft_psd=stft_psd,
                  autocorrelation_lags=np.arange(len(correlation)) / sample_rate,
                  autocorrelation=correlation, **envelope_arrays)
    if "envelope_times" in arrays:
        arrays["envelope_times"] += start_sample / sample_rate
    return metrics, arrays


def segment_slices(sample_count, sample_rate, config):
    config.validate(sample_rate)
    size = round(config.segment_seconds * sample_rate)
    if sample_count <= 0 or math.ceil(sample_count / size) > config.max_segments:
        raise ValueError("Empty recording or segment count exceeds the explicit report limit.")
    return [(start, min(start + size, sample_count)) for start in range(0, sample_count, size)]