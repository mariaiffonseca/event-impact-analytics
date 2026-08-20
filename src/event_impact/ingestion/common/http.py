"""Shared file-download utility, reused by every ingestion source (taxi, zones, schedule).

Streams to disk rather than buffering in memory, retries transient failures, and returns
enough metadata (size, sha256) to write a provenance record.
"""

from __future__ import annotations

import hashlib
import time
from dataclasses import dataclass
from pathlib import Path

import requests

from event_impact.config import DEFAULT_USER_AGENT

CHUNK_SIZE = 1024 * 1024  # 1 MiB


@dataclass(frozen=True)
class DownloadResult:
    url: str
    dest_path: Path
    size_bytes: int
    sha256: str


def download_file(
    url: str,
    dest_path: Path,
    *,
    max_retries: int = 3,
    timeout_seconds: int = 60,
) -> DownloadResult:
    """Download `url` to `dest_path`, streaming to disk, retrying transient failures."""
    dest_path.parent.mkdir(parents=True, exist_ok=True)
    headers = {"User-Agent": DEFAULT_USER_AGENT}

    last_error: requests.RequestException | None = None
    for attempt in range(1, max_retries + 1):
        try:
            digest = hashlib.sha256()
            size_bytes = 0
            with requests.get(url, headers=headers, stream=True, timeout=timeout_seconds) as response:
                response.raise_for_status()
                with open(dest_path, "wb") as f:
                    for chunk in response.iter_content(chunk_size=CHUNK_SIZE):
                        if not chunk:
                            continue
                        f.write(chunk)
                        digest.update(chunk)
                        size_bytes += len(chunk)
            return DownloadResult(
                url=url,
                dest_path=dest_path,
                size_bytes=size_bytes,
                sha256=digest.hexdigest(),
            )
        except requests.RequestException as exc:
            last_error = exc
            if attempt < max_retries:
                time.sleep(2**attempt)

    assert last_error is not None
    raise last_error
