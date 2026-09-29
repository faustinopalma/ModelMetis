import argparse
import copy
import json
import subprocess
import sys
import time
from datetime import UTC, datetime
from pathlib import Path

import numpy as np
import soundfile as sf

from modelmetis import dsp_inference, dsp_packet
from modelmetis.dsp import DspConfig
from modelmetis.dsp_packet import comparison_messages, make_packet, response_schema
from modelmetis.dsp_report import digest, generate_report
from modelmetis.visual_audio import canonical_json, evaluate_predictions

ROOT = Path(__file__).resolve().parents[1]


def read_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def write_json(path, value):
    Path(path).write_bytes(canonical_json(value))


def job_for(references, query, settings):
    body = {
        "model": settings["deployment"],
        "messages": comparison_messages(references, query),
        "reasoning_effort": settings["reasoning_effort"],
        "max_completion_tokens": settings["max_completion_tokens"],
        "response_format": response_schema(list(references)),
    }
    packets = [*references.values(), query]
    evidence_ids = [
        identifier
        for packet in packets
        for identifier in [
            packet["model"]["measurement_id"],
            *(image["evidence_id"] for image in packet["model"]["images"]),
        ]
    ]
    text_bytes = sum(
        len(item["text"].encode())
        for item in body["messages"][1]["content"]
        if item["type"] == "text"
    )
    return {
        "body": body,
        "body_sha256": dsp_packet.digest(canonical_json(body)),
        "allowed_ids": list(references),
        "evidence_ids": evidence_ids,
        "image_count": sum(len(packet["figures"]) for packet in packets),
        "text_bytes": text_bytes,
        "request_bytes": len(canonical_json(body)),
        "packet_audit": {packet["model"]["id"]: packet["audit"] for packet in packets},
    }


def prepare(output, source, settings_path):
    output, source = Path(output), Path(source)
    output.mkdir(parents=True, exist_ok=False)
    started = time.perf_counter()
    status = {"status": "running", "started_utc": datetime.now(UTC).isoformat()}
    try:
        settings = read_json(settings_path)
        config = DspConfig(**read_json(ROOT / "configs/dsp-report-v1.json"))
        audit = read_json(source / "audit.json")
        if audit["status"] != "completed" or audit["registration_sha256"] != digest(
            source / "registration.json"
        ):
            raise ValueError("Original source registration is not intact.")
        for name, expected in audit["files"].items():
            if digest(source / name) != expected:
                raise ValueError("Original prepared source metadata changed.")
        records = read_json(source / "manifest.json")
        inputs = read_json(source / "inputs.json")
        sealed = read_json(source / "sealed/sources.json")
        original_hashes = {row["recording_id"]: row["source_sha256"] for row in sealed}
        if len(records) != 6 or len(inputs["supports"]) != 3 or len(inputs["queries"]) != 3:
            raise ValueError("Expected the six frozen A/B sources.")
        registration = {
            "experiment": "EXP-012",
            "created_utc": datetime.now(UTC).isoformat(),
            "protocol": (ROOT / "docs/DSP_LLM_PROTOCOL.md")
            .read_text(encoding="utf-8")
            .split("## Execution Record")[0],
            "source_registration_sha256": digest(source / "registration.json"),
            "settings": settings,
            "settings_sha256": digest(settings_path),
            "code": {
                "runner": digest(__file__),
                "packet": digest(dsp_packet.__file__),
                "worker": digest(dsp_inference.__file__),
            },
            "jobs": [],
            "probe": {},
            "truth": {},
        }
        (output / "settings.json").write_bytes(Path(settings_path).read_bytes())
        write_json(output / "registration-draft.json", registration)
        (output / "reports").mkdir()
        (output / "jobs").mkdir()
        (output / "sealed").mkdir()
        report_paths = {}
        for index, row in enumerate(records, 1):
            audio = source / row["path"]
            if digest(audio) != original_hashes[row["recording_id"]]:
                raise ValueError("Original audio bytes changed.")
            target = output / "reports" / f"R{index:04}"
            generate_report(audio, target, config, f"R{index:04}", "original")
            report_paths[row["recording_id"]] = target
        references = {
            row["condition_id"]: make_packet(report_paths[row["recording_id"]], f"R{index:02}")
            for index, row in enumerate(inputs["supports"], 1)
        }
        source_map = {row["recording_id"]: row for row in records}
        schedule = [None, "C01", "C02", "C03"]
        for omitted in schedule:
            visible = {
                identifier: packet
                for identifier, packet in references.items()
                if identifier != omitted
            }
            fold = "all_known" if omitted is None else f"without_{omitted}"
            for query_id in inputs["queries"]:
                query = make_packet(report_paths[query_id], "Q01")
                reference_groups = {
                    source_map[row["recording_id"]]["group_id"] for row in inputs["supports"]
                }
                if source_map[query_id]["group_id"] in reference_groups:
                    raise ValueError("Physical source group crosses query/reference roles.")
                job = job_for(visible, query, settings)
                job.update(
                    fold=fold, recording_id=query_id, group_id=source_map[query_id]["group_id"]
                )
                name = f"jobs/{len(registration['jobs']) + 1:02}.json"
                write_json(output / name, job)
                registration["jobs"].append(
                    {
                        "path": name,
                        "sha256": digest(output / name),
                        "fold": fold,
                        "recording_id": query_id,
                        "image_count": job["image_count"],
                        "text_bytes": job["text_bytes"],
                        "request_bytes": job["request_bytes"],
                    }
                )
        truth = {
            row["recording_id"]: row["condition_id"] for row in sealed if row["split"] == "query"
        }
        write_json(output / "sealed/truth.json", truth)
        registration["truth"] = {
            "path": "sealed/truth.json",
            "sha256": digest(output / "sealed/truth.json"),
        }
        (output / "synthetic").mkdir()
        synthetic = []
        for index, (frequency, amplitude) in enumerate([(500, 0.1), (1500, 0.1), (500, 0.12)], 1):
            audio = output / "synthetic" / f"R{index:04}.wav"
            samples = amplitude * np.sin(2 * np.pi * frequency * np.arange(8000) / 16000)
            sf.write(audio, samples, 16000, subtype="PCM_24")
            target = output / "synthetic" / f"R{index:04}"
            generate_report(audio, target, config, f"R{index:04}", "original")
            synthetic.append(make_packet(target, f"R{index:02}" if index < 3 else "Q01"))
        probe = job_for({"C01": synthetic[0], "C02": synthetic[1]}, synthetic[2], settings)
        write_json(output / "jobs/probe.json", probe)
        registration["probe"] = {
            "path": "jobs/probe.json",
            "sha256": digest(output / "jobs/probe.json"),
            "expected_condition": "C01",
        }
        write_json(output / "registration.json", registration)
        status.update(status="completed", registration_sha256=digest(output / "registration.json"))
    except Exception as error:
        status.update(status="failed", error_type=type(error).__name__, error=str(error))
        raise
    finally:
        status["elapsed_seconds"] = time.perf_counter() - started
        write_json(output / "preparation.json", status)
        print(json.dumps(status), flush=True)


