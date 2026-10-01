from dataclasses import asdict, dataclass

import numpy as np
from scipy import signal


@dataclass(frozen=True)
class ShapeConfig:
    frame_seconds: tuple[float, ...] = (0.02, 0.1, 0.5)
    segment_seconds: float = 1.0
    frequency_min_hz: float = 20.0
    frequency_max_hz: float = 4000.0
    band_edges_hz: tuple[float, ...] = (20.0, 250.0, 1000.0, 2000.0, 4000.0)
    relative_floor_db: float = -80.0
    minimum_ac_rms_fs: float = 1e-10
    transient_distance_db: float = 6.0

    def validate(self, sample_rate):
        values = [*self.frame_seconds, self.segment_seconds, self.frequency_min_hz,
                  self.frequency_max_hz, *self.band_edges_hz, self.relative_floor_db,
                  self.minimum_ac_rms_fs, self.transient_distance_db]
        if (not np.isfinite(values).all() or not self.frame_seconds or len(self.band_edges_hz) < 2
                or not 8000 <= sample_rate <= 192000
                or tuple(sorted(set(self.frame_seconds))) != tuple(self.frame_seconds)
                or not 0 < min(self.frame_seconds) <= max(self.frame_seconds)
                <= self.segment_seconds
                or not 0 < self.frequency_min_hz < self.frequency_max_hz <= sample_rate / 2
                or tuple(sorted(set(self.band_edges_hz))) != tuple(self.band_edges_hz)
                or self.band_edges_hz[0] != self.frequency_min_hz
                or self.band_edges_hz[-1] != self.frequency_max_hz
                or self.relative_floor_db >= 0 or self.minimum_ac_rms_fs <= 0
                or self.transient_distance_db <= 0):
            raise ValueError("Invalid physical-resolution shape configuration.")
        if any(round(duration * sample_rate) < 32 for duration in self.frame_seconds):
            raise ValueError("Spectral frames require at least 32 samples.")


def centered_shape(power, relative_floor_db):
    floor = np.max(power, axis=0, keepdims=True) * 10 ** (relative_floor_db / 10)
    decibels = 10 * np.log10(np.maximum(power, np.maximum(floor, np.finfo(float).tiny)))
    return decibels - decibels.mean(axis=0, keepdims=True)


