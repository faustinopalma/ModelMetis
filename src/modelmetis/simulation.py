import argparse
import hashlib
import json
import math
import os
import random
import shutil
import subprocess
import time
import uuid
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path
from urllib.parse import urlparse

import joblib
import numpy as np

from modelmetis.audio import ModelAudioInput
from modelmetis.audio_models import ClapTeacher, fit_specialist, spectral_features
from modelmetis.learning import (
    Sample,
    SilverExample,
    TeacherRequest,
    collect_silver,
    validate_split,
)


def load_samples(directory: Path) -> list[Sample]:
    records = json.loads((directory / "manifest.json").read_text(encoding="utf-8"))
    samples = []
    for record in records:
        if set(record) != {"sample_id", "group_id", "partition"}:
            raise ValueError("Operational manifests must not contain reference fields.")
        identifier = record["sample_id"]
        if uuid.UUID(identifier).hex != identifier:
            raise ValueError("Invalid opaque sample ID.")
        audio = ModelAudioInput(identifier, (directory / f"{identifier}.wav").read_bytes())
        samples.append(Sample(audio, record["group_id"], record["partition"]))
    validate_split(samples)
    if len({sample.partition for sample in samples}) != 1:
        raise ValueError("One partition per worker invocation is required.")
    return samples


def write_json(path: Path, value: dict) -> None:
    path.write_text(json.dumps(value, indent=2, allow_nan=False) + "\n", encoding="utf-8")


def load_demonstrations(directory: Path, queries: list[Sample], taxonomy: tuple[str, ...]):
    from modelmetis.audio_teacher import AudioDemonstration, demonstration_digest

    manifest = directory / "manifest.json"
    package = json.loads(manifest.read_text(encoding="utf-8"))
    if (set(package) != {"schema", "label_source", "origin_partition", "examples"}
            or package["schema"] != 1 or package["origin_partition"] != "train"
            or package["label_source"] != "simulated_human_from_publisher"):
        raise ValueError("Unsupported support provenance.")
    examples, support_samples = [], []
    for row in package["examples"]:
        if set(row) != {"sample_id", "group_id", "label", "audio_sha256"}:
            raise ValueError("Unexpected support fields.")
        identifier = row["sample_id"]
        if uuid.UUID(identifier).hex != identifier:
            raise ValueError("Invalid opaque support ID.")
        item = Sample(ModelAudioInput(identifier, (directory / f"{identifier}.wav").read_bytes()),
                      row["group_id"], "train")
        if hashlib.sha256(item.audio.wav_bytes).hexdigest() != row["audio_sha256"]:
            raise ValueError("Support audio provenance mismatch.")
        support_samples.append(item)
        examples.append(AudioDemonstration(item.audio, row["label"]))
    labels = [item.label for item in examples]
    if len(labels) != len(taxonomy) or set(labels) != set(taxonomy):
        raise ValueError("Exactly one support example per category is required.")
    validate_split(support_samples + queries)
    groups = {item.group_id for item in support_samples}
    audio = {item.audio.wav_bytes for item in support_samples}
    if (len(groups) != len(support_samples) or len(audio) != len(support_samples)
            or any(item.group_id in groups or item.audio.wav_bytes in audio for item in queries)):
        raise ValueError("Support acquisitions must be disjoint from all query inputs.")
    examples = tuple(examples)
    metadata = {
        "manifest_sha256": hashlib.sha256(manifest.read_bytes()).hexdigest(),
        "support_set_sha256": demonstration_digest(examples),
        "example_count": len(examples), "shots_per_class": 1,
        "label_source": package["label_source"],
    }
    return examples, metadata


