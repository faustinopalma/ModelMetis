import argparse
import hashlib
import json
import platform
import sqlite3
import sys
import tarfile
import time
from contextlib import contextmanager
from dataclasses import asdict
from datetime import UTC, datetime
from pathlib import Path

import numpy as np

from modelmetis import visual_audio as visual

ROOT = Path(__file__).resolve().parents[1]
CONDITIONS = {"N": "C01", "MF1": "C02", "PC1": "C03"}
ARCHIVE_HASHES = {
    "A": "b3c6e3e1bc7ecd2c487dee154784fdb302634550118d33b923f010ef8616ad93",
    "B": "c8b20399eda5662f61e4a1483c57bfba666b4ff773678a4ae1eedb89252e8343",
}


def digest(path):
    with Path(path).open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def write_json(path, value):
    Path(path).write_bytes(visual.canonical_json(value))


def read_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


@contextmanager
def attempt(output, operation):
    started = time.perf_counter()
    entry = {"operation": operation, "started_utc": datetime.now(UTC).isoformat()}
    try:
        yield
        entry["status"] = "completed"
    except Exception as error:
        entry.update(status="failed", error_type=type(error).__name__, error=str(error))
        raise
    finally:
        entry["elapsed_seconds"] = time.perf_counter() - started
        with (Path(output) / "attempts.jsonl").open("ab") as stream:
            stream.write(visual.canonical_json(entry) + b"\n")
        print(json.dumps(entry), flush=True)


def load_config(path):
    config = visual.RenderConfig(**read_json(path))
    config.validate()
    return config