def verify_prepared(prepared):
    prepared = Path(prepared)
    receipt = read_json(prepared / "preparation.json")
    registration = read_json(prepared / "registration.json")
    if (
        receipt["status"] != "completed"
        or receipt["registration_sha256"] != digest(prepared / "registration.json")
        or registration["settings_sha256"] != digest(prepared / "settings.json")
        or registration["code"]
        != {
            "runner": digest(__file__),
            "packet": digest(dsp_packet.__file__),
            "worker": digest(dsp_inference.__file__),
        }
    ):
        raise ValueError("Frozen experiment code, settings or registration changed.")
    for binding in [*registration["jobs"], registration["probe"], registration["truth"]]:
        if digest(prepared / binding["path"]) != binding["sha256"]:
            raise ValueError("Frozen job or sealed truth file changed.")
    return registration


def worker(job, settings_path, output, timeout):
    started = time.perf_counter()
    try:
        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "modelmetis.dsp_inference",
                "--job",
                str(job),
                "--settings",
                str(settings_path),
                "--output",
                str(output),
            ],
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
        if result.returncode and not (output / "attempt.json").exists():
            raise RuntimeError("Worker exited before creating its attempt record.")
        attempt = read_json(output / "attempt.json")
    except subprocess.TimeoutExpired:
        previous = read_json(output / "attempt.json") if (output / "attempt.json").exists() else {}
        output.mkdir(parents=True, exist_ok=True)
        write_json(output / "interrupted-worker.json", previous)
        attempt = {
            "status": "failed",
            "error_type": "ProcessDeadline",
            "http_attempts": previous.get("http_attempts", 0),
            "estimated_cost_usd": None,
            "elapsed_seconds": time.perf_counter() - started,
            "error": "Worker terminated at deadline; server outcome may be unknown.",
        }
        write_json(output / "attempt.json", attempt)
    print(
        json.dumps(
            {
                key: attempt.get(key)
                for key in ("status", "http_attempts", "elapsed_seconds", "estimated_cost_usd")
            }
        ),
        flush=True,
    )
    return attempt


