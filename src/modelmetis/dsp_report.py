import base64
import hashlib
import html
import io
import json
import re
import time
from dataclasses import asdict
from datetime import UTC, datetime
from importlib.metadata import version
from pathlib import Path

import matplotlib
import numpy as np
from matplotlib.backends.backend_agg import FigureCanvasAgg
from matplotlib.figure import Figure
from PIL import Image

from modelmetis import dsp, visual_audio
from modelmetis.visual_audio import canonical_json

BLUE, GOLD = "#2166ac", "#b88600"

STYLE = """
:root {
  color-scheme: light;
  --cp-bg: #f7f4ef;
  --cp-bg-elevated: #fcfbf8;
  --cp-surface: #ffffff;
  --cp-surface-soft: #f5f5f5;
  --cp-border: #dedede;
  --cp-border-strong: #919191;
  --cp-text: #242424;
  --cp-text-muted: #5c5c5c;
  --cp-text-soft: #6f6f6f;
  --cp-accent: #b11f4b;
  --cp-accent-hover: #9a1a41;
  --cp-accent-soft: rgba(177, 31, 75, 0.08);
  --cp-accent-fg: #ffffff;
  --cp-success: #16a34a;
  --cp-danger: #dc2626;
  --cp-warning: #f59e0b;
  --cp-link: #0078d4;
  --cp-shadow: 0 18px 48px rgba(0, 0, 0, 0.12);
  --cp-overlay: rgba(255, 255, 255, 0.8);
  --cp-panel: rgba(255, 255, 255, 0.86);
  --cp-panel-strong: rgba(255, 255, 255, 0.96);
  --cp-sheen: rgba(255, 255, 255, 0.55);
  --cp-highlight: rgba(177, 31, 75, 0.12);
}
html[data-theme="dark"] {
  color-scheme: dark;
  --cp-bg: #3d3b3a;
  --cp-bg-elevated: #343231;
  --cp-surface: #292929;
  --cp-surface-soft: #2e2e2e;
  --cp-border: #474747;
  --cp-border-strong: #5f5f5f;
  --cp-text: #dedede;
  --cp-text-muted: #919191;
  --cp-text-soft: #b0b0b0;
  --cp-accent: #fd8ea1;
  --cp-accent-hover: #fb7b91;
  --cp-accent-soft: rgba(253, 142, 161, 0.14);
  --cp-accent-fg: #1a1a1a;
  --cp-success: #4ade80;
  --cp-danger: #f87171;
  --cp-warning: #fbbf24;
  --cp-link: #4da6ff;
  --cp-shadow: 0 18px 48px rgba(0, 0, 0, 0.32);
  --cp-overlay: rgba(41, 41, 41, 0.88);
  --cp-panel: rgba(41, 41, 41, 0.72);
  --cp-panel-strong: rgba(41, 41, 41, 0.96);
  --cp-sheen: rgba(255, 255, 255, 0.04);
  --cp-highlight: rgba(253, 142, 161, 0.12);
}
* { box-sizing: border-box; letter-spacing: 0; }
body { margin: 0; background: var(--cp-surface); color: var(--cp-text);
  font-family: "Segoe UI", Aptos, Calibri, -apple-system, BlinkMacSystemFont, sans-serif; }
header, main, footer { max-width: 1248px; margin: auto; padding: 24px; }
header { border-bottom: 3px solid var(--cp-accent); }
h1 { font-size: 30px; margin: 0 0 12px; } h2 { font-size: 22px; margin: 24px 0 12px; }
h3 { font-size: 18px; } p { line-height: 1.5; max-width: 1050px; }
.muted, figcaption { color: var(--cp-text-muted); }
.metrics { display: flex; gap: 24px; flex-wrap: wrap; padding: 16px 0; }
.metrics strong { display: block; font-size: 24px; }
nav { display: flex; flex-wrap: wrap; gap: 16px; padding-top: 12px; }
a { color: var(--cp-link); } a:focus-visible { outline: 2px solid var(--cp-link); }
section { margin: 24px 0; border-top: 1px solid var(--cp-border); padding-top: 8px; }
figure { margin: 24px 0; } img { width: 100%; height: auto; display: block; }
figcaption { padding: 10px 0; line-height: 1.5; }
.table-scroll { overflow-x: auto; } table { border-collapse: collapse; width: 100%; }
th, td { padding: 10px; border-bottom: 1px solid var(--cp-border); text-align: left; }
th { background: var(--cp-surface-soft); } td { font-variant-numeric: tabular-nums; }
details { border-top: 1px solid var(--cp-border); margin: 16px 0; padding: 16px 0; }
summary { font-size: 19px; font-weight: 600; cursor: pointer; }
code { font-family: Consolas, "Courier New", Courier, monospace; overflow-wrap: anywhere; }
@media(max-width:600px) { header, main, footer { padding:16px; } h1 { font-size:26px; }
  th, td { padding:8px; } .metrics { gap:16px; } }
"""