def prepare_drone(source, inventory, output, config):
    output = Path(output)
    output.mkdir(parents=True, exist_ok=False)
    registration_text = (ROOT / "docs/VISUAL_AUDIO_EXPERIMENT.md").read_text(
        encoding="utf-8",
    ).split("## Reproduction")[0]
    registration = {
        "experiment": "EXP-011", "registered_utc": datetime.now(UTC).isoformat(),
        "protocol": registration_text, "config": asdict(config),
        "config_sha256": config.sha256, "runner_sha256": digest(__file__),
        "renderer_sha256": digest(visual.__file__),
        "prompt_sha256": hashlib.sha256(visual.PROMPT.encode()).hexdigest(),
        "runtime": {"python": sys.version, "machine": platform.machine()},
        "conditions": CONDITIONS, "physical_split": {"A": "support", "B": "query"},
        "schedule": ["all_known", "without_C01", "without_C02", "without_C03"],
        "numeric": {"max_distance_db": 12.0, "min_margin_db": 2.0},
        "source_archive_sha256": ARCHIVE_HASHES, "confirmation_C_access": False,
        "promotion": "not_authorized", "live_calls": "blocked_no_verified_deployment",
    }
    write_json(output / "registration.json", registration)
    with attempt(output, "prepare_source_audio"):
        database = Path(inventory) / "restricted.sqlite"
        database_hash = digest(database)
        with sqlite3.connect(database.resolve().as_uri() + "?mode=ro", uri=True) as connection:
            connection.row_factory = sqlite3.Row
            query = """
                WITH paired AS (
                    SELECT drone, maneuver, fault, source_index, background, background_index, snr
                    FROM clips
                    WHERE drone IN ('A', 'B') AND fault IN ('N', 'MF1', 'PC1') AND maneuver = 'F'
                    GROUP BY drone, maneuver, fault, source_index, background, background_index, snr
                    HAVING count(*) = 2 AND count(DISTINCT mic) = 2
                ), candidates AS (
                    SELECT clips.*, row_number() OVER (
                        PARTITION BY drone, fault ORDER BY pcm_sha256, path
                    ) AS choice
                    FROM clips JOIN paired
                    USING (drone, maneuver, fault, source_index, background, background_index, snr)
                    WHERE mic = 'mic1'
                ) SELECT * FROM candidates WHERE choice = 1 ORDER BY drone, fault
            """
            chosen = [dict(row) for row in connection.execute(query)]
        if {(row["drone"], row["fault"]) for row in chosen} != {
            (drone, condition) for drone in "AB" for condition in CONDITIONS
        } or len(chosen) != 6:
            raise ValueError("The registered six source cells are not available.")
        selected = {row["path"]: row for row in chosen}
        (output / "audio").mkdir()
        (output / "sealed").mkdir()
        sources, masked, supports, queries, seen_pcm = [], [], [], [], set()
        for drone in "AB":
            archive_path = Path(source) / f"drone_{drone}.tar"
            with attempt(output, f"verify_and_extract_{drone}"):
                if digest(archive_path) != ARCHIVE_HASHES[drone]:
                    raise ValueError("Source archive SHA-256 changed; no reselection.")
                with tarfile.open(archive_path, "r|") as archive:
                    for member in archive:
                        if member.name not in selected:
                            continue
                        if not member.isfile() or member.size > 1_000_000:
                            raise ValueError("Unexpected selected archive member.")
                        row = selected.pop(member.name)
                        with archive.extractfile(member) as stream:
                            payload = stream.read()
                        identifier = hashlib.sha256(payload).hexdigest()[:24]
                        local_path = Path("audio") / f"{identifier}.wav"
                        (output / local_path).write_bytes(payload)
                        samples, metadata = visual.decode_audio(output / local_path, config)
                        if (samples.shape != (8000,) or metadata["source_sample_rate"] != 16000
                                or metadata["source_channels"] != 1
                                or metadata["transformations"]):
                            raise ValueError("Unexpected registered source format.")
                        integer_hash = hashlib.sha256(
                            np.rint(samples * 2 ** 31).astype("<i4").tobytes(),
                        ).hexdigest()
                        if integer_hash != row["pcm_sha256"] or integer_hash in seen_pcm:
                            raise ValueError("Source inventory mismatch or duplicate PCM.")
                        seen_pcm.add(integer_hash)
                        split = "support" if drone == "A" else "query"
                        group_id = "G01" if drone == "A" else "G02"
                        record = {"path": local_path.as_posix(), "recording_id": identifier,
                                  "group_id": group_id, "split": split}
                        masked.append(record)
                        condition_id = CONDITIONS[row["fault"]]
                        sources.append({**record, **metadata, "condition_id": condition_id,
                                        "source_inventory": row})
                        if split == "support":
                            supports.append({"condition_id": condition_id,
                                             "recording_id": identifier})
                        else:
                            queries.append(identifier)
        if selected or digest(database) != database_hash:
            raise ValueError("Incomplete extraction or changed inventory.")
        masked.sort(key=lambda row: row["recording_id"])
        write_json(output / "manifest.json", masked)
        write_json(output / "inputs.json", {"supports": sorted(
            supports, key=lambda row: row["condition_id"],
        ), "queries": sorted(queries)})
        write_json(output / "sealed/sources.json", sources)
        write_json(output / "audit.json", {
            "status": "completed", "recordings": 6, "physical_groups": 2,
            "source_inventory_sha256": database_hash, "independent_take_count": None,
            "registration_sha256": digest(output / "registration.json"),
            "files": {name: digest(output / name) for name in
                      ("manifest.json", "inputs.json", "sealed/sources.json")},
        })
    return output


def verify_prepared(prepared, config):
    registration = read_json(prepared / "registration.json")
    audit = read_json(prepared / "audit.json")
    if (audit["status"] != "completed"
            or audit["registration_sha256"] != digest(prepared / "registration.json")
            or registration["config_sha256"] != config.sha256
            or registration["runner_sha256"] != digest(__file__)
            or registration["renderer_sha256"] != digest(visual.__file__)):
        raise ValueError("Frozen configuration, code or registration changed.")
    for name, expected in audit["files"].items():
        if digest(prepared / name) != expected:
            raise ValueError("Prepared manifest integrity mismatch.")
    return registration