class CampaignLedger:
    def __init__(self, path: Path, max_requests: int):
        from modelmetis.audio_teacher import REQUEST_RESERVE_USD

        if type(max_requests) is not int or not 1 <= max_requests <= 160:
            raise ValueError("Campaign request limit must be between 1 and 160.")
        self.path = path
        self.lock = path.with_suffix(path.suffix + ".lock")
        self.reserve = REQUEST_RESERVE_USD
        self.config = {"schema": 2, "max_requests": max_requests,
                       "request_reserve_usd": self.reserve}
        self.state = {**self.config, "requests": 0, "accounted_usd": 0.0}
        self.pending = False

    def __enter__(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        descriptor = os.open(self.lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        os.close(descriptor)
        try:
            if self.path.exists():
                self.state = json.loads(self.path.read_text(encoding="utf-8"))
                if (set(self.state) != set(self.config) | {"requests", "accounted_usd"}
                        or any(self.state.get(key) != value for key, value in self.config.items())
                        or type(self.state["requests"]) is not int
                        or not 0 <= self.state["requests"] <= self.config["max_requests"]
                        or type(self.state["accounted_usd"]) not in (int, float)
                        or not math.isfinite(self.state["accounted_usd"])
                        or not 0 <= self.state["accounted_usd"]
                        <= self.state["requests"] * self.reserve):
                    raise ValueError("Invalid or changed campaign ledger.")
            self.save()
            return self
        except BaseException:
            self.lock.unlink()
            raise

    def __exit__(self, *exception):
        self.lock.unlink()

    def save(self):
        temporary = self.path.with_suffix(self.path.suffix + ".tmp")
        with temporary.open("w", encoding="utf-8") as stream:
            stream.write(json.dumps(self.state, indent=2, allow_nan=False) + "\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, self.path)

    def begin_request(self):
        if self.pending:
            raise RuntimeError("A request is already reserved.")
        if self.state["requests"] >= self.config["max_requests"]:
            raise RuntimeError("Campaign request limit reached.")
        self.state["requests"] += 1
        self.state["accounted_usd"] += self.reserve
        self.save()
        self.pending = True

    def finish_request(self, estimated_usd: float | None):
        if not self.pending:
            raise RuntimeError("No reserved request.")
        if estimated_usd is not None:
            if not math.isfinite(estimated_usd) or not 0 <= estimated_usd <= self.reserve:
                raise ValueError("Request accounting exceeds reserved limits.")
            self.state["accounted_usd"] += estimated_usd - self.reserve
        self.save()
        self.pending = False


def make_audio_teacher(args):
    from azure.identity import AzureCliCredential

    from modelmetis.audio_teacher import MODEL, VERSION, AzureAudioTeacher

    def cli_json(*command):
        result = subprocess.run(
            [shutil.which("az") or "az", *command, "--subscription", args.subscription,
             "--output", "json"], capture_output=True, text=True, timeout=30, check=False,
        )
        if result.returncode != 0:
            raise ValueError("Cannot verify Azure CLI resource context.")
        return json.loads(result.stdout)

    account = cli_json("account", "show")
    if account.get("id") != args.subscription or account.get("tenantId") != args.tenant_id:
        raise ValueError("Azure CLI subscription/tenant mismatch.")
    deployment = cli_json(
        "cognitiveservices", "account", "deployment", "show", "--resource-group",
        args.resource_group, "--name", urlparse(args.endpoint).hostname.split(".")[0],
        "--deployment-name", args.deployment,
    )
    properties = deployment.get("properties", {})
    model = properties.get("model", {})
    if (model.get("name") != MODEL or model.get("version") != VERSION
            or properties.get("provisioningState") != "Succeeded"
            or properties.get("versionUpgradeOption") != "NoAutoUpgrade"):
        raise ValueError("Azure deployment does not match the fixed teacher version.")
    credential = AzureCliCredential(subscription=args.subscription, process_timeout=10)
    return AzureAudioTeacher(
        args.endpoint, args.deployment,
        lambda: credential.get_token("https://ai.azure.com/.default").token,
        deployment_version_verified=True,
    )


def infer_audio(args) -> None:
    from modelmetis import audio_models, audio_teacher

    if not args.acknowledge_paid_requests:
        raise ValueError("Explicit paid-request acknowledgement is required.")
    if (not math.isfinite(args.minimum_score) or not 0 <= args.minimum_score <= 1
            or not math.isfinite(args.deadline_seconds) or not 1 <= args.deadline_seconds <= 1800):
        raise ValueError("Invalid score or execution deadline.")
    samples = load_samples(args.input)
    if samples[0].partition == "test":
        raise ValueError("The consumed final test is not an EXP-002 tuning input.")
    prompt_config = json.loads(args.prompts.read_text(encoding="utf-8"))[args.variant]
    taxonomy = audio_teacher.validate_prompt(prompt_config)
    demonstrations, support = (), None
    if getattr(args, "support", None) is not None:
        demonstrations, support = load_demonstrations(args.support, samples, taxonomy)
        expected = prompt_config.get("support_set_sha256", support["support_set_sha256"])
        if expected != support["support_set_sha256"]:
            raise ValueError("Prompt support provenance mismatch.")
        prompt_config = {**prompt_config, "support_set_sha256": support["support_set_sha256"]}
        audio_teacher.validate_prompt(prompt_config)
    elif "support_set_sha256" in prompt_config:
        raise ValueError("The frozen prompt requires its support set.")
    prompt = json.dumps(prompt_config, sort_keys=True)
    ledger = CampaignLedger(args.ledger, args.max_requests)
    args.output.mkdir(parents=True, exist_ok=False)
    report_path = args.output / "predictions.json"
    report = {
        "model": f"azure:{audio_teacher.MODEL}@{audio_teacher.VERSION}:{args.deployment}",
        "label_source": "teacher", "variant": args.variant,
        "prompt_format": "audio-json-v1", "prompt": prompt_config,
        "prompt_sha256": hashlib.sha256(prompt.encode()).hexdigest(),
        "manifest_sha256": hashlib.sha256((args.input / "manifest.json").read_bytes()).hexdigest(),
        "source_sha256": {Path(file).name: hashlib.sha256(Path(file).read_bytes()).hexdigest()
                          for file in (__file__, audio_teacher.__file__, audio_models.__file__)},
        "api_version": audio_teacher.API_VERSION, "endpoint": args.endpoint,
        "resource_group": args.resource_group,
        "model_parameters": {"temperature": 0, "max_tokens": audio_teacher.MAX_OUTPUT_TOKENS},
        "rates_usd_per_million_tokens": audio_teacher.PRICES,
        "partition": samples[0].partition, "minimum_score": args.minimum_score,
        "started_utc": datetime.now(UTC).isoformat(), "ended_utc": None,
        "expected_count": len(samples), "complete": False, "termination": "initializing",
        "predictions": [], "load_seconds": 0,
        "score_semantics": "Uncalibrated self-reported LLM confidence",
        "usage_ledger": str(args.ledger), "deadline_seconds": args.deadline_seconds,
    }
    if support is not None:
        report["support"] = support
    write_json(report_path, report)
    teacher = None
    started = time.perf_counter()
    try:
        with ledger:
            teacher = make_audio_teacher(args)
            teacher.demonstrations = demonstrations
            report["load_seconds"] = time.perf_counter() - started
            for sample in samples:
                if time.perf_counter() - started + 75 > args.deadline_seconds:
                    report["termination"] = "deadline_headroom_exhausted"
                    break
                report["termination"] = "request_limit_check"
                ledger.begin_request()
                report["termination"] = "request_in_flight"
                report["campaign_accounting"] = dict(ledger.state)
                write_json(report_path, report)
                request_started = time.perf_counter()
                row = {"sample_id": sample.audio.sample_id, "label": None, "score": None,
                       "status": "failed",
                       "audio_sha256": hashlib.sha256(sample.audio.wav_bytes).hexdigest()}
                try:
                    decision = teacher(TeacherRequest(sample.audio, taxonomy, prompt))
                    row["score"] = decision.score
                    if decision.label is None or decision.score < args.minimum_score:
                        row["status"] = "abstained"
                    else:
                        row.update(label=decision.label, status="accepted")
                except Exception:
                    row["error_code"] = "teacher_request_failed"
                row.update(seconds=time.perf_counter() - request_started,
                           metadata=teacher.last_metadata)
                ledger.finish_request(teacher.last_metadata.get("estimated_usd"))
                report["predictions"].append(row)
                report["campaign_accounting"] = dict(ledger.state)
                write_json(report_path, report)
                progress = f"audio {len(report['predictions'])}/{len(samples)}: {row['status']}"
                print(progress, flush=True)
                if row["status"] == "failed":
                    report["termination"] = "teacher_failure"
                    break
            else:
                report.update(complete=True, termination="completed")
    except Exception:
        raise RuntimeError("Audio campaign stopped; inspect its safe report.") from None
    finally:
        report["ended_utc"] = datetime.now(UTC).isoformat()
        report["seconds"] = time.perf_counter() - started
        report["campaign_accounting"] = dict(ledger.state)
        write_json(report_path, report)
        if teacher is not None:
            teacher.close()
    if not report["complete"]:
        raise RuntimeError("Audio campaign incomplete; specialist training must not run.")


def infer(args) -> None:
    samples = load_samples(args.input)
    prompts = json.loads(args.prompts.read_text(encoding="utf-8"))
    descriptions = prompts[args.variant]
    prompt = json.dumps(descriptions, sort_keys=True)
    taxonomy = tuple(descriptions)
    args.output.mkdir(parents=True, exist_ok=False)
    started = time.perf_counter()
    teacher = ClapTeacher(args.revision)
    load_seconds = time.perf_counter() - started
    predictions = []
    for index, sample in enumerate(samples):
        started = time.perf_counter()
        status = "accepted"
        label = None
        score = None
        try:
            if sample.partition == "train":
                result = collect_silver(
                    [sample], teacher, taxonomy=taxonomy, prompt=prompt,
                    teacher_id=teacher.teacher_id, minimum_score=args.minimum_score,
                )
                if result.examples:
                    label, score = result.examples[0].label, result.examples[0].score
                else:
                    status = "failed" if result.failed else "abstained"
            else:
                decision = teacher(TeacherRequest(sample.audio, taxonomy, prompt))
                label, score = decision.label, decision.score
                if label is None or score < args.minimum_score:
                    status, label = "abstained", None
        except Exception:
            status = "failed"
        predictions.append({
            "sample_id": sample.audio.sample_id, "label": label, "score": score,
            "status": status, "seconds": time.perf_counter() - started,
            "audio_sha256": hashlib.sha256(sample.audio.wav_bytes).hexdigest(),
        })
        print(f"audio {index + 1}/{len(samples)}: {status}", flush=True)
        write_json(args.output / "predictions.json", {
            "model": teacher.teacher_id, "label_source": "teacher",
            "variant": args.variant, "prompt": descriptions,
            "prompt_sha256": hashlib.sha256(prompt.encode("utf-8")).hexdigest(),
            "partition": samples[0].partition, "minimum_score": args.minimum_score,
            "load_seconds": load_seconds, "expected_count": len(samples),
            "complete": len(predictions) == len(samples), "predictions": predictions,
            "score_semantics": "Uncalibrated softmax over candidate text similarities",
        })
    if any(prediction["status"] == "failed" for prediction in predictions):
        raise RuntimeError("Teacher failures recorded; inspect before training.")


def train(args) -> None:
    samples = load_samples(args.input)
    if samples[0].partition != "train":
        raise ValueError("Specialist training requires the train partition.")
    silver = json.loads(args.silver.read_text(encoding="utf-8"))
    if silver["label_source"] != "teacher" or silver["partition"] != "train":
        raise ValueError("Not a teacher training collection.")
    if not silver["complete"] or silver["expected_count"] != len(samples):
        raise ValueError("Teacher collection is incomplete.")
    prompt_hash = hashlib.sha256(json.dumps(silver["prompt"], sort_keys=True).encode()).hexdigest()
    if prompt_hash != silver["prompt_sha256"]:
        raise ValueError("Prompt provenance mismatch.")
    if silver.get("prompt_format") == "audio-json-v1":
        from modelmetis.audio_teacher import validate_prompt

        taxonomy = validate_prompt(silver["prompt"])
    elif "prompt_format" not in silver:
        taxonomy = tuple(silver["prompt"])
    else:
        raise ValueError("Unknown teacher prompt format.")
    predictions = {record["sample_id"]: record for record in silver["predictions"]}
    if len(predictions) != len(silver["predictions"]):
        raise ValueError("Duplicate teacher result.")
    if set(predictions) != {sample.audio.sample_id for sample in samples}:
        raise ValueError("Teacher collection and train inputs differ.")
    examples = []
    for sample in samples:
        prediction = predictions[sample.audio.sample_id]
        if prediction["audio_sha256"] != hashlib.sha256(sample.audio.wav_bytes).hexdigest():
            raise ValueError("Teacher audio differs from specialist input.")
        if prediction["status"] not in ("accepted", "abstained", "failed"):
            raise ValueError("Unknown teacher result status.")
        if prediction["status"] != "accepted":
            continue
        if prediction["label"] not in taxonomy:
            raise ValueError("Invalid silver label.")
        if not np.isfinite(prediction["score"]) or not 0 <= prediction["score"] <= 1:
            raise ValueError("Invalid silver score.")
        examples.append(SilverExample(sample.audio, prediction["label"], prediction["score"],
                                      silver["model"], silver["prompt_sha256"]))
    sample_count = getattr(args, "sample_count", None)
    arrival = sorted(sample.audio.sample_id for sample in samples)
    random.Random(17).shuffle(arrival)
    if sample_count is not None:
        if type(sample_count) is not int or not 1 <= sample_count <= len(samples):
            raise ValueError("Snapshot size must be within the observed training collection.")
        selected = set(arrival[:sample_count])
        examples = [example for example in examples if example.audio.sample_id in selected]
    started = time.perf_counter()
    classifier = fit_specialist(examples)
    args.output.mkdir(parents=True, exist_ok=False)
    joblib.dump(classifier, args.output / "specialist.joblib")
    manifest_hash = hashlib.sha256((args.input / "manifest.json").read_bytes()).hexdigest()
    write_json(args.output / "training.json", {
        "model": "logistic-regression-spectral-v1", "label_source": "teacher",
        "examples": len(examples), "class_counts": dict(Counter(item.label for item in examples)),
        "teacher": silver["model"], "prompt_sha256": silver["prompt_sha256"],
        "train_manifest_sha256": manifest_hash,
        "silver_sha256": hashlib.sha256(args.silver.read_bytes()).hexdigest(),
        "seconds": time.perf_counter() - started,
        "parameters": {"features": 48, "max_iter": 1000, "random_state": 17},
        "observed_examples": sample_count if sample_count is not None else len(samples),
        "arrival_order": "sorted opaque sample IDs, Python Random(17).shuffle",
        "arrival_order_sha256": hashlib.sha256(json.dumps(arrival).encode()).hexdigest(),
    })
    print(f"Specialist fitted on {len(examples)} teacher labels.")


def predict(args) -> None:
    samples = load_samples(args.input)
    if samples[0].partition == "train":
        raise ValueError("Use held-out inputs for specialist evaluation.")
    started = time.perf_counter()
    classifier = joblib.load(args.model)
    load_seconds = time.perf_counter() - started
    predictions = []
    for sample in samples:
        started = time.perf_counter()
        scores = classifier.predict_proba([spectral_features(sample.audio)])[0]
        index = int(np.argmax(scores))
        predictions.append({
            "sample_id": sample.audio.sample_id, "label": str(classifier.classes_[index]),
            "score": float(scores[index]), "status": "accepted",
            "seconds": time.perf_counter() - started,
        })
    args.output.mkdir(parents=True, exist_ok=False)
    write_json(args.output / "predictions.json", {
        "model": "logistic-regression-spectral-v1", "label_source": "specialist",
        "model_sha256": hashlib.sha256(args.model.read_bytes()).hexdigest(),
        "partition": samples[0].partition, "expected_count": len(samples), "complete": True,
        "load_seconds": load_seconds, "predictions": predictions,
    })


def main() -> None:
    parser = argparse.ArgumentParser()
    commands = parser.add_subparsers(dest="command", required=True)
    teacher = commands.add_parser("infer")
    teacher.add_argument("--prompts", type=Path, required=True)
    teacher.add_argument("--variant", required=True)
    teacher.add_argument("--revision", required=True)
    teacher.add_argument("--minimum-score", type=float, default=0.0)
    audio_teacher = commands.add_parser("infer-audio")
    audio_teacher.add_argument("--prompts", type=Path, required=True)
    audio_teacher.add_argument("--variant", required=True)
    audio_teacher.add_argument("--support", type=Path)
    audio_teacher.add_argument("--endpoint", required=True)
    audio_teacher.add_argument("--deployment", required=True)
    audio_teacher.add_argument("--tenant-id", required=True)
    audio_teacher.add_argument("--subscription", required=True)
    audio_teacher.add_argument("--resource-group", required=True)
    audio_teacher.add_argument("--ledger", type=Path, required=True)
    audio_teacher.add_argument("--max-requests", type=int, required=True)
    audio_teacher.add_argument("--deadline-seconds", type=float, default=1800)
    audio_teacher.add_argument("--minimum-score", type=float, default=0.0)
    audio_teacher.add_argument("--acknowledge-paid-requests", action="store_true", required=True)
    specialist = commands.add_parser("train")
    specialist.add_argument("--silver", type=Path, required=True)
    specialist.add_argument("--sample-count", type=int)
    prediction = commands.add_parser("predict")
    prediction.add_argument("--model", type=Path, required=True)
    for command in (teacher, audio_teacher, specialist, prediction):
        command.add_argument("--input", type=Path, required=True)
        command.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    {"infer": infer, "infer-audio": infer_audio, "train": train, "predict": predict}[
        args.command
    ](args)


if __name__ == "__main__":
    main()
