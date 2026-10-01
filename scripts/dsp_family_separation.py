import argparse
import time
from collections import Counter
from itertools import combinations
from pathlib import Path

import matplotlib
import numpy as np

from modelmetis import dsp
from modelmetis.dsp_guide import VIEW_GUIDE
from modelmetis.dsp_report import digest
from scripts.audio_comparison import ROOT
from scripts.dsp_extended_experiment import read_json, write_json


def holdout_predictions(groups, distances, field):
    labels = sorted({group["class"] for group in groups})
    predictions = []
    for index, group in enumerate(groups):
        candidates = {label: [other for other, candidate in enumerate(groups)
                             if candidate["class"] == label and candidate[field] != group[field]]
                      for label in labels}
        scores = {label: float(np.min(distances[index, positions]))
                  for label, positions in candidates.items() if positions}
        predicted, state = None, "unavailable"
        if len(scores) == len(labels):
            ordered = sorted(scores, key=lambda label: (scores[label], label))
            if len(ordered) == 1 or not np.isclose(scores[ordered[0]], scores[ordered[1]],
                                                  rtol=1e-9, atol=1e-12):
                predicted, state = ordered[0], "forced"
            else:
                state = "tied"
        predictions.append({"group": group["id"], "regime": group[field],
                            "expected": group["class"], "predicted": predicted,
                            "status": state, "scores": scores})
    return predictions


def prediction_counts(predictions):
    return {"correct": sum(row["predicted"] == row["expected"] for row in predictions),
            "wrong": sum(row["predicted"] is not None and row["predicted"] != row["expected"]
                         for row in predictions),
            "tied_or_unavailable": sum(row["predicted"] is None for row in predictions),
            "total": len(predictions), "predictions": predictions}

def distance_summary(values):
    values = np.asarray(values, dtype=float)
    if not values.size:
        return {"pairs": 0, "median": None, "minimum": None, "maximum": None}
    if not np.isfinite(values).all():
        raise ValueError("Distance summaries require finite observed pairs.")
    return {"pairs": len(values), "median": float(np.median(values)),
            "minimum": float(values.min()), "maximum": float(values.max())}


