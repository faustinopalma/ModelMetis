import hashlib
import io
import json
import math
import uuid
import wave
from dataclasses import asdict, fields
from types import SimpleNamespace

import pytest

from modelmetis.audio import ModelAudioInput
from modelmetis.learning import (
    Sample,
    TeacherDecision,
    TeacherRequest,
    collect_silver,
    training_targets,
    validate_split,
)


def sample(partition="train", value=1, group_id=None):
    stream = io.BytesIO()
    with wave.open(stream, "wb") as audio:
        audio.setparams((1, 2, 8000, 80, "NONE", "not compressed"))
        audio.writeframes(value.to_bytes(2, "little", signed=True) * 80)
    return Sample(
        ModelAudioInput(uuid.uuid4().hex, stream.getvalue()),
        group_id or uuid.uuid4().hex,
        partition,
    )


def collect(samples, teacher, **kwargs):
    return collect_silver(
        samples, teacher, taxonomy=("healthy", "faulty"),
        prompt="Listen to the recording.", teacher_id="fixture-not-a-model", **kwargs,
    )


def test_teacher_labels_not_publisher_references_reach_training():
    samples = [sample(value=1), sample(value=2)]
    sealed_references = {samples[0].audio.sample_id: "faulty",
                         samples[1].audio.sample_id: "healthy"}
    requests = []
    decisions = iter(["healthy", "faulty"])

    def teacher(request):
        requests.append(request)
        return TeacherDecision(next(decisions), 0.8)

    collection = collect(samples, teacher)
    labels = training_targets(collection.examples)
    assert labels == ("healthy", "faulty")
    assert labels != tuple(sealed_references.values())
    assert collection.attempted == len(requests) == 2
    assert [item.name for item in fields(TeacherRequest)] == ["audio", "taxonomy", "prompt"]
    assert all(item.label_source == "teacher" for item in collection.examples)
    assert all(len(item.prompt_sha256) == 64 for item in collection.examples)


def test_supervised_control_is_separate_and_rejects_heldout_targets(monkeypatch):
    import importlib.util
    from pathlib import Path

    from sklearn.linear_model import LogisticRegression

    spec = importlib.util.spec_from_file_location(
        "supervised_control", Path(__file__).parents[1] / "scripts" / "supervised_control.py",
    )
    control = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(control)
    samples = [sample(value=number) for number in (1, 2, 10, 20)]
    references = [{"sample_id": item.audio.sample_id, "partition": "train",
                   "label": "healthy" if index < 2 else "faulty",
                   "audio_sha256": hashlib.sha256(item.audio.wav_bytes).hexdigest()}
                  for index, item in enumerate(samples)]
    captured = []
    real_fit = LogisticRegression.fit

    def capture(self, matrix, labels, *args, **kwargs):
        captured.extend(labels)
        return real_fit(self, matrix, labels, *args, **kwargs)

    monkeypatch.setattr(LogisticRegression, "fit", capture)
    artifact = control.fit_control(samples, references, "welch-logistic")
    assert artifact["kind"] == control.KIND
    assert captured == [row["label"] for row in references]
    query = sample("development", value=3)
    report = control.predict_control(artifact, [query])
    assert report["complete"] and report["expected_count"] == 1
    with pytest.raises(ValueError, match="overlaps"):
        control.predict_control(artifact, [sample("development", value=1)])
    with pytest.raises(ValueError, match="overlaps"):
        control.predict_control(artifact, [sample("development", value=4,
                                                  group_id=samples[0].group_id)])
    captured.clear()
    with pytest.raises(ValueError, match="training inputs only"):
        control.fit_control(samples, [{**row, "partition": "development"}
                                      for row in references], "welch-logistic")
    with pytest.raises(ValueError, match="Only training"):
        control.fit_control([query], references, "welch-logistic")
    with pytest.raises(ValueError, match="reference/audio mismatch"):
        control.fit_control(samples, [{**row, "audio_sha256": "0" * 64}
                                      for row in references], "welch-logistic")
    assert not captured


def test_jin_import_masks_directions_before_segmentation(tmp_path, monkeypatch):
    import importlib.util
    from pathlib import Path

    import numpy as np

    from modelmetis.simulation import load_demonstrations, load_samples

    spec = importlib.util.spec_from_file_location(
        "prepare_jin", Path(__file__).parents[1] / "scripts" / "prepare_jin.py",
    )
    importer = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(importer)
    source = tmp_path / "raw"
    source.mkdir()
    catalog = []
    for code in importer.LABELS:
        for direction in importer.OFFSETS:
            name = f"{code}{direction}10m{'_01' if code != 'n' else ''}.wav"
            content = name.encode()
            (source / name).write_bytes(content)
            catalog.append({"entry": {"filename": name, "content_details": {
                "sha256_hash": hashlib.sha256(content).hexdigest(),
            }}})
    catalog.append({"entry": {"filename": "readme.txt"}})
    (source / "catalog.json").write_text(json.dumps(catalog))
    signal = np.broadcast_to(np.float32(0.25), (600 * 44100,))
    monkeypatch.setattr(importer.wavfile, "read", lambda *args, **kwargs: (44100, signal))
    original_window = importer.canonical_window
    counter = iter(range(1, 137))

    def fixture_window(*args):
        frequency = next(counter)
        values = np.sin(2 * np.pi * frequency * np.arange(80000) / 8000)
        return original_window(values, 8000, 0)

    monkeypatch.setattr(importer, "canonical_window", fixture_window)
    output = tmp_path / "masked"
    report = importer.prepare(source, output)
    assert report["partitions"] == {"train": 120, "development": 12, "support": 4}
    train = load_samples(output / "train")
    development = load_samples(output / "development")
    validate_split(train + development)
    assert len({item.group_id for item in train}) == 4
    assert len({item.group_id for item in development}) == 4
    demonstrations, _ = load_demonstrations(
        output / "support", train + development, tuple(importer.LABELS.values()),
    )
    assert len(demonstrations) == 4
    references = json.loads((output / "sealed" / "supervised-train.json").read_text())
    assert len(references) == 120
    assert {row["partition"] for row in references} == {"train"}
    assert all("l10m" in row["source_path"] for row in references)
    with pytest.raises(ValueError, match="overwrite"):
        importer.prepare(source, output)
    (source / "b1f10m_01.wav").write_bytes(b"changed")
    with pytest.raises(ValueError, match="checksum"):
        importer.prepare(source, tmp_path / "bad")
    with pytest.raises(ValueError, match="Constant"):
        original_window(np.zeros(80000), 8000, 0)
    with pytest.raises(ValueError, match="complete finite"):
        original_window(np.full(80000, np.nan), 8000, 0)


