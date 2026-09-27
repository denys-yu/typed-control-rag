"""Download of the source dataset file.

Deliberately small: urllib from the standard library, a timeout, a bounded
number of retries, a temporary file and an atomic move once the payload has
been confirmed to be valid JSON.
"""

from __future__ import annotations

import hashlib
import json
import os
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

CHUNK_SIZE = 1 << 20
DEFAULT_TIMEOUT = 60.0
DEFAULT_ATTEMPTS = 3
USER_AGENT = "typed-rag/0.1 (research; stdlib urllib)"

# Provenance of the raw file lives next to it, so that reusing a local copy
# still carries the original download source into later reports.
SIDECAR_SUFFIX = ".source.json"


class DownloadError(Exception):
    """Raised when no configured source yielded a valid dataset file."""


@dataclass(frozen=True)
class DownloadResult:
    """What actually happened, for the manifest and the report."""

    path: Path
    source_url: str | None
    reused_existing: bool
    size_bytes: int
    sha256: str
    attempts: list[str]
    provenance: dict


def sidecar_path(destination: Path) -> Path:
    """Path of the provenance sidecar for a raw data file."""
    return destination.with_name(destination.name + SIDECAR_SUFFIX)


def read_provenance(destination: Path) -> dict:
    """Provenance recorded for an existing raw file, or an explicit 'unknown'.

    Never invents a source or a date: a missing sidecar is reported as such.
    """
    path = sidecar_path(destination)
    if not path.is_file():
        return {
            "original_source_url": None,
            "downloaded_at": None,
            "provenance_basis": f"no provenance sidecar found at {path.name}",
        }
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        return {
            "original_source_url": None,
            "downloaded_at": None,
            "provenance_basis": f"provenance sidecar unreadable ({exc})",
        }
    if not isinstance(payload, dict):
        return {
            "original_source_url": None,
            "downloaded_at": None,
            "provenance_basis": "provenance sidecar is not a JSON object",
        }
    return payload


def _write_provenance(destination: Path, url: str, sha256: str, size_bytes: int) -> dict:
    """Record where the file actually came from, at the moment it arrived."""
    payload = {
        "original_source_url": url,
        "downloaded_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "downloaded_at_basis": "recorded by typed_rag at download time",
        "raw_file": destination.name,
        "raw_sha256": sha256,
        "raw_size_bytes": size_bytes,
        "provenance_basis": "recorded by typed_rag at download time",
    }
    path = sidecar_path(destination)
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        handle.write(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n")
    return payload


def sha256_file(path: Path) -> str:
    """SHA-256 of a file, streamed so large files stay out of memory."""
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(CHUNK_SIZE), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _is_valid_json(path: Path) -> bool:
    try:
        with path.open("r", encoding="utf-8") as handle:
            json.load(handle)
    except (OSError, ValueError):
        return False
    return True


def _fetch(url: str, destination: Path, timeout: float) -> None:
    """Stream `url` into `destination` (already treated as a temporary file)."""
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=timeout) as response, destination.open("wb") as handle:
        while True:
            chunk = response.read(CHUNK_SIZE)
            if not chunk:
                break
            handle.write(chunk)


def download_dataset(
    urls: list[str],
    destination: Path,
    timeout: float = DEFAULT_TIMEOUT,
    attempts_per_url: int = DEFAULT_ATTEMPTS,
    force: bool = False,
) -> DownloadResult:
    """Ensure `destination` holds a valid JSON file, downloading it if needed.

    `urls` is tried in order; the first one that yields parsable JSON wins.
    An existing, parsable file is reused unless `force` is set.
    """
    destination.parent.mkdir(parents=True, exist_ok=True)

    if destination.is_file() and not force:
        if _is_valid_json(destination):
            return DownloadResult(
                path=destination,
                source_url=None,
                reused_existing=True,
                size_bytes=destination.stat().st_size,
                sha256=sha256_file(destination),
                attempts=["reused existing local file"],
                provenance=read_provenance(destination),
            )
        destination.unlink()

    if not urls:
        raise DownloadError("No download URLs configured")

    temporary = destination.with_name(destination.name + ".part")
    log: list[str] = []

    for url in urls:
        for attempt in range(1, attempts_per_url + 1):
            try:
                _fetch(url, temporary, timeout)
            except (urllib.error.URLError, OSError, TimeoutError) as exc:
                log.append(f"{url} attempt {attempt}: {type(exc).__name__}: {exc}")
                temporary.unlink(missing_ok=True)
                if attempt < attempts_per_url:
                    time.sleep(2.0 * attempt)
                continue

            if not _is_valid_json(temporary):
                log.append(f"{url} attempt {attempt}: downloaded payload is not valid JSON")
                temporary.unlink(missing_ok=True)
                continue

            os.replace(temporary, destination)
            log.append(f"{url} attempt {attempt}: ok")
            size_bytes = destination.stat().st_size
            digest = sha256_file(destination)
            return DownloadResult(
                path=destination,
                source_url=url,
                reused_existing=False,
                size_bytes=size_bytes,
                sha256=digest,
                attempts=log,
                provenance=_write_provenance(destination, url, digest, size_bytes),
            )

    raise DownloadError(
        "Could not obtain the dataset from any configured source:\n  " + "\n  ".join(log)
    )
