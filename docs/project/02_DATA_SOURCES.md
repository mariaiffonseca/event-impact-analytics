# Data Sources

| Field | Value |
|--------|-------|
| Name | Event Impact Analytics — Data Sources |
| Version | 1.1.0 |
| Status | Draft |
| Last Updated | 2026-08-20 |

---

## Purpose

Provide a structured inventory of all data sources currently considered for this project. This document records what is known about each source at the project-definition stage, sourced from publicly available documentation as of 2026-08-20. **No data is downloaded, and no acquisition, parsing, or validation code is written as part of this PR.** Full validation (exact schema, current file format, live availability, license terms) happens during data acquisition in a later PR.

---

## Validation Status Legend

| Status | Meaning |
|--------|---------|
| **Candidate** | The source has been identified as relevant and its general existence, purpose, and access point have been checked against public documentation, but its contents (exact schema, current format, live availability) have not been directly inspected. |
| **Requires Validation** | A specific detail below (a field, URL, format, or figure) is provisional, drawn from secondary or general documentation, and must be directly confirmed before being relied upon in later PRs. |
| **Deferred** | The source is not currently required; whether it is pursued depends on findings in later PRs. |

No source in this document is marked "Confirmed" in the sense of fully verified and ready to use — that level of verification requires actually acquiring the data, which is out of scope for this PR.

---

## Source 1: NYC TLC Yellow Taxi Trip Records

