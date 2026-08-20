# Data Acquisition

| Field | Value |
|--------|-------|
| Name | Event Impact Analytics — Data Acquisition |
| Version | 1.0.0 |
| Status | Draft (living document — extended by PR-004 and PR-005) |
| Last Updated | 2026-08-20 |

---

## Purpose

This is a **living data-provenance and acquisition record**, not a one-time specification.
It documents what was actually acquired, from where, in what form, with what validation
results, and with what limitations — as opposed to [`02_DATA_SOURCES.md`](02_DATA_SOURCES.md),
which recorded the pre-acquisition inventory of *candidate* sources. Anything stated here as a
fact was directly observed from real downloaded data on the date noted, not assumed.

This document is created by **PR-003** (project scaffolding + taxi validation slice),
extended by **PR-004** (full 12-month taxi acquisition), and finalized by **PR-005** (taxi
zones + Yankees schedule) — see the changelog at the bottom for what each PR contributed.

## Status legend

| Status | Meaning |
|--------|---------|
| **Confirmed** | Directly observed from real acquired data. |
| **Assumption** | Not yet directly verified; carried forward from `02_DATA_SOURCES.md` or general knowledge, flagged as such. |
| **Decision** | A choice made during acquisition (e.g. which format/URL to use), with the reasoning recorded. |
| **Unresolved** | A known open question, not yet answered, that a later PR must address. |

---

## Source 1: NYC TLC Yellow Taxi Trip Records

### Provider, format, and access — Confirmed

