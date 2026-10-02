import base64
import hashlib
import html
import io
import json
from importlib.metadata import version
from pathlib import Path

import numpy as np
import soundfile as sf
from matplotlib.backends.backend_agg import FigureCanvasAgg
from matplotlib.figure import Figure
from scipy import signal


def digest(path):
    with Path(path).open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def read_audio(path, start=0.0, duration=10.0, channel=1):
    path = Path(path)
    if (not np.isfinite([start, duration]).all() or start < 0 or not 0 < duration <= 120
            or type(channel) is not int or channel < 1):
        raise ValueError("Use start >= 0, 0 < duration <= 120 seconds and a 1-based channel.")
    if path.stat().st_size > 256 * 1024 * 1024:
        raise ValueError("Source exceeds the 256 MiB input limit.")
    payload = path.read_bytes()
    with sf.SoundFile(io.BytesIO(payload)) as source:
        rate = source.samplerate
        if not 1000 <= rate <= 192000 or channel > source.channels:
            raise ValueError("Unsupported sample rate or selected channel.")
        first = round(start * rate)
        count = min(round(duration * rate), source.frames - first)
        if count < 64 or count * source.channels > 40_000_000:
            raise ValueError("Empty/short selection or decoded sample limit exceeded.")
        source.seek(first)
        samples = source.read(count, dtype="float64", always_2d=True)[:, channel - 1]
        audit = {"source_name": path.name, "source_sha256": hashlib.sha256(payload).hexdigest(),
                 "source_duration_seconds": source.frames / rate,
                 "sample_rate": rate, "source_channels": source.channels,
                 "selected_channel": channel, "start_seconds": first / rate,
                 "duration_seconds": len(samples) / rate,
                 "requested_duration_seconds": duration,
                 "channel_policy": "one native channel; no mixing",
                 "sample_rate_policy": "native", "gain_normalization": "none"}
    if not np.isfinite(samples).all():
        raise ValueError("Audio contains nonfinite samples.")
    return samples, rate, audit