def separation_metrics(records, vectors):
    if not records or len(records) != len(vectors):
        raise ValueError("Every record requires one feature entry.")
    if len({record["id"] for record in records}) != len(records):
        raise ValueError("Duplicate recording identifiers.")
    groups = {}
    for index, record in enumerate(records):
        group = groups.setdefault(record["group"], {
            "id": record["group"], "class": record["class"], "regime": record["regime"],
            "profile": record.get("profile", record["regime"]),
            "indices": []})
        if group["class"] != record["class"] or group["regime"] != record["regime"]:
            raise ValueError("Acquisition group mixes classes or regimes.")
        group["indices"].append(index)
    base = {"recordings": len(records), "acquisitions": len(groups),
            "classes": len({record["class"] for record in records}),
            "available_recordings": sum(vector is not None for vector in vectors)}
    if any(vector is None for vector in vectors):
        return {**base, "status": "unavailable", "reason": "Incomplete representation coverage."}
    values = np.asarray(vectors, dtype=float)
    if values.ndim != 2 or values.shape[1] == 0:
        raise ValueError("Expected equally sized nonempty feature vectors.")
    common = np.isfinite(values).all(axis=0)
    base.update(feature_coordinates=values.shape[1], common_coordinates=int(common.sum()),
                common_fraction=float(common.mean()))
    if common.sum() < 1 or common.mean() < 0.2:
        return {**base, "status": "unavailable", "reason": "Less than 20% common measured support."}
    values = values[:, common]
    distances = np.zeros((len(records), len(records)))
    for first, second in combinations(range(len(records)), 2):
        distances[first, second] = distances[second, first] = np.sqrt(
            np.mean((values[first] - values[second]) ** 2))
    grouped = list(groups.values())
    group_distances = np.zeros((len(grouped), len(grouped)))
    for first, second in combinations(range(len(grouped)), 2):
        group_distances[first, second] = group_distances[second, first] = np.median(
            distances[np.ix_(grouped[first]["indices"], grouped[second]["indices"])])
    labels = sorted({group["class"] for group in grouped})
    within_session = [distances[first, second] for group in grouped
                      for first, second in combinations(group["indices"], 2)]
    class_rows = []
    for label in labels:
        own = [index for index, group in enumerate(grouped) if group["class"] == label]
        within = [group_distances[first, second] for first, second in combinations(own, 2)]
        competitors = {}
        matched = {}
        for other in labels:
            if other == label:
                continue
            rivals = [index for index, group in enumerate(grouped) if group["class"] == other]
            competitors[other] = [group_distances[first, second]
                                  for first in own for second in rivals]
            matched[other] = [group_distances[first, second] for first in own for second in rivals
                              if grouped[first]["regime"] == grouped[second]["regime"]]
        if not within or not competitors:
            class_rows.append({"class": label, "status": "insufficient_acquisitions"})
            continue
        nearest = min(competitors, key=lambda other: (np.median(competitors[other]), other))
        between = competitors[nearest]
        within_stats, between_stats = distance_summary(within), distance_summary(between)
        scale = between_stats["median"]
        gap = min(value for pairs in competitors.values() for value in pairs) - max(within)
        comparisons = np.asarray(within)[:, None] - np.asarray(between)[None, :]
        class_rows.append({
            "class": label, "status": "measured", "acquisitions": len(own),
            "nearest_class": nearest, "within": within_stats, "between": between_stats,
            "within_over_between": within_stats["median"] / scale if scale > 0 else None,
            "observed_gap": float(gap), "normalized_gap": float(gap / scale) if scale > 0 else None,
            "pair_ordering_fraction": float(np.mean((comparisons < 0) + 0.5 * (comparisons == 0))),
            "same_regime_between": {other: distance_summary(pairs)
                                    for other, pairs in matched.items()},
        })
    predictions = holdout_predictions(grouped, group_distances, "regime")
    measured = [row for row in class_rows if row["status"] == "measured"]
    ratios = [row["within_over_between"] for row in measured
              if row["within_over_between"] is not None]
    return {**base, "status": "measured", "per_class": class_rows,
            "within_session": distance_summary(within_session),
            "median_within_over_between": float(np.median(ratios)) if ratios else None,
            "complete_gap_classes": sum(row["observed_gap"] > 0 for row in measured),
            "forced_correct": sum(row["predicted"] == row["expected"] for row in predictions),
            "forced_wrong": sum(row["predicted"] is not None and row["predicted"] != row["expected"]
                                for row in predictions),
            "tied_or_unavailable": sum(row["predicted"] is None for row in predictions),
            "predictions": predictions, "groups": grouped,
            "profile_holdout": prediction_counts(holdout_predictions(
                grouped, group_distances, "profile")),
            "group_distances": group_distances.tolist()}


QUANTILES = np.array([0.1, 0.5, 0.9])


def centered_decibels(power):
    power = np.asarray(power, dtype=float)
    decibels = 10 * np.log10(np.maximum(power, max(float(np.nanmax(power)) * 1e-8, 1e-30)))
    return decibels - np.nanmean(decibels)


def spectrum_vector(amplitude):
    power = np.asarray(amplitude, dtype=float)[1:] ** 2
    groups = np.array_split(np.arange(len(power)), min(8192, len(power)))
    return centered_decibels(np.array([power[group].mean() for group in groups]))


def temporal_quantiles(values, center=False):
    values = np.asarray(values, dtype=float)
    if center:
        values = values - np.nanmean(values)
    return np.nanquantile(values, QUANTILES, axis=1).ravel()


