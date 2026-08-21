import pandas as pd
import pytest

from event_impact.ingestion import taxi
from event_impact.ingestion.common.http import DownloadResult
from event_impact.ingestion.common.provenance import write_provenance

VALID_ROW = {
    "PULocationID": 100,
    "DOLocationID": 200,
    "passenger_count": 1,
    "trip_distance": 2.5,
    "fare_amount": 10.0,
    "total_amount": 12.0,
}


@pytest.fixture
def fixture_month(tmp_path):
    """A tiny synthetic 2019-01 slice with one row per known issue this module checks for.
    No network access, no real TLC data — deterministic local fixture only."""
    rows = [
        # 0: fully valid
        dict(
            tpep_pickup_datetime="2019-01-05 08:00:00",
            tpep_dropoff_datetime="2019-01-05 08:20:00",
            **VALID_ROW,
        ),
        # 1: exact duplicate of row 0
        dict(
            tpep_pickup_datetime="2019-01-05 08:00:00",
            tpep_dropoff_datetime="2019-01-05 08:20:00",
            **VALID_ROW,
        ),
        # 2: dropoff before pickup
        dict(
            tpep_pickup_datetime="2019-01-05 09:00:00",
            tpep_dropoff_datetime="2019-01-05 08:50:00",
            **VALID_ROW,
        ),
        # 3: negative fare
        dict(
            tpep_pickup_datetime="2019-01-05 10:00:00",
            tpep_dropoff_datetime="2019-01-05 10:20:00",
            **{**VALID_ROW, "fare_amount": -5.0},
        ),
        # 4: out-of-range PULocationID
        dict(
            tpep_pickup_datetime="2019-01-05 11:00:00",
            tpep_dropoff_datetime="2019-01-05 11:20:00",
            **{**VALID_ROW, "PULocationID": 999},
        ),
        # 5: pickup outside the expected month
        dict(
            tpep_pickup_datetime="2019-02-01 00:10:00",
            tpep_dropoff_datetime="2019-02-01 00:30:00",
            **VALID_ROW,
        ),
        # 6: zero passenger_count
        dict(
            tpep_pickup_datetime="2019-01-05 12:00:00",
            tpep_dropoff_datetime="2019-01-05 12:20:00",
            **{**VALID_ROW, "passenger_count": 0},
        ),
        # 7: zero trip_distance
        dict(
            tpep_pickup_datetime="2019-01-05 13:00:00",
            tpep_dropoff_datetime="2019-01-05 13:20:00",
            **{**VALID_ROW, "trip_distance": 0.0},
        ),
        # 8: out-of-range DOLocationID (distinct from row 4's PULocationID case)
        dict(
            tpep_pickup_datetime="2019-01-05 14:00:00",
            tpep_dropoff_datetime="2019-01-05 14:20:00",
            **{**VALID_ROW, "DOLocationID": 999},
        ),
        # 9: negative total_amount (distinct from row 3's fare_amount case)
        dict(
            tpep_pickup_datetime="2019-01-05 15:00:00",
            tpep_dropoff_datetime="2019-01-05 15:20:00",
            **{**VALID_ROW, "total_amount": -3.0},
        ),
        # 10: null pickup timestamp — must not silently bypass every timestamp-based check
        dict(
            tpep_pickup_datetime=None,
            tpep_dropoff_datetime="2019-01-05 16:20:00",
            **VALID_ROW,
        ),
        # 11: 6h59m59s trip — exercises the hour-vs-second duration comparison. With
        # date_diff('hour', ...) this reports 6 (hour-boundary crossings, not elapsed
        # hours) and is wrongly excluded from excessive_trip_duration.
        dict(
            tpep_pickup_datetime="2019-01-05 17:00:00",
            tpep_dropoff_datetime="2019-01-05 23:59:59",
            **VALID_ROW,
        ),
    ]
    df = pd.DataFrame(rows)
    df["tpep_pickup_datetime"] = pd.to_datetime(df["tpep_pickup_datetime"])
    df["tpep_dropoff_datetime"] = pd.to_datetime(df["tpep_dropoff_datetime"])
    path = tmp_path / "yellow_tripdata_2019-01.parquet"
    df.to_parquet(path, engine="pyarrow", index=False)
    return path, "2019-01"


def issue(report, check_name):
    return next(i for i in report.issues if i.check == check_name)


def test_inspect_schema_reports_real_columns_and_row_count(fixture_month):
    path, year_month = fixture_month
    profile = taxi.inspect_schema(path, year_month)
    assert profile.row_count == 12
    assert "tpep_pickup_datetime" in profile.columns
    assert "PULocationID" in profile.columns
    assert profile.file_size_bytes > 0