def raw_analysis(samples, rate):
    centered = samples - samples.mean()
    frame = min(len(samples), max(64, round(rate * 0.25)))
    frequencies, power = signal.welch(centered, fs=rate, window="hann",
                                      nperseg=frame, noverlap=frame // 2)
    _, times, spectrogram = signal.spectrogram(
        centered, fs=rate, window="hann", nperseg=frame,
        noverlap=frame // 2, scaling="density")
    window = signal.windows.hann(len(samples), sym=False)
    amplitude = np.abs(np.fft.rfft(centered * window)) / window.sum()
    amplitude[1:] *= 2
    if len(samples) % 2 == 0:
        amplitude[-1] /= 2
    arrays = {"raw_frequencies_hz": frequencies, "raw_psd": power,
              "raw_stft_times_seconds": times, "raw_stft_psd": spectrogram,
              "raw_fft_frequencies_hz": np.fft.rfftfreq(len(samples), 1 / rate),
              "raw_fft_amplitude": amplitude}
    rms = float(np.sqrt(np.mean(centered ** 2)))
    metrics = {"rms_fs": rms, "peak_fs": float(np.max(np.abs(samples))),
               "dc_fs": float(samples.mean()),
               "crest_factor": float(np.max(np.abs(centered)) / rms) if rms else None,
               "samples_at_or_above_full_scale": int(np.sum(np.abs(samples) >= 1)),
               "welch_frame_samples": frame, "welch_bin_spacing_hz": rate / frame}
    return metrics, arrays


def decibels(values, amplitude=False):
    return (20 if amplitude else 10) * np.log10(np.maximum(values, 1e-15 if amplitude else 1e-30))


def axes_figure(rows=1):
    figure = Figure(figsize=(11, 3.8 * rows), dpi=110, layout="constrained")
    FigureCanvasAgg(figure)
    axes = np.atleast_1d(figure.subplots(rows, 1))
    for axis in axes:
        axis.grid(alpha=0.2)
    return figure, axes


def draw_map(axis, times, frequencies, power, bounds, minimum, maximum):
    if len(times) == 1:
        time_edges = np.asarray(bounds)
    else:
        time_edges = np.concatenate(([times[0] - (times[1] - times[0]) / 2],
                                     (times[1:] + times[:-1]) / 2,
                                     [times[-1] + (times[-1] - times[-2]) / 2]))
    frequency_edges = np.concatenate(([0], (frequencies[1:] + frequencies[:-1]) / 2,
                                       [frequencies[-1]
                                        + (frequencies[-1] - frequencies[-2]) / 2]))
    return axis.pcolormesh(time_edges, frequency_edges, decibels(power), shading="flat",
                           cmap="cividis", vmin=minimum, vmax=maximum)


def report_figures(samples, rate, reference, normalization, arrays):
    figures = []
    figure, axes = axes_figure(2)
    frame = max(1, round(rate * 0.02))
    starts = np.arange(0, len(samples), frame)
    counts = np.minimum(frame, len(samples) - starts)
    times = (starts + counts / 2) / rate
    axes[0].fill_between(times, np.minimum.reduceat(samples, starts),
                         np.maximum.reduceat(samples, starts), color="#2166ac", alpha=0.6)
    axes[0].set(xlabel="Selected interval time (s)", ylabel="Amplitude (FS)")
    rms = np.sqrt(np.add.reduceat(samples ** 2, starts) / counts)
    axes[1].plot(times, decibels(rms, amplitude=True), color="#2166ac")
    axes[1].set(xlabel="Selected interval time (s)", ylabel="RMS (dB re 1 FS)")
    figures.append(("waveform", "Waveform and levels", figure))
    figure, axes = axes_figure(2)
    axes[0].plot(arrays["raw_fft_frequencies_hz"],
                 decibels(arrays["raw_fft_amplitude"], amplitude=True), color="#2166ac")
    axes[0].set(xlabel="Frequency (Hz)", ylabel="FFT (dB re 1 FS peak)",
                xlim=(0, min(rate / 2, 4000)), ylim=(-120, 6))
    axes[1].plot(arrays["raw_frequencies_hz"], decibels(arrays["raw_psd"]), color="#2166ac")
    axes[1].set(xlabel="Frequency (Hz)", ylabel="PSD (dB re 1 FS^2/Hz)",
                xlim=(0, min(rate / 2, 4000)), ylim=(-130, 0))
    figures.append(("raw-spectrum", "Original FFT and Welch spectrum", figure))
    figure, axes = axes_figure()
    axis = axes[0]
    axis.grid(False)
    image = draw_map(axis, arrays["raw_stft_times_seconds"], arrays["raw_frequencies_hz"],
                     arrays["raw_stft_psd"], (0, len(samples) / rate), -130, 0)
    axis.set(xlabel="Selected interval time (s)", ylabel="Frequency (Hz)",
             ylim=(0, min(rate / 2, 4000)))
    figure.colorbar(image, ax=axis, label="dB re 1 FS^2/Hz")
    figures.append(("raw-stft", "Original time-frequency map", figure))
    figure, axes = axes_figure()
    if reference["kind"] == "known_rpm":
        axes[0].plot(arrays["base_times_seconds"], arrays["base_hz"] * 60, color="#b11f4b")
        axes[0].set(ylabel="Supplied speed (RPM)")
    else:
        for item in reference["estimation"]["frames"]:
            choices = item["candidates"][:3]
            axes[0].scatter([item["time_seconds"]] * len(choices),
                             [choice["base_hz"] for choice in choices],
                             s=[12 + choice["score"] * 24 for choice in choices],
                             color="#919191", alpha=0.45)
        selected = [item for item in reference["estimation"]["frames"] if "base_hz" in item]
        if selected:
            axes[0].plot([item["time_seconds"] for item in selected],
                         [item["base_hz"] for item in selected], color="#b11f4b")
        axes[0].set(ylabel="Estimated acoustic base (Hz)")
    axes[0].set(xlabel="Selected interval time (s)")
    figures.append(("reference", "Normalization reference", figure))
    if normalization["status"] != "available":
        return figures
    order_label = "Shaft order" if reference["kind"] == "known_rpm" else "Acoustic relative order"
    figure, axes = axes_figure(2)
    axes[0].plot(arrays["fft_orders"], decibels(arrays["fft_amplitude"], amplitude=True),
                 color="#b11f4b")
    axes[0].set(xlabel=order_label, ylabel="FFT (dB re 1 FS peak)", ylim=(-120, 6))
    axes[1].plot(arrays["orders"], decibels(arrays["order_psd"]), color="#b11f4b")
    axes[1].set(xlabel=order_label, ylabel="PSD (dB re 1 FS^2/order)", ylim=(-100, 10))
    figures.append(("order-spectrum", "Normalized FFT and Welch spectrum", figure))
    figure, axes = axes_figure()
    axis = axes[0]
    axis.grid(False)
    image = draw_map(axis, arrays["map_times_seconds"], arrays["map_orders"],
                     arrays["order_map_psd"],
                     arrays["angular_times_seconds"][[0, -1]], -100, 10)
    axis.set(xlabel="Selected interval time (s)", ylabel=order_label)
    figure.colorbar(image, ax=axis, label="dB re 1 FS^2/order")
    figures.append(("order-map", "Normalized time-order map", figure))
    figure, axes = axes_figure()
    axes[0].plot(arrays["orders"], decibels(arrays["envelope_order_psd"]), color="#b11f4b")
    axes[0].set(xlabel=order_label, ylabel="Envelope PSD (dB re 1 FS^2/order)", ylim=(-100, 10))
    figures.append(("envelope", "Angular wideband envelope spectrum", figure))
    figure, axes = axes_figure()
    mean, spread = arrays["synchronous_mean"], arrays["synchronous_std"]
    axes[0].fill_between(arrays["cycle_phase"], mean - spread, mean + spread,
                         color="#b11f4b", alpha=0.15, label="Cycle standard deviation")
    axes[0].plot(arrays["cycle_phase"], mean, color="#b11f4b", label="Cycle mean")
    axes[0].set(xlabel="Reference cycle phase", ylabel="Amplitude (FS)")
    axes[0].legend()
    figures.append(("synchronous", "Cycle-synchronous average", figure))
    figure, axes = axes_figure()
    axes[0].plot(arrays["autocorrelation_lag_cycles"], arrays["autocorrelation"],
                 color="#b11f4b")
    axes[0].set(xlabel="Lag (reference cycles)", ylabel="Normalized autocorrelation", ylim=(-1, 1))
    figures.append(("autocorrelation", "Angular autocorrelation", figure))
    return figures


def write_report(output, samples, rate, audit, reference, normalization, arrays):
    output = Path(output)
    output.mkdir(parents=True, exist_ok=False)
    (output / "images").mkdir()
    raw_metrics, raw_arrays = raw_analysis(samples, rate)
    arrays = {**raw_arrays, **arrays}
    np.savez_compressed(output / "arrays.npz", **arrays)
    document = {"schema": 1, "source": audit, "reference": reference,
                "normalization": normalization, "raw_metrics": raw_metrics,
                "runtime": {name: version(name) for name in
                            ("numpy", "scipy", "soundfile", "matplotlib")},
                "implementation_sha256": {"audio_order_known/" + path.name: digest(path)
                                          for path in Path(__file__).parent.glob("*.py")},
                "figures": []}
    if reference["kind"] == "estimated_acoustic_base":
        sibling = Path(__file__).parent.parent / "audio_order_estimated"
        document["implementation_sha256"].update({
            "audio_order_estimated/" + path.name: digest(path) for path in sibling.glob("*.py")})
    images = []
    figures = report_figures(samples, rate, reference, normalization, arrays)
    for identifier, title, figure in figures:
        path = output / "images" / f"{identifier}.png"
        figure.savefig(path, format="png", facecolor="white")
        figure.clear()
        document["figures"].append({"id": identifier, "title": title,
                                    "path": f"images/{path.name}", "sha256": digest(path)})
        encoded = base64.b64encode(path.read_bytes()).decode("ascii")
        height = 836 if identifier in ("waveform", "raw-spectrum", "order-spectrum") else 418
        images.append(f'<section id="{identifier}"><h2>{html.escape(title)}</h2>'
                  f'<img width="1210" height="{height}" src="data:image/png;base64,{encoded}" '
                  f'alt="{html.escape(title)}"></section>')
    available = normalization["status"] == "available"
    title = "Known-speed audio analysis" if reference["kind"] == "known_rpm" else (
        "Estimated-base audio analysis")
    conclusion = ("Audio normalized to the supplied shaft rotation." if reference["kind"]
                  == "known_rpm" else "Audio normalized to an estimated acoustic cycle.")
    if not available:
        conclusion = "Normalization unavailable: " + normalization["reason"]
    audio = io.BytesIO()
    sf.write(audio, samples, rate, format="WAV", subtype="PCM_16")
    audio_b64 = base64.b64encode(audio.getvalue()).decode("ascii")
    metrics = [("Channel", str(audit["selected_channel"])),
               ("Selected duration", f'{audit["duration_seconds"]:.3f} s'),
               ("Sample rate", f"{rate} Hz"), ("AC RMS", f'{raw_metrics["rms_fs"]:.5g} FS')]
    if available:
        metrics.extend([("Reference median", f'{normalization["base_hz_median"]:.3f} Hz'),
                        ("Complete cycles", str(normalization["complete_cycles"]))])
    summary = "".join(f"<div><span>{label}</span><strong>{value}</strong></div>"
                      for label, value in metrics)
    navigation = "".join(f'<a href="#{item["id"]}">{html.escape(item["title"])}</a>'
                         for item in document["figures"])
    limitations = [
        "Normalization preserves recorded gain. Speed-dependent amplitude, load, resonances "
        "and background noise can still differ between recordings.",
        "Order spectra have density units per order; original spectra have density units per Hz. "
        "Their dB heights are not directly comparable.",
        "The cycle origin is arbitrary. Cycle averaging can attenuate asynchronous impacts. "
        "The envelope uses the entire retained angular band.",
        "Audio playback is the selected original channel encoded as PCM16; samples outside "
        "full scale are clipped for playback only. Numerical analysis retains decoded values.",
    ]
    if reference["kind"] == "estimated_acoustic_base":
        limitations.append(reference["estimation"]["limitation"])
    technical = html.escape(json.dumps({"reference": reference, "normalization": normalization,
                                       "source": audit, "raw_metrics": raw_metrics},
                                      indent=2, allow_nan=False))
    style = Path(__file__).with_name("report.css").read_text(encoding="utf-8")
    theme = """<script>(() => {
const param = new URLSearchParams(window.location.search).get("scoutTheme");
const theme = param || (window.matchMedia("(prefers-color-scheme: dark)").matches
  ? "dark" : "light");
document.documentElement.setAttribute("data-theme", theme);
})();</script>"""
    page = (f'<!doctype html><html lang="en"><head><meta charset="utf-8">'
            f'<meta name="viewport" content="width=device-width,initial-scale=1">{theme}'
            f'<title>{title}</title><style>{style}</style></head><body>'
            f'<header><h1>{title}</h1><p class="conclusion">{html.escape(conclusion)}</p>'
            f'<p>{html.escape(audit["source_name"])}</p><div class="metrics">{summary}</div>'
            f'<audio controls preload="metadata" src="data:audio/wav;base64,{audio_b64}"></audio>'
            f'<nav>{navigation}</nav></header><main>{"".join(images)}'
            '<section><h2>Interpretation and scope</h2><ul>'
            + "".join(f"<li>{html.escape(item)}</li>" for item in limitations)
            + '</ul></section><details><summary>Measurements and method</summary>'
            f'<pre>{technical}</pre></details>'
            '<p><a href="measurements.json">Measurements JSON</a> '
            '<a href="arrays.npz">Full numerical arrays</a></p></main></body></html>')
    (output / "report.html").write_text(page, encoding="utf-8")
    (output / "measurements.json").write_text(json.dumps(document, indent=2, allow_nan=False),
                                             encoding="utf-8")
    manifest = {str(path.relative_to(output)).replace("\\", "/"): digest(path)
                for path in output.rglob("*") if path.is_file()}
    (output / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return document