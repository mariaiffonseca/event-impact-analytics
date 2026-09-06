"""Provenance sidecar records for acquired files.

Each downloaded file gets a small `<filename>.provenance.json` next to it, recording where
it came from and how to verify it — enough to answer "can this be reproduced?" at the scale
this project needs. Not a general asset-tracking system.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path

from event_impact.ingestion.common.http import DownloadResult, download_file


@dataclass(frozen=True)
class ProvenanceRecord:
    source_url: str
    file_name: str
    retrieved_at: str
    size_bytes: int
    sha256: str


def provenance_path_for(dest_path: Path) -> Path:
    return dest_path.with_name(dest_path.name + ".provenance.json")


def write_provenance(result: DownloadResult) -> Path:
    record = ProvenanceRecord(
        source_url=result.url,
        file_name=result.dest_path.name,
        retrieved_at=datetime.now(UTC).isoformat(),
        size_bytes=result.size_bytes,
        sha256=result.sha256,
    )
    path = provenance_path_for(result.dest_path)
    path.write_text(json.dumps(asdict(record), indent=2))
    return path


def read_provenance(dest_path: Path) -> ProvenanceRecord:
    """Read back the sidecar written by `write_provenance`. Forward-looking API: no caller
    yet, but later PRs need this to check an existing sidecar before deciding whether a raw
    file needs re-downloading (see `taxi.run_validation_slice`'s completeness check)."""
    data = json.loads(provenance_path_for(dest_path).read_text())
    return ProvenanceRecord(**data)


def is_already_acquired(dest_path: Path) -> bool:
    """True if `dest_path` and its provenance sidecar both already exist.

    A download interrupted after writing the raw file but before its provenance sidecar
    (process killed, disk full) must not be mistaken for complete — this is that guard,
    shared by every ingestion source instead of each reimplementing it.
    """
    return dest_path.exists() and provenance_path_for(dest_path).exists()


def download_and_record(url: str, dest_path: Path) -> Path:
    """Download `url` to `dest_path` and write its provenance sidecar, skipping the download
    entirely when `dest_path` was already fully acquired (see `is_already_acquired`).

    This is the download-then-record sequence every ingestion source needs; sources whose
    acquisition has an extra step between download and "fully acquired" (e.g. extracting an
    archive) should not use this directly — provenance must only be written once that step
    also succeeds, so they call `download_file`/`write_provenance` themselves instead.
    """
    if is_already_acquired(dest_path):
        return dest_path
    result = download_file(url, dest_path)
    write_provenance(result)
    return dest_path