def extension_vector(key, view, rate):
    if view["status"] != "available":
        return None
    if key == "spectral_kurtosis":
        spacing = 10.0
        output = np.full(round(rate / (2 * spacing)) - 1, np.nan)
        indices = np.rint(np.asarray(view["x"]) / spacing).astype(int) - 1
        if np.any(indices < 0) or np.any(indices >= len(output)):
            raise ValueError("Spectral-kurtosis grid differs from the registered 100 ms frame.")
        output[indices] = next(iter(view["series"].values()))
        return output
    if key == "ridge":
        return np.quantile(next(iter(view["series"].values())), np.linspace(0, 1, 101))
    if key == "persistence":
        histogram = np.asarray(view["values"], dtype=float)
        levels = np.asarray(view["y"], dtype=float)
        quantiles = []
        for column in histogram.T:
            total = column.sum()
            quantiles.append(np.interp(QUANTILES, np.cumsum(column) / total, levels)
                             if total > 0 else np.full(3, np.nan))
        values = np.asarray(quantiles)
        return (values - np.nanmean(values)).ravel()
    if key in {"stft_detail", "reassigned", "wavelet"}:
        return temporal_quantiles(view["values"], center=True)
    if view["kind"] == "map":
        return np.asarray(view["values"], dtype=float).ravel()
    series = []
    for name in sorted(view["series"]):
        values = np.asarray(view["series"][name], dtype=float)
        if key == "estimators":
            values = values - values.mean()
        if key == "harmonics" and values.sum() > 0:
            values = values / values.sum()
        series.append(values)
    return np.concatenate(series)


def base_vectors(samples, rate):
    metrics, arrays = dsp.analyze_segment(samples, rate, dsp.DspConfig())
    return {
        "levels": np.concatenate([np.quantile(arrays["level_" + key], np.linspace(0, 1, 101))
                                  for key in ("rms", "peak")]),
        "fft": spectrum_vector(arrays["fft_amplitude"]),
        "welch": centered_decibels(arrays["welch_psd"]),
        "stft": temporal_quantiles(centered_decibels(arrays["stft_psd"])),
        "bands": np.sqrt([band["fraction_of_welch_power"] for band in metrics["bands"]]),
        "envelope": arrays["envelope_amplitude"] / metrics["envelope"]["mean_envelope_fs"],
        "autocorrelation": arrays["autocorrelation"][1:],
        "baseline": 10 * np.log10(np.maximum(arrays["welch_psd"], 1e-30))
        - np.mean(10 * np.log10(np.maximum(arrays["welch_psd"], 1e-30))),
    }


def describe_representations():
    return {
        "levels": "RMS and peak empirical quantiles; no phase-aligned raw-waveform distance.",
        "fft": "8192 pooled linear-power bins excluding DC, relative -80 dB floor, centered dB.",
        "welch": "1024-sample Welch, relative -80 dB floor, centered dB; native frequency grid.",
        "baseline": "Historical full-band Welch (1024 samples), floor 1e-30, centered dB.",
        "stft": "Per-frequency 10/50/90% temporal quantiles of centered relative-floor dB PSD.",
        "bands": "Square roots of relative Welch band powers; all original physical bands.",
        "envelope": "Full broadband envelope spectrum divided by mean envelope.",
        "autocorrelation": "Full positive-lag normalized curve; lag zero excluded.",
        "extension_lines": "Full physical curves; estimators individually dB-centered, "
        "spacing histogram normalized; carrier envelopes already mean-relative.",
        "spectral_kurtosis": "Exact 10 Hz physical grid; unmeasured frequency bins are NaN.",
        "ridge": "101 empirical quantiles in Hz; no matching of arbitrary event times.",
        "persistence": "10/50/90% PSD-level quantiles from each frequency histogram on its "
        "actual dB axis, then centered; never compare record-dependent histogram row indices.",
        "temporal_maps": "Physical STFT/reassigned/wavelet retain each frequency's 10/50/90% "
        "time quantiles after global dB centering; chronology is not retained.",
        "other_maps": "All physical cells of cyclic, filter-bank kurtosis and carrier/modulation "
        "maps, with missing cells preserved. No frequency-axis averaging.",
        "masks": "Intersect finite coordinates across this exploratory dataset without labels; "
        "less than 20% common support is unavailable. This is transductive coverage, not a "
        "fully prospective learned-pipeline evaluation.",
        "distance": "RMS per representation; medians over all cross-window pairs define each "
        "acquisition-pair distance. Classes each contribute three acquisition groups.",
    }


