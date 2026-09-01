"""NYC TLC Yellow Taxi trip data — acquisition and source validation.

PR-003 scope: acquire and validate a single-month slice (2019-01) to establish the real
schema, coverage, and data-quality profile before committing to a full-year acquisition
strategy. Downloading and validating the remaining 11 months is PR-004's job, reusing the
functions here.

All inspection is done via PyArrow Parquet metadata and DuckDB querying the Parquet file
directly — the file is never loaded into memory as a whole (no `pandas.read_parquet()`).
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import duckdb
import pyarrow as pa
import pyarrow.parquet as pq

from event_impact.config import TAXI_RAW_DIR, taxi_trip_data_url
from event_impact.ingestion.common.http import download_file
from event_impact.ingestion.common.provenance import provenance_path_for, write_provenance
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


def raw_path_for(year_month: str) -> Path:
    return TAXI_RAW_DIR / f"yellow_tripdata_{year_month}.parquet"


def download_month(year_month: str) -> Path:
    """Download one month of trip data (e.g. '2019-01') to data/raw/taxi/, with provenance."""
    dest = raw_path_for(year_month)
    result = download_file(taxi_trip_data_url(year_month), dest)
    write_provenance(result)
    return dest


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
    if not pa.types.is_timestamp(pickup_field.type):
        # Distinguishes real schema drift (a future month storing this column as a
        # non-timestamp type) from the expected naive-timestamp case, which also has
        # `.tz is None` — see docs/project/03_DATA_ACQUISITION.md's schema-drift risk.
        raise TypeError(
            f"expected tpep_pickup_datetime to be a timestamp column, got "
            f"{pickup_field.type!r} in {year_month} ({path})"
        )
    pickup_tz = pickup_field.type.tz

    con = duckdb.connect()
    coverage = con.execute(
        """
        SELECT
            min(tpep_pickup_datetime), max(tpep_pickup_datetime),
            min(tpep_dropoff_datetime), max(tpep_dropoff_datetime)
        FROM read_parquet(?)
        """,
        [str(path)],
    ).fetchone()
    histogram = con.execute(
        """
        SELECT extract('hour' FROM tpep_pickup_datetime) AS hour, count(*) AS n
        FROM read_parquet(?)
        GROUP BY hour
        ORDER BY hour
        """,
        [str(path)],
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

    con = duckdb.connect()
    lo, hi = _PLAUSIBLE_LOCATION_ID_RANGE

    # (check_name, SQL condition, params for that condition, ok_message, problem_message,
    # severity). Conditions and their params are combined into a single query below via
    # `sum(CASE WHEN ... THEN 1 ELSE 0 END)` so the 7.7M-row file is scanned once for all of
    # these checks (plus one more scan for `duplicate_rows`, which needs whole-row DISTINCT)
    # instead of once per check. `read_parquet(?)` and the `?` placeholders below are bound
    # positionally by DuckDB in the order they appear in the query text — see the query
    # assembly loop, which relies on that ordering.
    checks: list[tuple[str, str, list[object], str, str, Severity]] = [
        (
            "null_or_invalid_pu_location_id",
            f"PULocationID IS NULL OR PULocationID < {lo} OR PULocationID > {hi}",
            [],
            "all PULocationID values within the plausible zone-ID range",
            "rows with null/out-of-range PULocationID",
            Severity.WARNING,
        ),
        (
            "null_or_invalid_do_location_id",
            f"DOLocationID IS NULL OR DOLocationID < {lo} OR DOLocationID > {hi}",
            [],
            "all DOLocationID values within the plausible zone-ID range",
            "rows with null/out-of-range DOLocationID",
            Severity.WARNING,
        ),
        (
            "invalid_trip_distance",
            "trip_distance IS NULL OR trip_distance <= 0",
            [],
            "all trip_distance values are positive",
            "rows with null/zero/negative trip_distance",
            Severity.WARNING,
        ),
        (
            "invalid_fare_amount",
            "fare_amount IS NULL OR fare_amount < 0",
            [],
            "all fare_amount values are non-negative",
            "rows with null/negative fare_amount",
            Severity.WARNING,
        ),
        (
            "invalid_total_amount",
            "total_amount IS NULL OR total_amount < 0",
            [],
            "all total_amount values are non-negative",
            "rows with null/negative total_amount",
            Severity.WARNING,
        ),
        (
            "invalid_passenger_count",
            "passenger_count IS NULL OR passenger_count <= 0",
            [],
            "all passenger_count values are positive",
            "rows with null/zero passenger_count",
            Severity.WARNING,
        ),
        (
            "null_pickup_or_dropoff_datetime",
            "tpep_pickup_datetime IS NULL OR tpep_dropoff_datetime IS NULL",
            [],
            "no rows with a null pickup or dropoff timestamp",
            (
                "rows with a null pickup or dropoff timestamp (SQL's three-valued logic "
                "means these silently pass every other timestamp-based check below)"
            ),
            Severity.ERROR,
        ),
        (
            "dropoff_before_pickup",
            "tpep_dropoff_datetime < tpep_pickup_datetime",
            [],
            "no rows with dropoff before pickup",
            "rows where dropoff_datetime precedes pickup_datetime",
            Severity.ERROR,
        ),
        (
            "zero_duration_trip",
            "tpep_dropoff_datetime = tpep_pickup_datetime",
            [],
            "no zero-duration trips",
            "rows with identical pickup and dropoff timestamps",
            Severity.WARNING,
        ),
        (
            "excessive_trip_duration",
            # Elapsed seconds, not date_diff('hour', ...): the latter counts hour-boundary
            # crossings, so a 6h59m59s trip reports date_diff=6 and would be missed.
            "date_diff('second', tpep_pickup_datetime, tpep_dropoff_datetime) > 6 * 3600",
            [],
            "no trips longer than 6 hours",
            "rows with trip duration over 6 hours (likely a data error)",
            Severity.WARNING,
        ),
        (
            "pickup_outside_expected_month",
            "date_trunc('month', tpep_pickup_datetime) != ?::TIMESTAMP",
            [f"{year_month}-01"],
            f"all pickups fall within {year_month}",
            (
                f"rows with pickup datetime outside the expected {year_month} month "
                "(a known category of TLC data-entry error)"
            ),
            Severity.WARNING,
        ),
    ]

    select_parts = ["count(*) AS total"]
    params: list[object] = []
    for name, condition, condition_params, *_ in checks:
        select_parts.append(f"sum(CASE WHEN {condition} THEN 1 ELSE 0 END) AS {name}")
        params.extend(condition_params)
    params.append(str(path))

    row = con.execute(f"SELECT {', '.join(select_parts)} FROM read_parquet(?)", params).fetchone()
    total = row[0]
    counts = dict(zip((c[0] for c in checks), row[1:], strict=True))

    for name, _condition, _condition_params, ok_message, problem_message, severity in checks:
        check_count(
            report,
            name,
            counts[name] or 0,
            total=total,
            ok_message=ok_message,
            problem_message=problem_message,
            severity=severity,
        )

    distinct_count = con.execute(
        "SELECT count(*) FROM (SELECT DISTINCT * FROM read_parquet(?)) t", [str(path)]
    ).fetchone()[0]
    check_count(
        report,
        "duplicate_rows",
        total - distinct_count,
        total=total,
        ok_message="no exact duplicate rows",
        problem_message="exact duplicate rows",
    )

    return report


def run_validation_slice(
    year_month: str = "2019-01",
) -> tuple[TaxiSliceProfile | None, ValidationReport]:
    """Download (if needed) and validate one month's slice end to end.

    Returns `(None, report)` if the file's schema is missing a required column: `report`
    carries the ERROR-severity `required_columns` issue in that case, and `inspect_schema` is
    not called (it assumes the required columns are present and would otherwise raise a raw
    KeyError instead of this clean error path).
    """
    path = raw_path_for(year_month)
    # A download that was interrupted after writing the raw file but before its provenance
    # sidecar (e.g. process killed, disk full) must not be mistaken for complete.
    if not path.exists() or not provenance_path_for(path).exists():
        download_month(year_month)

    report = ValidationReport(source=f"taxi:{path.name}")
    columns = pq.ParquetFile(path).schema.names
    check_required_columns(report, columns, REQUIRED_COLUMNS)
    if report.has_errors():
        return None, report

    profile = inspect_schema(path, year_month)
    report = validate_month(path, year_month)
    return profile, report


if __name__ == "__main__":
    profile, report = run_validation_slice()
    if profile is not None:
        print(profile)
        print()
    print(report.summary())
