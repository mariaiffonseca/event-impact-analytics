from pathlib import Path

from event_impact.ingestion.common.http import DownloadResult
from event_impact.ingestion.common.provenance import (
    ProvenanceRecord,
    download_and_record,
    is_already_acquired,
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


def test_is_already_acquired_false_when_neither_file_exists(tmp_path):
    assert not is_already_acquired(tmp_path / "missing.csv")


def test_is_already_acquired_false_when_only_dest_exists(tmp_path):
    dest = tmp_path / "partial.csv"
    dest.write_text("data")
    assert not is_already_acquired(dest)


def test_is_already_acquired_true_when_both_exist(tmp_path):
    dest = tmp_path / "complete.csv"
    dest.write_text("data")
    write_provenance(
        DownloadResult(url="https://example.test", dest_path=dest, size_bytes=4, sha256="x")
    )
    assert is_already_acquired(dest)


def test_download_and_record_downloads_and_writes_provenance_when_missing(tmp_path, monkeypatch):
    dest = tmp_path / "downloaded.csv"
    calls = []

    def fake_download_file(url, dest_path, **kwargs):
        calls.append((url, dest_path))
        dest_path.write_text("data")
        return DownloadResult(url=url, dest_path=dest_path, size_bytes=4, sha256="x")

    monkeypatch.setattr(
        "event_impact.ingestion.common.provenance.download_file", fake_download_file
    )

    result_path = download_and_record("https://example.test/file.csv", dest)

    assert result_path == dest
    assert dest.exists()
    assert provenance_path_for(dest).exists()
    assert len(calls) == 1


def test_download_and_record_skips_download_when_already_acquired(tmp_path, monkeypatch):
    dest = tmp_path / "downloaded.csv"
    dest.write_text("data")
    write_provenance(
        DownloadResult(url="https://example.test", dest_path=dest, size_bytes=4, sha256="x")
    )

    def fail_if_called(*args, **kwargs):
        raise AssertionError("download_file should not be called when already acquired")

    monkeypatch.setattr(
        "event_impact.ingestion.common.provenance.download_file", fail_if_called
    )

    result_path = download_and_record("https://example.test/file.csv", dest)

    assert result_path == dest
