import asyncio
import ipaddress
import logging
import sqlite3
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Annotated, Literal
from uuid import UUID

from fastapi import FastAPI, Query, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel, ConfigDict, Field, ValidationError
from starlette.concurrency import run_in_threadpool
from starlette.exceptions import HTTPException
from starlette.requests import ClientDisconnect

from modelmetis.audio import InvalidAudio
from modelmetis.repository import (
    REVIEW_LABELS,
    RecordingNotFound,
    RecordingRepository,
    ReviewLabel,
    RevisionConflict,
)
from modelmetis.settings import Settings

logger = logging.getLogger(__name__)
ReviewFilter = Literal["all", "unreviewed", "healthy", "fault_unspecified", "needs_review"]


class ReviewRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    expected_revision: int = Field(ge=0, le=2147483647)
    human_label: ReviewLabel
    note: str = Field(default="", max_length=2000)


def error_response(status: int, code: str, message: str, **details) -> JSONResponse:
    return JSONResponse(
        {"error": {"code": code, "message": message, **details}}, status_code=status
    )


async def bounded_body(request: Request, limit: int) -> bytes:
    declared = request.headers.get("content-length")
    if declared is not None:
        if not declared.isascii() or not declared.isdecimal() or len(declared) > 12:
            raise HTTPException(400, "Invalid Content-Length.")
        if int(declared) > limit:
            raise HTTPException(413, "Request exceeds the byte limit.")
    if request.headers.get("content-encoding", "identity") != "identity":
        raise HTTPException(415, "Encoded request bodies are not supported.")
    body = bytearray()
    try:
        async with asyncio.timeout(30):
            async for chunk in request.stream():
                if len(body) + len(chunk) > limit:
                    raise HTTPException(413, "Request exceeds the byte limit.")
                body.extend(chunk)
    except TimeoutError as error:
        raise HTTPException(408, "Request upload timed out.") from error
    except ClientDisconnect as error:
        raise HTTPException(400, "Upload was interrupted.") from error
    if declared is not None and len(body) != int(declared):
        raise HTTPException(400, "Content-Length does not match the request body.")
    return bytes(body)


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or Settings.from_environment()
    repository = RecordingRepository(settings.data_directory)

    @asynccontextmanager
    async def lifespan(application: FastAPI) -> AsyncIterator[None]:
        application.state.storage_initialized = False
        try:
            await run_in_threadpool(repository.initialize)
            application.state.storage_initialized = True
        except (OSError, sqlite3.Error):
            logger.exception("Local storage initialization failed")
        yield

    application = FastAPI(title="ModelMetis local audio review", lifespan=lifespan)
    application.state.repository = repository
    application.add_middleware(
        CORSMiddleware,
        allow_origins=list(settings.origins),
        allow_methods=["GET", "POST", "PUT"],
        allow_headers=["Content-Type"],
        allow_credentials=False,
    )

    @application.middleware("http")
    async def local_boundary(request: Request, call_next):
        try:
            local_peer = request.client is not None and ipaddress.ip_address(
                request.client.host
            ).is_loopback
            local_host = request.url.hostname in ("localhost", "127.0.0.1", "::1")
        except ValueError:
            local_peer = local_host = False
        forwarded = any(
            name == "forwarded" or name.startswith("x-forwarded-")
            for name in request.headers
        )
        origin = request.headers.get("origin")
        if not local_peer or not local_host or forwarded:
            return error_response(403, "local_only", "Only direct loopback access is enabled.")
        if origin is not None and origin not in settings.origins:
            return error_response(403, "origin_not_allowed", "This origin is not allowed.")
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Cache-Control"] = "no-store"
        return response

    @application.exception_handler(HTTPException)
    async def http_error(request: Request, error: HTTPException):
        codes = {
            400: "bad_request", 404: "not_found", 405: "method_not_allowed",
            408: "upload_timeout", 413: "too_large", 415: "unsupported_type",
            422: "invalid_request", 503: "storage_unavailable",
        }
        return error_response(error.status_code, codes.get(error.status_code, "error"),
                              str(error.detail))

    @application.exception_handler(RequestValidationError)
    async def request_error(request: Request, error: RequestValidationError):
        return error_response(422, "invalid_request", "Invalid path or query parameters.")

    @application.exception_handler(InvalidAudio)
    async def audio_error(request: Request, error: InvalidAudio):
        return error_response(422, "invalid_audio", str(error))

    @application.exception_handler(RecordingNotFound)
    async def missing_error(request: Request, error: RecordingNotFound):
        return error_response(404, "not_found", "Recording not found.")

    @application.exception_handler(RevisionConflict)
    async def revision_error(request: Request, error: RevisionConflict):
        return error_response(409, "revision_conflict", str(error),
                              current_revision=error.current_revision)

    async def storage_error(request: Request, error: Exception):
        logger.error("Local storage operation failed: %s", type(error).__name__)
        return error_response(503, "storage_unavailable", "Local storage is unavailable.")

    application.add_exception_handler(sqlite3.Error, storage_error)
    application.add_exception_handler(OSError, storage_error)

    @application.get("/healthz")
    def health():
        return {"status": "ok"}

    @application.get("/readyz")
    def ready():
        if not application.state.storage_initialized:
            raise HTTPException(503, "Local storage was not initialized. Restart after repair.")
        repository.check_ready()
        return {"status": "ready", "dependencies": {"sqlite": "ok", "audio_storage": "ok"}}

    @application.get("/api/status")
    def status():
        return {
            "mode": "local_only",
            "teacher": {"status": "not_configured", "display": "Not configured"},
            "specialist": {"status": "not_trained", "display": "Not trained"},
            "evaluation": {"status": "not_evaluated", "display": "Not evaluated"},
            "dataset": {"status": "not_downloaded", "display": "Ottawa not downloaded"},
            "counts": repository.counts(),
            "review_taxonomy": list(REVIEW_LABELS),
            "max_upload_bytes": settings.max_upload_bytes,
            "max_duration_seconds": 120,
        }

    @application.get("/api/recordings")
    def recordings(
        search: Annotated[str, Query(max_length=180)] = "",
        label: ReviewFilter = "all",
        limit: Annotated[int, Query(ge=1, le=100)] = 50,
        offset: Annotated[int, Query(ge=0, le=2147483647)] = 0,
    ):
        return repository.list(search, label, limit, offset)

    @application.post("/api/recordings", status_code=201)
    async def upload(
        request: Request,
        synthetic: bool,
    ):
        if request.headers.get("content-type", "").split(";")[0].lower() not in (
            "audio/wav", "audio/wave", "audio/x-wav", "application/octet-stream"
        ):
            raise HTTPException(415, "Send the raw WAV body, not multipart form data.")
        payload = await bounded_body(request, settings.max_upload_bytes)
        return await run_in_threadpool(
            repository.add, payload, synthetic, settings.max_upload_bytes,
        )

    @application.get("/api/recordings/{recording_id}")
    def recording(recording_id: UUID):
        return repository.get(recording_id.hex)

    @application.get("/api/recordings/{recording_id}/audio")
    def audio(recording_id: UUID):
        path = repository.audio_path(recording_id.hex)
        return FileResponse(path, media_type="audio/wav")

    @application.put("/api/recordings/{recording_id}/review")
    async def review(request: Request, recording_id: UUID):
        if request.headers.get("content-type", "").split(";")[0].lower() != "application/json":
            raise HTTPException(415, "Send review data as application/json.")
        body = await bounded_body(request, 16384)
        try:
            update = ReviewRequest.model_validate_json(body)
        except ValidationError as error:
            raise HTTPException(
                422, "Provide an integer expected_revision, a review label, "
                "and a note up to 2000 characters."
            ) from error
        return await run_in_threadpool(
            repository.save_review, recording_id.hex, update.expected_revision,
            update.human_label, update.note,
        )

    return application


app = create_app()