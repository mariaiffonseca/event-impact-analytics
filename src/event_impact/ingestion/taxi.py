"""NYC TLC Yellow Taxi trip data — acquisition and source validation.

PR-003 acquired and validated a single-month slice (2019-01) to establish the real schema,
coverage, and data-quality profile. PR-004 reuses `download_month()` / `inspect_schema()` /
`validate_month()` unchanged, once per month, to acquire and validate the full 2019 calendar
year (`acquire_and_validate_year()` / `aggregate_issue_counts()` below).

All inspection is done via PyArrow Parquet metadata and DuckDB querying the Parquet file
directly — the file is never loaded into memory as a whole (no `pandas.read_parquet()`), and
each month is validated independently (no 12-month in-memory concat).
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import duckdb
import pyarrow.parquet as pq

from event_impact.config import TAXI_RAW_DIR, taxi_trip_data_url
from event_impact.ingestion.common.http import download_file
from event_impact.ingestion.common.provenance import write_provenance
from event_impact.ingestion.common.validation import (
    Severity,
    ValidationReport,
    check_count,
    check_required_columns,
)

# Columns the analytical plan (docs/project/01_ANALYTICAL_PLAN.md) depends on. Confirmed
# present in the real 2019-01 file — not assumed from PR-002's guessed schema.
REQUIRED_COLUMNS = [
    "tpep_pickup_datetime",
    "tpep_dropoff_datetime",
    "PULocationID",
    "DOLocationID",
    "passenger_count",
    "trip_distance",
    "fare_amount",
    "total_amount",
]

# TLC taxi zones are numbered 1-263, plus 264/265 used for "N/A"/"Unknown". This range is
# used as a WARNING-level sanity check only; the authoritative check against the real zone
# lookup table happens in PR-005 once that data is acquired.
_PLAUSIBLE_LOCATION_ID_RANGE = (1, 265)

# Confirmed present in 2019-01 but not guaranteed for every month (see PR-003's
# 03_DATA_ACQUISITION.md) — reported as an informational diagnostic, not a hard requirement.
OPTIONAL_DIAGNOSTIC_COLUMNS = ["congestion_surcharge", "airport_fee"]

YEAR_MONTHS_2019 = [f"2019-{month:02d}" for month in range(1, 13)]


def raw_path_for(year_month: str) -> Path:
    return TAXI_RAW_DIR / f"yellow_tripdata_{year_month}.parquet"


def download_month(year_month: str) -> Path:
    """Download one month of trip data (e.g. '2019-01') to data/raw/taxi/, with provenance."""
    dest = raw_path_for(year_month)
    result = download_file(taxi_trip_data_url(year_month), dest)
    write_provenance(result)
    return dest


def _quoted_path(path: Path) -> str:
    # Paths here are always internally derived (config + our own filenames), never user
    # input, but escape defensively anyway before embedding in a SQL string literal.
    return "'" + str(path).replace("'", "''") + "'"


@dataclass
class TaxiSliceProfile:
    year_month: str
    file_size_bytes: int
    row_count: int
    columns: list[str]
    min_pickup: str
    max_pickup: str
    min_dropoff: str
    max_dropoff: str
    pickup_datetime_tz: str | None
    pickup_hour_histogram: list[tuple[int, int]]


def inspect_schema(path: Path, year_month: str) -> TaxiSliceProfile:
    """Cheap, metadata-level inspection: schema and row count via Parquet metadata (no full
    load), plus coverage and an hourly pickup histogram via DuckDB (streamed, not loaded into
    Python memory as a whole). The histogram is used to sanity-check timestamp semantics —
    see docs/project/03_DATA_ACQUISITION.md."""
    parquet_file = pq.ParquetFile(path)
    columns = parquet_file.schema.names
    row_count = parquet_file.metadata.num_rows
    file_size_bytes = path.stat().st_size

    pickup_field = parquet_file.schema_arrow.field("tpep_pickup_datetime")
    pickup_tz = getattr(pickup_field.type, "tz", None)

    source = _quoted_path(path)
    con = duckdb.connect()
    coverage = con.execute(
        f"""
        SELECT
            min(tpep_pickup_datetime), max(tpep_pickup_datetime),
            min(tpep_dropoff_datetime), max(tpep_dropoff_datetime)
        FROM read_parquet({source})
        """
    ).fetchone()
    histogram = con.execute(
        f"""
        SELECT extract('hour' FROM tpep_pickup_datetime) AS hour, count(*) AS n
        FROM read_parquet({source})
        GROUP BY hour
        ORDER BY hour
        """
    ).fetchall()

    return TaxiSliceProfile(
        year_month=year_month,
        file_size_bytes=file_size_bytes,
        row_count=row_count,
        columns=columns,
        min_pickup=str(coverage[0]),
        max_pickup=str(coverage[1]),
        min_dropoff=str(coverage[2]),
        max_dropoff=str(coverage[3]),
        pickup_datetime_tz=pickup_tz,
        pickup_hour_histogram=[(int(h), int(n)) for h, n in histogram if h is not None],
    )


def validate_month(path: Path, year_month: str) -> ValidationReport:
    """Source-quality validation over the Parquet file, entirely via DuckDB queries against
    the file on disk (no full in-memory load). This is validation only — no cleaning,
    imputation, or record removal happens here."""
    report = ValidationReport(source=f"taxi:{path.name}")

    columns = pq.ParquetFile(path).schema.names
    check_required_columns(report, columns, REQUIRED_COLUMNS)
    if report.has_errors():
        # The row-level checks below reference required columns directly; running them
        # against an incompatible schema would raise a SQL binder error instead of a
        # meaningful validation result, so stop here and report the missing-column error.
        return report

    source = _quoted_path(path)
    con = duckdb.connect()
    total = con.execute(f"SELECT count(*) FROM read_parquet({source})").fetchone()[0]

    def count_where(where_clause: str) -> int:
        return con.execute(
            f"SELECT count(*) FROM read_parquet({source}) WHERE {where_clause}"
        ).fetchone()[0]

    lo, hi = _PLAUSIBLE_LOCATION_ID_RANGE
    check_count(
        report,
        "null_or_invalid_pu_location_id",
        count_where(f"PULocationID IS NULL OR PULocationID < {lo} OR PULocationID > {hi}"),
        total=total,
        ok_message="all PULocationID values within the plausible zone-ID range",
        problem_message="rows with null/out-of-range PULocationID",
    )
    check_count(
        report,
        "null_or_invalid_do_location_id",
        count_where(f"DOLocationID IS NULL OR DOLocationID < {lo} OR DOLocationID > {hi}"),
        total=total,
        ok_message="all DOLocationID values within the plausible zone-ID range",
        problem_message="rows with null/out-of-range DOLocationID",
    )
    check_count(
        report,
        "invalid_trip_distance",
        count_where("trip_distance IS NULL OR trip_distance <= 0"),
        total=total,
        ok_message="all trip_distance values are positive",
        problem_message="rows with null/zero/negative trip_distance",
    )
    check_count(
        report,
        "invalid_fare_amount",
        count_where("fare_amount IS NULL OR fare_amount < 0"),
        total=total,
        ok_message="all fare_amount values are non-negative",
        problem_message="rows with null/negative fare_amount",
    )
    check_count(
        report,
        "invalid_total_amount",
        count_where("total_amount IS NULL OR total_amount < 0"),
        total=total,
        ok_message="all total_amount values are non-negative",
        problem_message="rows with null/negative total_amount",
    )
    check_count(
        report,
        "invalid_passenger_count",
        count_where("passenger_count IS NULL OR passenger_count <= 0"),
        total=total,
        ok_message="all passenger_count values are positive",
        problem_message="rows with null/zero passenger_count",
    )
    check_count(
        report,
        "dropoff_before_pickup",
        count_where("tpep_dropoff_datetime < tpep_pickup_datetime"),
        total=total,
        ok_message="no rows with dropoff before pickup",
        problem_message="rows where dropoff_datetime precedes pickup_datetime",
        severity=Severity.ERROR,
    )
    check_count(
        report,
        "zero_duration_trip",
        count_where("tpep_dropoff_datetime = tpep_pickup_datetime"),
        total=total,
        ok_message="no zero-duration trips",
        problem_message="rows with identical pickup and dropoff timestamps",
    )
    check_count(
        report,
        "excessive_trip_duration",
        count_where("date_diff('hour', tpep_pickup_datetime, tpep_dropoff_datetime) > 6"),
        total=total,
        ok_message="no trips longer than 6 hours",
        problem_message="rows with trip duration over 6 hours (likely a data error)",
    )
    check_count(
        report,
        "pickup_outside_expected_month",
        count_where(
            f"date_trunc('month', tpep_pickup_datetime) != TIMESTAMP '{year_month}-01'"
        ),
        total=total,
        ok_message=f"all pickups fall within {year_month}",
        problem_message=(
            f"rows with pickup datetime outside the expected {year_month} month "
            "(a known category of TLC data-entry error)"
        ),
    )
    check_count(
        report,
        "duplicate_rows",
        total
        - con.execute(f"SELECT count(*) FROM (SELECT DISTINCT * FROM read_parquet({source})) t").fetchone()[0],
        total=total,
        ok_message="no exact duplicate rows",
        problem_message="exact duplicate rows",
    )

    for column in OPTIONAL_DIAGNOSTIC_COLUMNS:
        if column not in columns:
            report.add(
                f"optional_column_absent:{column}",
                Severity.INFO,
                f"{column} is not present in this month's schema",
            )
            continue
        check_count(
            report,
            f"optional_column_null:{column}",
            count_where(f"{column} IS NULL"),
            total=total,
            ok_message=f"{column} present with no nulls",
            problem_message=f"{column} present but null for some rows",
            severity=Severity.INFO,
        )

    return report


def run_validation_slice(year_month: str = "2019-01") -> tuple[TaxiSliceProfile, ValidationReport]:
    """Download (if needed) and validate one month's slice end to end."""
    path = raw_path_for(year_month)
    if not path.exists():
        download_month(year_month)
    profile = inspect_schema(path, year_month)
    report = validate_month(path, year_month)
    return profile, report