| Field | Value |
|---|---|
| **Source name** | NYC Yellow Taxi Trip Records |
| **Provider** | NYC Taxi & Limousine Commission (TLC), in partnership with the NYC Department of Information Technology & Telecommunications (DOITT) |
| **Purpose** | Primary dataset. Trip-level records used to measure taxi demand and trip characteristics around Yankee Stadium. |
| **URL** | Official landing page: `https://www.nyc.gov/site/tlc/about/tlc-trip-record-data.page` (links to monthly files and the trip record user guide). Historical direct file distribution has used `https://s3.amazonaws.com/nyc-tlc/trip+data/yellow_tripdata_YYYY-MM.csv`; more recent TLC publications are distributed as Parquet from `https://d37ci6vzurychx.cloudfront.net/trip-data/yellow_tripdata_YYYY-MM.parquet`. **Requires validation:** which format/location is authoritative for the 2019 files at acquisition time. |
| **Data format** | CSV (original 2019 distribution) and/or Parquet (per TLC's more recent publishing practice) — **requires validation** for the specific 2019 monthly files. |
| **Temporal coverage** | Monthly files; full 2019 = 12 files (`2019-01` through `2019-12`). |
| **Spatial coverage** | New York City (5 boroughs), referenced via TLC Taxi Zone `LocationID`s rather than raw latitude/longitude (TLC moved from lat/long to zone IDs prior to 2019 for rider privacy, per TLC documentation). |
| **Relevant fields** | Per the publicly available TLC Trip Record User Guide (`https://www.nyc.gov/assets/tlc/downloads/pdf/trip_record_user_guide.pdf`): `tpep_pickup_datetime`, `tpep_dropoff_datetime`, `PULocationID`, `DOLocationID`, `passenger_count`, `trip_distance`, `fare_amount`, `tip_amount`, `tolls_amount`, `total_amount`, `payment_type`, `RatecodeID`, `VendorID`. The `congestion_surcharge` field was introduced during 2019 and may not appear in every monthly file. **Requires validation** against the actual downloaded files — field names and availability have changed across TLC publication periods. |
| **Expected granularity** | One row per individual trip. |
| **Acquisition method** | Direct file download. Not performed in this PR — planned for a future data-acquisition PR. |
| **Licensing / usage considerations** | Published by TLC as open data. TLC states the data was collected via TPEP/LPEP-authorized technology providers and explicitly makes no representation as to its accuracy. Full usage terms should be reviewed on the official page before acquisition. |
| **Limitations** | No accuracy guarantee per TLC; excludes non-taxi mobility modes (subway, bus, for-hire vehicles/rideshare, walking); zone-level rather than exact-coordinate spatial resolution; publicly documented history of data quality issues (e.g., outlier fares/distances/timestamps) that will need empirical assessment. |
| **Validation status** | **Candidate.** Official access point and general publication practice verified against public documentation on 2026-08-20. Exact 2019 file format, current download location, and field-by-field schema **require validation** during data acquisition. |

---

## Source 2: NYC Taxi Zone Lookup / Geographic Data

| Field | Value |
|---|---|
| **Source name** | NYC Taxi Zone Lookup Table and Zone Geometry |
| **Provider** | NYC TLC (lookup table); NYC Open Data / NYC Department of City Planning-derived boundaries (zone geometry) |
| **Purpose** | Maps `PULocationID` / `DOLocationID` values in the trip data to zone names, boroughs, and geographic boundaries. Required to identify the zone(s) covering Yankee Stadium and to support the spatial (distance-based) analysis in [01_ANALYTICAL_PLAN.md](01_ANALYTICAL_PLAN.md). |
| **URL** | Lookup table: `https://d37ci6vzurychx.cloudfront.net/misc/taxi_zone_lookup.csv` (linked from the official TLC trip record page). Zone boundary/geometry: candidate at the same CloudFront `/misc/` location (commonly distributed as `taxi_zones.zip`, a shapefile) — **requires validation**. Cross-check / alternative source: NYC Open Data, "NYC Taxi Zones" dataset at `https://data.cityofnewyork.us/Transportation/NYC-Taxi-Zones/8meu-9t5y`. |
| **Data format** | CSV (lookup table); Shapefile or GeoJSON (zone geometry, via NYC Open Data). |
| **Temporal coverage** | Not a time series — a static reference table. TLC has revised zone definitions historically; version alignment with 2019 trip data **requires validation**. |
| **Spatial coverage** | New York City, 5 boroughs; commonly cited as 263 zones — **requires validation** against the actual downloaded file. |
| **Relevant fields** | Per publicly documented structure: `LocationID`, `Borough`, `Zone`, `service_zone`. **Requires validation** against the actual downloaded file. |
| **Expected granularity** | One row per taxi zone. |
| **Acquisition method** | Direct file download. Not performed in this PR — planned for a future data-acquisition PR. |
| **Licensing / usage considerations** | Distributed as open data alongside TLC trip records, and/or under the NYC Open Data open-data policy. |
| **Limitations** | Zones are irregular polygons of varying size and shape, not concentric rings — any "distance from stadium" analysis will require an explicit, justified methodology (e.g., zone centroid distance), which has not yet been chosen. |
| **Validation status** | **Candidate.** Lookup table URL identified against public documentation on 2026-08-20. Zone geometry URL, exact field list, and zone-definition version **require validation** during data acquisition. |

---

## Source 3: New York Yankees 2019 Regular-Season Home Game Schedule

| Field | Value |
|---|---|
| **Source name** | New York Yankees 2019 Regular-Season Home Game Schedule (and, optionally, attendance) |
| **Provider** | Candidate sources, with distinct intended roles, none yet definitively selected — **Retrosheet** (`retrosheet.org`), the preferred/primary candidate as a structured, programmatically accessible source; **Baseball-Reference** (`baseball-reference.com`), a secondary source intended for cross-validation of the primary source; **Baseball Almanac** (`baseball-almanac.com`), an alternative/fallback source if the preferred sources prove insufficient. Final selection is deferred to data acquisition. |
| **Purpose** | Identify the dates and start times of all 2019 Yankees regular-season home games at Yankee Stadium, used to define event windows for the core analysis (H1–H4). Optionally, provide per-game attendance figures for the H5 extension. |
| **URL** | Retrosheet season game logs: `https://www.retrosheet.org/gamelogs`; Retrosheet event files: `https://www.retrosheet.org/eventfile.htm`. Baseball-Reference schedule/results page: `https://www.baseball-reference.com/teams/NYY/2019-schedule-scores.shtml`. Baseball Almanac schedule page: `https://www.baseball-almanac.com/teamstats/schedule.php?y=2019&t=NYA`. |
| **Data format** | Retrosheet: structured, delimited game log / event files intended for programmatic use. Baseball-Reference and Baseball Almanac: HTML tables, which would require scraping if used. |
| **Temporal coverage** | Full 2019 MLB regular season (approx. late March–September 2019). Per project scope ([00_PROJECT_CHARTER.md](00_PROJECT_CHARTER.md)), Yankees postseason games are out of scope for this project unless a future PR deliberately expands it. |
| **Spatial coverage** | Single venue: Yankee Stadium, Bronx, NY. Only home games are relevant to this project; away games are out of scope for event-window definition. |
| **Relevant fields** | Candidate, per Retrosheet's publicly documented game log structure: game date, home team, away team, start time, attendance, game site/venue. **Requires validation** against the actual downloaded files — exact field names and structure have not been directly inspected. |
| **Expected granularity** | One record per game. |
| **Acquisition method** | Not yet determined. Retrosheet, as the preferred/primary candidate, would be acquired via direct structured download; Baseball-Reference would be used for cross-validation and Baseball Almanac as an alternative/fallback if needed, both of which would require scraping if used. Direct download from a structured source is preferred over HTML scraping where possible. To be finalized during data acquisition. |
| **Licensing / usage considerations** | Retrosheet publishes data for research and non-commercial use under its own notice (`https://www.retrosheet.org/datause.txt`); terms must be reviewed before acquisition. If Baseball-Reference or Baseball Almanac are used instead or as cross-validation, their respective terms of use must be reviewed and respected. |
| **Limitations** | Reported attendance figures (if used for H5) are typically announced or ticketed attendance rather than verified turnstile counts, and may not closely track actual mobility demand. Schedule data should be cross-validated across sources, since games are occasionally rescheduled (e.g., due to weather) or played as part of doubleheaders. |
| **Validation status** | **Candidate.** General existence and structure of these sources verified against public documentation on 2026-08-20. Exact schedule and attendance data, field-level schema, and licensing terms **require validation** during data acquisition. Per the project's methodological principles, attendance data specifically must be validated for availability and quality before H5 is pursued. |

---

## Source 4: Weather Data (Potential, Deferred)

| Field | Value |
|---|---|
| **Source name** | NOAA daily/hourly weather observations for New York City |
| **Provider** | Candidate — NOAA National Centers for Environmental Information (NCEI), via Climate Data Online (CDO). |
| **Purpose** | Potential confounder control. Weather (e.g., precipitation, temperature) may independently affect taxi demand and could need to be accounted for if a later PR's exploratory analysis shows it materially confounds the game-day comparison. |
| **URL** | Climate Data Online portal: `https://www.ncei.noaa.gov/cdo-web/`. Candidate representative station: NY City Central Park, station ID `GHCND:USW00094728`. Exact programmatic access path (API endpoint, if used) not yet verified. |
| **Data format** | CSV or JSON, depending on access method (CDO web export vs. NCEI data-access API) — **requires validation**. |
| **Temporal coverage** | Daily (or sub-daily, depending on the specific dataset selected) for 2019, if acquired. |
| **Spatial coverage** | Single representative station (Central Park), used as a citywide proxy. Does not capture hyper-local conditions at Yankee Stadium specifically. |
| **Relevant fields** | Not yet determined — depends on which NOAA dataset is selected (e.g., GHCN-Daily vs. Local Climatological Data) if this source is pursued. |
| **Expected granularity** | Daily, or hourly if a sub-daily dataset is used. |
| **Acquisition method** | Not yet determined. Only to be pursued if a later PR's exploratory analysis indicates weather is a material confounder that needs to be controlled for. |
| **Licensing / usage considerations** | NOAA/NCEI data is U.S. government public-domain data; standard attribution practices apply. |
| **Limitations** | Single-station proxy; potential mismatch between citywide weather conditions and hyper-local, stadium-area effects. |
| **Validation status** | **Deferred.** Not currently required for this project. Inclusion is contingent on findings in a later exploratory-analysis PR and is out of scope for this PR. |

---

## Summary

| # | Source | Status | Required for core hypotheses (H1–H4)? |
|---|--------|--------|----------------------------------------|
| 1 | NYC Yellow Taxi Trip Records | Candidate | Yes |
| 2 | NYC Taxi Zone Lookup / Geographic Data | Candidate | Yes |
| 3 | NY Yankees 2019 Regular-Season Home Game Schedule (+ attendance) | Candidate | Yes (schedule); attendance only for optional H5 |
| 4 | NOAA Weather Data | Deferred | No — only if later validated as necessary |

---

## Related Documents

- [00_PROJECT_CHARTER.md](00_PROJECT_CHARTER.md)
- [01_ANALYTICAL_PLAN.md](01_ANALYTICAL_PLAN.md)
- [PR-002 — Project Definition](../execution/PR-002_PROJECT_DEFINITION.md)

---

## Changelog

### 1.1.0
Clarified primary/secondary/fallback roles among the candidate Yankees schedule sources (Retrosheet, Baseball-Reference, Baseball Almanac); confirmed regular-season scope for the Yankees schedule source, consistent with the Project Charter.

### 1.0.0
Initial version, created under PR-002 (Project Definition).