def test_validate_month_passes_required_columns_check(fixture_month):
    path, year_month = fixture_month
    report = taxi.validate_month(path, year_month)
    assert issue(report, "required_columns").severity.value == "info"


def test_validate_month_rejects_schema_missing_required_columns(tmp_path):
    df = pd.DataFrame({"tpep_pickup_datetime": pd.to_datetime(["2019-01-01"])})
    path = tmp_path / "bad_schema.parquet"
    df.to_parquet(path, engine="pyarrow", index=False)

    report = taxi.validate_month(path, "2019-01")

    assert report.has_errors()
    required_columns_issue = issue(report, "required_columns")
    assert required_columns_issue.severity.value == "error"
    # Only the schema check should have run — row-level checks are skipped on bad schema.
    assert len(report.issues) == 1


def test_run_validation_slice_reports_missing_schema_without_crashing(tmp_path, monkeypatch):
    """inspect_schema assumes required columns are present and raises a raw KeyError on a
    bad schema; run_validation_slice must check the schema first and route to the clean
    required_columns error instead of calling inspect_schema at all."""
    monkeypatch.setattr(taxi, "TAXI_RAW_DIR", tmp_path)
    df = pd.DataFrame({"tpep_pickup_datetime": pd.to_datetime(["2019-01-01"])})
    path = taxi.raw_path_for("2019-01")
    df.to_parquet(path, engine="pyarrow", index=False)
    write_provenance(
        DownloadResult(url="https://example.test", dest_path=path, size_bytes=1, sha256="x")
    )

    profile, report = taxi.run_validation_slice("2019-01")

    assert profile is None
    assert report.has_errors()
    assert issue(report, "required_columns").severity.value == "error"


def test_run_validation_slice_returns_profile_despite_row_level_errors(tmp_path, monkeypatch):
    """`dropoff_before_pickup` is an ERROR-severity row-level issue that legitimately fires on
    real, schema-valid data (see docs/project/03_DATA_ACQUISITION.md) — it must not be mistaken
    for the schema-missing-columns case that suppresses `inspect_schema`."""
    monkeypatch.setattr(taxi, "TAXI_RAW_DIR", tmp_path)
    path = taxi.raw_path_for("2019-01")
    df = pd.DataFrame(
        [
            dict(
                tpep_pickup_datetime="2019-01-05 09:00:00",
                tpep_dropoff_datetime="2019-01-05 08:50:00",
                **VALID_ROW,
            )
        ]
    )
    df["tpep_pickup_datetime"] = pd.to_datetime(df["tpep_pickup_datetime"])
    df["tpep_dropoff_datetime"] = pd.to_datetime(df["tpep_dropoff_datetime"])
    df.to_parquet(path, engine="pyarrow", index=False)
    write_provenance(
        DownloadResult(url="https://example.test", dest_path=path, size_bytes=1, sha256="x")
    )

    profile, report = taxi.run_validation_slice("2019-01")

    assert profile is not None
    assert report.has_errors()
    assert issue(report, "dropoff_before_pickup").severity.value == "error"


def test_validate_month_detects_dropoff_before_pickup(fixture_month):
    path, year_month = fixture_month
    report = taxi.validate_month(path, year_month)
    dropoff_issue = issue(report, "dropoff_before_pickup")
    assert dropoff_issue.count == 1
    assert dropoff_issue.severity.value == "error"
    assert report.has_errors()


def test_validate_month_detects_invalid_fare(fixture_month):
    path, year_month = fixture_month
    report = taxi.validate_month(path, year_month)
    assert issue(report, "invalid_fare_amount").count == 1


def test_validate_month_detects_invalid_total_amount(fixture_month):
    path, year_month = fixture_month
    report = taxi.validate_month(path, year_month)
    assert issue(report, "invalid_total_amount").count == 1


def test_validate_month_detects_out_of_range_location_id(fixture_month):
    path, year_month = fixture_month
    report = taxi.validate_month(path, year_month)
    assert issue(report, "null_or_invalid_pu_location_id").count == 1
    assert issue(report, "null_or_invalid_do_location_id").count == 1


def test_validate_month_detects_null_pickup_or_dropoff_datetime(fixture_month):
    path, year_month = fixture_month
    report = taxi.validate_month(path, year_month)
    null_ts_issue = issue(report, "null_pickup_or_dropoff_datetime")
    assert null_ts_issue.count == 1
    assert null_ts_issue.severity.value == "error"
    assert report.has_errors()


