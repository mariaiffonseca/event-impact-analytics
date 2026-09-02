import hashlib

import pytest
import requests

from event_impact.ingestion.common import http


class FakeResponse:
    """Stands in for `requests.get(..., stream=True)`'s context-managed response."""

    def __init__(self, chunk_iterable, headers=None, status_ok=True):
        self._chunk_iterable = chunk_iterable
        self.headers = headers or {}
        self._status_ok = status_ok

    def __enter__(self):
        return self

    def __exit__(self, *exc_info):
        return False

    def raise_for_status(self):
        if not self._status_ok:
            raise requests.HTTPError("simulated HTTP error")

    def iter_content(self, chunk_size):
        return iter(self._chunk_iterable)


def _part_path(dest):
    return dest.with_name(dest.name + ".part")


def test_download_file_streams_to_disk_and_returns_metadata(tmp_path, monkeypatch):
    def fake_get(url, headers, stream, timeout):
        assert stream is True
        return FakeResponse([b"hello ", b"world"])

    monkeypatch.setattr(http.requests, "get", fake_get)

    dest = tmp_path / "nested" / "out.bin"
    result = http.download_file("https://example.test/f", dest)

    assert dest.read_bytes() == b"hello world"
    assert result.size_bytes == 11
    assert result.sha256 == hashlib.sha256(b"hello world").hexdigest()
    assert result.dest_path == dest
    assert result.url == "https://example.test/f"
    assert not _part_path(dest).exists()


def test_download_file_retries_transient_failure_then_succeeds(tmp_path, monkeypatch):
    calls = {"n": 0}

    def fake_get(url, headers, stream, timeout):
        calls["n"] += 1
        if calls["n"] == 1:
            raise requests.ConnectionError("transient failure")
        return FakeResponse([b"hello world"])

    monkeypatch.setattr(http.requests, "get", fake_get)
    monkeypatch.setattr(http.time, "sleep", lambda _seconds: None)

    dest = tmp_path / "out.bin"
    result = http.download_file("https://example.test/f", dest, max_retries=2)

    assert calls["n"] == 2
    assert dest.read_bytes() == b"hello world"
    assert result.size_bytes == 11


def test_download_file_does_not_leave_partial_file_after_stream_failure(tmp_path, monkeypatch):
    """A connection dropping mid-stream must not leave a corrupt file at dest_path — a
    caller checking `dest_path.exists()` should never mistake it for a completed download."""

    def failing_chunks():
        yield b"some-bytes-before-the-drop"
        raise requests.ConnectionError("connection dropped mid-stream")

    def fake_get(url, headers, stream, timeout):
        return FakeResponse(failing_chunks())

    monkeypatch.setattr(http.requests, "get", fake_get)

    dest = tmp_path / "out.bin"
    with pytest.raises(requests.ConnectionError):
        http.download_file("https://example.test/f", dest, max_retries=1)

    assert not dest.exists()
    assert not _part_path(dest).exists()


def test_download_file_raises_on_content_length_mismatch(tmp_path, monkeypatch):
    def fake_get(url, headers, stream, timeout):
        return FakeResponse([b"short"], headers={"Content-Length": "999"})

    monkeypatch.setattr(http.requests, "get", fake_get)

    dest = tmp_path / "out.bin"
    with pytest.raises(requests.RequestException):
        http.download_file("https://example.test/f", dest, max_retries=1)

    assert not dest.exists()
    assert not _part_path(dest).exists()


def test_download_file_skips_length_check_for_encoded_response(tmp_path, monkeypatch):
    """`iter_content()` yields decoded bytes, but Content-Length on an encoded response
    describes the compressed wire size — comparing them would false-positive deterministically
    on every gzip/deflate response, so the check must be skipped when Content-Encoding is set."""

    def fake_get(url, headers, stream, timeout):
        return FakeResponse(
            [b"decoded-body-longer-than-compressed"],
            headers={"Content-Length": "12", "Content-Encoding": "gzip"},
        )

    monkeypatch.setattr(http.requests, "get", fake_get)

    dest = tmp_path / "out.bin"
    result = http.download_file("https://example.test/f", dest, max_retries=1)

    assert dest.read_bytes() == b"decoded-body-longer-than-compressed"
    assert result.size_bytes == len(b"decoded-body-longer-than-compressed")


def test_download_file_rejects_non_positive_max_retries(tmp_path):
    with pytest.raises(ValueError):
        http.download_file("https://example.test/f", tmp_path / "out.bin", max_retries=0)
