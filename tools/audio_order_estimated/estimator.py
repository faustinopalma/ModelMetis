from dataclasses import asdict, dataclass

import numpy as np
from scipy import signal


@dataclass(frozen=True)
class EstimatorConfig:
    min_hz: float = 10.0
    max_hz: float = 300.0
    frame_seconds: float = 0.5
    hop_seconds: float = 0.1
    harmonics: int = 8
    min_score: float = 0.65
    min_margin: float = 0.08
    continuity_penalty: float = 4.0


def frame_candidates(samples, rate, config):
    centered = samples - samples.mean()
    if np.sqrt(np.mean(centered ** 2)) < 1e-9:
        return []
    frequencies, power = signal.periodogram(
        centered, fs=rate, window="hann", nfft=4 * len(samples), scaling="spectrum")
    band = (frequencies >= config.min_hz) & (
        frequencies <= min(config.max_hz * config.harmonics, rate * 0.45))
    floor = max(float(np.median(power[band])), float(power.max()) * 1e-12)
    decibels = 10 * np.log10(np.maximum(power, floor))
    positions, _ = signal.find_peaks(decibels, prominence=8, distance=4)
    positions = positions[band[positions] & (power[positions] >= floor * 16)
                          & (power[positions] >= power.max() * 0.001)]
    positions = positions[np.argsort(power[positions])[-40:]]
    if len(positions) < 2:
        return []
    delta = 0.5 * (decibels[positions - 1] - decibels[positions + 1]) / (
        decibels[positions - 1] - 2 * decibels[positions] + decibels[positions + 1])
    peak_hz = (positions + np.clip(delta, -0.5, 0.5)) * rate / (4 * len(samples))
    weights = np.sqrt(power[positions])
    weights /= weights.sum()
    seeds = (peak_hz[:, None] / np.arange(1, config.harmonics + 1)).ravel()
    seeds = np.unique(np.round(seeds[(seeds >= config.min_hz)
                                     & (seeds <= config.max_hz)], 2))
    candidates = []
    resolution = rate / len(samples)
    for seed in seeds:
        orders = np.rint(peak_hz / seed).astype(int)
        tolerance = 0.8 * resolution + 0.006 * peak_hz
        distance = np.abs(peak_hz - orders * seed)
        matched = (orders >= 1) & (orders <= config.harmonics) & (distance < tolerance)
        matched_orders = orders[matched]
        if len(set(matched_orders)) < 2 or np.gcd.reduce(matched_orders) != 1:
            continue
        fit = float(np.sum(weights[matched] * matched_orders * peak_hz[matched])
                    / np.sum(weights[matched] * matched_orders ** 2))
        if not config.min_hz <= fit <= config.max_hz:
            continue
        agreement = np.maximum(0, 1 - (distance[matched] / tolerance[matched]) ** 2)
        score = float(np.sum(weights[matched] * agreement))
        candidates.append({"base_hz": fit, "score": score,
                           "matched_orders": sorted(set(matched_orders.tolist())),
                           "matched_peaks_hz": peak_hz[matched].tolist()})
    selected = []
    for candidate in sorted(candidates, key=lambda item: -item["score"]):
        if all(abs(np.log(candidate["base_hz"] / prior["base_hz"])) > 0.04
               for prior in selected):
            selected.append(candidate)
        if len(selected) == 12:
            break
    return selected


def estimate_base(samples, sample_rate, config=None):
    config = config or EstimatorConfig()
    samples = np.asarray(samples, dtype=float)
    if (samples.ndim != 1 or not np.isfinite(samples).all()
            or not np.isfinite(sample_rate) or sample_rate <= 0
            or not np.isfinite(list(asdict(config).values())).all()
            or not 0 < config.min_hz < config.max_hz < sample_rate * 0.45
            or config.frame_seconds * config.min_hz < 4
            or not 0 < config.hop_seconds <= config.frame_seconds / 2
            or type(config.harmonics) is not int or not 2 <= config.harmonics <= 16
            or not 0 < config.min_score <= 1 or not 0 <= config.min_margin <= 1
            or config.continuity_penalty < 0):
        raise ValueError("Invalid estimator input, frequency bounds, or frame configuration.")
    frame = round(config.frame_seconds * sample_rate)
    hop = max(1, round(config.hop_seconds * sample_rate))
    if len(samples) < frame + hop:
        raise ValueError("At least two complete estimation frames are required.")
    starts = np.arange(0, len(samples) - frame + 1, hop)
    if len(starts) > 2000:
        raise ValueError("Estimation frame limit exceeded; shorten the selected interval.")
    candidates = [frame_candidates(samples[start:start + frame], sample_rate, config)
                  for start in starts]
    times = (starts + frame / 2) / sample_rate
    frames = [{"time_seconds": float(clock), "candidates": choices}
              for clock, choices in zip(times, candidates, strict=True)]
    result = {
        "method": "harmonic-comb candidates with continuity-penalized dynamic programming",
        "config": asdict(config), "frames": frames,
        "frequency_resolution_hz": sample_rate / frame,
        "score_meaning": "heuristic harmonic amplitude coverage; not a probability",
        "shaft_rpm": None,
        "limitation": "Acoustic periodicity can be a blade-pass, firing, electrical or gear "
                      "frequency. Its relationship to shaft speed requires independent evidence.",
        "status": "unreliable", "reason": "Some frames have fewer than two coherent harmonics.",
    }
    if any(not choices for choices in candidates):
        return result, None
    previous = np.array([item["score"] for item in candidates[0]])
    parents = []
    for prior, current in zip(candidates[:-1], candidates[1:], strict=True):
        jumps = np.abs(np.log(np.array([item["base_hz"] for item in prior])[:, None]
                              / np.array([item["base_hz"] for item in current])[None, :]))
        objective = previous[:, None] - config.continuity_penalty * jumps
        parent = np.argmax(objective, axis=0)
        parents.append(parent)
        previous = objective[parent, np.arange(len(current))] + [
            item["score"] for item in current]
    path = [int(np.argmax(previous))]
    for parent in reversed(parents):
        path.append(int(parent[path[-1]]))
    path.reverse()
    selected_hz, valid = [], []
    for item, choices, position in zip(frames, candidates, path, strict=True):
        selected = choices[position]
        rival = max((choice["score"] for index, choice in enumerate(choices)
                     if index != position), default=0.0)
        margin = selected["score"] - rival
        reliable = selected["score"] >= config.min_score and margin >= config.min_margin
        item.update({"base_hz": selected["base_hz"], "score": selected["score"],
                     "margin": margin, "reliable": reliable})
        selected_hz.append(selected["base_hz"])
        valid.append(reliable)
    result["reliable_frames"] = sum(valid)
    result["total_frames"] = len(frames)
    if not all(valid):
        result["reason"] = "Harmonic evidence or separation from a competing base is insufficient."
        return result, None
    if np.max(np.abs(np.diff(np.log(selected_hz)))) > np.log(1.2):
        result["reason"] = "Estimated base changes by more than 20 percent between frames."
        return result, None
    first, last = int(np.ceil(times[0] * sample_rate)), int(np.floor(times[-1] * sample_rate))
    clock = np.arange(first, last + 1) / sample_rate
    trace = np.interp(clock, times, selected_hz)
    result.update({"status": "accepted_acoustic_reference", "reason": None,
                   "base_hz_median": float(np.median(trace)),
                   "valid_start_sample": first, "valid_end_sample_exclusive": last + 1,
                   "edge_policy": "Only frame-center support is normalized; no extrapolation."})
    return result, trace