def render_summary(name, rows, labels, output):
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    available = sorted([row for row in rows if row["status"] == "measured"],
                       key=lambda row: (-row["profile_holdout"]["correct"],
                                        row["median_within_over_between"] or float("inf")))
    titles = [VIEW_GUIDE[row["view"]][0] if row["view"] in VIEW_GUIDE else "Historical Welch"
              for row in available]
    figure, axes = plt.subplots(1, 2, figsize=(15, 12), gridspec_kw={"width_ratios": [1.3, 1]})
    positions = np.arange(len(available))
    axes[0].barh(positions, [row["median_within_over_between"] or 0 for row in available],
                 color="#0078d4")
    axes[0].axvline(1, color="#b11f4b", linestyle="--")
    axes[0].set(yticks=positions, yticklabels=titles,
                xlabel="Within-class / nearest-class median distance (lower is better)")
    axes[0].invert_yaxis()
    counts = [row["profile_holdout"]["correct"] for row in available]
    axes[1].barh(positions, counts, color="#c88a00")
    for position, count, row in zip(positions, counts, available, strict=True):
        axes[1].text(count + 0.15, position, f"{count}/{row['acquisitions']}",
                 va="center", fontsize=9)
    axes[1].set(yticks=positions, yticklabels=[], xlim=(0, available[0]["acquisitions"] + 4),
                xlabel="Correct forced labels with a whole direction/profile withheld")
    axes[1].invert_yaxis()
    figure.suptitle(f"{name}: observed class stability and cross-regime separation", fontsize=16)
    figure.tight_layout()
    figure.savefig(output / f"{name.lower()}-summary.png", dpi=130)
    plt.close(figure)
    matrix = np.array([[next(entry["within_over_between"] for entry in row["per_class"]
                             if entry["class"] == label) for label in labels] for row in available])
    figure, axis = plt.subplots(figsize=(13, 12))
    image = axis.imshow(matrix, cmap="cividis", vmin=0, vmax=2, aspect="auto")
    axis.set(yticks=positions, yticklabels=titles, xticks=np.arange(len(labels)),
             xticklabels=[labels[label].replace("_", " ") for label in labels])
    axis.tick_params(axis="x", labelrotation=45)
    for row_index, row in enumerate(matrix):
        for column, value in enumerate(row):
            axis.text(column, row_index, f"{value:.2f}", ha="center", va="center", fontsize=8,
                      color="white" if value < 0.9 else "black")
    figure.colorbar(image, ax=axis, label="Within / nearest-between; color capped at 2")
    figure.suptitle(f"{name}: stability by publisher class (lower is better)", fontsize=15)
    figure.tight_layout()
    figure.savefig(output / f"{name.lower()}-families.png", dpi=130)
    plt.close(figure)


