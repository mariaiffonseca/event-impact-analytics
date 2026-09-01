from pathlib import Path

from event_impact.ingestion.common.http import DownloadResult
from event_impact.ingestion.common.provenance import (
    ProvenanceRecord,
    provenance_path_for,
    read_provenance,
    write_provenance,
)


def test_provenance_path_for_appends_suffix():
    dest = Path("/data/raw/taxi/yellow_tripdata_2019-01.parquet")
    assert provenance_path_for(dest) == Path(
        "/data/raw/taxi/yellow_tripdata_2019-01.parquet.provenance.json"
    )


def test_write_then_read_provenance_round_trips(tmp_path):
    dest = tmp_path / "yellow_tripdata_2019-01.parquet"
    result = DownloadResult(
        url="https://example.test/yellow_tripdata_2019-01.parquet",
        dest_path=dest,
        size_bytes=123,
        sha256="deadbeef",
    )

    written_path = write_provenance(result)

    assert written_path == provenance_path_for(dest)
    assert written_path.exists()

    record = read_provenance(dest)

    assert record == ProvenanceRecord(
        source_url=result.url,
        file_name=dest.name,
        retrieved_at=record.retrieved_at,
        size_bytes=result.size_bytes,
        sha256=result.sha256,
    )
