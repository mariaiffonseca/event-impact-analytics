# PR-003: Data Acquisition Foundation

| Field | Value |
|--------|-------|
| Name | PR-003 — Data Acquisition Foundation |
| Subtitle | Project scaffolding + initial taxi source validation |
| Version | 1.0.0 |
| Status | Complete |
| Last Updated | 2026-08-20 |

---

## Purpose

Answer the question the task set for this stage: **can we reliably acquire, reproduce, and
validate the data the analytical plan depends on?** — starting with the NYC TLC Yellow Taxi
trip data, the largest and highest-engineering-risk of the three core sources. This is also
the first PR to introduce any code into the repository, so it establishes the Python project
scaffolding, package layout, data directories, and shared ingestion utilities that PR-004 and
PR-005 build on.

## Context

[PR-001 (Repository & Common Foundation)](../foundation/07_REPOSITORY_CONVENTIONS.md) and
[PR-002 (Project Definition)](PR-002_PROJECT_DEFINITION.md) are merged. PR-002's
[`02_DATA_SOURCES.md`](../project/02_DATA_SOURCES.md) inventoried three core sources — TLC
Yellow Taxi, taxi zones, Yankees schedule — but explicitly deferred all verification (format,
schema, reachability) to a later data-acquisition stage. That stage was originally scoped as
a single "PR-003." Given its size and the genuinely different engineering concerns across the
three sources (large columnar taxi data, geospatial zone data, a separate web-sourced
schedule), it was split into three PRs for reviewability:

1. **PR-003 — Data Acquisition Foundation** (this PR): project scaffolding + taxi validation
   slice.
2. **PR-004 — Full 2019 Taxi Dataset Acquisition**: executes the full 12-month acquisition
   strategy this PR documents.
3. **PR-005 — Event & Spatial Data Acquisition**: taxi zones + Yankees schedule.