@dataclass
class MonthResult:
    year_month: str
    profile: TaxiSliceProfile
    report: ValidationReport


def acquire_and_validate_year(year_months: list[str] = YEAR_MONTHS_2019) -> list[MonthResult]:
    """Download (if needed) and validate every month in `year_months`, independently.

    No month's failure stops the others — if a month can't be downloaded or its schema is
    invalid, that's itself a finding to document (see `03_DATA_ACQUISITION.md`), not a reason
    to silently drop the month from the results.
    """
    results = []
    for year_month in year_months:
        profile, report = run_validation_slice(year_month)
        results.append(MonthResult(year_month=year_month, profile=profile, report=report))
    return results


def aggregate_issue_counts(results: list[MonthResult]) -> dict[str, int]:
    """Sum each check's row count across all months (checks with no count, i.e. no problem
    found that month, contribute 0)."""
    totals: dict[str, int] = {}
    for result in results:
        for issue in result.report.issues:
            totals[issue.check] = totals.get(issue.check, 0) + (issue.count or 0)
    return totals


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--full-year",
        action="store_true",
        help="Acquire and validate all 12 months of 2019 instead of just the 2019-01 slice.",
    )
    args = parser.parse_args()

    if args.full_year:
        year_results = acquire_and_validate_year()
        for month_result in year_results:
            print(month_result.profile)
            print(month_result.report.summary())
            print()
        total_rows = sum(r.profile.row_count for r in year_results)
        total_bytes = sum(r.profile.file_size_bytes for r in year_results)
        print(f"TOTAL: {total_rows:,} rows across {len(year_results)} months, {total_bytes:,} bytes")
        print(f"Aggregate issue counts: {aggregate_issue_counts(year_results)}")
    else:
        slice_profile, slice_report = run_validation_slice()
        print(slice_profile)
        print()
        print(slice_report.summary())