def compare_offline(prepared, output, config):
    prepared, output = Path(prepared), Path(output)
    output.mkdir(parents=True, exist_ok=False)
    with attempt(output, "offline_comparison"):
        registration = verify_prepared(prepared, config)
        records = read_json(prepared / "manifest.json")
        for row in records:
            row["path"] = str(prepared / row["path"])
        with attempt(output, "render_six_original_clips"):
            rendered = visual.render_recordings(records, output / "images", config)
        render_map = {row["recording_id"]: row for row in rendered["recordings"]}
        if any(len(row["windows"]) != 1 for row in render_map.values()):
            raise ValueError("The registered experiment requires exactly one window per clip.")
        inputs = read_json(prepared / "inputs.json")
        features, pngs = {}, {}
        with attempt(output, "extract_numerical_features"):
            for row in records:
                samples, metadata = visual.decode_audio(row["path"], config)
                rendered_row = render_map[row["recording_id"]]
                if metadata["source_sha256"] != rendered_row["source_sha256"]:
                    raise ValueError("Source changed after rendering.")
                features[row["recording_id"]] = visual.welch_features(samples, config)
                window = rendered_row["windows"][0]
                image_path = output / "images" / window["image"]
                if digest(image_path) != window["image_sha256"]:
                    raise ValueError("Rendered image hash mismatch.")
                pngs[row["recording_id"]] = image_path.read_bytes()
        (output / "messages").mkdir()
        predictions, payloads = [], []
        for fold in registration["schedule"]:
            omitted = None if fold == "all_known" else fold.removeprefix("without_")
            visible = [row for row in inputs["supports"] if row["condition_id"] != omitted]
            reference_features = {row["condition_id"]: features[row["recording_id"]]
                                  for row in visible}
            for query_id in inputs["queries"]:
                started = time.perf_counter()
                decision = visual.numerical_decision(
                    features[query_id], reference_features, **registration["numeric"],
                )
                predictions.append({
                    "fold": fold, "recording_id": query_id,
                    "group_id": render_map[query_id]["group_id"],
                    "visible_ids": [row["condition_id"] for row in visible],
                    "distances_db": decision.pop("distances_db"), "decision": decision,
                    "elapsed_seconds": time.perf_counter() - started,
                })
                messages = visual.image_messages([
                    (row["condition_id"], pngs[row["recording_id"]]) for row in visible
                ], pngs[query_id], config)
                message_name = f"{fold}-{query_id}.json"
                write_json(output / "messages" / message_name, {"messages": messages})
                payloads.append({"fold": fold, "recording_id": query_id,
                                 "messages_sha256": digest(output / "messages" / message_name),
                                 "image_count": len(visible) + 1, "submitted": False})
        write_json(output / "numerical-predictions.json", predictions)
        write_json(output / "prepared-payloads.json", payloads)
        write_json(output / "binding.json", {
            "registration_sha256": digest(prepared / "registration.json"),
            "render_manifest_sha256": digest(output / "images/manifest.json"),
            "predictions_sha256": digest(output / "numerical-predictions.json"),
            "payloads_sha256": digest(output / "prepared-payloads.json"),
        })
        return predictions