THEME = """<script>
(() => {
  const param = new URLSearchParams(window.location.search).get("scoutTheme");
  const theme = param || (window.matchMedia("(prefers-color-scheme: dark)").matches
    ? "dark" : "light");
  document.documentElement.setAttribute("data-theme", theme);
})();
</script>"""


def digest(path):
    with Path(path).open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def number(value, precision=3):
    return "undefined" if value is None else f"{value:.{precision}f}"


def figure_axes(config, rows=1):
    figure = Figure(figsize=(config.image_width / config.image_dpi,
                            config.image_height / config.image_dpi), dpi=config.image_dpi,
                    facecolor="white", layout="constrained")
    FigureCanvasAgg(figure)
    axes = np.atleast_1d(figure.subplots(rows, 1))
    for axis in axes:
        axis.grid(alpha=0.18)
    return figure, axes


def save_figure(figure, path, title, description, config):
    output = io.BytesIO()
    figure.savefig(output, format="png", dpi=config.image_dpi)
    figure.clear()
    with Image.open(io.BytesIO(output.getvalue())) as image:
        image.convert("RGB").save(path, format="PNG")
    return {"path": "images/" + path.name, "title": title, "description": description,
            "sha256": digest(path), "width": config.image_width, "height": config.image_height}


def level_plot(arrays, start, end, title, path, config):
    figure, axes = figure_axes(config, 2)
    clock = arrays["level_times"]
    axes[0].fill_between(clock, arrays["level_minimum"], arrays["level_maximum"],
                         color=BLUE, alpha=0.5, step="mid")
    if len(clock) == 1:
        axes[0].plot(clock, arrays["level_maximum"], marker="o", color=BLUE)
    axes[0].set(title=title, ylabel="Amplitude (FS)", ylim=(-1.1, 1.1), xlim=(start, end))
    axes[1].plot(clock, 20 * np.log10(np.maximum(arrays["level_rms"], 1e-15)),
                 color=BLUE, label="RMS", marker="o" if len(clock) == 1 else None)
    axes[1].plot(clock, 20 * np.log10(np.maximum(arrays["level_peak"], 1e-15)),
                 color=GOLD, label="Peak")
    axes[1].set(xlabel="Recording time (s)", ylabel="Level (dB re 1 FS)",
                ylim=(config.amplitude_db_min, config.amplitude_db_max), xlim=(start, end))
    axes[1].legend(loc="lower right")
    return save_figure(figure, path, title,
                       "Min/max waveform envelope and RMS/peak per level frame. "
                       "Amplitude above +/-1.1 FS lies outside the fixed waveform axis; "
                       "exact peaks and clipping counts remain in the measurements.", config)