See [Stage Breakdown](#stage-breakdown-across-pr-003-pr-004-pr-005) below for how the three
PRs relate and each one's acceptance criteria.

## Objective

1. Stand up the Python project (dependency management, package layout, data directories, test
   infrastructure) — nothing existed before this PR.
2. Add small, reusable ingestion utilities (download, provenance, generic validation
   reporting) that every source (taxi now, zones/schedule in PR-005) can reuse.
3. Acquire and validate a single-month taxi slice (2019-01) — actual schema, row count, file
   size, temporal coverage, timestamp/timezone semantics, and data-quality issues, all from
   real downloaded data rather than PR-002's provisional guesses.
4. Document a concrete, reproducible strategy for the full 12-month acquisition, without
   executing it.
5. Create [`docs/project/03_DATA_ACQUISITION.md`](../project/03_DATA_ACQUISITION.md) as the
   living acquisition/provenance record, with the taxi section fully populated and the
   zones/schedule sections explicitly marked deferred.

## Scope

**In scope:**

- `pyproject.toml` (uv-managed), `src/event_impact/` package (src layout), `tests/`,
  `data/{raw,interim,processed}/` with `.gitkeep`, `.gitignore` updates so raw data and
  provenance sidecars are never committed.
- `src/event_impact/config.py` — plain module-level constants for data paths and source URLs.
- `src/event_impact/ingestion/common/` — `http.py` (streaming download with retries),
  `provenance.py` (JSON sidecar per downloaded file), `validation.py` (a small
  `ValidationReport`/`ValidationIssue` structure and a couple of genuinely generic checks).
- `src/event_impact/ingestion/taxi.py` — download one month, inspect schema/coverage via
  PyArrow + DuckDB (no full in-memory load), and run source-quality validation: required
  columns, null/out-of-range LocationIDs, invalid distance/fare/total/passenger-count values,
  pickup/dropoff timestamp consistency (`dropoff >= pickup`, non-negative duration, excessive
  duration), duplicate rows, and pickup-month sanity.
- Investigating and documenting taxi timestamp/timezone semantics (naive local NYC time vs.
  UTC) from the real data, without implementing the event-time methodology itself.
- Deterministic, network-free tests for the above.
- `docs/project/03_DATA_ACQUISITION.md` and this execution document.

**Out of scope (deferred, not silently skipped):**

- Downloading or validating the other 11 months of 2019 taxi data — PR-004.
- Taxi zone lookup/geometry acquisition and Yankee Stadium zone identification — PR-005.
- Yankees schedule acquisition and cross-validation — PR-005.
- Any EDA, event windows, baseline/control-group selection, Difference-in-Differences or
  other causal-inference methods, hypothesis testing, causal claims, final feature
  engineering, final visualizations, machine learning, or weather data — out of scope for the
  entire acquisition stage (PR-003/004/005), not just this PR.
- Additional tooling not already required by the repository foundation docs (DVC, MLflow,
  pre-commit, mypy, CI pipelines) — not introduced here; would be scope creep.

## Deliverables and Requirements

1. **Project scaffolding** — `pyproject.toml`, `src/event_impact/`, `tests/`,
   `data/{raw,interim,processed}/`, updated `.gitignore`, `README.md`.
2. **Shared ingestion utilities** — `download_file()`, provenance sidecar read/write, and a
   small generic validation-report structure, each justified by concrete reuse across
   sources; no generic ingestion/validation framework built beyond that.
3. **Taxi validation module** — `src/event_impact/ingestion/taxi.py`, covering schema
   inspection, coverage inspection (including the timezone-semantics check), and the full
   validation-check list above.
4. **Tests** — `tests/ingestion/test_validation.py`, `tests/ingestion/test_taxi.py`; all
   deterministic, using local synthetic fixtures, no network access.
5. **Documentation** — `docs/project/03_DATA_ACQUISITION.md` (taxi section complete,
   zones/schedule sections deferred) and this file.

## Acceptance Criteria

- [x] `pyproject.toml` + `src/event_impact` package + `data/{raw,interim,processed}` exist;
      raw data directory is gitignored.
- [x] Shared download/provenance/validation utilities exist and are used by the taxi module.
- [x] 2019-01 taxi Parquet file downloaded, with a provenance sidecar recorded.
- [x] Actual schema, row count, file size, and temporal coverage of the slice are documented
      from real inspection (not assumed from PR-002).
- [x] Malformed/invalid record checks implemented and findings documented.
- [x] Pickup/dropoff timestamp consistency checks implemented and findings documented.
- [x] Timestamp/timezone semantics investigated and documented from real inspection.
- [x] A concrete, reproducible strategy for the full 12-month acquisition is documented (not
      executed).
- [x] `docs/project/03_DATA_ACQUISITION.md` exists with the taxi section complete, other
      sections explicitly deferred.
- [x] This execution document exists, including acceptance criteria for PR-004 and PR-005.
- [x] Deterministic, network-free tests exist and pass (`uv run pytest` — 25 passed).
- [x] Lint clean (`uv run ruff check .`).
- [x] No zone or schedule acquisition code, no full 12-month download, no analytical/EDA code.

## Stage Breakdown (across PR-003, PR-004, PR-005)

### PR-004 — Full 2019 Taxi Dataset Acquisition (not yet implemented)

Executes the full 2019 acquisition strategy documented in `03_DATA_ACQUISITION.md` (all 12
monthly Parquet files → `data/raw/taxi/`), reusing `download_month()` / `inspect_schema()` /
`validate_month()` from this PR unchanged for each month.

**Responsible for:** acquiring all 12 monthly raw taxi files; running this PR's source-level
validation checks against each of them; documenting coverage and data-quality issues per
month and in aggregate; recording provenance for every file.

**Explicitly NOT responsible for:** constructing the final analytical dataset, building
game × zone × time-bin (or any other) aggregates, event enrichment, EDA, event windows, or
event-impact calculation.

**Acceptance criteria:**
- [ ] All 12 months acquired with provenance sidecars.
- [ ] Per-month and aggregate validation results documented in `03_DATA_ACQUISITION.md`.
- [ ] No month silently dropped without documentation if it fails to acquire or validate
      cleanly.
- [ ] The two timestamp-semantics open questions from this PR (DST-transition behavior in
      March/November 2019, `congestion_surcharge` population across months) are checked and
      documented.

### PR-005 — Event & Spatial Data Acquisition (not yet implemented)

Taxi zone lookup + geometry acquisition and validation, Yankee Stadium zone identification,
and the Yankees 2019 regular-season home schedule (Retrosheet, cross-validated against
Baseball-Reference where reachable).

**Acceptance criteria:**
- [ ] Zone lookup table acquired and validated (LocationID uniqueness, required fields).
- [ ] Zone geometry acquired and validated (geometry validity, CRS).
- [ ] Zone LocationIDs cross-checked against this PR's 2019-01 taxi slice
      (`PULocationID`/`DOLocationID`) for compatibility.
- [ ] Yankee Stadium zone(s) identified.
- [ ] Yankees 2019 regular-season home schedule acquired from Retrosheet, filtered to home
      games / regular season.
- [ ] Schedule cross-checked against Baseball-Reference where reachable; discrepancies
      documented rather than silently resolved.
- [ ] Attendance-field availability and quality assessed and documented as optional (for H5).
- [ ] `docs/project/03_DATA_ACQUISITION.md` finalized — zones and schedule sections complete,
      satisfying the overall acquisition stage's acceptance criteria.

## Suggested Commits

1. `chore(ingestion): scaffold python project and data directories`
2. `feat(ingestion): add shared download/provenance/validation utilities`
3. `feat(ingestion): validate 2019-01 taxi trip data slice`
4. `test(ingestion): add taxi and validation tests`
5. `docs: add data acquisition documentation and PR-003 execution record`

## Related Documents

- [00_PROJECT_CHARTER.md](../project/00_PROJECT_CHARTER.md)
- [01_ANALYTICAL_PLAN.md](../project/01_ANALYTICAL_PLAN.md)
- [02_DATA_SOURCES.md](../project/02_DATA_SOURCES.md)
- [03_DATA_ACQUISITION.md](../project/03_DATA_ACQUISITION.md)
- [PR-002 — Project Definition](PR-002_PROJECT_DEFINITION.md)
- [Repository Conventions](../foundation/07_REPOSITORY_CONVENTIONS.md)

## Changelog

### 1.0.0
Initial version. Project scaffolding established; NYC TLC Yellow Taxi 2019-01 validation
slice acquired and validated; full 12-month acquisition strategy documented; PR-004 and
PR-005 scoped with explicit acceptance criteria.