def shape_features(samples, sample_rate, config=None):
    config = config or ShapeConfig()
    config.validate(sample_rate)
    samples = np.asarray(samples, dtype=np.float64)
    if samples.ndim != 1 or not len(samples) or not np.isfinite(samples).all():
        raise ValueError("Expected nonempty finite samples from one explicitly selected channel.")
    segment_size = round(config.segment_seconds * sample_rate)
    result = {
        "sample_rate": sample_rate, "sample_count": len(samples), "config": asdict(config),
        "quality": {"rms_fs": float(np.sqrt(np.mean(samples ** 2))),
                    "dc_offset_fs": float(samples.mean()),
                    "peak_fs": float(np.max(np.abs(samples))),
                    "near_full_scale_fraction": float(np.mean(np.abs(samples) >= 0.999))},
        "resolutions": [], "baseline": baseline_shape(samples, sample_rate),
        "controls": {
            "band_1024": controlled_welch(samples, sample_rate, config, 1024, False),
            "floor_1024": controlled_welch(samples, sample_rate, config, 1024, True),
            **{f"welch_{duration:g}": controlled_welch(
                samples, sample_rate, config, round(duration * sample_rate), True)
                for duration in config.frame_seconds},
        },
    }
    for duration in config.frame_seconds:
        frame_size = round(duration * sample_rate)
        hop_size = max(1, frame_size // 4)
        segments, shapes, floors = [], [], []
        frequencies = np.fft.rfftfreq(frame_size, 1 / sample_rate)
        selected = (frequencies >= config.frequency_min_hz) & (
            frequencies <= config.frequency_max_hz)
        for start in range(0, len(samples), segment_size):
            block = samples[start:start + segment_size]
            centered = block - block.mean()
            entry = {"start_sample": start, "end_sample_exclusive": start + len(block),
                     "ac_rms_fs": float(np.sqrt(np.mean(centered ** 2)))}
            if len(block) < frame_size or entry["ac_rms_fs"] < config.minimum_ac_rms_fs:
                entry.update(status="unavailable", reason="short_or_low_energy")
            else:
                _, _, power = signal.spectrogram(
                    centered, fs=sample_rate, window="hann", nperseg=frame_size,
                    noverlap=frame_size - hop_size, detrend=False, scaling="density", mode="psd",
                )
                power = power[selected]
                average = power.mean(axis=1)
                if average.sum() * sample_rate / frame_size < config.minimum_ac_rms_fs ** 2:
                    entry.update(status="unavailable", reason="no_power_in_comparison_band")
                    segments.append(entry)
                    continue
                shape = centered_shape(average, config.relative_floor_db)
                frame_energy = power.sum(axis=0)
                active = frame_energy > np.max(frame_energy) * 10 ** (
                    config.relative_floor_db / 10)
                frame_shapes = centered_shape(power[:, active], config.relative_floor_db)
                departures = np.sqrt(np.mean((frame_shapes - shape[:, None]) ** 2, axis=0))
                floors.append(float(np.mean(average <= np.max(average) * 10 ** (
                    config.relative_floor_db / 10))))
                shapes.append(shape)
                entry.update(
                    status="available", frames=power.shape[1], active_frames=int(active.sum()),
                    uncovered_tail_samples=(len(block) - frame_size) % hop_size,
                    transient_frame_fraction=float(np.mean(
                        departures > config.transient_distance_db)),
                )
            segments.append(entry)
        resolution = {
            "requested_frame_seconds": duration, "actual_frame_seconds": frame_size / sample_rate,
            "frame_samples": frame_size, "hop_samples": hop_size,
            "bin_spacing_hz": sample_rate / frame_size,
            "hann_enbw_hz": 1.5 * sample_rate / frame_size,
            "frequencies_hz": frequencies[selected].tolist(), "segments": segments,
            "available_segments": len(shapes), "total_segments": len(segments),
            "status": "available" if shapes else "unavailable",
        }
        if shapes:
            matrix = np.stack(shapes)
            median = np.median(matrix, axis=0)
            resolution.update(
                median_db=median.tolist(), q10_db=np.quantile(matrix, 0.1, axis=0).tolist(),
                q90_db=np.quantile(matrix, 0.9, axis=0).tolist(),
                segment_shapes_db=matrix.tolist(), floored_bin_fraction=floors,
                temporal_distance_db=np.sqrt(np.mean((matrix - median) ** 2, axis=1)).tolist(),
            )
        result["resolutions"].append(resolution)
    return result


def compare_shapes(query, reference):
    if query["config"] != reference["config"]:
        raise ValueError("Comparisons require identical representation configurations.")
    comparisons = []
    for query_view, reference_view in zip(
        query["resolutions"], reference["resolutions"], strict=True,
    ):
        frequencies = np.asarray(query_view["frequencies_hz"])
        reference_frequencies = np.asarray(reference_view["frequencies_hz"])
        entry = {"frame_seconds": query_view["requested_frame_seconds"]}
        if (frequencies.shape != reference_frequencies.shape
                or not np.allclose(frequencies, reference_frequencies, rtol=0, atol=1e-9)):
            entry.update(status="unavailable", reason="physical_frequency_grid_mismatch")
        elif query_view["status"] != "available" or reference_view["status"] != "available":
            entry.update(status="unavailable", reason="missing_spectral_evidence")
        else:
            delta = np.asarray(query_view["median_db"]) - reference_view["median_db"]
            squared = delta ** 2
            edges = query["config"]["band_edges_hz"]
            bands = []
            for lower, upper in zip(edges[:-1], edges[1:], strict=True):
                selected = (frequencies >= lower) & (
                    (frequencies <= upper) if upper == edges[-1] else (frequencies < upper))
                bands.append({"lower_hz": lower, "upper_hz": upper,
                              "bins": int(selected.sum()),
                              "squared_distance_contribution_db2": float(
                                  squared[selected].sum() / len(squared))})
            segment_delta = (np.asarray(query_view["segment_shapes_db"])
                             - reference_view["median_db"])
            entry.update(status="available", distance_db=float(np.sqrt(squared.mean())),
                         difference_db=delta.tolist(), bands=bands,
                         query_segment_distance_db=np.sqrt(
                             np.mean(segment_delta ** 2, axis=1)).tolist())
        comparisons.append(entry)
    return comparisons


def baseline_shape(samples, sample_rate):
    vectors = []
    for start in range(0, len(samples), 10 * sample_rate):
        block = samples[start:start + 10 * sample_rate]
        if len(block) < 32 or np.std(block) < 1e-10:
            return {"status": "unavailable"}
        frame_size = min(1024, len(block))
        _, power = signal.welch(
            block - block.mean(), fs=sample_rate, window="hann", nperseg=frame_size,
            noverlap=frame_size - min(256, frame_size), detrend=False, scaling="density",
        )
        decibels = 10 * np.log10(np.maximum(power, 1e-30))
        vectors.append(decibels - decibels.mean())
    if len({len(vector) for vector in vectors}) != 1:
        return {"status": "unavailable"}
    return {"status": "available", "shape_db": np.mean(vectors, axis=0).tolist(),
            "sample_rate": sample_rate, "segment_seconds": 10, "frame_samples": 1024,
            "hop_samples": 256, "absolute_floor_psd": 1e-30, "frequency_scope": "full_band"}


def baseline_distance(query, reference):
    if (query["status"] != "available" or reference["status"] != "available"
            or query["sample_rate"] != reference["sample_rate"]
            or len(query["shape_db"]) != len(reference["shape_db"])):
        return None
    return float(np.sqrt(np.mean((np.asarray(query["shape_db"]) - reference["shape_db"]) ** 2)))


def controlled_welch(samples, sample_rate, config, frame_size, relative_floor):
    vectors = []
    frequencies = np.fft.rfftfreq(frame_size, 1 / sample_rate)
    selected = (frequencies >= config.frequency_min_hz) & (frequencies <= config.frequency_max_hz)
    for start in range(0, len(samples), 10 * sample_rate):
        block = samples[start:start + 10 * sample_rate]
        if (len(block) < frame_size or np.std(block) < config.minimum_ac_rms_fs
            or not selected.any()):
            return {"status": "unavailable"}
        _, power = signal.welch(
            block - block.mean(), fs=sample_rate, window="hann", nperseg=frame_size,
            noverlap=frame_size - max(1, frame_size // 4), detrend=False, scaling="density",
        )
        power = power[selected]
        if power.sum() * sample_rate / frame_size < config.minimum_ac_rms_fs ** 2:
            return {"status": "unavailable"}
        if relative_floor:
            vectors.append(centered_shape(power, config.relative_floor_db))
        else:
            decibels = 10 * np.log10(np.maximum(power, 1e-30))
            vectors.append(decibels - decibels.mean())
    return {"status": "available", "shape_db": np.mean(vectors, axis=0).tolist(),
            "sample_rate": sample_rate, "frequencies_hz": frequencies[selected].tolist()}


def class_ranking(references, distances):
    rows = []
    for class_id in sorted({item["class_id"] for item in references}):
        members = [item for item in references if item["class_id"] == class_id]
        regimes = []
        for regime_id in sorted({item["regime_id"] for item in members}):
            regime_members = [item for item in members if item["regime_id"] == regime_id]
            groups = sorted({item["group_id"] for item in regime_members})
            group_distances = [float(np.median([
                distances[item["id"]] for item in regime_members if item["group_id"] == group
            ])) for group in groups] if all(
                distances[item["id"]] is not None for item in regime_members) else []
            regimes.append({"regime_id": regime_id, "references": len(regime_members),
                            "acquisition_groups": len(groups),
                            "distance_db": float(np.median(group_distances))
                            if group_distances else None})
        complete = all(regime["distance_db"] is not None for regime in regimes)
        best = min(regimes, key=lambda item: item["distance_db"]) if complete else None
        rows.append({"class_id": class_id, "references": len(members), "regimes": regimes,
                     "distance_db": best["distance_db"] if best else None,
                     "closest_regime": best["regime_id"] if best else None})
    ranked = sorted(rows, key=lambda row: (row["distance_db"] is None,
                                           row["distance_db"] or 0, row["class_id"]))
    complete = all(row["distance_db"] is not None for row in ranked)
    margin = (ranked[1]["distance_db"] - ranked[0]["distance_db"]
              if complete and len(rows) > 1 else None)
    return {"classes": ranked, "complete": complete,
            "forced_candidate": ranked[0]["class_id"] if complete and margin != 0 else None,
            "competing_class": ranked[1]["class_id"] if complete and len(rows) > 1 else None,
            "margin_db": margin, "tie": margin == 0}


def compare_bank(query, references):
    if not references or len(references) > 64:
        raise ValueError("A bank requires 1 to 64 references.")
    records = [query, *references]
    for field in ("id", "content_sha256"):
        if len({item[field] for item in records}) != len(records):
            raise ValueError("Duplicate identifiers or decoded audio in the comparison.")
    if query["group_id"] in {item["group_id"] for item in references}:
        raise ValueError("Query and reference acquisition groups overlap.")
    for group in {item["group_id"] for item in references}:
        if len({item["class_id"] for item in references if item["group_id"] == group}) != 1:
            raise ValueError("An acquisition group has conflicting reference classes.")
    comparisons = [{"reference_id": reference["id"], "class_id": reference["class_id"],
                    "regime_id": reference["regime_id"],
                    "views": compare_shapes(query["features"], reference["features"]),
                    "baseline_distance_db": baseline_distance(
                        query["features"]["baseline"], reference["features"]["baseline"])}
                   for reference in references]
    rankings, variability = [], []
    for position, duration in enumerate(query["features"]["config"]["frame_seconds"]):
        distances = {item["reference_id"]: item["views"][position].get("distance_db")
                     for item in comparisons}
        rankings.append({"frame_seconds": duration, **class_ranking(references, distances)})
    for class_id in sorted({item["class_id"] for item in references}):
        members = [item for item in references if item["class_id"] == class_id]
        for position, duration in enumerate(query["features"]["config"]["frame_seconds"]):
            for scope in ("within_regime", "across_regimes"):
                distances, independent = [], 0
                for index, first in enumerate(members):
                    for second in members[index + 1:]:
                        same_regime = first["regime_id"] == second["regime_id"]
                        if same_regime != (scope == "within_regime"):
                            continue
                        comparison = compare_shapes(first["features"], second["features"])[position]
                        if comparison["status"] == "available":
                            distances.append(comparison["distance_db"])
                            independent += first["group_id"] != second["group_id"]
                variability.append({"class_id": class_id, "frame_seconds": duration,
                                    "scope": scope, "pairs": len(distances),
                                    "cross_acquisition_pairs": independent,
                                    "min_db": min(distances) if distances else None,
                                    "median_db": float(np.median(distances)) if distances else None,
                                    "max_db": max(distances) if distances else None})
    baseline = class_ranking(references, {item["reference_id"]: item["baseline_distance_db"]
                                         for item in comparisons})
    controls = {name: class_ranking(references, {
        reference["id"]: baseline_distance(view, reference["features"]["controls"][name])
        for reference in references}) for name, view in query["features"]["controls"].items()}
    sizes = [tuple(sorted(regime["acquisition_groups"] for regime in row["regimes"]))
             for row in rankings[0]["classes"]]
    candidates = [row["forced_candidate"] for row in [baseline, *controls.values(), *rankings]]
    return {"schema": 1, "status": "uncalibrated_review_required",
            "query_id": query["id"], "reference_count": len(references),
            "class_count": len(sizes), "comparisons": comparisons, "rankings": rankings,
            "baseline_ranking": baseline, "control_rankings": controls,
            "within_class_variability": variability,
            "unequal_bank_sizes": len(set(sizes)) != 1,
            "diagnostic_disagreement": len({value for value in candidates if value}) > 1,
            "incomplete_rankings": any(value is None for value in candidates),
            "decision": None, "diagnostic_correctness": "unmeasured"}