def test_mechanic_import_masks_references_and_keeps_sources_whole(tmp_path):
    import importlib.util
    import zipfile
    from pathlib import Path

    from modelmetis.simulation import load_samples

    spec = importlib.util.spec_from_file_location(
        "prepare_mechanic", Path(__file__).parents[1] / "scripts" / "prepare_mechanic.py",
    )
    importer = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(importer)
    metadata = {"version": 1, "files": []}
    archive_path = tmp_path / "fixture.zip"
    labels = ("idling", "air leak", "oil cap off engine inside cabin", "background noise")
    with zipfile.ZipFile(archive_path, "w") as archive:
        for category_index, label in enumerate(labels):
            for recording_index in range(3):
                source_path = f"training/{label}-{recording_index}.wav"
                content = io.BytesIO()
                with wave.open(content, "wb") as recording:
                    recording.setparams((1, 2, 16000, 176000, "NONE", "not compressed"))
                    value = category_index * 3 + recording_index + 1
                    cycle = (value.to_bytes(2, "little", signed=True)
                             + (-value).to_bytes(2, "little", signed=True))
                    recording.writeframes(cycle * 88000)
                archive.writestr("ai-mechanic-export/" + source_path, content.getvalue())
                metadata["files"].append({"path": source_path, "category": "training",
                                          "label": {"label": label}})
                if category_index == recording_index == 0:
                    duplicate_path = "training/duplicate.wav"
                    archive.writestr("ai-mechanic-export/" + duplicate_path, content.getvalue())
                    metadata["files"].append({"path": duplicate_path, "category": "training",
                                              "label": {"label": label}})
        content = io.BytesIO()
        with wave.open(content, "wb") as recording:
            recording.setparams((1, 2, 16000, 160000, "NONE", "not compressed"))
            recording.writeframes((-8).to_bytes(2, "little", signed=True) * 160000)
        for label in ("idling", "air leak"):
            source_path = f"training/constant-{label}.wav"
            archive.writestr("ai-mechanic-export/" + source_path, content.getvalue())
            metadata["files"].append({"path": source_path, "category": "training",
                                      "label": {"label": label}})
        metadata["files"].append({"category": "testing", "path": "must-not-be-read"})
        archive.writestr("ai-mechanic-export/info.labels", json.dumps(metadata))
    output = tmp_path / "masked"
    report = importer.prepare(archive_path, output)
    assert report["partitions"] == {"development": 8, "train": 4}
    assert report["duplicate_canonical_windows_removed"] == 1
    assert report["constant_or_empty_windows_removed"] == 2
    samples = load_samples(output / "development") + load_samples(output / "train")
    validate_split(samples)
    assert len({item.group_id for item in samples}) == 12
    for item in samples:
        with wave.open(io.BytesIO(item.audio.wav_bytes)) as recording:
            assert recording.getnframes() == 160000
    for partition in ("train", "development"):
        rows = json.loads((output / partition / "manifest.json").read_text())
        assert all(set(row) == {"sample_id", "group_id", "partition"} for row in rows)
    with pytest.raises(ValueError, match="overwrite"):
        importer.prepare(archive_path, output)
    conflict_path = tmp_path / "conflict.zip"
    with zipfile.ZipFile(archive_path) as original, zipfile.ZipFile(conflict_path, "w") as changed:
        for entry in original.infolist():
            if entry.filename.endswith("info.labels"):
                next(row for row in metadata["files"] if row.get("path")
                     == "training/duplicate.wav")["label"]["label"] = "air leak"
                changed.writestr(entry.filename, json.dumps(metadata))
            else:
                changed.writestr(entry, original.read(entry.filename))
    with pytest.raises(ValueError, match="conflicting"):
        importer.prepare(conflict_path, tmp_path / "conflict")


@pytest.mark.parametrize("partition", ["development", "test"])
def test_held_out_audio_never_reaches_label_collection(partition):
    def forbidden(request):
        pytest.fail("Teacher was invoked on held-out audio.")

    with pytest.raises(ValueError, match="training partition"):
        collect([sample(), sample(partition, value=2)], forbidden)


def test_group_and_audio_duplicates_cannot_cross_partitions():
    original = sample()
    with pytest.raises(ValueError, match="crosses partitions"):
        validate_split([original, sample("test", value=2, group_id=original.group_id)])
    with pytest.raises(ValueError, match="crosses partitions"):
        validate_split([original, sample("test", value=1)])


def test_abstention_failure_and_invalid_decisions_are_not_labels():
    decisions = iter([
        TeacherDecision("healthy", 0.9), TeacherDecision(None, 0.9),
        TeacherDecision("faulty", 0.1), TeacherDecision("unknown", 0.9),
        TeacherDecision("faulty", math.nan), {"reference_label": "faulty"},
    ])
    collection = collect([sample(value=index + 1) for index in range(6)],
                         lambda request: next(decisions), minimum_score=0.5)
    assert collection.attempted == 6
    assert len(collection.examples) == 1
    assert collection.abstained == 2
    assert collection.failed == 3
    with pytest.raises(ValueError, match="two teacher classes"):
        training_targets(collection.examples)


def test_failures_do_not_persist_provider_payloads_or_reference_sentinels():
    sentinel = "SOURCE_FAULT_\u00e9_ROTOR"

    def teacher(request):
        raise RuntimeError(sentinel)

    assert sentinel in str(RuntimeError(sentinel))
    collection = collect([sample()], teacher)
    serialized = json.dumps(asdict(collection))
    assert collection.attempted == collection.failed == 1
    assert sentinel not in serialized
    assert json.dumps(sentinel)[1:-1] not in serialized
    with pytest.raises(ValueError, match="No accepted teacher"):
        training_targets(collection.examples)


def test_empty_and_nonopaque_inputs_fail_closed():
    with pytest.raises(ValueError, match="empty dataset"):
        validate_split([])
    valid = sample()
    with pytest.raises(ValueError):
        Sample(ModelAudioInput("motor-faulty", valid.audio.wav_bytes), valid.group_id, "train")


def test_real_specialist_fit_receives_only_teacher_targets(monkeypatch):
    pytest.importorskip("sklearn")
    from sklearn.linear_model import LogisticRegression

    from modelmetis.audio_models import fit_specialist

    captured = []
    original = LogisticRegression.fit

    def capture(self, features, labels, *args, **kwargs):
        captured.extend(labels)
        return original(self, features, labels, *args, **kwargs)

    monkeypatch.setattr(LogisticRegression, "fit", capture)
    decisions = iter(["healthy", "faulty", "healthy", "faulty"])
    collection = collect([sample(value=value) for value in (1, 10, 2, 20)],
                         lambda request: TeacherDecision(next(decisions), 0.8))
    model = fit_specialist(collection.examples)
    assert captured == ["healthy", "faulty", "healthy", "faulty"]
    assert set(model.classes_) == {"healthy", "faulty"}


