# PR-004: Full 2019 Taxi Dataset Acquisition

| Field | Value |
|--------|-------|
| Name | PR-004 — Full 2019 Taxi Dataset Acquisition |
| Version | 1.0.0 |
| Status | Complete |
| Last Updated | 2026-08-21 |

---

## Purpose

Execute the full 2019 taxi acquisition strategy that
[PR-003](PR-003_DATA_ACQUISITION_FOUNDATION.md) validated on a single month and documented,
but did not run: download and validate all 12 monthly Parquet files, reusing PR-003's
functions unchanged, and resolve the two questions PR-003 explicitly left open (whether
`congestion_surcharge` stays populated across the year, and whether the naive-local-time
timestamp conclusion holds across the March/November DST transitions).

## Context

PR-003 (Data Acquisition Foundation) acquired and validated a single-month slice (2019-01)
and documented, but did not execute, a strategy for the full 12-month acquisition — see its
[Stage Breakdown](PR-003_DATA_ACQUISITION_FOUNDATION.md#stage-breakdown-across-pr-003-pr-004-pr-005)
section for the acceptance criteria this PR is expected to satisfy. This PR branches from
PR-003 (not `main`, since PR-003 is not yet merged) and depends only on its scaffolding and
`src/event_impact/ingestion/taxi.py` module.

## Objective

1. Add a thin orchestration layer over PR-003's per-month functions
   (`acquire_and_validate_year()`, `aggregate_issue_counts()`) — no change to the underlying
   download/inspect/validate logic.
2. Actually download and validate all 12 months of 2019 taxi trip data.
3. Document per-month and aggregate results in `docs/project/03_DATA_ACQUISITION.md`.
4. Resolve PR-003's two open questions with real evidence from the full year of data.

## Scope

**In scope:**

- `acquire_and_validate_year()` / `MonthResult` / `aggregate_issue_counts()` in
  `src/event_impact/ingestion/taxi.py`, plus a `--full-year` CLI flag.
- An informational diagnostic for `congestion_surcharge` and `airport_fee` (present but not
  required in every month per PR-003's findings) — null-rate per month, so their real-world
  usability across the year can be assessed.
- Downloading and validating all 12 real monthly files.
- Updating `docs/project/03_DATA_ACQUISITION.md`'s taxi section with full-year results.
- Deterministic, network-free tests for the new orchestration/aggregation logic (using
  synthetic fixtures and `monkeypatch`, not real downloads).

**Out of scope (per the Stage Breakdown in PR-003's execution doc):**

- Constructing the final analytical dataset, game × zone × time-bin or any other aggregates,
  event enrichment, EDA, event windows, or event-impact calculation.
- Taxi zones and Yankees schedule acquisition — PR-005.
- Any decision about filtering/cleaning the data-quality issues found (that's for whichever
  later PR builds the analytical dataset — this PR only documents them).
- Additional tooling (DVC, MLflow, pre-commit, mypy, CI) not already required by the
  repository foundation docs.

## What was found

All 12 months acquired successfully — no month failed to download or validate, so none was
dropped. Full results are in
[`docs/project/03_DATA_ACQUISITION.md`](../project/03_DATA_ACQUISITION.md#full-2019-acquisition--confirmed-pr-004).
Highlights:

- **84,598,444 rows** across 12 months, **1,243,532,931 bytes (≈1.24 GB)** total — in line
  with PR-003's ~1.3 GB estimate.
- Schema and the `PULocationID`/`DOLocationID` plausible-range check are clean in every
  month — the January slice's schema was representative of the full year.
- **`congestion_surcharge`** is present every month; its null rate is dramatically higher in
  January (63.47%) than any other month (0.42%–0.74%) — consistent with a rollout gap when
  NY State's congestion surcharge law took effect, not a data-integrity problem. Resolves
  PR-003's open question.
- **`airport_fee` is null for 100% of rows in every single month of 2019** — the column
  exists but carries no usable data this year. Not previously confirmed at this scale by
  PR-003 (which only had one month to look at).
- **DST transitions confirm naive local wall-clock time, resolving PR-003's other open
  question, with a concrete data-quality consequence:** March 10 (spring-forward) has exactly
  zero pickups in the skipped 2–3 AM hour; November 3 (fall-back) has roughly double the
  normal pickup count in the repeated 1–2 AM hour; and **973 of the year's 1,071
  `dropoff_before_pickup` rows (91%) occur on November 3 alone** — trips spanning the fold
  read as ending before they started. This is documented, not corrected, in this PR.

## Acceptance Criteria

- [x] All 12 months acquired with provenance sidecars.
- [x] Per-month and aggregate validation results documented in `03_DATA_ACQUISITION.md`.
- [x] No month silently dropped without documentation if it fails to acquire or validate
      cleanly (none did).
- [x] The two timestamp-semantics open questions from PR-003 (DST-transition behavior,
      `congestion_surcharge` population across months) are checked and documented.
- [x] Deterministic, network-free tests exist for the new orchestration/aggregation logic
      (`uv run pytest` — 18 passed).
- [x] Lint clean (`uv run ruff check .`).
- [x] No analytical dataset, aggregates, event enrichment, EDA, or event-window code
      introduced.

## Suggested Commits

1. `feat(ingestion): add full-year taxi acquisition and validation orchestration`
2. `docs: document full 2019 taxi acquisition results`

## Related Documents

- [00_PROJECT_CHARTER.md](../project/00_PROJECT_CHARTER.md)
- [01_ANALYTICAL_PLAN.md](../project/01_ANALYTICAL_PLAN.md)
- [03_DATA_ACQUISITION.md](../project/03_DATA_ACQUISITION.md)
- [PR-003 — Data Acquisition Foundation](PR-003_DATA_ACQUISITION_FOUNDATION.md)

## Changelog

### 1.0.0
Initial version. All 12 months of 2019 NYC TLC Yellow Taxi trip data acquired and validated;
both open questions from PR-003 resolved with real full-year evidence.