def segment_plots(metrics, arrays, rate, config, directory, prefix):
    directory = Path(directory)
    prefix_title = f"{metrics['start_seconds']:.3f}-{metrics['end_seconds']:.3f} s"
    charts = [level_plot(arrays, metrics["start_seconds"], metrics["end_seconds"],
                         "Waveform and levels | " + prefix_title,
                         directory / f"{prefix}-levels.png", config)]
    if metrics["spectral_status"] != "available":
        return charts
    figure, axes = figure_axes(config, 2)
    for axis, upper, title in (
        (axes[0], rate / 2, "FFT full band | " + prefix_title),
        (axes[1], min(config.fft_zoom_max_hz, rate / 2), "FFT fixed low-frequency detail"),
    ):
        axis.plot(arrays["fft_frequencies"],
                  20 * np.log10(np.maximum(arrays["fft_amplitude"], 1e-15)), color=BLUE)
        for peak in metrics["peaks"]:
            axis.plot(peak["frequency_hz"], peak["amplitude_db_re_1_fs_peak"],
                      marker="o", color=GOLD, markersize=5)
        axis.set(title=title, xlabel="Frequency (Hz)", ylabel="dB re 1 FS peak",
                 xlim=(0, upper), ylim=(config.amplitude_db_min, config.amplitude_db_max))
    charts.append(save_figure(figure, directory / f"{prefix}-fft.png", "FFT amplitude spectrum",
                              f"Periodic Hann; {metrics['fft']['bin_spacing_hz']:.3f} Hz bins; "
                              "coherent-gain-corrected amplitudes. No zero padding. "
                              "Markers identify the peaks in the table. "
                              f"Fixed zoom: 0-{min(config.fft_zoom_max_hz, rate / 2):g} Hz.",
                              config))
    figure, axes = figure_axes(config)
    axes[0].plot(arrays["welch_frequencies"],
                 10 * np.log10(np.maximum(arrays["welch_psd"], 1e-30)), color=BLUE)
    axes[0].set(title="Welch power spectral density | " + prefix_title, xlabel="Frequency (Hz)",
                ylabel="PSD (dB re 1 FS^2/Hz)", xlim=(0, rate / 2),
                ylim=(config.psd_db_min, config.psd_db_max))
    charts.append(save_figure(figure, directory / f"{prefix}-welch.png", "Welch PSD",
                              "Mean of overlapping Hann-windowed periodograms. "
                              "Density units differ from FFT peak amplitude units.", config))
    figure, axes = figure_axes(config)
    axis = axes[0]
    axis.grid(False)
    clock, frequencies, shading = arrays["stft_times"], arrays["welch_frequencies"], "nearest"
    if len(clock) == 1:
        half_frame = metrics["welch"]["frame_samples"] / (2 * rate)
        clock = np.array([clock[0] - half_frame, clock[0] + half_frame])
        frequencies = np.concatenate(([0.0], (frequencies[:-1] + frequencies[1:]) / 2, [rate / 2]))
        shading = "flat"
    image = axis.pcolormesh(clock, frequencies,
                            10 * np.log10(np.maximum(arrays["stft_psd"], 1e-30)),
                            shading=shading, cmap="cividis", vmin=config.psd_db_min,
                            vmax=config.psd_db_max, rasterized=True)
    axis.set(title="STFT power spectral density | " + prefix_title,
             xlabel="Recording time (s)", ylabel="Frequency (Hz)",
             xlim=(metrics["start_seconds"], metrics["end_seconds"]), ylim=(0, rate / 2))
    figure.colorbar(image, ax=axis, label="dB re 1 FS^2/Hz")
    charts.append(save_figure(figure, directory / f"{prefix}-stft.png", "STFT spectrogram",
                              "Short-Time Fourier Transform power density. Fixed color scale; "
                              "no boundary padding. Tail samples outside full STFT frames "
                              "remain in waveform, level and FFT measurements.", config))
    figure, axes = figure_axes(config)
    bands = metrics["bands"]
    labels = [f"{band['low_hz']:g}-{band['high_hz']:g}" for band in bands]
    powers = [max(config.amplitude_db_min, band["db_re_1_fs_squared"]
                  if band["db_re_1_fs_squared"] is not None else config.amplitude_db_min)
              for band in bands]
    axes[0].barh(labels, np.array(powers) - config.amplitude_db_min,
                 left=config.amplitude_db_min, color=BLUE)
    axes[0].set(title="Band-integrated power | " + prefix_title, ylabel="Band (Hz)",
                xlabel="Power (dB re 1 FS^2)",
                xlim=(config.amplitude_db_min, config.amplitude_db_max))
    charts.append(save_figure(figure, directory / f"{prefix}-bands.png", "Band power",
                              "Sum of Welch PSD bins times bin width. Band edges use bin centers; "
                              "The final band includes Nyquist. Zero power appears at the floor.",
                              config))
    figure, axes = figure_axes(config)
    axes[0].plot(1000 * arrays["autocorrelation_lags"], arrays["autocorrelation"], color=BLUE)
    axes[0].set(title="Normalized autocorrelation | " + prefix_title, xlabel="Lag (ms)",
                ylabel="Correlation / zero-lag energy", ylim=(-1.05, 1.05),
                xlim=(0, config.autocorrelation_max_seconds * 1000))
    charts.append(save_figure(figure, directory / f"{prefix}-autocorrelation.png",
                              "Autocorrelation", "Repeated intervals; biased normalization. "
                              "A correlation peak is not a measured shaft speed.", config))
    if metrics["envelope"]["status"] == "available":
        figure, axes = figure_axes(config, 2)
        stride = max(1, len(arrays["envelope"]) // 6000)
        axes[0].plot(arrays["envelope_times"][::stride], arrays["envelope"][::stride], color=BLUE)
        axes[0].set(title="Hilbert envelope | " + prefix_title,
                    xlabel="Recording time (s)", ylabel="Envelope (FS)", ylim=(0, 1.1))
        axes[1].plot(arrays["envelope_frequencies"],
                     20 * np.log10(np.maximum(arrays["envelope_amplitude"], 1e-15)), color=BLUE)
        axes[1].set(xlabel="Modulation frequency (Hz)", ylabel="Amplitude (dB re 1 FS peak)",
                    xlim=(0, min(config.envelope_max_hz, rate / 2)),
                    ylim=(config.amplitude_db_min, config.amplitude_db_max))
        charts.append(save_figure(figure, directory / f"{prefix}-envelope.png",
                                  "Envelope and modulation spectrum",
                                  "Hilbert magnitude with fixed edge exclusion. "
                                  "Broadband beating can create modulation peaks. "
                                  f"Display stride {stride}; calculations use every valid sample. "
                                  f"Filter band: {metrics['envelope']['band_hz']} Hz.", config))
    return charts


def segment_description(metrics):
    result = (f"Interval {metrics['start_seconds']:.3f}-{metrics['end_seconds']:.3f} s: "
              f"RMS {number(metrics['rms_db_re_1_fs'])} dB re 1 FS, "
              f"peak {number(metrics['peak_fs'], 6)} FS, "
              f"DC offset {number(metrics['dc_offset_fs'], 6)} FS, "
              f"crest factor {number(metrics['crest_factor_db'])} dB. "
              f"Clipped samples: {metrics['clipped_samples']}/{metrics['valid_samples']}. "
              f"Level-change candidates: {len(metrics['level_changes'])}.")
    if metrics["spectral_status"] == "available":
        result += (f" FFT bin spacing {metrics['fft']['bin_spacing_hz']:.3f} Hz; "
                   f"Welch bin spacing {metrics['welch']['bin_spacing_hz']:.3f} Hz; "
                   f"Welch frame count {metrics['welch']['frame_count']}. "
                   f"Spectral centroid {number(metrics['welch']['spectral_centroid_hz'])} Hz; "
                   f"spectral flatness {number(metrics['welch']['spectral_flatness'], 6)}.")
    else:
        result += " Too few samples for spectral measurements; no synthetic duration was added."
    return result


def format_outputs(evidence, output):
    description = evidence["summary"]
    lines = ["# Audio DSP Evidence", "", description, "", "## Limits", ""]
    body = [
        '<details><summary>Units, methods and limitations</summary>',
        *[f"<p>{html.escape(text)}</p>" for text in evidence["limits"]], '</details>',
    ]
    lines.extend(evidence["limits"])

    def chart_html(chart):
        encoded = base64.b64encode((output / chart["path"]).read_bytes()).decode("ascii")
        return (f'<figure><img loading="lazy" width="{chart["width"]}" '
                f'height="{chart["height"]}" alt="{html.escape(chart["title"])}" '
                f'src="data:image/png;base64,{encoded}"><figcaption>'
                f'{html.escape(chart["description"])}</figcaption></figure>')

    for channel in evidence["channels"]:
        title = f"Channel {channel['channel']}"
        body.append(f'<section id="channel-{channel["channel"]}"><h2>{title}</h2>')
        body.append(chart_html(channel["overview_image"]))
        lines.extend([
            "", f"## {title}", "", f"![Overview]({channel['overview_image']['path']})", "",
        ])
        body.append('<h3>All intervals</h3><div class="table-scroll"><table><thead><tr>'
                    '<th>Time (s)</th><th>RMS (dB)</th><th>Peak (FS)</th><th>DC (FS)</th>'
                    '<th>Clipped</th><th>Top FFT peak (Hz)</th><th>Plots</th></tr></thead><tbody>')
        for segment in channel["segments"]:
            peaks = segment.get("peaks", [])
            strongest = number(peaks[0]["frequency_hz"]) if peaks else "none"
            target = f'c{channel["channel"]}-s{segment["segment"]}'
            detail = f'<a href="#{target}">Available</a>' if segment["images"] else "Not sampled"
            body.append(f'<tr><td>{segment["start_seconds"]:.3f}-{segment["end_seconds"]:.3f}</td>'
                        f'<td>{number(segment["rms_db_re_1_fs"])}</td>'
                        f'<td>{number(segment["peak_fs"])}</td>'
                        f'<td>{number(segment["dc_offset_fs"], 6)}</td>'
                        f'<td>{segment["clipped_samples"]}</td><td>{strongest}</td>'
                        f'<td>{detail}</td></tr>')
        body.append("</tbody></table></div>")
        for segment in channel["segments"]:
            text = segment_description(segment)
            lines.extend(["", f"### Interval {segment['segment']}", "", text, ""])
            if segment["images"]:
                target = f'c{channel["channel"]}-s{segment["segment"]}'
                opened = " open" if segment["segment"] == 1 else ""
                body.append(f'<details id="{target}"{opened}><summary>'
                            f'Interval {segment["segment"]} / {segment["start_seconds"]:.3f}'
                            f'-{segment["end_seconds"]:.3f} s</summary><p>{html.escape(text)}</p>')
                peaks = segment.get("peaks", [])
                if peaks:
                    body.append('<h3>Measured FFT peaks</h3><div class="table-scroll"><table>'
                                '<tr><th>Frequency (Hz)</th><th>Amplitude (FS peak)</th>'
                                '<th>Amplitude (dB)</th><th>Prominence (dB)</th></tr>')
                    for peak in peaks:
                        body.append(f'<tr><td>{peak["frequency_hz"]:.3f}</td>'
                                    f'<td>{peak["amplitude_fs_peak"]:.6f}</td>'
                                    f'<td>{number(peak["amplitude_db_re_1_fs_peak"])}</td>'
                                    f'<td>{peak["prominence_db"]:.3f}</td></tr>')
                    body.append("</table></div>")
                for chart in segment["images"]:
                    body.append(chart_html(chart))
                    lines.extend([
                        f"![{chart['title']}]({chart['path']})", "", chart["description"], "",
                    ])
                body.append("</details>")
        body.append("</section>")
    (output / "report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    navigation = " ".join(f'<a href="#channel-{row["channel"]}">Channel {row["channel"]}</a>'
                          for row in evidence["channels"])
    page = (f'<!doctype html><html lang="en"><head><meta charset="utf-8">'
            f'<meta name="viewport" content="width=device-width, initial-scale=1">'
            f'<title>{evidence["recording_id"]} | Audio DSP Evidence</title>{THEME}'
            f'<style>{STYLE}</style></head><body><header><h1>Audio DSP Evidence / '
            f'{evidence["recording_id"]}</h1><p>{html.escape(description)}</p><div class="metrics">'
            f'<span><strong>{evidence["duration_seconds"]:.3f} s</strong>Duration</span>'
            f'<span><strong>{evidence["sample_rate"]:,} Hz</strong>Native sampling</span>'
            f'<span><strong>{len(evidence["channels"])}</strong>Channels</span>'
            f'<span><strong>{evidence["segment_count"]}</strong>Intervals per channel</span>'
            f'</div><nav>{navigation}</nav></header><main>{"".join(body)}</main>'
            '<footer><p>Deterministic signal measurements. No LLM calls or fault diagnosis.</p>'
            '</footer><script>function reveal(){const node=document.getElementById('
            'location.hash.slice(1));if(node&&node.tagName==="DETAILS"){node.open=true;'
            'node.scrollIntoView();}}addEventListener("hashchange",reveal);reveal();</script>'
            '</body></html>')
    (output / "report.html").write_text(page, encoding="utf-8")


def generate_report(source, output, config=None, recording_id="R0001", source_state="unknown"):
    config = config or dsp.DspConfig()
    if re.fullmatch(r"R[0-9]{4}", recording_id) is None:
        raise ValueError("Use an opaque recording ID such as R0001.")
    if source_state not in {"original", "derived", "derived_peak_normalized", "unknown"}:
        raise ValueError("Unsupported source history declaration.")
    output = Path(output)
    output.mkdir(parents=True, exist_ok=False)
    started = time.perf_counter()
    manifest = {"schema": 1, "status": "running", "started_utc": datetime.now(UTC).isoformat(),
                "config": asdict(config), "config_sha256": hashlib.sha256(
                    canonical_json(asdict(config))).hexdigest(),
                "code_sha256": {"dsp": digest(dsp.__file__), "report": digest(__file__),
                                "decoder": digest(visual_audio.__file__)},
                "versions": {name: version(name) for name in
                             ("numpy", "scipy", "soundfile", "av", "matplotlib", "pillow")},
                "timings": {}, "files": {}}
    try:
        decoded_at = time.perf_counter()
        samples, rate, provenance = dsp.decode_recording(source, config)
        manifest["timings"]["decode_seconds"] = time.perf_counter() - decoded_at
        provenance["source_state_declared"] = source_state
        (output / "provenance.json").write_bytes(canonical_json(provenance))
        intervals = dsp.segment_slices(len(samples), rate, config)
        selected = dsp.plotted_segment_indices(len(intervals), config)
        (output / "images").mkdir()
        (output / "arrays").mkdir()
        limits = [
            "Digital full-scale (FS) units are not calibrated sound pressure. "
            "RMS means root mean square; PSD means power spectral density. RMS dB uses "
            "1 FS RMS as reference; a full-scale sine has RMS -3.0103 dB on this convention.",
            "FFT means Fast Fourier Transform; STFT means Short-Time Fourier Transform. "
            "FFT shows a whole-interval spectrum, Welch averages periodograms, and STFT "
            "retains time variation. FFT bin spacing is not two-tone resolving power; "
            "Hann equivalent noise bandwidth is reported separately.",
            "Each original channel is analyzed separately at its native sample rate. Spectral "
            "analyses subtract each interval's mean; waveform, RMS, peak and DC retain original "
            "levels. No peak normalization, downmixing, resampling or duration padding is applied.",
            f"All {len(intervals)} intervals have measurements and numeric arrays. Detailed images "
            f"use uniform time sampling at interval indices {[index + 1 for index in selected]}. "
            "Unillustrated intervals are not verified homogeneous or free of short events.",
            "Fixed intervals and level-change candidates are not validated operating-regime "
            "boundaries. Envelope peaks can reflect beating; autocorrelation does not measure RPM. "
            "No mechanical fault, component identity, SNR or causal diagnosis is inferred.",
            f"Declared source history: {source_state}. Earlier processing and recorder gain "
            "cannot be reconstructed from the waveform. Absolute levels across recordings "
            "require comparable acquisition gain and calibration.",
        ]
        evidence = {"schema": 1, "recording_id": recording_id, "sample_rate": rate,
                    "duration_seconds": len(samples) / rate, "segment_count": len(intervals),
                    "plotted_segment_indices": [index + 1 for index in selected],
                    "configuration": asdict(config), "limits": limits, "channels": [],
                    "input_to_future_interpreter": ["report.md", "evidence.json", "images/"],
                    "not_interpreter_input": ["provenance.json", "manifest.json", "arrays/"]}
        analysis_seconds = plot_seconds = 0.0
        with matplotlib.rc_context({"font.family": "DejaVu Sans", "font.size": 12}):
            for channel_index in range(samples.shape[1]):
                channel = {"channel": channel_index + 1, "segments": []}
                level_parts = {}
                for index, (start, end) in enumerate(intervals):
                    clock = time.perf_counter()
                    metrics, arrays = dsp.analyze_segment(
                        samples[start:end, channel_index], rate, config, start,
                        provenance["positive_clip_threshold"],
                    )
                    analysis_seconds += time.perf_counter() - clock
                    prefix = f"c{channel_index + 1:02}-s{index + 1:04}"
                    np.savez_compressed(output / "arrays" / f"{prefix}.npz", **arrays)
                    for key, value in arrays.items():
                        if key.startswith("level_"):
                            level_parts.setdefault(key, []).append(value)
                    metrics.update(segment=index + 1, images=[], arrays=f"arrays/{prefix}.npz")
                    if index in selected:
                        clock = time.perf_counter()
                        metrics["images"] = segment_plots(metrics, arrays, rate, config,
                                                          output / "images", prefix)
                        plot_seconds += time.perf_counter() - clock
                    channel["segments"].append(metrics)
                clock = time.perf_counter()
                level_arrays = {key: np.concatenate(value) for key, value in level_parts.items()}
                np.savez_compressed(output / "arrays" / f"c{channel_index + 1:02}-overview.npz",
                                    **level_arrays)
                channel["overview_image"] = level_plot(
                    level_arrays, 0, len(samples) / rate,
                    f"Complete recording | channel {channel_index + 1}",
                    output / "images" / f"c{channel_index + 1:02}-overview.png", config,
                )
                plot_seconds += time.perf_counter() - clock
                evidence["channels"].append(channel)
        manifest["timings"].update(analysis_seconds=analysis_seconds, plot_seconds=plot_seconds)
        clipped = sum(item["clipped_samples"] for channel in evidence["channels"]
                      for item in channel["segments"])
        silent = sum(item["silent"] for channel in evidence["channels"]
                     for item in channel["segments"])
        evidence["summary"] = (
            f"{recording_id}: {len(samples) / rate:.3f} seconds, {rate} Hz, "
            f"{samples.shape[1]} original channel(s). All samples belong to a fixed interval. "
            f"Detected {clipped} full-scale clipped channel-samples and {silent} exactly silent "
            "channel-intervals. Measurements describe the recording; diagnostic status is unknown."
        )
        (output / "evidence.json").write_bytes(canonical_json(evidence))
        format_outputs(evidence, output)
        for path in sorted(output.rglob("*")):
            if path.is_file():
                manifest["files"][path.relative_to(output).as_posix()] = {
                    "sha256": digest(path), "bytes": path.stat().st_size,
                }
        manifest.update(status="completed", recording_id=recording_id,
                        image_count=len(list((output / "images").glob("*.png"))))
        return evidence
    except Exception as error:
        manifest.update(status="failed", error_type=type(error).__name__, error=str(error))
        raise
    finally:
        manifest["elapsed_seconds"] = time.perf_counter() - started
        (output / "manifest.json").write_bytes(canonical_json(manifest))
        with (output / "attempts.jsonl").open("ab") as stream:
            stream.write(canonical_json({key: manifest[key] for key in
                                        ("status", "started_utc", "elapsed_seconds")}) + b"\n")
        print(json.dumps({"status": manifest["status"], "output": str(output),
                          "elapsed_seconds": manifest["elapsed_seconds"]}), flush=True)