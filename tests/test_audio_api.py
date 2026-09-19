import io
import json
import struct
import uuid
import wave
from concurrent.futures import ThreadPoolExecutor
from dataclasses import fields
from threading import Barrier

import pytest
from fastapi.testclient import TestClient

from modelmetis.api import create_app
from modelmetis.audio import InvalidAudio, inspect_wav
from modelmetis.repository import RecordingNotFound, RecordingRepository, RevisionConflict
from modelmetis.settings import Settings


def pcm_wav(*, channels=1, width=2, frames=80, rate=8000) -> bytes:
    stream = io.BytesIO()
    with wave.open(stream, "wb") as audio:
        audio.setnchannels(channels)
        audio.setsampwidth(width)
        audio.setframerate(rate)
        audio.writeframes(bytes(frames * channels * width))
    return stream.getvalue()


@pytest.fixture
def settings(tmp_path):
    return Settings(data_directory=tmp_path / "store", max_upload_bytes=4096)


@pytest.fixture
def client(settings):
    with TestClient(
        create_app(settings), base_url="http://127.0.0.1:8000", client=("127.0.0.1", 51000)
    ) as http:
        yield http


def upload(client, payload=None, *, filename="fixture.wav", synthetic=True):
    return client.post(
        "/api/recordings",
        params={"filename": filename, "synthetic": str(synthetic).lower()},
        content=pcm_wav() if payload is None else payload,
        headers={"Content-Type": "audio/wav"},
    )


def save_review(client, recording_id, revision=0, label="healthy", note="Manual review"):
    return client.put(
        f"/api/recordings/{recording_id}/review",
        json={"expected_revision": revision, "human_label": label, "note": note},
    )


def test_health_readiness_and_honest_empty_status(client):
    health = client.get("/healthz", follow_redirects=False)
    assert health.status_code == 200
    assert health.json() == {"status": "ok"}
    assert client.get("/readyz", follow_redirects=False).status_code == 200
    status = client.get("/api/status").json()
    assert status["counts"] == {"total": 0, "reviewed": 0, "unreviewed": 0, "synthetic": 0}
    assert status["specialist"]["status"] == "not_trained"
    assert status["evaluation"]["status"] == "not_evaluated"
    assert status["teacher"]["status"] == "not_configured"
    assert status["dataset"]["status"] == "not_downloaded"
    assert status["review_taxonomy"] == ["healthy", "fault_unspecified", "needs_review"]
    assert client.get("/api/recordings").json() == {"items": [], "total": 0}


@pytest.mark.parametrize("channels,width,rate", [(1, 1, 8000), (2, 2, 42000), (1, 3, 44100),
                                               (2, 4, 192000)])
def test_pcm_upload_metadata_and_exact_audio_roundtrip(client, channels, width, rate):
    payload = pcm_wav(channels=channels, width=width, rate=rate)
    response = upload(client, payload)
    assert response.status_code == 201
    recording = response.json()
    assert recording["sample_rate"] == rate
    assert recording["channels"] == channels
    assert recording["bits_per_sample"] == width * 8
    assert recording["frames"] == 80
    assert recording["duration_seconds"] == pytest.approx(80 / rate)
    assert recording["byte_length"] == len(payload)
    assert recording["synthetic"] is True
    assert "reference_label" not in recording
    assert recording["human_label"] is None
    assert recording["prediction"] == {"status": "not_available", "label": None}
    audio = client.get(f"/api/recordings/{recording['id']}/audio")
    assert audio.status_code == 200
    assert audio.content == payload
    assert audio.headers["content-type"] == "audio/wav"
    partial = client.get(
        f"/api/recordings/{recording['id']}/audio", headers={"Range": "bytes=0-15"}
    )
    assert partial.status_code == 206
    assert partial.content == payload[:16]


