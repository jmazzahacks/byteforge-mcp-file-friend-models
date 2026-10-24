"""Shared dataclass contracts; all timestamps are Unix seconds."""

import math
import os
import re
from dataclasses import asdict, dataclass, field
from pathlib import Path
from urllib.parse import urlsplit


def validate_id(file_id: str) -> str:
    if not isinstance(file_id, str) or re.fullmatch(r"[0-9a-f]{32}", file_id) is None:
        raise ValueError("Invalid file ID")
    return file_id


def validate_metadata(metadata: dict, size: int) -> dict:
    name = metadata.get("filename", "")
    if (
        not isinstance(name, str)
        or not name
        or name in (".", "..")
        or len(name.encode("utf-8")) > 200
        or any(c in name for c in "/\\")
        or any(ord(c) < 32 or ord(c) == 127 for c in name)
    ):
        raise ValueError("Invalid filename")
    digest = metadata.get("sha256", "")
    if not isinstance(digest, str) or not re.fullmatch(r"[0-9a-fA-F]{64}", digest):
        raise ValueError("Invalid SHA-256")
    if type(size) is not int or size < 0:
        raise ValueError("Invalid upload length")
    raw_ttl = metadata.get("ttl", "86400")
    if isinstance(raw_ttl, bool) or not str(raw_ttl).isdigit():
        raise ValueError("TTL must be an integer number of seconds")
    ttl = int(raw_ttl)
    if not 1 <= ttl <= 604800:
        raise ValueError("TTL must be between 1 and 604800 seconds")
    return {"filename": name, "sha256": digest.lower(), "size": size, "ttl": ttl}


@dataclass(frozen=True)
class UploadRequest:
    filename: str
    sha256: str
    size: int
    ttl: int = 86400

    @classmethod
    def from_dict(cls, data: dict) -> "UploadRequest":
        return cls(**validate_metadata(data, data.get("size")))

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass(frozen=True)
class FileReference:
    id: str
    url: str
    filename: str
    sha256: str
    size: int
    created_at: int
    expires_at: int

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "FileReference":
        if not isinstance(data, dict):
            raise TypeError("Reference must be an object")
        validate_id(data["id"])
        validate_metadata(data, data["size"])
        if any(type(data[key]) is not int for key in ("created_at", "expires_at")):
            raise ValueError("Timestamps must be integer seconds")
        if data["expires_at"] < data["created_at"]:
            raise ValueError("Expiry precedes creation")
        if not isinstance(data["url"], str):
            raise TypeError("Reference URL must be a string")
        if urlsplit(data["url"]).scheme not in ("http", "https"):
            raise ValueError("Invalid reference URL")
        values = {key: data[key] for key in cls.__dataclass_fields__}
        values["sha256"] = values["sha256"].lower()
        return cls(**values)


@dataclass(frozen=True)
class FriendConfig:
    root: Path
    public_url: str
    tusd_url: str = "http://127.0.0.1:8080/files/"
    hook_token: str = field(default="", repr=False)
    dev_admin_token: str = ""
    max_size: int = 50 * 1024**3
    min_free: int = 1024**3
    max_active: int = 16
    incomplete_ttl: int = 86400
    incomplete_max_age: int = 604800
    reservation_ttl: int = 300
    retention: int = 604800
    worker_timeout: float = 3600
    worker_grace: float = 15
    storage_budget: int = 200 * 1024**3
    auth_mode: str = "development"
    ingress_shared_secret: str = field(default="", repr=False)

    @classmethod
    def from_env(cls) -> "FriendConfig":
        return cls(
            root=Path(os.environ.get("FF_DATA_DIR", "./data")).resolve(),
            public_url=os.environ.get("FF_PUBLIC_URL", "http://127.0.0.1:8081"),
            tusd_url=os.environ.get("FF_TUSD_URL", "http://127.0.0.1:8080/files/"),
            hook_token=os.environ.get("FF_HOOK_TOKEN", ""),
            dev_admin_token=os.environ.get("FF_DEV_ADMIN_TOKEN", ""),
            auth_mode=os.environ.get("FF_AUTH_MODE", "development"),
            ingress_shared_secret=os.environ.get("FF_INGRESS_SHARED_SECRET", ""),
            max_size=int(os.environ.get("FF_MAX_SIZE", str(50 * 1024**3))),
            min_free=int(os.environ.get("FF_MIN_FREE_BYTES", str(1024**3))),
            max_active=int(os.environ.get("FF_MAX_ACTIVE", "16")),
            storage_budget=int(os.environ.get("FF_STORAGE_BUDGET_BYTES", str(200 * 1024**3))),
            incomplete_ttl=int(os.environ.get("FF_INCOMPLETE_TTL", "86400")),
            incomplete_max_age=int(os.environ.get("FF_INCOMPLETE_MAX_AGE", "604800")),
            reservation_ttl=int(os.environ.get("FF_RESERVATION_TTL", "300")),
            retention=int(os.environ.get("FF_RETENTION", "604800")),
            worker_timeout=float(os.environ.get("FF_WORKER_TIMEOUT", "3600")),
            worker_grace=float(os.environ.get("FF_WORKER_GRACE", "15")),
        )

    def validate(self) -> None:
        if self.auth_mode not in ("development", "ingress"):
            raise ValueError("FF_AUTH_MODE must be development or ingress")
        if self.auth_mode == "ingress":
            if not re.fullmatch(r"[A-Za-z0-9_-]{32,512}", self.ingress_shared_secret):
                raise ValueError("FF_INGRESS_SHARED_SECRET must be 32-512 URL-safe ASCII characters")
            if self.dev_admin_token:
                raise ValueError("FF_DEV_ADMIN_TOKEN must be unset in ingress mode")
            if self.ingress_shared_secret == self.hook_token:
                raise ValueError("Ingress and hook credentials must be distinct")
        elif self.ingress_shared_secret:
            raise ValueError("FF_INGRESS_SHARED_SECRET requires ingress mode")
        if self.max_size < 0 or self.min_free < 0 or self.max_active < 1 or self.storage_budget < 0:
            raise ValueError("Invalid storage limits")
        if (
            min(
                self.incomplete_ttl,
                self.incomplete_max_age,
                self.reservation_ttl,
                self.retention,
                self.worker_timeout,
                self.worker_grace,
            )
            <= 0
        ):
            raise ValueError("Lifecycle time limits must be positive")
        if not all(math.isfinite(value) for value in (self.worker_timeout, self.worker_grace)):
            raise ValueError("Worker time limits must be finite")
        for url in (self.public_url, self.tusd_url):
            if not isinstance(url, str) or any(ord(char) <= 32 or ord(char) == 127 for char in url):
                raise ValueError("Invalid configured service URL")
            parsed = urlsplit(url)
            if (
                parsed.scheme not in ("http", "https")
                or not parsed.hostname
                or parsed.username
                or parsed.password
                or parsed.query
                or parsed.fragment
                or parsed.port == 0
            ):
                raise ValueError("Invalid configured service URL")
        if urlsplit(self.public_url).path not in ("", "/"):
            raise ValueError("FF_PUBLIC_URL must be an origin without a path")
        if not re.fullmatch(r"[A-Za-z0-9_-]{32,512}", self.hook_token):
            raise ValueError("FF_HOOK_TOKEN must be 32-512 URL-safe ASCII characters")
