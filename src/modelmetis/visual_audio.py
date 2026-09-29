import base64
import hashlib
import io
import json
import math
import re
import struct
import time
from dataclasses import asdict, dataclass
from importlib.metadata import version
from pathlib import Path

import numpy as np
import soundfile as sf
from scipy import signal


@dataclass(frozen=True)
class RenderConfig:
    schema: int = 1
    sample_rate: int = 16000
    channel_policy: str = "require_mono"
    resample_policy: str = "reject"
    window_seconds: float = 0.5
    overlap_seconds: float = 0.0
    tail: str = "zero_pad_with_valid_duration"
    stft_window: str = "hann_periodic"
    stft_boundary: str = "none"
    nfft: int = 512
    hop: int = 64
    frequency_min: float = 0.0
    frequency_max: float = 8000.0
    reference_power: float = 1.0
    db_min: float = -110.0
    db_max: float = -10.0
    colormap: str = "cividis"
    width: int = 1024
    height: int = 768
    dpi: int = 128
    scaling: str = "PSD_FS_squared_per_Hz"

    def validate(self):
        if (self.schema != 1 or self.channel_policy not in {"require_mono", "mean"}
            or self.resample_policy not in {"reject", "polyphase"}
                or self.tail != "zero_pad_with_valid_duration"
                or self.stft_window != "hann_periodic" or self.scaling != "PSD_FS_squared_per_Hz"
                or self.stft_boundary != "none"
                or self.colormap != "cividis"):
            raise ValueError("Unsupported rendering policy.")
        if not all(np.isfinite(value) for value in asdict(self).values()
                   if isinstance(value, int | float)):
            raise ValueError("Rendering parameters must be finite.")
        if (self.sample_rate < 8000 or not 0 < self.hop <= self.nfft
                or self.nfft < 16 or self.window_samples < self.nfft
                or not 0 <= self.overlap_samples < self.window_samples
                or not 0 <= self.frequency_min < self.frequency_max <= self.sample_rate / 2
                or self.reference_power <= 0 or self.db_min >= self.db_max
                or self.width < 512 or self.height < 384 or self.dpi < 72):
            raise ValueError("Invalid rendering dimensions or signal parameters.")
        for seconds in (self.window_seconds, self.overlap_seconds):
            if abs(seconds * self.sample_rate - round(seconds * self.sample_rate)) > 1e-8:
                raise ValueError("Window boundaries must be integer sample offsets.")

    @property
    def window_samples(self):
        return round(self.window_seconds * self.sample_rate)

    @property
    def overlap_samples(self):
        return round(self.overlap_seconds * self.sample_rate)

    @property
    def sha256(self):
        return hashlib.sha256(canonical_json(asdict(self))).hexdigest()