def run(source, output):
    source, output = Path(source).resolve(), Path(output).resolve()
    manifest = read_json(source / "manifest.json")
    output.mkdir(parents=True, exist_ok=False)
    write_json(output / "registration.json", {
        "code_sha256": {str(Path(__file__).relative_to(ROOT)): digest(__file__),
                        str(Path(dsp.__file__).relative_to(ROOT)): digest(dsp.__file__)},
        "source_manifest_sha256": digest(source / "manifest.json"),
        "representations": describe_representations(), "model_calls": 0,
        "selection": "All48 existing extended-study recordings; no outcome-based subsetting.",
        "scope": "Descriptive labeled stability screen; previously consumed acquisitions; "
        "Jin direction and Ottawa profile/load contexts, not independent-machine validation.",
    })
    started = time.perf_counter()
    write_json(output / "attempt.json", {"status": "started", "model_calls": 0})
    all_rows = []
    for name, original_name in (("Jin", "dsp-jin-v1"), ("Ottawa", "dsp-ottawa-v2")):
        original = ROOT / "outputs" / original_name
        dataset_path = source / name / "dataset.json"
        if digest(dataset_path) != manifest["files"][f"{name}/dataset.json"]:
            raise ValueError("Source dataset changed.")
        dataset = read_json(dataset_path)
        metadata = [{"id": item["id"], "class": item.get("truth", item.get("condition")),
                     "audio_sha256": item["audioHash"]}
                    for item in [*dataset["references"], *dataset["queries"]]]
        labels = {item["condition"]: item["label"] for item in dataset["references"]}
        del dataset
        protocol = read_json(original / "protocol.json")
        source_registration = read_json(original / "registration.json")
        if digest(original / "protocol.json") != source_registration["protocol_sha256"]:
            raise ValueError("Source protocol changed.")
        items = {item["id"]: item for item in [*protocol["known"], *protocol["queries"]]}
        features = {key: [] for key in [*VIEW_GUIDE, "baseline"]}
        grids, rates = {}, set()
        for record in metadata:
            item = items[record["id"]]
            record["group"] = item.get("group_id", item["id"])
            record["regime"] = (item["direction"] if name == "Jin" else
                                f"profile{item['profile']}-load{item['load']}")
            record["profile"] = (item["direction"] if name == "Jin" else
                                 f"profile{item['profile']}")
            if record["audio_sha256"] != item["audio_sha256"]:
                raise ValueError("Source audio binding differs.")
            samples, rate, provenance = dsp.decode_recording(item["wav"], dsp.DspConfig())
            if provenance["source_sha256"] != record["audio_sha256"] or samples.shape[1] != 1:
                raise ValueError("Registered mono WAV changed.")
            rates.add(rate)
            if len(rates) != 1:
                raise ValueError("Never align different physical sample-rate grids implicitly.")
            vectors = base_vectors(samples[:, 0], rate)
            relative = f"{name}/{record['id']}/evidence.json"
            if digest(source / relative) != manifest["files"][relative]:
                raise ValueError("Stored extension evidence changed.")
            evidence = read_json(source / relative)
            if evidence["config"]["frame_seconds"] != 0.1:
                raise ValueError("Unexpected extension physical grid.")
            for key, view in evidence["views"].items():
                if view["status"] == "available":
                    for dimension in ("x", "y") if view["kind"] == "map" else ("x",):
                        if ((key == "persistence" and dimension == "y")
                                or key == "spectral_kurtosis"):
                            continue
                        coordinate = np.asarray(view[dimension])
                        previous = grids.setdefault((key, dimension), coordinate)
                        if (previous.shape != coordinate.shape
                            or not np.allclose(previous, coordinate)):
                            raise ValueError("Physical plot coordinates differ across records.")
                vectors[key] = extension_vector(key, view, rate)
            for key, vector in vectors.items():
                features[key].append(vector)
            print(f"{name} {record['id']}: bound audio and 26 representations", flush=True)
        rows = [{"dataset": name, "view": key, **separation_metrics(metadata, vectors)}
                for key, vectors in features.items()]
        write_json(output / f"{name.lower()}-features.json", {
            "records": metadata, "labels": labels, "vectors": features,
            "regimes": dict(Counter(record["regime"] for record in metadata))})
        write_json(output / f"{name.lower()}-separation.json", rows)
        render_summary(name, rows, labels, output)
        all_rows.extend(rows)
    write_json(output / "summary.json", all_rows)
    write_json(output / "attempt.json", {"status": "completed", "model_calls": 0,
                                         "elapsed_seconds": time.perf_counter() - started})
    write_json(output / "manifest.json", {"files": {
        path.name: digest(path) for path in output.iterdir() if path.is_file()}})
    return [{key: row[key] for key in ("dataset", "view", "status", "acquisitions",
                                     "median_within_over_between", "complete_gap_classes",
                                     "forced_correct", "profile_holdout") if key in row}
            for row in all_rows]


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Within-family and between-family DSP separation.")
    parser.add_argument("--source", type=Path, default=Path("outputs/dsp-extended-v1"))
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    run(args.source, args.output)