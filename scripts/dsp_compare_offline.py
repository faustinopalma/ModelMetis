import argparse
import base64
import html
import json
import re
import time
from dataclasses import asdict, replace
from importlib.metadata import version
from pathlib import Path

import numpy as np

from modelmetis import dsp, dsp_comparison, dsp_report, visual_audio
from modelmetis.dsp_comparison import ShapeConfig, compare_bank, shape_features
from modelmetis.dsp_report import BLUE, GOLD, STYLE, THEME, digest, figure_axes, number, save_figure


def write_json(path, value):
    Path(path).write_bytes(visual_audio.canonical_json(value))


def read_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def load_record(item, root, config):
    required = {"id", "group_id", "wav", "audio_sha256", "channel"}
    if not required <= item.keys() or item.keys() - required - {"class_id", "regime_id"}:
        raise ValueError("Unexpected or missing comparison input fields.")
    for field, prefix in (("id", "RQTD"), ("class_id", "C"), ("regime_id", "M")):
        if field in item and not re.fullmatch(f"[{prefix}][0-9]{{2,6}}", item[field]):
            raise ValueError("Report identifiers must be opaque numbered IDs.")
    if not isinstance(item["group_id"], str) or not item["group_id"]:
        raise ValueError("A nonempty acquisition group is required.")
    source = (root / item["wav"]).resolve()
    if digest(source) != item["audio_sha256"]:
        raise ValueError("Source byte hash mismatch.")
    samples, rate, provenance = dsp.decode_recording(source, dsp.DspConfig())
    if provenance["source_sha256"] != item["audio_sha256"]:
        raise ValueError("Source byte hash changed during decoding.")
    channel = item["channel"]
    if type(channel) is not int or not 0 <= channel < samples.shape[1]:
        raise ValueError("Select an existing native channel explicitly.")
    selected = samples[:, channel]
    return {"id": item["id"], "group_id": item["group_id"],
            **{field: item[field] for field in ("class_id", "regime_id") if field in item},
            "content_sha256": visual_audio.pcm_sha256(selected),
            "features": shape_features(selected, rate, config)}, provenance


def public_features(record):
    return {"id": record["id"], "features": record["features"],
            **{field: record[field] for field in ("class_id", "regime_id") if field in record}}


def table(headers, rows):
    return '<div class="table-scroll"><table><thead><tr>' + "".join(
        f"<th>{html.escape(str(value))}</th>" for value in headers
    ) + "</tr></thead><tbody>" + "".join(
        "<tr>" + "".join(f"<td>{html.escape(str(value))}</td>" for value in row) + "</tr>"
        for row in rows
    ) + "</tbody></table></div>"