def run(prepared, output, phase):
    prepared, output = Path(prepared), Path(output)
    registration = verify_prepared(prepared)
    settings = registration["settings"]
    if phase == "probe":
        output.mkdir(parents=True, exist_ok=False)
        write_json(
            output / "binding.json", {"registration_sha256": digest(prepared / "registration.json")}
        )
        result = worker(
            prepared / registration["probe"]["path"],
            prepared / "settings.json",
            output / "probe",
            settings["request_process_timeout_seconds"],
        )
        success = (
            result["status"] == "completed"
            and result["decision"]["outcome"] == "known"
            and result["decision"]["condition_id"] == registration["probe"]["expected_condition"]
        )
        write_json(output / "probe-gate.json", {"passed": success, "diagnostic_evidence": False})
        if not success:
            raise ValueError("Synthetic transport/format gate failed; no real requests authorized.")
        return
    if (
        read_json(output / "binding.json")["registration_sha256"]
        != digest(prepared / "registration.json")
        or not read_json(output / "probe-gate.json")["passed"]
    ):
        raise ValueError("Live probe has not passed for this registration.")
    suite = output / "real"
    suite.mkdir(exist_ok=False)
    if len(registration["jobs"]) > settings["max_real_requests"]:
        raise ValueError("Registered request count exceeds the bound.")
    started = time.perf_counter()
    records = []
    for index, entry in enumerate(registration["jobs"], 1):
        if (
            time.perf_counter() - started + settings["request_process_timeout_seconds"]
            > settings["run_deadline_seconds"]
        ):
            break
        result = worker(
            prepared / entry["path"],
            prepared / "settings.json",
            suite / f"{index:02}",
            settings["request_process_timeout_seconds"],
        )
        records.append({"job": entry["path"], "result": result})
        write_json(output / "results.json", records)
        if result["status"] != "completed":
            break
    write_json(
        output / "run-summary.json",
        {
            "attempted": len(records),
            "unsent": len(registration["jobs"]) - len(records),
            "elapsed_seconds": time.perf_counter() - started,
        },
    )


def evaluate(prepared, run_path, output):
    prepared, run_path, output = Path(prepared), Path(run_path), Path(output)
    registration = verify_prepared(prepared)
    output.mkdir(parents=True, exist_ok=False)
    truth = read_json(prepared / registration["truth"]["path"])
    results = read_json(run_path / "results.json")
    rows = []
    for item in results:
        job = read_json(prepared / item["job"])
        result = item["result"]
        row = {
            "truth": truth[job["recording_id"]],
            "recording_id": job["recording_id"],
            "group_id": job["group_id"],
            "fold": job["fold"],
            "visible_ids": job["allowed_ids"],
        }
        if result["status"] == "completed":
            row["decision"] = {
                key: result["decision"][key] for key in ("outcome", "condition_id", "explanation")
            }
        else:
            row["technical_failure"] = True
        rows.append(row)
    attempts = [read_json(run_path / "probe/attempt.json"), *(item["result"] for item in results)]
    costs = [
        item["estimated_cost_usd"] for item in attempts if item["estimated_cost_usd"] is not None
    ]
    aggregate = {
        "experiment": "EXP-012",
        "metrics": evaluate_predictions(rows),
        "unsent": len(registration["jobs"]) - len(results),
        "by_fold": {
            fold: evaluate_predictions([row for row in rows if row["fold"] == fold])
            for fold in ("all_known", "without_C01", "without_C02", "without_C03")
        },
        "estimated_known_cost_usd_including_probe": sum(costs),
        "unknown_cost_attempts": len(attempts) - len(costs),
        "attempts_including_probe": len(attempts),
        "promotion": "not_authorized",
        "verdict": "exploratory_no_deployment_quality_gate",
        "settings": copy.deepcopy(registration["settings"]),
        "registration_sha256": digest(prepared / "registration.json"),
        "human_work": {
            "publisher_reference_labels": 3,
            "extra_calibration_labels": 0,
            "new_diagnoses": 0,
            "human_minutes": None,
        },
        "model_http_seconds": [item.get("model_http_seconds") for item in attempts],
        "tokens": [item.get("usage") for item in attempts],
        "independence": "One query drone, three clips reused across folds; no IID inference.",
    }
    write_json(output / "aggregate.json", aggregate)
    write_json(output / "evaluated-rows.json", rows)
    return aggregate


if __name__ == "__main__":
    started = time.perf_counter()
    parser = argparse.ArgumentParser(description="EXP-012 bounded DSP-reference model comparison.")
    parser.add_argument("command", choices=["prepare", "probe", "run", "evaluate"])
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--source", type=Path, default=ROOT / "data/visual-audio-exp011-v1")
    parser.add_argument("--settings", type=Path, default=ROOT / "configs/dsp-sol-v1.json")
    parser.add_argument("--prepared", type=Path)
    parser.add_argument("--run", type=Path)
    args = parser.parse_args()
    try:
        if args.command == "prepare":
            prepare(args.output, args.source, args.settings)
        elif args.command in {"probe", "run"}:
            if not args.prepared:
                parser.error("--prepared is required")
            run(args.prepared, args.output, args.command)
        else:
            if not args.prepared or not args.run:
                parser.error("--prepared and --run are required")
            evaluate(args.prepared, args.run, args.output)
    finally:
        print(f"CommandElapsedSeconds={time.perf_counter() - started:.6f}", flush=True)