@pytest.mark.parametrize(
    "field_offset,format_code,value",
    [(4, "I", 0), (20, "H", 3), (22, "H", 0), (24, "I", 0),
     (24, "I", 0x7FC00000), (28, "I", 1), (32, "H", 0), (34, "H", 7), (40, "I", 9999)],
)
def test_invalid_pcm_headers_leave_storage_empty(client, field_offset, format_code, value):
    payload = bytearray(pcm_wav())
    struct.pack_into(f"<{format_code}", payload, field_offset, value)
    response = upload(client, bytes(payload))
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "invalid_audio"
    assert client.get("/api/status").json()["counts"]["total"] == 0


@pytest.mark.parametrize("payload", [b"", b"not a wav", pcm_wav(frames=0), pcm_wav()[:-1]])
def test_invalid_or_empty_audio_is_rejected(client, payload):
    assert upload(client, payload).status_code == 422


def test_partial_pcm_frame_is_rejected(client):
    payload = bytearray(pcm_wav()[:-1])
    struct.pack_into("<I", payload, 4, len(payload) - 8)
    struct.pack_into("<I", payload, 40, len(payload) - 44)
    assert upload(client, bytes(payload)).status_code == 422


def test_duration_limit():
    payload = pcm_wav(width=1, frames=8000 * 121)
    with pytest.raises(InvalidAudio, match="120 seconds"):
        inspect_wav(payload, 2 * 1024 * 1024)


def test_oversize_declared_and_streamed_uploads(client):
    response = upload(client, b"x" * 4097)
    assert response.status_code == 413

    def chunks():
        yield b"a" * 2048
        yield b"b" * 2049

    response = client.post(
        "/api/recordings?filename=large.wav&synthetic=true", content=chunks(),
        headers={"Content-Type": "audio/wav"},
    )
    assert response.status_code == 413
    assert response.json()["error"]["code"] == "too_large"
    assert client.get("/api/status").json()["counts"]["total"] == 0


def test_display_filename_cannot_control_storage_path(client, settings):
    recording = upload(client, filename="../../outside\\test.wav").json()
    assert recording["filename"] == f"sample-{recording['id']}.wav"
    assert len(recording["id"]) == 32
    files = list((settings.data_directory / "audio").iterdir())
    assert [file.name for file in files] == [f"{recording['id']}.wav"]
    with pytest.raises(RecordingNotFound):
        client.app.state.repository.audio_path("../../escape")


def test_review_persists_across_application_instances(client, settings):
    recording = upload(client).json()
    response = save_review(client, recording["id"], label="fault_unspecified", note="Needs audit")
    assert response.status_code == 200
    assert response.json()["revision"] == 1
    with TestClient(
        create_app(settings), base_url="http://127.0.0.1:8000", client=("127.0.0.1", 51001)
    ) as restarted:
        stored = restarted.get(f"/api/recordings/{recording['id']}").json()
        assert stored["human_label"] == "fault_unspecified"
        assert stored["review_note"] == "Needs audit"
        assert stored["reviewed_at"] is not None
        assert "reference_label" not in stored
        assert stored["prediction"]["label"] is None
        assert restarted.get(f"/api/recordings/{recording['id']}/audio").content == pcm_wav()


def test_stale_revision_returns_409_without_overwrite(client):
    recording_id = upload(client).json()["id"]
    assert save_review(client, recording_id).status_code == 200
    conflict = save_review(client, recording_id, label="fault_unspecified")
    assert conflict.status_code == 409
    assert conflict.json()["error"]["current_revision"] == 1
    stored = client.get(f"/api/recordings/{recording_id}").json()
    assert stored["human_label"] == "healthy"
    assert stored["revision"] == 1
    assert save_review(client, recording_id, revision=1, label="needs_review").status_code == 200


