import hashlib
import os
import re
import sqlite3
import uuid
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path
from typing import Literal

from modelmetis.audio import ModelAudioInput, canonical_wav, inspect_wav

ReviewLabel = Literal["healthy", "fault_unspecified", "needs_review"]
REVIEW_LABELS: tuple[ReviewLabel, ...] = ("healthy", "fault_unspecified", "needs_review")

SCHEMA = """
CREATE TABLE IF NOT EXISTS recordings (
    id TEXT PRIMARY KEY,
    filename TEXT NOT NULL,
    created_at TEXT NOT NULL,
    sample_rate INTEGER NOT NULL,
    channels INTEGER NOT NULL,
    bits_per_sample INTEGER NOT NULL,
    frames INTEGER NOT NULL,
    duration_seconds REAL NOT NULL,
    byte_length INTEGER NOT NULL,
    sha256 TEXT NOT NULL,
    synthetic INTEGER NOT NULL CHECK (synthetic IN (0, 1)),
    human_label TEXT CHECK (human_label IN ('healthy', 'fault_unspecified', 'needs_review')),
    review_note TEXT NOT NULL DEFAULT '',
    revision INTEGER NOT NULL DEFAULT 0,
    reviewed_at TEXT
);
CREATE TABLE IF NOT EXISTS reviews (
    recording_id TEXT NOT NULL REFERENCES recordings(id),
    revision INTEGER NOT NULL,
    human_label TEXT NOT NULL,
    review_note TEXT NOT NULL,
    reviewed_at TEXT NOT NULL,
    PRIMARY KEY (recording_id, revision)
);
CREATE INDEX IF NOT EXISTS recording_created ON recordings(created_at DESC, id DESC);
"""


class RecordingNotFound(LookupError):
    pass


class RevisionConflict(Exception):
    def __init__(self, current_revision: int):
        self.current_revision = current_revision
        super().__init__("The recording was reviewed elsewhere. Reload before saving.")