def test_evaluator_rejects_empty_partial_and_wrong_partition():
    pytest.importorskip("sklearn")
    from scripts.evaluate_audio import evaluate

    predictions = {"partition": "test", "complete": True, "expected_count": 1,
                   "predictions": []}
    with pytest.raises(ValueError, match="Empty"):
        evaluate(predictions, [], "test")
    references = [{"sample_id": "heldout", "label": "healthy", "partition": "test"}]
    with pytest.raises(ValueError, match="sample mismatch"):
        evaluate(predictions, references, "test")
    with pytest.raises(ValueError, match="held-out partition"):
        evaluate(predictions, references, "development")


def test_experiment_bundle_reconciles_usage_without_sample_answers(tmp_path):
    from scripts.report_audio import bundle

    root = tmp_path / "campaign"
    attempt = root / "attempt"
    attempt.mkdir(parents=True)
    ledger = root / "usage.json"
    ledger.write_text(json.dumps({"requests": 1, "accounted_usd": 0.01}))
    sentinel = "PRIVATE_ANSWER_\u00e9"
    (attempt / "predictions.json").write_text(json.dumps({
        "usage_ledger": str(ledger), "model": "fixture", "complete": True,
        "support": {"shots_per_class": 1, "example_count": 4,
                    "label_source": "simulated_human_from_publisher",
                    "source_path": sentinel, "examples": [{"answer": sentinel}]},
        "predictions": [{"sample_id": sentinel, "source_path": sentinel, "label": "normal",
                         "status": "accepted", "metadata": {"http_status": 200,
                         "estimated_usd": 0.01, "observations": [sentinel]}}],
    }))
    report = bundle([root])
    assert report["reserved_requests"] == report["http_responses"] == 1
    assert report["known_estimated_usd"] == 0.01
    assert report["runs"][0]["accepted_class_counts"] == {"normal": 1}
    assert report["runs"][0]["support"] == {
        "shots_per_class": 1, "example_count": 4,
        "label_source": "simulated_human_from_publisher",
    }
    serialized = json.dumps(report)
    assert sentinel not in serialized
    assert json.dumps(sentinel)[1:-1] not in serialized
    with pytest.raises(ValueError, match="Duplicate"):
        bundle([root, root])
    ledger.write_text(json.dumps({"requests": 2, "accounted_usd": 0.02}))
    with pytest.raises(ValueError, match="reconciliation"):
        bundle([root])
    with pytest.raises(ValueError, match="No experiment"):
        bundle([])


def test_curve_only_treats_known_empty_class_failures_as_blocked(monkeypatch):
    import subprocess

    from scripts.learning_curve import execute

    known = "ValueError: Fewer than two teacher classes; training must not run."
    outputs = iter([(1, known), (1, known), (1, "secret failure"), (0, "")])

    def worker(command, **kwargs):
        assert kwargs == {"capture_output": True, "text": True, "timeout": 120, "check": False}
        code, error = next(outputs)
        return subprocess.CompletedProcess(command, code, stdout="", stderr=error)

    monkeypatch.setattr(subprocess, "run", worker)
    assert execute(["fixture"], allow_blocked=True) is False
    for allow_blocked in (False, True):
        with pytest.raises(RuntimeError, match="worker failed"):
            execute(["fixture"], allow_blocked=allow_blocked)
    assert execute(["fixture"]) is True


def test_evaluator_counts_abstentions_as_errors_and_no_leaked_rows():
    pytest.importorskip("sklearn")
    from scripts.evaluate_audio import evaluate

    predictions = {
        "partition": "test", "complete": True, "expected_count": 2,
        "model": "test-fixture", "load_seconds": 0,
        "predictions": [
            {"sample_id": "first", "label": "healthy", "status": "accepted", "seconds": 0.1},
            {"sample_id": "second", "label": None, "status": "abstained", "seconds": 0.1},
        ],
    }
    references = [
        {"sample_id": "first", "label": "healthy", "partition": "test"},
        {"sample_id": "second", "label": "faulty", "partition": "test"},
    ]
    result = evaluate(predictions, references, "test")
    assert result["samples"] == 2
    assert result["coverage"] == result["accuracy"] == 0.5
    assert "first" not in json.dumps(result)


