import hashlib
import math
import uuid
from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from typing import Literal

from modelmetis.audio import ModelAudioInput, canonical_wav


@dataclass(frozen=True)
class Sample:
    audio: ModelAudioInput
    group_id: str
    partition: Literal["development", "train", "test"]

    def __post_init__(self):
        for identifier in (self.audio.sample_id, self.group_id):
            if uuid.UUID(identifier).hex != identifier:
                raise ValueError("Sample and group IDs must be opaque UUID hex strings.")
        if self.partition not in ("development", "train", "test"):
            raise ValueError("Unknown partition.")
        object.__setattr__(self, "audio", ModelAudioInput(
            self.audio.sample_id, canonical_wav(self.audio.wav_bytes, 32 * 1024 * 1024)
        ))


def validate_split(samples: Sequence[Sample]) -> None:
    if not samples:
        raise ValueError("An empty dataset is not a valid experiment.")
    identifiers: set[str] = set()
    groups: dict[str, str] = {}
    contents: dict[str, str] = {}
    for sample in samples:
        identifier = sample.audio.sample_id
        if identifier in identifiers:
            raise ValueError("Duplicate sample ID.")
        identifiers.add(identifier)
        digest = hashlib.sha256(sample.audio.wav_bytes).hexdigest()
        for mapping, key in ((groups, sample.group_id), (contents, digest)):
            previous = mapping.setdefault(key, sample.partition)
            if previous != sample.partition:
                raise ValueError("Acquisition group or duplicate audio crosses partitions.")


@dataclass(frozen=True)
class TeacherRequest:
    audio: ModelAudioInput
    taxonomy: tuple[str, ...]
    prompt: str


@dataclass(frozen=True)
class TeacherDecision:
    label: str | None
    score: float


@dataclass(frozen=True)
class SilverExample:
    audio: ModelAudioInput
    label: str
    score: float
    teacher_id: str
    prompt_sha256: str
    label_source: Literal["teacher"] = field(default="teacher", init=False)


@dataclass(frozen=True)
class Collection:
    examples: tuple[SilverExample, ...]
    attempted: int
    abstained: int
    failed: int


def collect_silver(
    samples: Sequence[Sample],
    teacher: Callable[[TeacherRequest], TeacherDecision],
    *,
    taxonomy: tuple[str, ...],
    prompt: str,
    teacher_id: str,
    minimum_score: float = 0.0,
) -> Collection:
    validate_split(samples)
    if any(sample.partition != "train" for sample in samples):
        raise ValueError("Only the training partition may enter silver collection.")
    if len(taxonomy) < 2 or len(set(taxonomy)) != len(taxonomy) or not all(taxonomy):
        raise ValueError("Provide at least two distinct class names.")
    if not prompt.strip() or not teacher_id.strip():
        raise ValueError("Prompt and teacher identity are required.")
    if not math.isfinite(minimum_score) or not 0 <= minimum_score <= 1:
        raise ValueError("Minimum score must be between zero and one.")
    prompt_hash = hashlib.sha256(prompt.encode("utf-8")).hexdigest()
    examples = []
    abstained = 0
    failed = 0
    for sample in samples:
        try:
            decision = teacher(TeacherRequest(sample.audio, taxonomy, prompt))
            if not isinstance(decision, TeacherDecision):
                raise ValueError("Invalid teacher response.")
            if not math.isfinite(decision.score) or not 0 <= decision.score <= 1:
                raise ValueError("Invalid teacher score.")
            if decision.label is not None and decision.label not in taxonomy:
                raise ValueError("Unknown teacher label.")
        except Exception:
            failed += 1
            continue
        if decision.label is None or decision.score < minimum_score:
            abstained += 1
            continue
        examples.append(SilverExample(
            sample.audio, decision.label, decision.score, teacher_id, prompt_hash
        ))
    return Collection(tuple(examples), len(samples), abstained, failed)


def training_targets(examples: Sequence[SilverExample]) -> tuple[str, ...]:
    if not examples:
        raise ValueError("No accepted teacher labels; training must not run.")
    if any(type(example) is not SilverExample for example in examples):
        raise ValueError("Training requires teacher-produced silver examples.")
    labels = tuple(example.label for example in examples)
    if len(set(labels)) < 2:
        raise ValueError("Fewer than two teacher classes; training must not run.")
    if len({example.teacher_id for example in examples}) != 1:
        raise ValueError("Freeze the teacher before collection.")
    if len({example.prompt_sha256 for example in examples}) != 1:
        raise ValueError("Freeze the prompt before collection.")
    if len({example.audio.sample_id for example in examples}) != len(examples):
        raise ValueError("Duplicate training example.")
    return labels