- **Provider:** NYC Taxi & Limousine Commission (TLC).
- **Distribution:** `https://d37ci6vzurychx.cloudfront.net/trip-data/yellow_tripdata_{YYYY-MM}.parquet`
- **Format:** **Parquet.** Confirmed directly by downloading and reading
  `yellow_tripdata_2019-01.parquet` — this resolves the open question left in
  `02_DATA_SOURCES.md` ("requires validation: which format/location is authoritative for the
  2019 files"). **Decision:** use this CloudFront Parquet distribution for all 2019 months,
  not the historical `s3://nyc-tlc/trip+data/*.csv` path — Parquet is columnar, smaller on
  disk, and lets DuckDB/PyArrow read schema and run aggregate queries without loading the
  file into memory, which CSV does not offer as cleanly.
- **Licensing:** Published by TLC as open data. TLC states the data was collected via
  TPEP/LPEP-authorized technology providers and makes no representation as to its accuracy
  (this shapes how validation findings below are treated — as documented data-quality issues
  to work around, not as errors to report upstream).

### Acquisition method — Confirmed

Direct HTTPS download, streamed to disk (`src/event_impact/ingestion/common/http.py:download_file`),
never buffered fully in memory. A JSON provenance sidecar
(`src/event_impact/ingestion/common/provenance.py`) is written next to every downloaded file,
recording source URL, retrieval timestamp, size, and SHA-256 — this is the reproducibility
record for that file; it is not committed to Git (see [Data Storage](#data-storage)).

### Validation slice: 2019-01 — Confirmed

One month (January 2019) was downloaded and inspected before deciding on a full-year
strategy, per the task's "validate a slice first" requirement.

| Property | Value |
|---|---|
| File | `yellow_tripdata_2019-01.parquet` |
| Retrieved | 2026-08-20 |
| File size | 110,439,634 bytes (110.4 MB / 105.3 MiB) |
| SHA-256 | `3ad95f39714bfc9864219e69e577f119925c6ba32d384ac68d40bdad1dc7726d` |
| Row count | 7,696,617 |

**Actual schema (19 columns, confirmed — not assumed from PR-002's guess):**

`VendorID`, `tpep_pickup_datetime`, `tpep_dropoff_datetime`, `passenger_count`,
`trip_distance`, `RatecodeID`, `store_and_fwd_flag`, `PULocationID`, `DOLocationID`,
`payment_type`, `fare_amount`, `extra`, `mta_tax`, `tip_amount`, `tolls_amount`,
`improvement_surcharge`, `total_amount`, `congestion_surcharge`, `airport_fee`

All fields PR-002 anticipated for the analytical plan (`tpep_pickup_datetime`,
`tpep_dropoff_datetime`, `PULocationID`, `DOLocationID`, `passenger_count`, `trip_distance`,
`fare_amount`, `total_amount`) are present. Two discoveries relative to PR-002:

- `congestion_surcharge` **is** present in the January 2019 file — PR-002 flagged this as
  possibly month-dependent; confirmed present from month 1. Whether it stays populated (vs.
  present-but-null) across all 12 months is left for PR-004 to check.
- `airport_fee` is present and was **not** mentioned anywhere in `02_DATA_SOURCES.md`'s field
  list — an extra column beyond what PR-002 anticipated. Not currently used by any core
  hypothesis (H1–H4); noted here for completeness.

### Temporal coverage — Confirmed

Raw min/max timestamps in the file:

| | min | max |
|---|---|---|
| `tpep_pickup_datetime` | 2001-02-02 14:55:07 | 2088-01-24 00:25:39 |
| `tpep_dropoff_datetime` | 2001-02-02 15:07:27 | 2088-01-24 07:28:25 |

These extremes are **not** the real coverage of the file — they are the known TLC
data-entry-error category also caught by the `pickup_outside_expected_month` check below (537
rows, 0.0070%). The overwhelming majority of rows fall within January 2019 as expected;
outlier timestamps are documented as a data-quality issue, not corrected here (no cleaning
happens in this PR — see [Known data-quality issues](#known-data-quality-issues-confirmed)).

### Timestamp / timezone semantics — Confirmed

This directly addresses the task's requirement to establish timestamp semantics before any
later temporal analysis compares trip times to Yankees game start times:

- **Parquet type:** `tpep_pickup_datetime`'s Arrow type carries **no timezone** (`tz=None`) —
  it is a naive timestamp, not a UTC-aware one.
- **Empirical check:** an hourly histogram of pickups in the slice shows the expected daily
  NYC taxi demand shape for **local** time — a trough around 3–5 AM (hour 3: 78,086: hour 4:
  61,424, the daily minimum) rising to an evening peak around 6 PM (hour 18: 515,390). If
  these timestamps were actually UTC mislabeled as local, the real local trough (~4 AM EST)
  would appear at hour 9 in the raw data instead — it does not. This is consistent with TLC's
  documented convention that trip timestamps are local (America/New_York) wall-clock time.
- **Conclusion for later PRs:** treat `tpep_pickup_datetime` / `tpep_dropoff_datetime` as
  naive America/New_York local time, not UTC. January 2019 does not span a DST transition
  (2019's transitions were March 10 and November 3), so this slice cannot directly confirm
  DST-boundary behavior (e.g. whether the fall-back hour is duplicated/ambiguous in the raw
  data). **Unresolved, deferred to PR-004:** re-check this specifically for the March and
  November 2019 files once acquired.
- **Not decided here:** whether/how to explicitly localize these timestamps (e.g. attach a
  timezone) for the eventual comparison against Yankees game start times — that belongs to
  the event-time methodology in a later analytical PR, not this acquisition stage.

### Validation results — Confirmed

All checks below ran directly against the Parquet file via DuckDB (`read_parquet`, no full
in-memory load) — see `src/event_impact/ingestion/taxi.py:validate_month`. This is
source-quality validation only; no rows were removed, cleaned, or imputed.

| Check | Result |
|---|---|
| Required columns present | OK — all present |
| `PULocationID` / `DOLocationID` null or outside plausible range (1–265) | OK — none found. **Caveat:** "plausible range" is a hardcoded sanity bound, not yet cross-checked against the real zone lookup table — that authoritative check is PR-005's job once the lookup table is acquired. |
| Invalid `trip_distance` (null/zero/negative) | 55,089 rows (0.7158%) |
| Invalid `fare_amount` (null/negative) | 7,129 rows (0.0926%) |
| Invalid `total_amount` (null/negative) | 7,127 rows (0.0926%) |
| Invalid `passenger_count` (null/zero) | 146,053 rows (1.8976%) |
| `dropoff_datetime` before `pickup_datetime` | **4 rows (0.0001%)** — flagged as an error-severity issue |
| Zero-duration trips (`dropoff == pickup`) | 6,553 rows (0.0851%) |
| Trip duration over 6 hours | 20,524 rows (0.2667%) |
| Pickup outside the expected month (2019-01) | 537 rows (0.0070%) — this is the source of the 2001/2088 extremes above |
| Exact duplicate rows | 0 |

### Known data-quality issues — Confirmed

All of the above are real, from the actual January 2019 file, and are consistent with TLC's
own no-accuracy-guarantee disclaimer:

- A small but non-zero fraction of rows have invalid trip distance, fare, or passenger count
  (each well under 2% of rows).
- A tiny number (4) of rows have a dropoff timestamp before pickup — physically impossible,
  clearly a data error, and rare enough not to threaten overall data usability.
- A small number of rows carry corrupted timestamps placing them far outside January 2019
  (as early as 2001, as late as 2088).
- None of these issues are fixed in this PR. They are documented so later PRs (full
  acquisition, analytical dataset construction) apply a **consistent, justified** filtering
  strategy instead of ad hoc exclusions.

### Full 2019 acquisition strategy — Decision (documented here, executed in PR-004)

- Reuse `download_month()` / `inspect_schema()` / `validate_month()` from
  `src/event_impact/ingestion/taxi.py` unchanged, once per month for `2019-01` through
  `2019-12`.
- Each month is validated independently via DuckDB directly against its own Parquet file — no
  month is ever loaded fully into Python/pandas memory. Cross-month aggregation (e.g. total
  row count, combined validation summary) can be done either by combining each month's
  DuckDB-computed summary numbers, or via `read_parquet('data/raw/taxi/yellow_tripdata_2019-*.parquet')`
  (DuckDB's glob support), which still doesn't require an in-memory pandas concat of 12 files.
- Estimated full-year size: ~110 MB × 12 ≈ 1.3 GB — confirmed small enough for local disk,
  no need for cloud storage or out-of-process handling.
- PR-004 must decide (not decided here) how to treat months where a check fails
  unexpectedly (e.g. a month missing `congestion_surcharge` entirely, or a formatting change)
  — the strategy is "validate every month with the same checks and document what's found,"
  not "assume all 12 months are structurally identical to January."

---

## Source 2: NYC Taxi Zone Lookup / Geographic Data — Deferred to PR-005

Not acquired in this PR. Reachability was checked during planning (read-only, not treated as
acquisition):

- `https://d37ci6vzurychx.cloudfront.net/misc/taxi_zone_lookup.csv` — reachable; header
  confirmed as `LocationID, Borough, Zone, service_zone`, matching `02_DATA_SOURCES.md`'s
  expectation exactly.
- `https://d37ci6vzurychx.cloudfront.net/misc/taxi_zones.zip` — reachable; confirmed to be a
  real Shapefile archive (`.shp`/`.dbf`/`.prj`/`.cpg`), ~1 MB.

Full acquisition, LocationID-uniqueness validation, geometry/CRS validation, compatibility
cross-check against the taxi `PULocationID`/`DOLocationID` values above (this PR's slice can
be reused for that — no need to wait for PR-004's full year), and Yankee Stadium zone
identification are all PR-005's scope.

## Source 3: NY Yankees 2019 Regular-Season Home Game Schedule — Deferred to PR-005

Not acquired in this PR. Reachability was checked during planning:

- `https://www.retrosheet.org/gamelogs/gl2019.zip` — reachable. Confirmed **regular-season
  only** (Retrosheet distributes postseason game logs as separate archives), which lines up
  directly with this project's regular-season-only scope.
- Confirmed fields present in the Retrosheet game log format: date, visiting/home team, park
  ID, attendance, and game duration in minutes.
- **Discovery relative to PR-002:** there is **no game start-time (clock) field** in
  Retrosheet's game logs — only a day/night indicator and game duration. PR-002's initial
  assumption ("a sufficiently accurate schedule with dates **and start times**") is only
  partly correct: dates are reliably available from Retrosheet, but a clock start time is
  not. If a start-time field ends up necessary for the event-window methodology, PR-005 will
  need another source for it (e.g. Baseball-Reference) — not assumed resolved here.
- `https://www.nyc.gov/site/tlc/about/tlc-trip-record-data.page` and
  `https://www.baseball-reference.com/teams/NYY/2019-schedule-scores.shtml` both returned
  HTTP 403 to a plain fetch during reachability checking — basic bot-blocking on their HTML
  pages (the TLC data files themselves, served from CloudFront, are unaffected). **Unresolved,
  for PR-005:** acquisition code will need a realistic `User-Agent` (already the default in
  `src/event_impact/ingestion/common/http.py`); if Baseball-Reference remains blocked even
  with that, cross-validation there may have to be a documented best-effort/manual step
  rather than fully automated.

Full acquisition, regular-season/home-game filtering, Baseball-Reference cross-validation
with discrepancies documented (not silently resolved), and attendance-field
availability/quality assessment for the optional H5 are all PR-005's scope.

---

## Data provenance mechanism

Every downloaded file gets a `<filename>.provenance.json` sidecar (written by
`src/event_impact/ingestion/common/provenance.py:write_provenance`) recording: source URL,
retrieval timestamp (UTC), file size, and SHA-256. This is a lightweight, per-file JSON
record — not a database or asset-tracking system — proportional to this project's scale. The
sidecar lives next to the raw file under `data/raw/`, so it is excluded from Git by the same
rule that excludes the data itself (see [Data Storage](#data-storage)); the facts that matter
for reproducibility (URL, format, date, size, checksum) are instead captured directly in this
document.

## Data Storage

```
data/
├── raw/        # untouched downloads (e.g. data/raw/taxi/yellow_tripdata_2019-01.parquet) — gitignored
├── interim/     # not yet used
└── processed/   # not yet used
```

`data/raw/`, `data/interim/`, and `data/processed/` are gitignored (only `.gitkeep` is
tracked, so the directory structure exists in a fresh checkout). No dataset, and no
provenance sidecar, is committed to Git.

## Reproducibility instructions

```bash
uv sync
uv run python -m event_impact.ingestion.taxi
```

This downloads `data/raw/taxi/yellow_tripdata_2019-01.parquet` (if not already present),
writes its provenance sidecar, and prints the schema/coverage profile and validation report
shown above. Re-running it after the file already exists skips the download and re-validates
the file on disk.

To validate the underlying logic without any network access:

```bash
uv run pytest
```

---

## Unresolved issues

- Whether `congestion_surcharge` stays populated (vs. present-but-null) across all 12 months
  — check during PR-004.
- Whether the January 2019 timestamp-semantics conclusion (naive local NYC time) holds across
  DST transitions (March/November 2019) — check during PR-004.
- Whether the "plausible LocationID range" sanity check (1–265) matches the authoritative
  zone lookup table — resolve during PR-005.
- Whether Baseball-Reference will allow automated cross-validation of the Yankees schedule, or
  whether that has to remain a documented manual/best-effort step — resolve during PR-005.
- Whether a Yankees game start-time (clock) is actually needed for the eventual event-window
  methodology, and if so, which source provides it — not this stage's decision; flagged for
  whichever later PR defines event windows.

## Decisions deferred to later PRs

- The full 12-month taxi acquisition and its aggregate validation results — PR-004.
- Any decision about filtering/cleaning the data-quality issues documented above (invalid
  distances/fares/passenger counts, corrupted timestamps, dropoff-before-pickup rows) —
  deferred to whichever later PR builds the analytical dataset. This PR only documents them.
- Taxi zone lookup/geometry acquisition, Yankee Stadium zone identification, and the
  zone-to-taxi-data LocationID compatibility check — PR-005.
- Yankees schedule acquisition, regular-season/home-game filtering, and cross-validation
  against Baseball-Reference — PR-005.
- The event-time methodology (how pickup/dropoff timestamps get related to game start times,
  what event window is used) — explicitly out of scope for the acquisition stage entirely,
  per `01_ANALYTICAL_PLAN.md`.

---

## Related Documents

- [00_PROJECT_CHARTER.md](00_PROJECT_CHARTER.md)
- [01_ANALYTICAL_PLAN.md](01_ANALYTICAL_PLAN.md)
- [02_DATA_SOURCES.md](02_DATA_SOURCES.md)
- [PR-003 — Data Acquisition Foundation](../execution/PR-003_DATA_ACQUISITION_FOUNDATION.md)

---

## Changelog

### 1.0.0
Initial version, created under PR-003 (Data Acquisition Foundation). Taxi source fully
documented from a real validation slice (2019-01); taxi zones and Yankees schedule sections
created but explicitly deferred to PR-005, pending only reachability checks performed during
planning.
