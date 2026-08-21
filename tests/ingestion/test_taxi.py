import pandas as pd
import pytest

from event_impact.ingestion import taxi

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
    assert profile.row_count == 8
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


def test_validate_month_detects_out_of_range_location_id(fixture_month):
    path, year_month = fixture_month
    report = taxi.validate_month(path, year_month)
    assert issue(report, "null_or_invalid_pu_location_id").count == 1


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