class RecordingRepository:
    def __init__(self, directory: Path):
        self.directory = directory.resolve()
        self.audio_directory = self.directory / "audio"
        self.database = self.directory / "recordings.sqlite3"

    @contextmanager
    def connection(self) -> Iterator[sqlite3.Connection]:
        connection = sqlite3.connect(self.database, timeout=5)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        try:
            with connection:
                yield connection
        finally:
            connection.close()

    def initialize(self) -> None:
        self.audio_directory.mkdir(parents=True, exist_ok=True)
        with self.connection() as connection:
            connection.execute("PRAGMA journal_mode = WAL")
            connection.executescript(SCHEMA)

    def check_ready(self) -> None:
        with self.connection() as connection:
            connection.execute("BEGIN IMMEDIATE")
            connection.execute("SELECT id FROM recordings LIMIT 1").fetchall()
            connection.execute("SELECT recording_id FROM reviews LIMIT 1").fetchall()
            connection.execute("UPDATE recordings SET revision = revision WHERE 0")
            connection.rollback()
        probe = self.audio_directory / f".ready-{uuid.uuid4().hex}"
        try:
            with probe.open("xb") as stream:
                stream.write(b"ready")
                stream.flush()
                os.fsync(stream.fileno())
            if probe.read_bytes() != b"ready":
                raise OSError("Storage verification failed.")
        finally:
            probe.unlink(missing_ok=True)

    def _audio_path(self, recording_id: str) -> Path:
        if not re.fullmatch(r"[0-9a-f]{32}", recording_id):
            raise RecordingNotFound("Recording not found.")
        path = self.audio_directory / f"{recording_id}.wav"
        if path.is_symlink() or path.resolve().parent != self.audio_directory.resolve():
            raise RecordingNotFound("Recording not found.")
        return path

    @staticmethod
    def _record(row: sqlite3.Row) -> dict:
        result = {key: row[key] for key in (
            "id", "created_at", "sample_rate", "channels", "bits_per_sample", "frames",
            "duration_seconds", "byte_length", "sha256", "synthetic", "human_label",
            "review_note", "revision", "reviewed_at",
        )}
        result["filename"] = f"sample-{row['id']}.wav"
        result["synthetic"] = bool(result["synthetic"])
        result["prediction"] = {"status": "not_available", "label": None}
        return result

    def add(
        self, payload: bytes, synthetic: bool, max_bytes: int
    ) -> dict:
        payload = canonical_wav(payload, max_bytes)
        metadata = inspect_wav(payload, max_bytes)
        recording_id = uuid.uuid4().hex
        filename = f"sample-{recording_id}.wav"
        created_at = datetime.now(UTC).isoformat()
        path = self._audio_path(recording_id)
        temporary = path.with_suffix(".upload")
        try:
            with temporary.open("xb") as stream:
                stream.write(payload)
                stream.flush()
                os.fsync(stream.fileno())
            temporary.replace(path)
            with self.connection() as connection:
                connection.execute(
                    """INSERT INTO recordings (
                        id, filename, created_at, sample_rate, channels, bits_per_sample,
                        frames, duration_seconds, byte_length, sha256, synthetic
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (
                        recording_id, filename, created_at, metadata.sample_rate,
                        metadata.channels, metadata.bits_per_sample, metadata.frames,
                        metadata.duration_seconds, metadata.byte_length,
                        hashlib.sha256(payload).hexdigest(), int(synthetic),
                    ),
                )
        except BaseException:
            path.unlink(missing_ok=True)
            raise
        finally:
            temporary.unlink(missing_ok=True)
        return self.get(recording_id)

    def get(self, recording_id: str) -> dict:
        with self.connection() as connection:
            row = connection.execute(
                "SELECT * FROM recordings WHERE id = ?", (recording_id,)
            ).fetchone()
        if row is None:
            raise RecordingNotFound("Recording not found.")
        return self._record(row)

    def list(
        self, search: str = "", label: str = "all", limit: int = 50, offset: int = 0
    ) -> dict:
        clauses = ["instr('sample-' || id || '.wav', lower(?)) > 0"]
        parameters: list[str | int] = [search]
        if label == "unreviewed":
            clauses.append("human_label IS NULL")
        elif label in REVIEW_LABELS:
            clauses.append("human_label = ?")
            parameters.append(label)
        elif label != "all":
            raise ValueError("Unknown review filter.")
        where = " AND ".join(clauses)
        with self.connection() as connection:
            connection.execute("BEGIN")
            total = connection.execute(
                f"SELECT COUNT(*) FROM recordings WHERE {where}", parameters
            ).fetchone()[0]
            rows = connection.execute(
                f"SELECT * FROM recordings WHERE {where} "
                "ORDER BY created_at DESC, id DESC LIMIT ? OFFSET ?",
                [*parameters, limit, offset],
            ).fetchall()
        return {"items": [self._record(row) for row in rows], "total": total}

    def counts(self) -> dict:
        with self.connection() as connection:
            row = connection.execute(
                """SELECT COUNT(*) AS total,
                    COALESCE(SUM(human_label IS NULL), 0) AS unreviewed,
                    COALESCE(SUM(human_label IS NOT NULL), 0) AS reviewed,
                    COALESCE(SUM(synthetic), 0) AS synthetic
                    FROM recordings"""
            ).fetchone()
        return dict(row)

    def audio_path(self, recording_id: str) -> Path:
        self.get(recording_id)
        path = self._audio_path(recording_id)
        if not path.is_file():
            raise OSError("Stored audio is unavailable.")
        return path

    def model_input(self, recording_id: str, max_bytes: int) -> ModelAudioInput:
        path = self._audio_path(recording_id)
        with self.connection() as connection:
            exists = connection.execute(
                "SELECT id FROM recordings WHERE id = ?", (recording_id,)
            ).fetchone()
        if exists is None:
            raise RecordingNotFound("Recording not found.")
        with path.open("rb") as stream:
            payload = stream.read(max_bytes + 1)
        return ModelAudioInput(recording_id, canonical_wav(payload, max_bytes))

    def save_review(
        self, recording_id: str, expected_revision: int, human_label: ReviewLabel, note: str
    ) -> dict:
        reviewed_at = datetime.now(UTC).isoformat()
        with self.connection() as connection:
            connection.execute("BEGIN IMMEDIATE")
            current = connection.execute(
                "SELECT revision FROM recordings WHERE id = ?", (recording_id,)
            ).fetchone()
            if current is None:
                raise RecordingNotFound("Recording not found.")
            if current["revision"] != expected_revision:
                raise RevisionConflict(current["revision"])
            revision = expected_revision + 1
            connection.execute(
                """UPDATE recordings SET human_label = ?, review_note = ?, revision = ?,
                    reviewed_at = ? WHERE id = ? AND revision = ?""",
                (human_label, note, revision, reviewed_at, recording_id, expected_revision),
            )
            connection.execute(
                "INSERT INTO reviews VALUES (?, ?, ?, ?, ?)",
                (recording_id, revision, human_label, note, reviewed_at),
            )
            saved = connection.execute(
                "SELECT * FROM recordings WHERE id = ?", (recording_id,)
            ).fetchone()
        return self._record(saved)