def canonical_json(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()


def pcm_sha256(samples):
    return hashlib.sha256(np.asarray(samples, dtype="<f8").tobytes()).hexdigest()


def windows(samples, config, positive_clip_threshold=1.0):
    config.validate()
    samples = np.asarray(samples, dtype=np.float64)
    if samples.ndim != 1 or samples.size == 0 or not np.isfinite(samples).all():
        raise ValueError("Expected finite, nonempty mono samples.")
    step = config.window_samples - config.overlap_samples
    for start in range(0, len(samples), step):
        end = min(start + config.window_samples, len(samples))
        valid = samples[start:end]
        padded = np.pad(valid, (0, config.window_samples - len(valid)))
        yield padded, {
            "start_sample": start, "end_sample_exclusive": end,
            "start_seconds": start / config.sample_rate,
            "end_seconds": end / config.sample_rate,
            "valid_samples": len(valid), "padding_samples": len(padded) - len(valid),
            "rms": float(np.sqrt(np.mean(valid ** 2))),
            "peak": float(np.max(np.abs(valid))),
            "silence": bool(np.max(np.abs(valid)) == 0),
            "clipped_samples": int(np.count_nonzero(
                (valid <= -1) | (valid >= positive_clip_threshold),
            )),
            "regime": "unverified_may_include_transitions",
        }
        if end == len(samples):
            break


def stft_power(samples, config):
    config.validate()
    samples = np.asarray(samples, dtype=np.float64)
    if samples.shape != (config.window_samples,) or not np.isfinite(samples).all():
        raise ValueError("STFT requires one finite, explicitly padded analysis window.")
    frequencies, times, power = signal.spectrogram(
        samples, fs=config.sample_rate, window=signal.windows.hann(config.nfft, sym=False),
        nperseg=config.nfft, noverlap=config.nfft - config.hop, nfft=config.nfft,
        detrend=False, return_onesided=True, scaling="density", mode="psd",
    )
    selected = (frequencies >= config.frequency_min) & (frequencies <= config.frequency_max)
    decibels = 10 * np.log10(np.maximum(power[selected] / config.reference_power, 1e-30))
    return frequencies[selected], times, decibels


def decode_audio(path, config):
    config.validate()
    payload = Path(path).read_bytes()
    if payload[:4] == b"RIFF":
        if len(payload) < 44 or payload[8:12] != b"WAVE":
            raise ValueError("Invalid WAV signature.")
        if struct.unpack_from("<I", payload, 4)[0] + 8 != len(payload):
            raise ValueError("Incomplete or inconsistent RIFF length.")
        offset, data_bytes = 12, None
        while offset < len(payload):
            if offset + 8 > len(payload):
                raise ValueError("Incomplete WAV chunk header.")
            size = struct.unpack_from("<I", payload, offset + 4)[0]
            if offset + 8 + size > len(payload):
                raise ValueError("Incomplete WAV chunk.")
            if payload[offset:offset + 4] == b"data":
                if data_bytes is not None:
                    raise ValueError("Multiple WAV data chunks are unsupported.")
                data_bytes = size
            offset += 8 + size + (size % 2)
        if data_bytes is None or not data_bytes:
            raise ValueError("Missing WAV data.")
    elif payload[:4] != b"fLaC":
        raise ValueError("Only content-identified WAV and FLAC are supported.")
    decoder = "libsndfile"
    with sf.SoundFile(io.BytesIO(payload)) as recording:
        rate, channels, frames = recording.samplerate, recording.channels, recording.frames
        container, subtype = recording.format, recording.subtype
        if subtype not in {"PCM_U8", "PCM_16", "PCM_24", "PCM_32", "FLOAT", "DOUBLE"}:
            raise ValueError("Unsupported sample encoding.")
        if container == "WAV":
            widths = {"PCM_U8": 1, "PCM_16": 2, "PCM_24": 3, "PCM_32": 4,
                      "FLOAT": 4, "DOUBLE": 8}
            if data_bytes != frames * channels * widths[subtype]:
                raise ValueError("Incomplete WAV sample frame.")
        try:
            samples = recording.read(dtype="float64", always_2d=True)
        except sf.LibsndfileError:
            if container != "FLAC":
                raise
            import av

            with av.open(io.BytesIO(payload)) as alternate:
                blocks = list(alternate.decode(audio=0))
            if not blocks or any(block.format.name != "s32" or block.sample_rate != rate
                                 or len(block.layout.channels) != channels for block in blocks):
                raise ValueError("Unsupported fallback decoded format.") from None
            samples = np.concatenate([
                block.to_ndarray().reshape(-1, channels) for block in blocks
            ]).astype(np.float64) / 2 ** 31
            decoder = "ffmpeg_after_libsndfile_error"
    if samples.shape != (frames, channels) or frames == 0 or not np.isfinite(samples).all():
        raise ValueError("Incomplete, empty or nonfinite decoded audio.")
    if container == "FLAC":
        if (len(payload) < 42 or payload[4] & 127 != 0
                or int.from_bytes(payload[5:8]) != 34):
            raise ValueError("Missing FLAC STREAMINFO.")
        declared_frames = int.from_bytes(payload[18:26]) & ((1 << 36) - 1)
        if declared_frames != frames or payload[26:42] == bytes(16):
            raise ValueError("FLAC requires a verified frame count and embedded PCM checksum.")
        width = int(subtype.split("_")[1]) // 8
        integers = np.rint(samples * 2 ** 31).astype("<i4")
        raw = integers.view(np.uint8).reshape(-1, 4)[:, 4 - width:].tobytes()
        if hashlib.md5(raw, usedforsecurity=False).digest() != payload[26:42]:
            raise ValueError("FLAC PCM checksum mismatch.")
    bits = {"PCM_U8": 8, "PCM_16": 16, "PCM_24": 24, "PCM_32": 32}.get(subtype)
    positive_clip_threshold = 1 - 2 ** (1 - bits) if bits else 1.0
    metadata = {
        "source_sha256": hashlib.sha256(payload).hexdigest(),
        "source_pcm_sha256": pcm_sha256(samples), "source_sample_rate": rate,
        "source_frames": frames, "source_channels": channels,
        "source_duration_seconds": frames / rate, "container": container,
        "subtype": subtype, "decoder": decoder, "transformations": [],
        "source_peak": float(np.max(np.abs(samples))),
        "source_rms": float(np.sqrt(np.mean(samples ** 2))),
        "positive_clip_threshold": positive_clip_threshold,
        "source_clipped_samples": int(np.count_nonzero(
            (samples <= -1) | (samples >= positive_clip_threshold),
        )),
    }
    if channels != 1 and config.channel_policy == "require_mono":
        raise ValueError("Multichannel input requires an explicit mean channel policy.")
    if channels != 1:
        metadata["transformations"].append("arithmetic_channel_mean")
    samples = samples.mean(axis=1)
    if rate != config.sample_rate:
        if config.resample_policy != "polyphase":
            raise ValueError("Sample-rate mismatch; explicitly enable polyphase resampling.")
        divisor = math.gcd(rate, config.sample_rate)
        samples = signal.resample_poly(samples, config.sample_rate // divisor, rate // divisor)
        metadata["transformations"].append({"resample_poly": {
            "from": rate, "to": config.sample_rate, "window": ["kaiser", 5.0],
            "padtype": "constant", "cval": 0.0,
        }})
    metadata["analysis_pcm_sha256"] = pcm_sha256(samples)
    return samples, metadata


def render_png(samples, valid_samples, config):
    import matplotlib
    from matplotlib.backends.backend_agg import FigureCanvasAgg
    from matplotlib.figure import Figure
    from PIL import Image

    if not 0 < valid_samples <= config.window_samples:
        raise ValueError("Invalid valid-sample count.")
    frequencies, times, decibels = stft_power(samples, config)
    with matplotlib.rc_context({"font.family": "DejaVu Sans", "font.size": 13}):
        figure = Figure(figsize=(config.width / config.dpi, config.height / config.dpi),
                        dpi=config.dpi, facecolor="white")
        FigureCanvasAgg(figure)
        axes = figure.add_axes((0.115, 0.13, 0.70, 0.76))
        image = axes.pcolormesh(times, frequencies, decibels, shading="nearest",
                               cmap=config.colormap, vmin=config.db_min, vmax=config.db_max,
                               rasterized=True)
        axes.set(xlim=(0, config.window_seconds),
                 ylim=(config.frequency_min, config.frequency_max),
                 xlabel="Time (s)", ylabel="Frequency (Hz)",
                 title="STFT power spectral density")
        if valid_samples < config.window_samples:
            boundary = valid_samples / config.sample_rate
            axes.axvspan(boundary, config.window_seconds, color="0.85", alpha=0.85)
            axes.axvline(boundary, color="black", linewidth=1)
        color_axes = figure.add_axes((0.85, 0.13, 0.025, 0.76))
        figure.colorbar(image, cax=color_axes,
                        label=f"dB re {config.reference_power:g} FS^2/Hz")
        output = io.BytesIO()
        figure.savefig(output, format="png", dpi=config.dpi)
        figure.clear()
    clean = io.BytesIO()
    with Image.open(io.BytesIO(output.getvalue())) as image:
        image.convert("RGB").save(clean, format="PNG", optimize=False)
    return clean.getvalue()


def render_recordings(records, output, config):
    config.validate()
    output = Path(output)
    output.mkdir(parents=True, exist_ok=False)
    seen_ids, seen_pcm, group_splits = set(), {}, {}
    for row in records:
        if not set(row) == {"path", "recording_id", "group_id", "split"}:
            raise ValueError("Manifest requires only path, recording_id, group_id and split.")
        if row["recording_id"] in seen_ids:
            raise ValueError("Duplicate recording identity.")
        seen_ids.add(row["recording_id"])
        previous = group_splits.setdefault(row["group_id"], row["split"])
        if previous != row["split"]:
            raise ValueError("Acquisition group crosses splits before segmentation.")
    manifest = {
        "schema": 1, "config": asdict(config), "config_sha256": config.sha256,
        "renderer_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "versions": {name: version(name) for name in
                     ("numpy", "scipy", "soundfile", "av", "matplotlib", "pillow")},
        "recordings": [], "status": "running",
    }
    started = time.monotonic()
    try:
        if not records:
            raise ValueError("No source recordings supplied.")
        for row in records:
            entry = {**row, "status": "decoding", "windows": []}
            manifest["recordings"].append(entry)
            samples, metadata = decode_audio(row["path"], config)
            entry.update(metadata)
            previous = seen_pcm.setdefault(metadata["analysis_pcm_sha256"], row["split"])
            if previous != row["split"]:
                raise ValueError("Duplicate decoded audio crosses splits.")
            for number, (segment, offsets) in enumerate(windows(
                samples, config, metadata["positive_clip_threshold"],
            )):
                segment_id = hashlib.sha256(canonical_json([
                    row["recording_id"], metadata["analysis_pcm_sha256"], offsets,
                    config.sha256, manifest["renderer_sha256"], manifest["versions"],
                ])).hexdigest()
                png = render_png(segment, offsets["valid_samples"], config)
                image_name = f"{segment_id}.png"
                (output / image_name).write_bytes(png)
                entry["windows"].append({
                    **offsets, "index": number, "segment_id": segment_id,
                    "image": image_name, "image_sha256": hashlib.sha256(png).hexdigest(),
                    "segment_pcm_sha256": pcm_sha256(segment),
                })
            entry["status"] = "completed"
        manifest["status"] = "completed"
    except Exception as error:
        manifest.update(status="failed", error_type=type(error).__name__, error=str(error))
        raise
    finally:
        manifest["elapsed_seconds"] = time.monotonic() - started
        (output / "manifest.json").write_bytes(canonical_json(manifest))
    return manifest


PROMPT = (
    "Compare the query STFT power spectrogram with the supplied reference spectrograms. "
    "Every image uses the same time/frequency axes and absolute dB color scale. "
    "Each reference represents one known condition, which may itself be a fault. "
    "Return known only when one supplied condition is supported; outside_reference for "
    "a condition not represented; indeterminate for ambiguous, mixed, insufficient or "
    "incompatible evidence. Outside-reference does not imply a fault. Do not force a "
    "nearest-reference answer. Give a concise visual explanation; do not invent a diagnosis. "
    "Return exactly outcome, condition_id (null unless known), and explanation."
)


def parse_decision(value, allowed_ids):
    if (not isinstance(value, dict)
            or set(value) != {"outcome", "condition_id", "explanation"}
            or not isinstance(value["outcome"], str)
            or (value["condition_id"] is not None and not isinstance(value["condition_id"], str))
            or value["outcome"] not in {"known", "outside_reference", "indeterminate"}
            or not isinstance(value["explanation"], str)
            or not value["explanation"].strip()):
        raise ValueError("Malformed decision.")
    if value["outcome"] == "known":
        if value["condition_id"] not in allowed_ids:
            raise ValueError("Known condition is not in the visible reference set.")
    elif value["condition_id"] is not None:
        raise ValueError("Only a known decision may contain a condition ID.")
    return value


def image_messages(references, query_png, config):
    from PIL import Image

    identifiers = [identifier for identifier, _ in references]
    if (not references or len(set(identifiers)) != len(identifiers)
            or any(re.fullmatch(r"C[0-9]{2}", identifier) is None
                   for identifier in identifiers)):
        raise ValueError("References require unique opaque condition IDs.")
    content = []
    for title, payload in [*(
        (f"Reference {identifier}", image) for identifier, image in references
    ), ("Query", query_png)]:
        with Image.open(io.BytesIO(payload)) as image:
            image.load()
            if (image.format != "PNG" or image.size != (config.width, config.height)
                    or image.mode != "RGB" or image.info):
                raise ValueError("Expected metadata-free RGB PNG at frozen dimensions.")
        content.extend([
            {"type": "text", "text": title},
            {"type": "image_url", "image_url": {
                "url": "data:image/png;base64," + base64.b64encode(payload).decode("ascii"),
                "detail": "high",
            }},
        ])
    return [{"role": "system", "content": PROMPT}, {"role": "user", "content": content}]


def welch_features(samples, config):
    config.validate()
    samples = np.asarray(samples, dtype=np.float64)
    if samples.shape != (config.window_samples,) or not np.isfinite(samples).all():
        raise ValueError("Welch requires the same finite analysis window as STFT.")
    frequencies, power = signal.welch(
        samples, fs=config.sample_rate, window=signal.windows.hann(config.nfft, sym=False),
        nperseg=config.nfft, noverlap=config.nfft - config.hop, nfft=config.nfft,
        detrend=False, scaling="density", average="mean",
    )
    selected = (frequencies >= config.frequency_min) & (frequencies <= config.frequency_max)
    return np.clip(10 * np.log10(np.maximum(power[selected] / config.reference_power, 1e-30)),
                   config.db_min, config.db_max)


def numerical_decision(query, references, max_distance_db=12.0, min_margin_db=2.0):
    if (not references or max_distance_db < 0 or min_margin_db < 0
            or not np.isfinite([max_distance_db, min_margin_db]).all()):
        raise ValueError("Invalid numerical reference set or rejection policy.")
    distances = sorted((float(np.sqrt(np.mean((query - feature) ** 2))), identifier)
                       for identifier, feature in references.items())
    distance, identifier = distances[0]
    if distance > max_distance_db:
        outcome, identifier = "outside_reference", None
    elif len(distances) > 1 and distances[1][0] - distance < min_margin_db:
        outcome, identifier = "indeterminate", None
    else:
        outcome = "known"
    return {"outcome": outcome, "condition_id": identifier,
            "explanation": "Frozen RMS log-Welch distance and ambiguity rule.",
            "distances_db": {identifier: distance for distance, identifier in distances}}


def evaluate_predictions(rows):
    categories = ("correct_known", "wrong_known", "known_false_rejection", "unknown_false_accept",
                  "correct_unknown_rejection", "indeterminate", "technical_failure")
    counts = dict.fromkeys(categories, 0)
    confusion, per_condition = {}, {}
    known_total = unknown_total = accepted = 0
    groups, recordings = set(), set()
    for row in rows:
        known = row["truth"] in row["visible_ids"]
        known_total += int(known)
        unknown_total += int(not known)
        groups.add(row["group_id"])
        recordings.add(row["recording_id"])
        if row.get("technical_failure"):
            category, prediction = "technical_failure", "technical_failure"
        else:
            decision = parse_decision(row["decision"], row["visible_ids"])
            prediction = decision["condition_id"] or decision["outcome"]
            if decision["outcome"] == "indeterminate":
                category = "indeterminate"
            elif decision["outcome"] == "outside_reference":
                category = "known_false_rejection" if known else "correct_unknown_rejection"
            else:
                accepted += 1
                category = ("unknown_false_accept" if not known else
                            "correct_known" if decision["condition_id"] == row["truth"]
                            else "wrong_known")
        counts[category] += 1
        condition = per_condition.setdefault(row["truth"], dict.fromkeys(categories, 0))
        condition[category] += 1
        expected = row["truth"] if known else "outside_reference"
        cells = confusion.setdefault(expected, {})
        cells[prediction] = cells.get(prediction, 0) + 1
    total = len(rows)
    return {"counts": counts, "total_decisions": total, "known_trials": known_total,
            "unknown_trials": unknown_total, "accepted_known_labels": accepted,
            "known_label_coverage": accepted / total if total else None,
            "accepted_label_error": (counts["wrong_known"] + counts["unknown_false_accept"])
            / accepted if accepted else None,
            "decision_coverage": (total - counts["technical_failure"] - counts["indeterminate"])
            / total if total else None,
            "unknown_false_acceptance_rate": counts["unknown_false_accept"] / unknown_total
            if unknown_total else None,
            "query_physical_groups": len(groups), "query_recordings": len(recordings),
            "independent_acquisitions": None, "confusion": confusion,
            "per_condition": per_condition,
            "uncertainty": "No IID confidence interval: repeated folds and one query unit."}