def render_report(output, query, references, evidence):
    blocks = ["<section><h2>Forced candidates remain uncalibrated</h2>", table(
        ["Representation", "Closest class", "Competitor", "Margin (dB)", "Complete"],
        [[name, ranking["forced_candidate"], ranking["competing_class"],
          number(ranking["margin_db"]), ranking["complete"]]
         for name, ranking in [("Baseline: full band / 1024 samples", evidence["baseline_ranking"]),
                               *evidence["control_rankings"].items(),
                               *[(f"{row['frame_seconds']:g} s / 20-4000 Hz", row)
                                 for row in evidence["rankings"]]]]), "</section>"]
    blocks += ["<section><h2>Class and regime evidence</h2>", table(
        ["Frame (s)", "Class", "Regime", "References", "Acquisitions", "Distance (dB)"],
        [[ranking["frame_seconds"], row["class_id"], regime["regime_id"], regime["references"],
          regime["acquisition_groups"], number(regime["distance_db"])]
         for ranking in evidence["rankings"] for row in ranking["classes"]
         for regime in row["regimes"]]), "</section>"]
    blocks += ["<section><h2>Reference distances</h2>", table(
        ["Reference", "Class", "Regime", "Baseline (dB)", *[
            f"{duration:g} s (dB)" for duration in query["features"]["config"]["frame_seconds"]]],
                [[row["reference_id"], row["class_id"], row["regime_id"],
                    number(row["baseline_distance_db"]),
          *[number(view.get("distance_db")) for view in row["views"]]]
         for row in evidence["comparisons"]]), "</section>"]
    blocks += ["<section><h2>Within-class variability</h2>", table(
        ["Class", "Frame (s)", "Scope", "Pairs", "Cross-acquisition pairs", "Min/median/max dB"],
        [[row["class_id"], row["frame_seconds"], row["scope"], row["pairs"],
          row["cross_acquisition_pairs"], " / ".join(number(row[key]) for key in (
              "min_db", "median_db", "max_db"))] for row in evidence["within_class_variability"]]),
        "</section>"]
    quality_rows = []
    for record in [query, *references]:
        features = record["features"]
        quality = features["quality"]
        for view in features["resolutions"]:
            covered = sum(segment["end_sample_exclusive"] - segment["start_sample"]
                          - segment.get("uncovered_tail_samples", 0)
                          for segment in view["segments"] if segment["status"] == "available")
            quality_rows.append([
                record["id"], view["requested_frame_seconds"], number(quality["rms_fs"], 6),
                number(quality["peak_fs"]), number(quality["near_full_scale_fraction"], 6),
                f"{view['available_segments']}/{view['total_segments']}",
                f"{covered}/{features['sample_count']}",
                number(float(np.mean(view["floored_bin_fraction"])))
                if view["status"] == "available" else "unavailable",
            ])
    blocks += ["<section><h2>Level and coverage evidence</h2>", table(
        ["ID", "Frame (s)", "RMS (FS)", "Peak (FS)", "Near full scale", "Windows", "Samples",
         "Floored bins"], quality_rows), "</section>"]
    image_config = replace(dsp.DspConfig(), image_height=1100)
    (output / "images").mkdir()
    for reference, comparison in zip(references, evidence["comparisons"], strict=True):
        blocks.append(f"<details><summary>{reference['id']} / {reference['class_id']} / "
                      f"{reference['regime_id']}</summary>")
        for index, view in enumerate(comparison["views"]):
            if view["status"] != "available":
                blocks.append(f"<p>{view['frame_seconds']:g} s: {view['reason']}</p>")
                continue
            query_view = query["features"]["resolutions"][index]
            reference_view = reference["features"]["resolutions"][index]
            frequencies = query_view["frequencies_hz"]
            figure, axes = figure_axes(image_config, 4)
            for record_view, color, label in ((query_view, BLUE, query["id"]),
                                               (reference_view, GOLD, reference["id"])):
                axes[0].plot(frequencies, record_view["median_db"], color=color, label=label)
                axes[0].fill_between(frequencies, record_view["q10_db"], record_view["q90_db"],
                                     color=color, alpha=0.15)
            axes[0].set(ylabel="Centered shape (dB)", title=(
                f"{query['id']} vs {reference['id']} / {view['frame_seconds']:g} s / "
                f"distance {view['distance_db']:.3f} dB"))
            axes[0].legend()
            axes[1].plot(frequencies, view["difference_db"], color=BLUE)
            axes[1].set(ylabel="Query - reference (dB)", xlabel="Frequency (Hz)")
            axes[2].bar([f"{band['lower_hz']:g}-{band['upper_hz']:g}" for band in view["bands"]],
                        [band["squared_distance_contribution_db2"] for band in view["bands"]],
                        color=BLUE)
            axes[2].set(ylabel="Contribution (dB squared)", xlabel="Band (Hz)")
            starts = [segment["start_sample"] / query["features"]["sample_rate"]
                      for segment in query_view["segments"] if segment["status"] == "available"]
            axes[3].plot(starts, view["query_segment_distance_db"], color=BLUE, marker="o")
            axes[3].set(ylabel="Window distance (dB)", xlabel="Query window start (s)")
            image_path = output / "images" / f"{reference['id']}-{index}.png"
            save_figure(figure, image_path, "Pairwise shape evidence", "", image_config)
            encoded = base64.b64encode(image_path.read_bytes()).decode("ascii")
            blocks.append(f'<figure><img width="1200" height="1100" alt="{reference["id"]} '
                          f'{view["frame_seconds"]:g} s comparison" src="data:image/png;base64,'
                          f'{encoded}"><figcaption>10th-90th window quantiles; '
                          f'bin spacing {query_view["bin_spacing_hz"]:g} Hz; Hann bandwidth '
                          f'{query_view["hann_enbw_hz"]:g} Hz. Correlated windows; '
                          'quantiles are not confidence intervals.</figcaption></figure>')
        blocks.append("</details>")
    text = ("<!doctype html><html lang='en'><head><meta charset='utf-8'>"
            "<meta name='viewport' content='width=device-width,initial-scale=1'>"
            f"<title>Multi-reference DSP comparison</title>{THEME}<style>{STYLE}</style></head>"
            "<body><header><h1>Multi-reference DSP comparison</h1>"
            "<p>Measured spectral comparisons; diagnostic correctness unmeasured. "
            "No calibrated acceptance or rejection decision.</p>"
            f"<p>Query {query['id']}; {len(references)} references; "
            f"{evidence['class_count']} classes. Resolution disagreement: "
            f"{evidence['diagnostic_disagreement']}. Unequal bank sizes: "
            f"{evidence['unequal_bank_sizes']}.</p></header><main>"
            + "".join(blocks) + "</main></body></html>")
    (output / "report.html").write_text(text, encoding="utf-8")