@pytest.fixture
def training_invocation(tmp_path):
    pytest.importorskip("sklearn")
    from modelmetis.simulation import write_json

    samples = [sample(value=value) for value in (1, 10, 2, 20)]
    args = SimpleNamespace(input=tmp_path / "input", silver=tmp_path / "silver.json",
                           output=tmp_path / "trained")
    args.input.mkdir()
    manifest = []
    for recording in samples:
        identifier = recording.audio.sample_id
        (args.input / f"{identifier}.wav").write_bytes(recording.audio.wav_bytes)
        manifest.append({"sample_id": identifier, "group_id": recording.group_id,
                         "partition": "train"})
    (args.input / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    prompt = {"healthy": "Steady motor sound.", "faulty": "Irregular motor sound."}
    decisions = iter(["healthy", "faulty", "healthy", "faulty"])
    collection = collect_silver(
        samples, lambda request: TeacherDecision(next(decisions), 0.8),
        taxonomy=tuple(prompt), prompt=json.dumps(prompt, sort_keys=True),
        teacher_id="fixture-not-a-model",
    )
    write_json(args.silver, {
        "label_source": "teacher", "partition": "train", "complete": True,
        "expected_count": len(samples), "model": "fixture-not-a-model", "prompt": prompt,
        "prompt_sha256": collection.examples[0].prompt_sha256,
        "predictions": [{
            "sample_id": example.audio.sample_id, "label": example.label,
            "score": example.score, "status": "accepted",
            "audio_sha256": hashlib.sha256(example.audio.wav_bytes).hexdigest(),
        } for example in collection.examples],
    })
    return args, collection


def test_training_entrypoint_fits_silver_not_sealed_references(training_invocation, monkeypatch):
    from sklearn.linear_model import LogisticRegression

    from modelmetis.simulation import train

    args, collection = training_invocation
    references = [{"sample_id": example.audio.sample_id,
                   "label": "faulty" if example.label == "healthy" else "healthy"}
                  for example in collection.examples]
    sealed = args.input.parent / "sealed-references.json"
    sealed.write_text(json.dumps(references), encoding="utf-8")
    captured = []
    original = LogisticRegression.fit

    def capture(self, features, labels, *fit_args, **kwargs):
        captured.extend(labels)
        return original(self, features, labels, *fit_args, **kwargs)

    monkeypatch.setattr(LogisticRegression, "fit", capture)
    train(args)
    assert captured == [example.label for example in collection.examples]
    assert captured != [reference["label"] for reference in references]
    report = json.loads((args.output / "training.json").read_text(encoding="utf-8"))
    assert report["examples"] == len(captured) == 4
    assert report["label_source"] == "teacher"
    assert (args.output / "specialist.joblib").stat().st_size > 0


@pytest.mark.parametrize("mutation, message", [
    ("manifest_reference", "reference fields"),
    ("development", "train partition"),
    ("test", "train partition"),
    ("source", "teacher training collection"),
    ("incomplete", "incomplete"),
    ("prompt", "Prompt provenance mismatch"),
    ("audio", "audio differs"),
    ("duplicate", "Duplicate teacher result"),
    ("missing", "inputs differ"),
    ("status", "Unknown teacher result status"),
])
def test_training_entrypoint_rejects_contamination_before_fit(
    training_invocation, monkeypatch, mutation, message,
):
    from modelmetis import simulation

    args, _ = training_invocation
    manifest_path = args.input / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    silver = json.loads(args.silver.read_text(encoding="utf-8"))
    if mutation == "manifest_reference":
        manifest[0]["reference_label"] = "SOURCE_FAULT_\u00e9_ROTOR"
    elif mutation in ("development", "test"):
        for row in manifest:
            row["partition"] = mutation
    elif mutation == "source":
        silver["label_source"] = "publisher_reference"
    elif mutation == "incomplete":
        silver["complete"] = False
    elif mutation == "prompt":
        silver["prompt"]["healthy"] = "Modified after collection."
    elif mutation == "audio":
        silver["predictions"][0]["audio_sha256"] = "0" * 64
    elif mutation == "duplicate":
        silver["predictions"].append(silver["predictions"][0])
    elif mutation == "missing":
        silver["predictions"].pop()
    elif mutation == "status":
        silver["predictions"][0]["status"] = "publisher_verified"
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    simulation.write_json(args.silver, silver)

    def forbidden(examples):
        pytest.fail("Contaminated input reached classifier fit.")

    monkeypatch.setattr(simulation, "fit_specialist", forbidden)
    with pytest.raises(ValueError, match=message):
        simulation.train(args)
    assert not args.output.exists()


@pytest.fixture
def audio_prompt():
    return {
        "taxonomy": {"healthy": "Steady sound", "faulty": "Irregular sound"},
        "instructions": "Listen without assuming a diagnosis.",
        "response_contract": "Return JSON with label, score and observations.",
    }


def test_support_selection_and_loader_keep_queries_unlabeled(tmp_path):
    import importlib.util
    from pathlib import Path

    from modelmetis.simulation import load_demonstrations, load_samples, write_json

    spec = importlib.util.spec_from_file_location(
        "prepare_mechanic", Path(__file__).parents[1] / "scripts" / "prepare_mechanic.py",
    )
    importer = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(importer)
    frozen = tmp_path / "frozen"
    references = []
    for partition, values in (("train", range(1, 7)), ("development", range(7, 9))):
        directory = frozen / partition
        directory.mkdir(parents=True)
        manifest = []
        for value in values:
            item = sample(partition=partition, value=value)
            manifest.append({"sample_id": item.audio.sample_id, "group_id": item.group_id,
                             "partition": partition})
            (directory / f"{item.audio.sample_id}.wav").write_bytes(item.audio.wav_bytes)
            references.append({"sample_id": item.audio.sample_id, "partition": partition,
                               "label": "healthy" if value % 2 else "faulty",
                               "audio_sha256": hashlib.sha256(item.audio.wav_bytes).hexdigest(),
                               "source_path": "private_source_answer_\u00e9"})
        write_json(directory / "manifest.json", manifest)
    (frozen / "sealed").mkdir()
    write_json(frozen / "sealed" / "references.json", references)
    taxonomy = ("healthy", "faulty")
    output = tmp_path / "one-shot"
    audit = importer.prepare_support(frozen, output, taxonomy)
    assert audit["partitions"] == {"support": 2, "train": 4, "development": 2}
    assert (frozen / "development" / "manifest.json").read_bytes() == (
        output / "development" / "manifest.json"
    ).read_bytes()
    queries = load_samples(output / "train") + load_samples(output / "development")
    examples, metadata = load_demonstrations(output / "support", queries, taxonomy)
    assert metadata["shots_per_class"] == 1
    assert metadata["label_source"] == "simulated_human_from_publisher"
    assert len(examples) == 2
    for example in examples:
        expected = min(row["audio_sha256"] for row in references
                       if row["partition"] == "train" and row["label"] == example.label)
        assert hashlib.sha256(example.audio.wav_bytes).hexdigest() == expected
    assert len(load_samples(frozen / "train")) == 6
    manifest_path = output / "support" / "manifest.json"
    original = manifest_path.read_text()
    sentinel = "private_source_answer_\u00e9"
    assert sentinel not in original and json.dumps(sentinel)[1:-1] not in original
    rows = json.loads(original)["examples"]
    for mutation in ("group", "audio", "extra", "label", "held_out", "hash"):
        package = json.loads(original)
        if mutation == "group":
            package["examples"][0]["group_id"] = queries[0].group_id
        elif mutation == "audio":
            row = package["examples"][0]
            row["sample_id"] = queries[0].audio.sample_id
            row["audio_sha256"] = hashlib.sha256(queries[0].audio.wav_bytes).hexdigest()
            (output / "support" / f"{row['sample_id']}.wav").write_bytes(queries[0].audio.wav_bytes)
        elif mutation == "extra":
            package["examples"][0]["source_path"] = sentinel
        elif mutation == "label":
            package["examples"][0]["label"] = package["examples"][1]["label"]
        elif mutation == "held_out":
            package["origin_partition"] = "development"
        else:
            package["examples"][0]["audio_sha256"] = "0" * 64
        write_json(manifest_path, package)
        with pytest.raises(ValueError):
            load_demonstrations(output / "support", queries, taxonomy)
    assert len(rows) > 0
    with pytest.raises(ValueError, match="overwrite"):
        importer.prepare_support(frozen, output, taxonomy)


def test_one_shot_payload_and_fail_closed_boundaries(audio_prompt):
    import base64
    from dataclasses import replace

    import httpx

    from modelmetis.audio_teacher import (
        AudioDemonstration,
        AzureAudioTeacher,
        demonstration_digest,
    )

    query = sample().audio
    examples = tuple(AudioDemonstration(
        replace(sample().audio, wav_bytes=query.wav_bytes[:-2] + index.to_bytes(2, "little")),
        label,
    ) for index, label in enumerate(audio_prompt["taxonomy"], start=101))
    prompt = {**audio_prompt, "message_layout": "system-instructions-v1",
              "support_set_sha256": demonstration_digest(examples)}
    captured = []

    def handle(request):
        captured.append(json.loads(request.content))
        return httpx.Response(200, json=completion_response())

    teacher = AzureAudioTeacher(
        "https://fixture.openai.azure.com", "teacher", lambda: "fixture-token",
        transport=httpx.MockTransport(handle), demonstrations=examples,
    )
    taxonomy = tuple(audio_prompt["taxonomy"])
    try:
        teacher(TeacherRequest(query, taxonomy, json.dumps(prompt)))
        messages = captured[0]["messages"]
        assert [row["role"] for row in messages] == [
            "system", "user", "assistant", "user", "assistant", "user",
        ]
        for index, example in enumerate(examples):
            content = messages[1 + 2 * index]["content"]
            assert base64.b64decode(content[1]["input_audio"]["data"]) == example.audio.wav_bytes
            assert json.loads(messages[2 + 2 * index]["content"]) == {"label": example.label}
            assert example.audio.sample_id not in json.dumps(captured)
        query_data = messages[-1]["content"][1]["input_audio"]["data"]
        assert base64.b64decode(query_data) == query.wav_bytes
        assert query.sample_id not in json.dumps(captured)
        for invalid in (
            {**prompt, "support_set_sha256": "0" * 64},
            {**prompt, "audio_preprocessing": "dc-peak-v1"},
            audio_prompt,
        ):
            with pytest.raises(ValueError):
                teacher(TeacherRequest(query, taxonomy, json.dumps(invalid)))
        with pytest.raises(ValueError):
            teacher(TeacherRequest(examples[0].audio, taxonomy, json.dumps(prompt)))
        with pytest.raises(ValueError):
            teacher(TeacherRequest(replace(query, wav_bytes=examples[0].audio.wav_bytes),
                                   taxonomy, json.dumps(prompt)))
        for invalid_examples in ((), examples[:1], (examples[0], examples[0])):
            teacher.demonstrations = invalid_examples
            with pytest.raises(ValueError):
                teacher(TeacherRequest(query, taxonomy, json.dumps(prompt)))
        assert len(captured) == 1
    finally:
        teacher.close()


def completion_response(content=None):
    return {
        "model": "gpt-audio-1.5-2026-02-23",
        "usage": {"prompt_tokens": 520, "completion_tokens": 50,
                  "prompt_tokens_details": {"audio_tokens": 500}},
        "choices": [{"finish_reason": "stop", "message": {"content": content or json.dumps({
            "label": "faulty", "score": 0.6, "observations": ["Periodic rattling"],
        })}}],
    }


def test_audio_teacher_sends_canonical_audio_without_ids_or_reference(audio_prompt):
    import base64

    import httpx

    from modelmetis.audio_teacher import AzureAudioTeacher

    recording = sample()
    captured = []

    def handle(request):
        captured.append(json.loads(request.content))
        assert request.headers["Authorization"] == "Bearer fixture-token"
        assert request.url.params["api-version"] == "2025-01-01-preview"
        return httpx.Response(200, json=completion_response())

    teacher = AzureAudioTeacher(
        "https://fixture.openai.azure.com", "teacher", lambda: "fixture-token",
        transport=httpx.MockTransport(handle),
    )
    try:
        decision = teacher(TeacherRequest(recording.audio, tuple(audio_prompt["taxonomy"]),
                                          json.dumps(audio_prompt, sort_keys=True)))
        assert decision.label == "faulty"
        assert teacher.last_metadata["estimated_usd"] == pytest.approx(0.01655)
    finally:
        teacher.close()
    assert len(captured) == 1
    body = captured[0]
    assert body["modalities"] == ["text"]
    assert "response_format" not in body
    assert "tools" not in body
    assert body["max_tokens"] == 1024
    content = body["messages"][0]["content"]
    assert base64.b64decode(content[1]["input_audio"]["data"]) == recording.audio.wav_bytes
    assert json.loads(content[0]["text"]) == audio_prompt
    assert recording.audio.sample_id not in json.dumps(body)
    assert recording.group_id not in json.dumps(body)


@pytest.mark.parametrize("content", [
    '{"label":"unknown","score":0.9,"observations":[]}',
    '{"label":"healthy","score":NaN,"observations":[]}',
    '{"label":"healthy","score":true,"observations":[]}',
    '{"label":"healthy","score":1.01,"observations":[]}',
    '{"label":"healthy","label":"faulty","score":0.5,"observations":[]}',
    '{"label":"healthy","score":0.5,"observations":[],"reference_label":"faulty"}',
    '```json\n{"label":null,"score":0,"observations":[]}\n```',
])
def test_audio_parser_rejects_invalid_or_ambiguous_output(content):
    from modelmetis.audio_teacher import parse_decision

    with pytest.raises(ValueError, match="Invalid teacher response"):
        parse_decision(content, ("healthy", "faulty"))


def test_audio_parser_preserves_abstention():
    from modelmetis.audio_teacher import parse_decision

    decision, observations = parse_decision(
        '{"label":null,"score":0,"observations":["Insufficient audible evidence"]}',
        ("healthy", "faulty"),
    )
    assert decision.label is None
    assert observations == ["Insufficient audible evidence"]


def test_completion_shape_diagnostics_never_log_rejected_text(audio_prompt):
    import httpx

    from modelmetis.audio_teacher import AzureAudioTeacher, validate_prompt

    sentinel = "PRIVATE_RESPONSE_\u00e9"
    response = completion_response()
    response["choices"][0]["message"]["content"] = sentinel
    teacher = AzureAudioTeacher(
        "https://fixture.openai.azure.com", "teacher", lambda: "fixture",
        transport=httpx.MockTransport(lambda request: httpx.Response(200, json=response)),
    )
    try:
        with pytest.raises(ValueError, match="Invalid audio completion"):
            teacher(TeacherRequest(sample().audio, validate_prompt(audio_prompt),
                                   json.dumps(audio_prompt)))
        assert teacher.last_metadata["content_shape"] == "non_json"
        assert teacher.last_metadata["finish_reason"] == "stop"
        expected_hash = hashlib.sha256(sentinel.encode()).hexdigest()
        assert teacher.last_metadata["content_sha256"] == expected_hash
        serialized = json.dumps(teacher.last_metadata)
        assert sentinel not in serialized
        assert json.dumps(sentinel)[1:-1] not in serialized
    finally:
        teacher.close()


def test_system_layout_separates_instructions_and_audio(audio_prompt):
    import httpx

    from modelmetis.audio_teacher import AzureAudioTeacher, validate_prompt

    audio_prompt["message_layout"] = "system-instructions-v1"
    audio_prompt["representation"] = "audio-statistics-v1"
    recording = sample()

    def handle(request):
        messages = json.loads(request.content)["messages"]
        assert [message["role"] for message in messages] == ["system", "user"]
        assert audio_prompt["instructions"] in messages[0]["content"]
        assert audio_prompt["response_contract"] in messages[0]["content"]
        assert messages[1]["content"][0]["text"] == "Classify this recording."
        assert messages[1]["content"][1]["type"] == "input_audio"
        assert messages[1]["content"][2]["text"].startswith("Measurements computed only")
        assert recording.audio.sample_id not in request.content.decode()
        return httpx.Response(200, json=completion_response())

    teacher = AzureAudioTeacher(
        "https://fixture.openai.azure.com", "teacher", lambda: "fixture",
        transport=httpx.MockTransport(handle),
    )
    try:
        teacher(TeacherRequest(recording.audio, validate_prompt(audio_prompt),
                               json.dumps(audio_prompt)))
    finally:
        teacher.close()
    audio_prompt["message_layout"] = "unknown"
    with pytest.raises(ValueError, match="layout"):
        validate_prompt(audio_prompt)


def test_normalization_preserves_shape_without_clipping_or_identity(audio_prompt):
    import base64

    import httpx
    import numpy as np

    from modelmetis.audio_models import acoustic_summary, normalize_audio
    from modelmetis.audio_teacher import AzureAudioTeacher, validate_prompt

    values = np.tile(np.array([-20, -10, 0, 10, 20], dtype="<i2"), 1600)
    content = io.BytesIO()
    with wave.open(content, "wb") as recording:
        recording.setparams((1, 2, 8000, len(values), "NONE", "not compressed"))
        recording.writeframes((values + 7).astype("<i2").tobytes())
    original = ModelAudioInput(uuid.uuid4().hex, content.getvalue())
    normalized, metadata = normalize_audio(original)
    with wave.open(io.BytesIO(normalized.wav_bytes)) as recording:
        result = np.frombuffer(recording.readframes(recording.getnframes()), dtype="<i2")
        assert recording.getframerate() == 8000
    assert abs(float(result.mean())) < 1
    assert np.max(np.abs(result)) == pytest.approx(0.95 * 32767, abs=1)
    assert np.max(np.abs(result - values * metadata["gain"])) < 1
    assert metadata["source_dc_pcm"] == 7
    audio_prompt.update(audio_preprocessing="dc-peak-v1", message_layout="system-instructions-v1")
    audio_prompt["representation"] = "audio-statistics-v1"

    def handle(request):
        messages = json.loads(request.content)["messages"]
        encoded = messages[1]["content"][1]["input_audio"]["data"]
        assert base64.b64decode(encoded) == normalized.wav_bytes
        measured = json.loads(messages[1]["content"][2]["text"].split(": ", 1)[1])
        assert measured == acoustic_summary(normalized)
        assert original.sample_id not in request.content.decode()
        return httpx.Response(200, json=completion_response())

    teacher = AzureAudioTeacher(
        "https://fixture.openai.azure.com", "teacher", lambda: "fixture",
        transport=httpx.MockTransport(handle),
    )
    try:
        teacher(TeacherRequest(original, validate_prompt(audio_prompt), json.dumps(audio_prompt)))
        assert teacher.last_metadata["sent_audio_sha256"] == hashlib.sha256(
            normalized.wav_bytes,
        ).hexdigest()
    finally:
        teacher.close()


def test_acoustic_summary_measures_tone_and_silence_without_identity():
    import io
    import wave

    import numpy as np

    from modelmetis.audio import ModelAudioInput
    from modelmetis.audio_models import acoustic_summary

    for frequency in (0, 440):
        signal = 0.5 * np.sin(2 * np.pi * frequency * np.arange(48000) / 48000)
        content = io.BytesIO()
        with wave.open(content, "wb") as recording:
            recording.setnchannels(1)
            recording.setsampwidth(2)
            recording.setframerate(48000)
            recording.writeframes((signal * 32767).astype("<i2").tobytes())
        identifier = uuid.uuid4().hex
        audio = ModelAudioInput(identifier, content.getvalue())
        result = acoustic_summary(audio)
        assert identifier not in json.dumps(result, allow_nan=False)
        assert result == acoustic_summary(ModelAudioInput(uuid.uuid4().hex, audio.wav_bytes))
        if frequency:
            assert result["strongest_local_spectral_peaks"][0]["frequency_hz"] == 440
            assert result["crest_factor"] == pytest.approx(2 ** 0.5, abs=0.01)
            assert result["energy_fraction_by_band_hz"]["300-1000"] > 0.99
        else:
            assert result["strongest_local_spectral_peaks"] == []
            assert result["crest_factor"] == 0


def test_audio_statistics_transport_contains_only_measured_context(audio_prompt):
    import httpx

    from modelmetis.audio_models import acoustic_summary
    from modelmetis.audio_teacher import AzureAudioTeacher, validate_prompt

    audio_prompt["representation"] = "audio-statistics-v1"
    recording = sample()

    def handle(request):
        body = json.loads(request.content)
        text = body["messages"][0]["content"][2]["text"]
        assert json.loads(text.split(": ", 1)[1]) == acoustic_summary(recording.audio)
        assert recording.audio.sample_id not in request.content.decode()
        return httpx.Response(200, json=completion_response())

    teacher = AzureAudioTeacher("https://fixture.openai.azure.com", "teacher", lambda: "fixture",
                                transport=httpx.MockTransport(handle))
    try:
        teacher(TeacherRequest(recording.audio, validate_prompt(audio_prompt),
                               json.dumps(audio_prompt)))
        assert teacher.last_metadata["acoustic_summary"] == acoustic_summary(recording.audio)
    finally:
        teacher.close()
    audio_prompt["representation"] = "source-labels"
    with pytest.raises(ValueError, match="representation"):
        validate_prompt(audio_prompt)


@pytest.mark.parametrize("mutation", ["version", "truncated", "no_usage", "http_error"])
def test_audio_teacher_fails_closed_without_logging_payload(audio_prompt, mutation):
    import httpx

    from modelmetis.audio_teacher import AzureAudioTeacher

    response = completion_response()
    sentinel = "SOURCE_FAULT_\u00e9_ROTOR"
    if mutation == "version":
        response["model"] = sentinel
    elif mutation == "truncated":
        response["choices"][0]["finish_reason"] = "length"
    elif mutation == "no_usage":
        del response["usage"]
    else:
        response = {"error": {"message": sentinel}}
    teacher = AzureAudioTeacher(
        "https://fixture.openai.azure.com", "teacher", lambda: "fixture-token",
        transport=httpx.MockTransport(lambda request: httpx.Response(
            403 if mutation == "http_error" else 200, json=response,
        )),
    )
    try:
        with pytest.raises((ValueError, RuntimeError)) as error:
            teacher(TeacherRequest(sample().audio, tuple(audio_prompt["taxonomy"]),
                                   json.dumps(audio_prompt)))
        serialized = json.dumps(teacher.last_metadata) + str(error.value)
        assert sentinel not in serialized
        assert json.dumps(sentinel)[1:-1] not in serialized
    finally:
        teacher.close()


def test_audio_cost_uses_conservative_rate_without_modality_breakdown():
    from modelmetis.audio_teacher import usage_cost

    usage, cost = usage_cost({"prompt_tokens": 1000, "completion_tokens": 100})
    assert usage["input_pricing"] == "all_input_at_audio_rate"
    assert cost == pytest.approx(0.033)


@pytest.mark.parametrize("verified", [False, True])
def test_bare_response_model_requires_control_plane_version_check(audio_prompt, verified):
    import httpx

    from modelmetis.audio_teacher import AzureAudioTeacher

    response = completion_response()
    response["model"] = "gpt-audio-1.5"
    teacher = AzureAudioTeacher(
        "https://fixture.openai.azure.com", "teacher", lambda: "fixture",
        deployment_version_verified=verified,
        transport=httpx.MockTransport(lambda request: httpx.Response(200, json=response)),
    )
    try:
        request = TeacherRequest(sample().audio, tuple(audio_prompt["taxonomy"]),
                                 json.dumps(audio_prompt))
        if verified:
            teacher(request)
            assert teacher.last_metadata["deployment_version_verified"]
        else:
            with pytest.raises(ValueError, match="model version"):
                teacher(request)
    finally:
        teacher.close()


@pytest.mark.parametrize("mismatch", [None, "tenant", "version"])
def test_audio_credential_validates_context_without_combining_cli_selectors(
    audio_invocation, monkeypatch, mismatch,
):
    import sys

    from modelmetis import simulation

    args = audio_invocation
    captured = []

    class Credential:
        def __init__(self, **kwargs):
            assert kwargs == {"subscription": args.subscription, "process_timeout": 10}

        def get_token(self, scope):
            captured.append(scope)
            return SimpleNamespace(token="fixture-token")

    def account_context(command, **kwargs):
        assert command[-4:] == ["--subscription", args.subscription, "--output", "json"]
        if command[1:3] == ["account", "show"]:
            result = {"id": args.subscription,
                      "tenantId": "wrong" if mismatch == "tenant" else args.tenant_id}
        else:
            assert command[1:5] == ["cognitiveservices", "account", "deployment", "show"]
            result = {"properties": {"model": {
                "name": "gpt-audio-1.5",
                "version": "wrong" if mismatch == "version" else "2026-02-23",
            }, "provisioningState": "Succeeded", "versionUpgradeOption": "NoAutoUpgrade"}}
        return SimpleNamespace(returncode=0, stdout=json.dumps(result))

    monkeypatch.setitem(sys.modules, "azure.identity",
                        SimpleNamespace(AzureCliCredential=Credential))
    monkeypatch.setattr(simulation.subprocess, "run", account_context)
    if mismatch:
        with pytest.raises(ValueError, match="tenant mismatch|fixed teacher version"):
            simulation.make_audio_teacher(args)
        assert captured == []
    else:
        teacher = simulation.make_audio_teacher(args)
        try:
            assert teacher.token_provider() == "fixture-token"
            assert teacher.deployment_version_verified
            assert captured == ["https://ai.azure.com/.default"]
        finally:
            teacher.close()


def test_campaign_ledger_reserves_before_io_and_survives_restart(tmp_path):
    from modelmetis.simulation import CampaignLedger

    path = tmp_path / "ledger.json"
    with CampaignLedger(path, 2) as budget:
        budget.begin_request()
        persisted = json.loads(path.read_text())
        assert set(persisted) == {
            "schema", "max_requests", "request_reserve_usd", "requests", "accounted_usd",
        }
        assert persisted["requests"] == 1
        assert persisted["accounted_usd"] == 4.11
    with CampaignLedger(path, 2) as budget:
        budget.begin_request()
        budget.finish_request(None)
        with pytest.raises(RuntimeError, match="limit"):
            budget.begin_request()
    assert json.loads(path.read_text())["accounted_usd"] == 8.22
    assert not path.with_suffix(".json.lock").exists()


def test_campaign_ledger_refunds_only_verified_cost_and_enforces_call_limit(tmp_path):
    from modelmetis.simulation import CampaignLedger

    path = tmp_path / "ledger.json"
    with CampaignLedger(path, 1) as budget:
        budget.begin_request()
        budget.finish_request(0.02)
        assert budget.state["accounted_usd"] == pytest.approx(0.02)
        with pytest.raises(RuntimeError, match="limit"):
            budget.begin_request()
        with pytest.raises(FileExistsError), CampaignLedger(path, 1):
            pytest.fail("Concurrent campaign was allowed.")
    with pytest.raises(ValueError, match="changed campaign"), CampaignLedger(path, 2):
        pytest.fail("Changed campaign request limit was accepted.")


@pytest.fixture
def audio_invocation(training_invocation, audio_prompt):
    args, _ = training_invocation
    args.prompts = args.input.parent / "prompts.json"
    args.prompts.write_text(json.dumps({"fixture": audio_prompt}), encoding="utf-8")
    args.variant = "fixture"
    args.endpoint = "https://fixture.openai.azure.com"
    args.deployment = "teacher"
    args.tenant_id = str(uuid.uuid4())
    args.subscription = str(uuid.uuid4())
    args.resource_group = "fixture-audio"
    args.ledger = args.input.parent / "ledger.json"
    args.max_requests = 10
    args.deadline_seconds = 1800
    args.minimum_score = 0
    args.acknowledge_paid_requests = True
    args.output = args.input.parent / "audio-output"
    return args


@pytest.mark.parametrize("with_support", [False, True])
def test_audio_worker_and_real_training_use_only_audio_teacher_labels(
    audio_invocation, monkeypatch, with_support,
):
    import httpx

    from modelmetis import simulation
    from modelmetis.audio_teacher import AzureAudioTeacher

    args = audio_invocation
    labels = iter(["healthy", "faulty", "healthy", "faulty"])
    if with_support:
        args.support = args.input.parent / "support"
        args.support.mkdir()
        rows = []
        for value, label in ((101, "faulty"), (102, "healthy")):
            item = sample(value=value)
            (args.support / f"{item.audio.sample_id}.wav").write_bytes(item.audio.wav_bytes)
            rows.append({"sample_id": item.audio.sample_id, "group_id": item.group_id,
                         "label": label,
                         "audio_sha256": hashlib.sha256(item.audio.wav_bytes).hexdigest()})
        simulation.write_json(args.support / "manifest.json", {
            "schema": 1, "label_source": "simulated_human_from_publisher",
            "origin_partition": "train", "examples": rows,
        })
        prompts = json.loads(args.prompts.read_text())
        prompts[args.variant]["message_layout"] = "system-instructions-v1"
        simulation.write_json(args.prompts, prompts)

    def handle(request):
        if with_support:
            messages = json.loads(request.content)["messages"]
            assert len(messages) == 6
            assert json.loads(messages[2]["content"])["label"] == "faulty"
            assert json.loads(messages[4]["content"])["label"] == "healthy"
        response = completion_response(json.dumps({
            "label": next(labels), "score": 0.6, "observations": [],
        }))
        return httpx.Response(200, json=response)

    monkeypatch.setattr(simulation, "make_audio_teacher", lambda arguments: AzureAudioTeacher(
        arguments.endpoint, arguments.deployment, lambda: "fixture",
        transport=httpx.MockTransport(handle),
    ))
    simulation.infer_audio(args)
    report_path = args.output / "predictions.json"
    report = json.loads(report_path.read_text())
    assert report["complete"]
    assert report["termination"] == "completed"
    assert report["prompt_format"] == "audio-json-v1"
    assert "budget" not in json.dumps(report).lower()
    assert report["campaign_accounting"]["requests"] == 4
    assert report["campaign_accounting"]["accounted_usd"] == pytest.approx(4 * 0.01655)
    if with_support:
        assert report["support"]["example_count"] == 2
        assert report["support"]["label_source"] == "simulated_human_from_publisher"
        assert report["support"]["support_set_sha256"] == report["prompt"]["support_set_sha256"]
        assert all(row["metadata"]["support_examples"] == 2 for row in report["predictions"])
    training = SimpleNamespace(input=args.input, silver=report_path,
                               output=args.input.parent / "audio-trained")
    simulation.train(training)
    fitted = json.loads((training.output / "training.json").read_text())
    assert fitted["class_counts"] == {"healthy": 2, "faulty": 2}
    with pytest.raises(FileExistsError):
        simulation.infer_audio(args)


@pytest.mark.parametrize("failure", ["transport", "request_limit", "deadline"])
def test_audio_worker_preserves_incomplete_attempt(audio_invocation, monkeypatch, failure):
    import httpx

    from modelmetis import simulation
    from modelmetis.audio_teacher import AzureAudioTeacher

    args = audio_invocation
    calls = []
    sentinel = "SOURCE_FAULT_\u00e9_ROTOR"

    def handle(request):
        calls.append(request)
        if failure == "transport":
            raise httpx.ReadTimeout(sentinel)
        return httpx.Response(200, json=completion_response())

    monkeypatch.setattr(simulation, "make_audio_teacher", lambda arguments: AzureAudioTeacher(
        arguments.endpoint, arguments.deployment, lambda: "fixture",
        transport=httpx.MockTransport(handle),
    ))
    if failure == "request_limit":
        args.max_requests = 1
    elif failure == "deadline":
        args.deadline_seconds = 1
    with pytest.raises(RuntimeError):
        simulation.infer_audio(args)
    serialized = (args.output / "predictions.json").read_text()
    report = json.loads(serialized)
    assert not report["complete"]
    assert report["ended_utc"]
    assert sentinel not in serialized
    assert json.dumps(sentinel)[1:-1] not in serialized
    assert len(calls) == (0 if failure == "deadline" else 1)
    if failure == "transport":
        assert report["campaign_accounting"]["accounted_usd"] == 4.11
        assert report["predictions"][0]["error_code"] == "teacher_request_failed"


def test_audio_worker_rejects_consumed_test_before_network(audio_invocation, monkeypatch):
    from modelmetis import simulation

    args = audio_invocation
    path = args.input / "manifest.json"
    manifest = json.loads(path.read_text())
    for row in manifest:
        row["partition"] = "test"
    path.write_text(json.dumps(manifest))
    monkeypatch.setattr(simulation, "make_audio_teacher",
                        lambda arguments: pytest.fail("Network constructed for test set"))
    with pytest.raises(ValueError, match="consumed final test"):
        simulation.infer_audio(args)
    assert not args.output.exists()


def test_audio_worker_rejects_invalid_support_before_accounting(audio_invocation, monkeypatch):
    from modelmetis import simulation

    args = audio_invocation
    args.support = args.input.parent / "held-out-support"
    args.support.mkdir()
    simulation.write_json(args.support / "manifest.json", {
        "schema": 1, "label_source": "simulated_human_from_publisher",
        "origin_partition": "development", "examples": [],
    })
    monkeypatch.setattr(simulation, "make_audio_teacher",
                        lambda arguments: pytest.fail("Network constructed for invalid support"))
    with pytest.raises(ValueError, match="provenance"):
        simulation.infer_audio(args)
    assert not args.output.exists()
    assert not args.ledger.exists()


def test_registered_audio_prompts_have_same_taxonomy_and_no_reference_input():
    from pathlib import Path

    from modelmetis.audio_teacher import validate_prompt

    path = Path(__file__).resolve().parents[1] / "configs" / "audio-llm-prompts.json"
    prompts = json.loads(path.read_text(encoding="utf-8"))
    assert set(prompts) == {"direct-v1", "evidence-v1"}
    assert prompts["direct-v1"]["taxonomy"] == prompts["evidence-v1"]["taxonomy"]
    for prompt in prompts.values():
        assert len(validate_prompt(prompt)) == 8


def test_learning_curve_uses_nested_randomized_arrivals_not_reference_classes(
    training_invocation, monkeypatch,
):
    import random

    from modelmetis import simulation

    args, collection = training_invocation
    order = sorted(example.audio.sample_id for example in collection.examples)
    random.Random(17).shuffle(order)
    captured = []

    def capture(examples):
        captured.append({example.audio.sample_id: example.label for example in examples})
        return {"fixture": "not a fitted model"}

    monkeypatch.setattr(simulation, "fit_specialist", capture)
    for count in (2, 4):
        args.sample_count = count
        args.output = args.input.parent / f"snapshot-{count}"
        simulation.train(args)
        assert set(captured[-1]) == set(order[:count])
        expected = {example.audio.sample_id: example.label for example in collection.examples
                    if example.audio.sample_id in order[:count]}
        assert captured[-1] == expected
        report = json.loads((args.output / "training.json").read_text())
        assert report["observed_examples"] == count
    assert captured[0].items() <= captured[1].items()


def test_one_class_snapshot_cannot_fit(training_invocation):
    from modelmetis.simulation import train

    args, _ = training_invocation
    args.sample_count = 1
    with pytest.raises(ValueError, match="two teacher classes"):
        train(args)
    assert not args.output.exists()