def test_validate_month_detects_excessive_trip_duration_near_boundary(fixture_month):
    path, year_month = fixture_month
    report = taxi.validate_month(path, year_month)
    assert issue(report, "excessive_trip_duration").count == 1


def test_validate_month_detects_pickup_outside_expected_month(fixture_month):
    path, year_month = fixture_month
    report = taxi.validate_month(path, year_month)
    assert issue(report, "pickup_outside_expected_month").count == 1


def test_validate_month_detects_duplicate_rows(fixture_month):
    path, year_month = fixture_month
    report = taxi.validate_month(path, year_month)
    assert issue(report, "duplicate_rows").count == 1


def test_validate_month_detects_invalid_passenger_count_and_distance(fixture_month):
    path, year_month = fixture_month
    report = taxi.validate_month(path, year_month)
    assert issue(report, "invalid_passenger_count").count == 1
    assert issue(report, "invalid_trip_distance").count == 1


def test_validate_month_flags_optional_columns_absent_when_missing(fixture_month):
    # The fixture's rows don't include congestion_surcharge / airport_fee at all — a
    # realistic case for months where TLC hadn't yet added a field.
    path, year_month = fixture_month
    report = taxi.validate_month(path, year_month)
    for column in taxi.OPTIONAL_DIAGNOSTIC_COLUMNS:
        absent_issue = issue(report, f"optional_column_absent:{column}")
        assert absent_issue.severity.value == "info"


def test_validate_month_reports_optional_column_nulls_when_present(tmp_path):
    rows = [
        {"tpep_pickup_datetime": "2019-01-05 08:00:00", "congestion_surcharge": 2.5, **VALID_ROW,
         "tpep_dropoff_datetime": "2019-01-05 08:20:00"},
        {"tpep_pickup_datetime": "2019-01-05 09:00:00", "congestion_surcharge": None, **VALID_ROW,
         "tpep_dropoff_datetime": "2019-01-05 09:20:00"},
    ]
    df = pd.DataFrame(rows)
    df["tpep_pickup_datetime"] = pd.to_datetime(df["tpep_pickup_datetime"])
    df["tpep_dropoff_datetime"] = pd.to_datetime(df["tpep_dropoff_datetime"])
    path = tmp_path / "yellow_tripdata_2019-01.parquet"
    df.to_parquet(path, engine="pyarrow", index=False)

    report = taxi.validate_month(path, "2019-01")

    null_issue = issue(report, "optional_column_null:congestion_surcharge")
    assert null_issue.count == 1
    assert null_issue.severity.value == "info"


def test_acquire_and_validate_year_runs_one_slice_per_month(monkeypatch, fixture_month):
    path, year_month = fixture_month
    calls: list[str] = []

    def fake_run_validation_slice(requested_year_month: str = "2019-01"):
        calls.append(requested_year_month)
        return taxi.inspect_schema(path, year_month), taxi.validate_month(path, year_month)

    monkeypatch.setattr(taxi, "run_validation_slice", fake_run_validation_slice)

    results = taxi.acquire_and_validate_year(["2019-01", "2019-02"])

    assert calls == ["2019-01", "2019-02"]
    assert [r.year_month for r in results] == ["2019-01", "2019-02"]
    assert all(isinstance(r, taxi.MonthResult) for r in results)


def test_aggregate_issue_counts_sums_across_months():
    def make_report(dropoff_before_pickup_count: int) -> taxi.ValidationReport:
        report = taxi.ValidationReport(source="test")
        report.add(
            "dropoff_before_pickup",
            taxi.Severity.ERROR,
            "rows where dropoff precedes pickup",
            count=dropoff_before_pickup_count,
        )
        report.add("required_columns", taxi.Severity.INFO, "all required columns present")
        return report

    profile_stub = taxi.TaxiSliceProfile(
        year_month="2019-01",
        file_size_bytes=1,
        row_count=1,
        columns=[],
        min_pickup="",
        max_pickup="",
        min_dropoff="",
        max_dropoff="",
        pickup_datetime_tz=None,
        pickup_hour_histogram=[],
    )
    results = [
        taxi.MonthResult(year_month="2019-01", profile=profile_stub, report=make_report(2)),
        taxi.MonthResult(year_month="2019-02", profile=profile_stub, report=make_report(3)),
    ]

    totals = taxi.aggregate_issue_counts(results)

    assert totals["dropoff_before_pickup"] == 5
    # An issue with no count (info, no problem found) contributes 0, not a missing key.
    assert totals["required_columns"] == 0