def execute(spec, output, root, config=None, replay=None):
    config = config or ShapeConfig()
    if spec.keys() != {"schema", "references", "query"} or spec["schema"] != 1:
        raise ValueError("Expected schema, references and query only.")
    output = Path(output)
    output.mkdir(parents=True, exist_ok=False)
    started = time.perf_counter()
    write_json(output / "attempt.json", {"status": "started", "model_calls": 0})
    try:
        (output / "audit").mkdir()
        write_json(output / "audit/spec.json", spec)
        code = {
            Path(module.__file__).relative_to(Path(__file__).resolve().parents[1]).as_posix():
            digest(module.__file__) for module in (dsp, dsp_comparison, dsp_report, visual_audio)
        }
        code["scripts/dsp_compare_offline.py"] = digest(__file__)
        registration = {"schema": 1, "config": asdict(config), "code_sha256": code,
                        "spec_sha256": digest(output / "audit/spec.json"),
                        "runtime": {name: version(name) for name in (
                            "numpy", "scipy", "soundfile", "matplotlib", "pillow")},
                        "scope": "offline_exploratory_no_threshold_fitting",
                        "acceptance_rejection_correctness": "unmeasured", "model_calls": 0}
        if replay is not None:
            write_json(output / "audit/replay.json", replay)
            registration["replay_sha256"] = digest(output / "audit/replay.json")
        write_json(output / "registration.json", registration)
        if not 1 <= len(spec["references"]) <= 64:
            raise ValueError("A bank requires 1 to 64 references.")
        references, provenances = [], {}
        for item in spec["references"]:
            if not {"class_id", "regime_id"} <= item.keys():
                raise ValueError("Every reference requires class and regime identifiers.")
            record, provenance = load_record(item, root, config)
            references.append(record)
            provenances[record["id"]] = provenance
        if {"class_id", "regime_id"} & spec["query"].keys():
            raise ValueError("Query labels are excluded from the comparison input.")
        query, provenance = load_record(spec["query"], root, config)
        provenances[query["id"]] = provenance
        evidence = compare_bank(query, references)
        write_json(output / "evidence.json", evidence)
        write_json(output / "features.json", [public_features(record)
                                             for record in [query, *references]])
        render_report(output, query, references, evidence)
        if replay is not None:
            rows = []
            for item in replay["queries"]:
                current, provenance = load_record(item, root, config)
                provenances[current["id"]] = provenance
                for bank_name, bank in (("seed", references[:4]), ("expanded", references)):
                    measured = compare_bank(current, bank)
                    for representation, ranking in [
                        ("baseline", measured["baseline_ranking"]),
                        *measured["control_rankings"].items(),
                        *[(str(row["frame_seconds"]), row) for row in measured["rankings"]],
                    ]:
                        rows.append({"query_id": current["id"], "bank": bank_name,
                                     "representation": representation,
                                     "candidate": ranking["forced_candidate"],
                                     "margin_db": ranking["margin_db"]})
            write_json(output / "predictions.json", rows)
            truth_path = Path(replay["truth_path"])
            if digest(truth_path) != replay["truth_sha256"]:
                raise ValueError("Evaluator truth changed after registration.")
            truth = read_json(truth_path)
            scores = []
            for bank in ("seed", "expanded"):
                for representation in ("baseline", *query["features"]["controls"],
                                       *map(str, config.frame_seconds)):
                    selected = [row for row in rows if row["bank"] == bank
                                and row["representation"] == representation]
                    groups = {item["group_id"] for item in replay["queries"]}
                    query_groups = {item["id"]: item["group_id"] for item in replay["queries"]}
                    if not selected or len({row["query_id"] for row in selected}) != len(
                        replay["queries"]
                    ):
                        raise ValueError("Scoring requires one prediction per registered query.")
                    scores.append({"bank": bank, "representation": representation,
                                   "queries": len(selected),
                                   "acquisition_groups": len(groups),
                                   "all_windows_correct_groups": sum(all(
                                       row["candidate"] == truth[row["query_id"]]["condition_id"]
                                       for row in selected if query_groups[row["query_id"]] == group
                                   ) for group in groups),
                                   "correct_forced_label": sum(row["candidate"] == truth[
                                       row["query_id"]]["condition_id"] for row in selected),
                                   "wrong_forced_label": sum(row["candidate"] is not None and row[
                                       "candidate"] != truth[row["query_id"]]["condition_id"]
                                       for row in selected),
                                   "unavailable_or_tied": sum(row["candidate"] is None
                                                              for row in selected)})
            write_json(output / "scores.json", {
                "scope": "previously_consumed_Jin_exploratory_replay",
                "query_acquisitions": len({item["group_id"] for item in replay["queries"]}),
                "reference_labels_seed": 4, "reference_labels_expanded": len(references),
                "prediction_sha256": digest(output / "predictions.json"), "scores": scores,
                "recognition_with_rejection": "unmeasured", "human_enrichment": "not_executed",
            })
        write_json(output / "audit/provenance.json", provenances)
        root_path = Path(__file__).resolve().parents[1]
        if any(digest(root_path / name) != expected for name, expected in code.items()):
            raise ValueError("Implementation changed during the offline attempt.")
        write_json(output / "attempt.json", {"status": "completed", "model_calls": 0,
                                             "elapsed_seconds": time.perf_counter() - started})
        write_json(output / "manifest.json", {"files": {
            path.relative_to(output).as_posix(): digest(path)
            for path in sorted(output.rglob("*")) if path.is_file()}})
        return evidence
    except Exception as error:
        write_json(output / "attempt.json", {"status": "failed", "model_calls": 0,
                                             "error_type": type(error).__name__})
        raise


