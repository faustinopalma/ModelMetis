import os
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlsplit

DEFAULT_ORIGINS = ("http://127.0.0.1:5173", "http://localhost:5173")


@dataclass(frozen=True)
class Settings:
    data_directory: Path = Path("data/local")
    max_upload_bytes: int = 16 * 1024 * 1024
    origins: tuple[str, ...] = DEFAULT_ORIGINS
    mode: str = "local"

    def __post_init__(self) -> None:
        if self.mode != "local":
            raise ValueError("Production is disabled until real authentication is implemented.")
        if not 44 <= self.max_upload_bytes <= 32 * 1024 * 1024:
            raise ValueError("Upload limit must be between 44 bytes and 32 MiB.")
        for origin in self.origins:
            parsed = urlsplit(origin)
            if (
                parsed.scheme != "http"
                or parsed.hostname not in ("127.0.0.1", "localhost", "::1")
                or parsed.username is not None
                or parsed.password is not None
                or parsed.path
                or parsed.query
                or parsed.fragment
            ):
                raise ValueError("Only explicit local HTTP origins are allowed.")
            if parsed.port is None:
                raise ValueError("A local origin must specify its port.")

    @classmethod
    def from_environment(cls) -> "Settings":
        return cls(
            data_directory=Path(os.environ.get("MODELMETIS_DATA_DIR", "data/local")),
            max_upload_bytes=int(os.environ.get("MODELMETIS_MAX_UPLOAD_BYTES", 16777216)),
            origins=tuple(
                origin.strip()
                for origin in os.environ.get(
                    "MODELMETIS_ORIGINS", ",".join(DEFAULT_ORIGINS)
                ).split(",")
            ),
            mode=os.environ.get("MODELMETIS_ENV", "local"),
        )