def test_concurrent_review_has_one_winner_and_one_history_entry(client, settings):
    recording_id = upload(client).json()["id"]
    barrier = Barrier(2)

    def attempt(label):
        repository = RecordingRepository(settings.data_directory)
        barrier.wait(timeout=5)
        try:
            repository.save_review(recording_id, 0, label, "Concurrent test")
            return "saved"
        except RevisionConflict:
            return "conflict"

    with ThreadPoolExecutor(max_workers=2) as executor:
        outcomes = list(executor.map(attempt, ["healthy", "needs_review"]))
    assert sorted(outcomes) == ["conflict", "saved"]
    with client.app.state.repository.connection() as connection:
        assert connection.execute("SELECT COUNT(*) FROM reviews").fetchone()[0] == 1
    assert client.get(f"/api/recordings/{recording_id}").json()["revision"] == 1


def test_search_filters_pagination_and_real_counts(client):
    first = upload(client, filename="Pump North.wav").json()
    upload(client, filename="Fan South.wav", synthetic=False)
    save_review(client, first["id"], label="needs_review")
    result = client.get(
        f"/api/recordings?search={first['id']}&label=needs_review"
    ).json()
    assert result["total"] == 1
    assert result["items"][0]["id"] == first["id"]
    assert client.get("/api/recordings?label=unreviewed").json()["total"] == 1
    page = client.get("/api/recordings?limit=1&offset=1").json()
    assert len(page["items"]) == 1
    assert page["total"] == 2
    assert client.get("/api/recordings?search=%25").json()["total"] == 0
    assert client.get("/api/recordings?search=north").json()["total"] == 0
    assert client.get("/api/status").json()["counts"] == {
        "total": 2, "reviewed": 1, "unreviewed": 1, "synthetic": 1,
    }


def test_missing_recording_has_json_404(client):
    missing = uuid.uuid4().hex
    for endpoint in (f"/api/recordings/{missing}", f"/api/recordings/{missing}/audio"):
        response = client.get(endpoint)
        assert response.status_code == 404
        assert response.json()["error"]["code"] == "not_found"
    assert save_review(client, missing).status_code == 404
    assert client.get("/api/recordings/not-an-id/audio").status_code == 422


@pytest.mark.parametrize("revision,label", [(-1, "healthy"), (True, "healthy"),
                                          (1.5, "healthy"), (0, "invented_ottawa_class")])
def test_invalid_reviews(client, revision, label):
    recording_id = upload(client).json()["id"]
    assert save_review(client, recording_id, revision=revision, label=label).status_code == 422
    assert client.get(f"/api/recordings/{recording_id}").json()["revision"] == 0


def test_review_body_is_bounded(client):
    recording_id = upload(client).json()["id"]
    assert save_review(client, recording_id, note="a" * 2001).status_code == 422
    assert save_review(client, recording_id, note="a" * 17000).status_code == 413


def test_unavailable_storage_changes_readiness_not_liveness(client, monkeypatch):
    def unavailable():
        raise OSError("Private path must not be returned to the client")

    monkeypatch.setattr(client.app.state.repository, "check_ready", unavailable)
    response = client.get("/readyz")
    assert response.status_code == 503
    assert response.json()["error"]["message"] == "Local storage is unavailable."
    assert client.get("/healthz").status_code == 200


def test_failed_initialization_preserves_liveness(tmp_path):
    blocked = tmp_path / "file-not-directory"
    blocked.write_bytes(b"fixture")
    with TestClient(
        create_app(Settings(data_directory=blocked)), base_url="http://127.0.0.1:8000",
        client=("127.0.0.1", 51000),
    ) as http:
        assert http.get("/healthz").status_code == 200
        assert http.get("/readyz").status_code == 503


def test_production_and_nonlocal_origins_fail_closed():
    with pytest.raises(ValueError, match="Production is disabled"):
        Settings(mode="production")
    with pytest.raises(ValueError, match="local HTTP origins"):
        Settings(origins=("https://example.org",))