def jin_replay(folder):
    protocol_path = folder / "protocol.json"
    truth_path = folder / "sealed/truth.json"
    registration = read_json(folder / "registration.json")
    if (digest(protocol_path) != registration["protocol_sha256"]
            or digest(truth_path) != registration["truth_sha256"]):
        raise ValueError("Historical registration hashes do not match.")
    protocol = read_json(protocol_path)
    truth = read_json(truth_path)
    if protocol["dataset"] != "10.17632/9dpmkgpncw.1":
        raise ValueError("This fixed replay requires the Jin registration.")
    support = read_json(Path("data/jin-directions-v1/support/manifest.json"))["examples"]

    def input_record(item):
        return {field: item[field] for field in ("id", "wav", "audio_sha256", "group_id")} | {
            "channel": 0}

    references = []
    for item in protocol["known"]:
        source = next(row for row in support if row["audio_sha256"] == item["audio_sha256"])
        references.append({**input_record({**item, "group_id": source["group_id"]}),
                           "class_id": item["condition_id"], "regime_id": "M01"})
    additions = [item for item in protocol["queries"] if item["role"] == "development"
                 and truth[item["id"]]["offset_seconds"] == 0]
    references.extend({**input_record(item), "class_id": truth[item["id"]]["condition_id"],
                       "regime_id": "M02"} for item in additions)
    queries = [input_record(item) for item in protocol["queries"] if item["role"] == "final"]
    if len(references) != 8 or len(queries) != 12:
        raise ValueError("Expected four front/four left references and twelve right queries.")
    return {"schema": 1, "references": references, "query": queries[0]}, {
        "queries": queries, "truth_path": str(truth_path.resolve()),
        "truth_sha256": digest(truth_path), "source_protocol_sha256": digest(protocol_path),
        "allocation": "front_0s_seed; left_0s_additions; right_0_120_240s_queries",
        "query_labels_used_for_selection": False,
        "reference_label_origin": "simulated_human_from_publisher",
        "regimes": "M01=front, M02=left; acquisition direction, not inferred mechanical regime",
    }


def main():
    parser = argparse.ArgumentParser(description="Offline DSP comparison; no model execution.")
    choice = parser.add_mutually_exclusive_group(required=True)
    choice.add_argument("--spec", type=Path)
    choice.add_argument("--jin-replay", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.jin_replay:
        spec, replay = jin_replay(args.jin_replay)
        execute(spec, args.output, Path.cwd(), replay=replay)
    else:
        execute(read_json(args.spec), args.output, args.spec.resolve().parent)
    print(json.dumps({"report": str(args.output / "report.html"), "model_calls": 0}))


if __name__ == "__main__":
    main()