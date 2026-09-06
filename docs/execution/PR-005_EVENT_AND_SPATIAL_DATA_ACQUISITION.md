# PR-005: Event & Spatial Data Acquisition

| Field | Value |
|--------|-------|
| Name | PR-005 — Event & Spatial Data Acquisition |
| Version | 1.1.0 |
| Status | Complete |
| Last Updated | 2026-09-06 |

---

## Purpose

Acquire and validate the two remaining core data sources the analytical plan depends on: the
NYC taxi zone lookup/geometry (needed to identify Yankee Stadium's zone and support the
spatial analysis) and the 2019 Yankees regular-season home schedule (needed to define event
windows). This PR completes the overall "Data Acquisition & Source Validation" stage's
acceptance criteria, alongside PR-003 and PR-004.

## Context

[PR-003 (Data Acquisition Foundation)](PR-003_DATA_ACQUISITION_FOUNDATION.md) established
project scaffolding and shared ingestion utilities, and checked (during planning, read-only)
that the taxi zone lookup/geometry and Retrosheet's 2019 game logs were reachable — but did
not acquire them. Its
[Stage Breakdown](PR-003_DATA_ACQUISITION_FOUNDATION.md#stage-breakdown-across-pr-003-pr-004-pr-005)
section defined this PR's acceptance criteria in advance.

This PR originally branched from `feature/pr-003-data-acquisition-foundation` (not `main`,
not PR-004 — PR-005 only depends on PR-003's scaffolding and shared utilities, not on
PR-004's full-year taxi acquisition, per PR-003's own dependency note) and has since been
rebased onto `main` now that PR-003 is merged; it remains independent of PR-004, which is
still unmerged. It reuses PR-003's 2019-01 taxi validation slice for the LocationID
compatibility check rather than waiting on PR-004.

**Note on `docs/project/03_DATA_ACQUISITION.md`:** since PR-004 and PR-005 both branched from
PR-003 and both extend that document independently (PR-004 the taxi section, PR-005 the zones
and schedule sections plus the document's closing sections), the header-version/changelog
conflict this created has now been reconciled in this branch as part of rebasing onto `main`:
`1.2.0` (this PR, after addressing review findings) stacks above `1.0.1` (PR-003's
post-merge review fixes) — the actual section content never conflicted, since the two PRs
edit different sections. PR-004 is still unmerged and branches from pre-fix PR-003, so it
will need the same reconciliation (docs only, not code) when it's rebased or merged.

## Objective

1. Acquire and validate the taxi zone lookup table and zone geometry.
2. Confirm LocationID compatibility between the zone lookup and real taxi trip data.
3. Identify the taxi zone containing Yankee Stadium.
4. Acquire the 2019 Yankees regular-season home schedule from Retrosheet, filtered to home
   games.
5. Cross-validate the schedule against a secondary source, documenting (not silently
   resolving) any discrepancy.
6. Assess attendance-field availability and quality for the optional H5, without committing
   the project to using it.
7. Finalize `docs/project/03_DATA_ACQUISITION.md`'s zones and schedule sections.

## Scope

**In scope:**

- `src/event_impact/ingestion/taxi_zones.py`: download/validate the lookup table and
  geometry, a LocationID-compatibility check against taxi data, and Yankee Stadium zone
  identification via point-in-polygon.
- `src/event_impact/ingestion/yankees_schedule.py`: download and parse Retrosheet's 2019
  regular-season game log (field layout confirmed against the real file), filter to Yankees
  home games, validate the result, and cross-validate against a secondary source.
- `taxi.distinct_location_ids()` (small addition to PR-003's taxi module) and a few new
  `config.py` constants (zone/schedule URLs and raw-data paths) — reused, not duplicated.
- Deterministic, network-free tests for all of the above (synthetic DataFrames/GeoDataFrames
  and synthetic Retrosheet-format rows — no downloaded files, no live HTTP calls).
- Updating `docs/project/03_DATA_ACQUISITION.md`'s zones and schedule sections with real
  results, and this execution document.

**Out of scope:**

- Any change to the taxi acquisition/validation logic itself (PR-003/PR-004's scope).
- The zone distance/adjacency methodology for the spatial analysis (H3) — identification of
  Yankee Stadium's zone only, per `01_ANALYTICAL_PLAN.md`.
- The event-time methodology, event windows, or any use of the attendance data for H5 itself
  — acquisition and validation only.
- Any EDA, baseline/control-group selection, causal inference, hypothesis testing, feature
  engineering, visualization, ML, or weather data — out of scope for the entire acquisition
  stage.

## What was found

Full details in
[`docs/project/03_DATA_ACQUISITION.md`](../project/03_DATA_ACQUISITION.md#source-2-nyc-taxi-zone-lookup--geographic-data).
Highlights:

- **Taxi zones:** lookup table has 265 rows (`LocationID` 1–265: 263 real zones plus
  placeholder codes 264 "Unknown" and 265 "Outside of NYC"); geometry has 263 rows, all valid,
  CRS EPSG:2263. Every `LocationID` used in the 2019-01 taxi slice is present in the lookup
  table (full compatibility); the 2 unused lookup zones (Governor's/Ellis/Liberty Island and
  Great Kills Park) both have an obvious explanation.
- **Yankee Stadium zone: `LocationID 247` ("West Concourse", Bronx)** — identified via
  point-in-polygon against the stadium's real coordinates; a single, unambiguous match whose
  zone name independently corroborates the result.
- **Extraction bug caught and fixed:** the zone geometry zip's own top-level entry is already
  a `taxi_zones/` folder; extracting into a same-named subdirectory doubly-nested the path.
  Fixed before this PR's validation ran against real data.
- **Yankees schedule:** 81 regular-season home games (2019-03-28 to 2019-09-22), all at a
  single park ID (`NYC21`), confirming this Retrosheet park code for Yankee Stadium from the
  data itself.
- **Baseball-Reference confirmed blocked** (HTTP 403, even with a realistic browser
  `User-Agent`) — **Baseball Almanac used instead**, per PR-002's own named fallback.
  Cross-validating home-game dates against it found **zero discrepancies** in either
  direction.
- **Attendance:** available for 79 of 81 games; the 2 zero-attendance records are both
  doubleheader-game-1 records, where Retrosheet conventionally records combined attendance
  under game 2 — a known pattern, not a data error. Assessed as usable for the optional H5.
- **Confirmed (not newly discovered):** no game start-time (clock) field exists in either
  source — only day/night indicator and duration.

## Acceptance Criteria

- [x] Zone lookup table acquired and validated (LocationID uniqueness, required fields).
- [x] Zone geometry acquired and validated (geometry validity, CRS).
- [x] Zone LocationIDs cross-checked against PR-003's 2019-01 taxi slice for compatibility.
- [x] Yankee Stadium zone(s) identified.
- [x] Yankees 2019 regular-season home schedule acquired from Retrosheet, filtered to home
      games / regular season.
- [x] Schedule cross-checked against a secondary source where practical; discrepancies
      documented rather than silently resolved (none found).
- [x] Attendance-field availability and quality assessed and documented as optional (for H5).
- [x] `docs/project/03_DATA_ACQUISITION.md`'s zones and schedule sections completed.
- [x] Deterministic, network-free tests exist and pass (`uv run pytest` — 76 passed).
- [x] Lint clean (`uv run ruff check .`).

## Suggested Commits

1. `feat(ingestion): add config and shared helper for zones/schedule sources`
2. `feat(ingestion): add taxi zone lookup and geometry acquisition/validation`
3. `feat(ingestion): add Yankees 2019 schedule acquisition and cross-validation`
4. `docs: document taxi zone and Yankees schedule acquisition results`

## Related Documents

- [00_PROJECT_CHARTER.md](../project/00_PROJECT_CHARTER.md)
- [01_ANALYTICAL_PLAN.md](../project/01_ANALYTICAL_PLAN.md)
- [02_DATA_SOURCES.md](../project/02_DATA_SOURCES.md)
- [03_DATA_ACQUISITION.md](../project/03_DATA_ACQUISITION.md)
- [PR-003 — Data Acquisition Foundation](PR-003_DATA_ACQUISITION_FOUNDATION.md)
- [PR-004 — Full 2019 Taxi Dataset Acquisition](PR-004_FULL_TAXI_ACQUISITION.md)

## Changelog

### 1.1.0
Rebased onto `main` and addressed code-review findings on the taxi-zones and Yankees-schedule
modules — no acquisition numbers changed, all implementation-only fixes (see
[docs/project/03_DATA_ACQUISITION.md's 1.2.0 changelog entry](../project/03_DATA_ACQUISITION.md#changelog)
for the full list): a null `LocationID` no longer mislabels as a duplicate; zone-geometry
provenance is recorded only after extraction succeeds; the extracted shapefile is discovered
by search instead of a hardcoded path; `find_yankee_stadium_zone` now requires exactly one
matching zone; `check_location_id_compatibility`'s result now has severity encoding via a new
`validate_location_id_compatibility`; the Baseball Almanac cross-check degrades gracefully
instead of crashing on a network/parse failure, and a cross-validation failure severe enough
to indicate a broken secondary source is now ERROR-severity; a malformed schedule date is now
rejected instead of silently corrupted; and each module gained a `run_*_acquisition()`
orchestration function (plus `__main__` entry point) as the single reproducible path to this
document's numbers, reusing a new shared `download_and_record()` helper. Test count grew from
37 to 76 covering the above.

### 1.0.0
Initial version. Taxi zone lookup and geometry acquired and validated; Yankee Stadium zone
identified; Yankees 2019 regular-season home schedule acquired and cross-validated against
Baseball Almanac (used in place of the blocked Baseball-Reference). This PR completes the
overall Data Acquisition & Source Validation stage's acceptance criteria alongside PR-003 and
PR-004.