def test_host_origin_and_forwarding_headers_do_not_grant_access(client):
    for headers in (
        {"Host": "attacker.example"}, {"Origin": "https://attacker.example"},
        {"X-Forwarded-For": "127.0.0.1"}, {"Forwarded": "for=127.0.0.1"},
    ):
        response = client.get("/api/status", headers=headers)
        assert response.status_code == 403
    response = client.get("/api/status", headers={"Origin": "http://127.0.0.1:5173"})
    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "http://127.0.0.1:5173"


def test_remote_peer_cannot_authenticate_with_client_headers(settings):
    with TestClient(
        create_app(settings), base_url="http://127.0.0.1:8000", client=("192.0.2.1", 51000)
    ) as remote:
        response = remote.get(
            "/api/status", headers={"Authorization": "Bearer fake", "X-User-Id": "admin"}
        )
        assert response.status_code == 403


def test_wrong_media_type_and_missing_provenance_are_rejected(client):
    response = client.post(
        "/api/recordings?filename=test.wav&synthetic=true", content=pcm_wav(),
        headers={"Content-Type": "text/plain"},
    )
    assert response.status_code == 415
    assert client.post("/api/recordings?filename=test.wav", content=pcm_wav()).status_code == 422


def test_label_metadata_is_removed_without_changing_pcm(client, caplog):
    secret = "SOURCE_FAULT_\u00e9_ROTOR"
    raw = pcm_wav()
    metadata = secret.encode("utf-8")
    chunk = b"LIST" + struct.pack("<I", len(metadata)) + metadata
    if len(metadata) % 2:
        chunk += b"\x00"
    contaminated = bytearray(raw + chunk)
    struct.pack_into("<I", contaminated, 4, len(contaminated) - 8)
    assert metadata in contaminated
    response = upload(client, bytes(contaminated), filename=f"{secret}.wav")
    assert response.status_code == 201
    sample = response.json()
    served = client.get(f"/api/recordings/{sample['id']}/audio").content
    assert served == raw
    assert sample["byte_length"] == len(raw)
    serialized = json.dumps(sample)
    for marker in (secret, json.dumps(secret)[1:-1]):
        assert marker not in serialized
        assert marker not in caplog.text
    assert metadata not in served
    assert client.get("/api/recordings").json()["total"] == 1


def test_model_input_and_review_view_exclude_legacy_reference_fields(client, monkeypatch):
    sample = upload(client).json()
    repository = client.app.state.repository
    secret = "HIDDEN_REFERENCE_\u00e9_LABEL"
    with repository.connection() as connection:
        connection.execute("ALTER TABLE recordings ADD COLUMN reference_label TEXT")
        connection.execute(
            "UPDATE recordings SET reference_label = ?, filename = ? WHERE id = ?",
            (secret, f"{secret}.wav", sample["id"]),
        )
        assert connection.execute("SELECT reference_label FROM recordings").fetchone()[0] == secret
    assert save_review(client, sample["id"], note="Authorized human review").status_code == 200
    for endpoint in ("/api/recordings", f"/api/recordings/{sample['id']}"):
        result = client.get(endpoint)
        assert result.status_code == 200
        serialized = json.dumps(result.json())
        assert "reference_label" not in serialized
        for marker in (secret, json.dumps(secret)[1:-1]):
            assert marker not in serialized
    assert client.get("/api/recordings", params={"search": secret}).json()["total"] == 0

    def forbidden_row_access(*args, **kwargs):
        raise AssertionError("Model input must not read operational review records")

    monkeypatch.setattr(repository, "get", forbidden_row_access)
    observation = repository.model_input(sample["id"], 4096)
    assert {field.name for field in fields(observation)} == {"sample_id", "wav_bytes"}
    assert observation.sample_id == sample["id"]
    assert observation.wav_bytes == pcm_wav()
    assert secret not in repr(observation)
    with pytest.raises(InvalidAudio):
        repository.model_input(sample["id"], 10)
    with pytest.raises(RecordingNotFound):
        repository.model_input(uuid.uuid4().hex, 4096)