def evaluate(prepared, run, output, config):
    prepared, run, output = Path(prepared), Path(run), Path(output)
    output.mkdir(parents=True, exist_ok=False)
    with attempt(output, "sealed_evaluation"):
        verify_prepared(prepared, config)
        bindings = read_json(run / "binding.json")
        if (bindings["registration_sha256"] != digest(prepared / "registration.json")
                or bindings["predictions_sha256"] != digest(run / "numerical-predictions.json")
                or bindings["render_manifest_sha256"] != digest(run / "images/manifest.json")
                or bindings["payloads_sha256"] != digest(run / "prepared-payloads.json")):
            raise ValueError("Evaluation integrity mismatch.")
        sources = read_json(prepared / "sealed/sources.json")
        labels = {row["recording_id"]: row["condition_id"] for row in sources
                  if row["split"] == "query"}
        source_hashes = {row["recording_id"]: row["source_sha256"] for row in sources}
        rendered = read_json(run / "images/manifest.json")
        for row in rendered["recordings"]:
            if row["source_sha256"] != source_hashes[row["recording_id"]]:
                raise ValueError("Rendered original differs from the sealed preparation.")
        predictions = read_json(run / "numerical-predictions.json")
        expected_trials = {(fold, identifier) for fold in
                           ("all_known", "without_C01", "without_C02", "without_C03")
                           for identifier in labels}
        if (len(predictions) != 12 or {(row["fold"], row["recording_id"])
                                      for row in predictions} != expected_trials):
            raise ValueError("Incomplete or duplicate evaluation trials.")
        rows = [{**row, "truth": labels[row["recording_id"]]} for row in predictions]
        aggregate = {
            "experiment": "EXP-011", "status": "blocked_visual_access_offline_complete",
            "verdict": "inconclusive_no_real_visual_comparison",
            "numeric": visual.evaluate_predictions(rows),
            "by_fold": {fold: visual.evaluate_predictions([
                row for row in rows if row["fold"] == fold
            ]) for fold in ("all_known", "without_C01", "without_C02", "without_C03")},
            "visual": {"status": "not_run_no_verified_deployment", "submitted_requests": 0,
                       "technical_inference_failures": 0, "prepared_requests": 12,
                       "prepared_image_instances": 39, "unique_images": 6,
                       "tokens": None, "latency_seconds": None, "inference_cost_usd": 0,
                       "cost_basis": "No inference requests sent; no billable token usage.",
                       "candidate_pricing": "not_verified_not_used_for_an_estimate"},
            "human_work": {"publisher_reference_labels_used": 3,
                           "new_human_diagnoses": 0, "extra_calibration_labels": 0,
                           "query_corrections": 0, "physical_verifications": 0,
                           "human_minutes": None,
                           "note": "Elapsed automation time is not measured human labor."},
            "observed_seconds": {
                "render": rendered["elapsed_seconds"],
                "numerical_decisions_total": sum(row["elapsed_seconds"] for row in predictions),
                "numerical_decision_median": float(np.median([
                    row["elapsed_seconds"] for row in predictions
                ])),
            },
            "quality": [{"split": row["split"], "windows": len(row["windows"]),
                         "silence_windows": sum(item["silence"] for item in row["windows"]),
                         "clipped_samples": sum(item["clipped_samples"] for item in row["windows"]),
                         "valid_seconds": sum(item["valid_samples"] for item in row["windows"])
                         / config.sample_rate} for row in rendered["recordings"]],
            "bindings": bindings, "confirmation_C_access": False,
            "promotion": "not_authorized", "independence": "Two physical groups; one query unit; "
            "unknown take lineage; no independent-acquisition population inference.",
        }
        write_json(output / "aggregate.json", aggregate)
        return aggregate


def main():
    parser = argparse.ArgumentParser(description="STFT-only audio rendering and offline EXP-011.")
    parser.add_argument("command", choices=[
        "render", "prepare-drone", "compare-offline", "evaluate",
    ])
    parser.add_argument("--config", type=Path, default=ROOT / "configs/visual-audio-stft-v1.json")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--manifest", type=Path)
    parser.add_argument("--source", type=Path, default=ROOT / "data/drone-source-v1")
    parser.add_argument("--inventory", type=Path, default=ROOT / "artifacts/drone-audit-v5")
    parser.add_argument("--prepared", type=Path)
    parser.add_argument("--run", type=Path)
    args = parser.parse_args()
    config = load_config(args.config)
    if args.command == "render":
        if not args.manifest:
            parser.error("render requires --manifest")
        records = read_json(args.manifest)
        for row in records:
            row["path"] = str(args.manifest.parent / row["path"])
        visual.render_recordings(records, args.output, config)
    elif args.command == "prepare-drone":
        prepare_drone(args.source, args.inventory, args.output, config)
    else:
        if not args.prepared:
            parser.error("comparison/evaluation requires --prepared")
        if args.command == "compare-offline":
            compare_offline(args.prepared, args.output, config)
        else:
            if not args.run:
                parser.error("evaluate requires --run")
            evaluate(args.prepared, args.run, args.output, config)


if __name__ == "__main__":
    started = time.perf_counter()
    try:
        main()
    finally:
        print(f"CommandElapsedSeconds={time.perf_counter() - started:.6f}", flush=True)