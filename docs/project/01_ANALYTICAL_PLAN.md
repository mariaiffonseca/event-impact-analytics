# Analytical Plan

| Field | Value |
|--------|-------|
| Name | Event Impact Analytics — Analytical Plan |
| Version | 1.0.0 |
| Status | Draft |
| Last Updated | 2026-08-20 |

---

## Purpose

Define the analytical direction for the project: the questions it investigates, the hypotheses it tests, and the candidate methods available to test them. This document intentionally distinguishes between:

- **Planned** — decided as part of the project's direction.
- **Candidate** — a plausible approach under consideration, not yet chosen.
- **Data-dependent** — cannot be finalized until real data is acquired and validated in a later PR.

No implementation choice in this document should be read as final. Fixed parameters such as a specific event window, baseline, control group, statistical test, or causal inference method are explicitly **not** locked in here — see [Event Windows](#event-windows), [Baseline Strategies](#baseline-strategies), [Comparison / Control Strategies](#comparison--control-strategies), and [Candidate Statistical Approaches](#candidate-statistical-approaches).

---

## Main Research Question

> How do New York Yankees home games affect taxi demand and travel patterns around Yankee Stadium?

As stated in [00_PROJECT_CHARTER.md](00_PROJECT_CHARTER.md), this is an observational study. See [Association vs. Causality](#association-vs-causality).

---

## Analytical Questions

1. Is taxi activity around Yankee Stadium higher during periods surrounding home games than during comparable non-game periods?
2. When does any observed effect appear, relative to the game — i.e., how does it behave before and after the game?
3. Does the magnitude of any observed change decrease with distance from Yankee Stadium?
4. Do trip characteristics such as duration, distance, and fare change around home games?
5. *(Optional extension)* Is game attendance associated with the magnitude of any observed mobility change?

---

## Initial Hypotheses

These are working hypotheses to be investigated, not established facts. They will be revised, narrowed, or discarded as evidence accumulates.

**H1** — Taxi activity around Yankee Stadium is higher during periods surrounding home games than during comparable non-game periods.

**H2** — The increase in taxi activity is concentrated in specific periods before and after the game, rather than spread uniformly across a wide time span.

**H3** — The magnitude of the observed change decreases with distance from Yankee Stadium.

**H4** — Home games are associated with changes in trip characteristics such as trip duration, distance, and fare.

**H5** — *(Optional extension)* Games with higher attendance may be associated with larger changes in taxi activity. This hypothesis is explicitly optional and depends on validating the availability and quality of game-level attendance data (see [02_DATA_SOURCES.md](02_DATA_SOURCES.md)).

---

## Unit(s) of Analysis

Candidate units, to be finalized once data volume and structure are validated:

- **Trip-level records** — individual taxi trips, as originally published.
- **Zone × time-bin aggregates** — trip counts (and other metrics) aggregated per taxi zone per time interval (e.g., hourly). Likely primary unit for demand analysis.
- **Game-level aggregates** — summary statistics computed per game across a defined window, used to compare across games (e.g., for H5).

The exact time-bin granularity (e.g., 15-minute vs. hourly) is data-dependent and will be chosen based on data volume, noise level, and the resolution needed to resolve the temporal questions in H2.

---

## Candidate Metrics

- Trip counts (pickups and/or drop-offs) per zone per time bin — primary demand metric.
- Trip duration.
- Trip distance.
- Fare amount / total amount.
- Pickup–drop-off imbalance (net inbound vs. outbound flow) near the stadium, as a candidate secondary metric.
- Passenger count, as a candidate secondary metric.

Final metric selection depends on field availability and quality, to be confirmed in [02_DATA_SOURCES.md](02_DATA_SOURCES.md) during data acquisition.

---

## Temporal Analysis

**Planned:** Analyze taxi activity as a function of time relative to game start time, and compare game days to non-game days at comparable times and days of week.

**Candidate considerations:**

- Day-of-week and time-of-day seasonality are expected to be strong and must be accounted for rather than treated as part of the "game effect."
- The specific temporal resolution and the exact pre-/post-game span to examine are data-dependent (see [Event Windows](#event-windows)).

---

## Spatial Analysis

**Planned:** Compare taxi zones near Yankee Stadium against zones at increasing distance to investigate H3.

**Candidate approach:** Order or group taxi zones by distance from the stadium (e.g., the zone containing the stadium, then progressively more distant zones or distance bands) and compare the magnitude of any observed change across groups.

**Data-dependent:** The exact zone(s) corresponding to Yankee Stadium, and the distance metric used (e.g., zone centroid distance vs. shared-border adjacency), depend on validating the taxi zone geometry described in [02_DATA_SOURCES.md](02_DATA_SOURCES.md). This has not been done as part of this PR.

---

## Event Windows

**Not locked in.** No fixed pre-/post-game window (e.g., a specific "-3h/+3h" span) is assumed by this plan. Any such window is a candidate reference point at most, and must be validated empirically — e.g., by examining when observed activity actually begins to deviate from baseline and when it returns to baseline — before being adopted. Determining the effective event window is itself part of what the analysis is expected to produce (see Analytical Question 2 and H2), not a precondition set in advance.

---

## Baseline Strategies

Candidates, not yet chosen:

- **Temporal baseline** — the same taxi zone(s) on comparable non-game days/times (e.g., matched by day of week and season, excluding known holidays or other major events where feasible).
- **Typical pattern baseline** — a historical average or typical activity profile per zone per time-of-week, against which game-day observations are compared.

The choice between these (or a combination) depends on how much non-game variability is observed in the data and is deferred to a later PR.

---

## Comparison / Control Strategies

Candidates, not yet chosen:

- **Comparable non-game period comparison** — as described under Baseline Strategies.
- **Spatial control areas** — zones with broadly similar characteristics (e.g., similar borough, density, or baseline traffic level) but without a major venue nearby, used to help separate citywide temporal trends from a stadium-specific effect.
- **Difference-in-differences framing** — comparing (stadium-area zones vs. control zones) × (game days vs. non-game days). This is a candidate only, contingent on the data supporting the assumptions such an approach requires (e.g., reasonably parallel trends in the absence of games). Whether this is appropriate will be assessed, not assumed.

---

## Candidate Statistical Approaches

None of the following are committed to. The final approach(es) will be chosen and justified in a later PR based on the actual distributional and structural properties of the data:

- Descriptive comparison of summary statistics and distributions (game vs. non-game periods).
- Hypothesis testing for differences in central tendency (e.g., t-test, Mann–Whitney U, or another test appropriate to the data's distribution).
- Regression modeling that includes covariates such as day-of-week and time-of-day, to estimate the association between games and activity while adjusting for known confounders.
- Difference-in-differences, only if justified by the data (see [Comparison / Control Strategies](#comparison--control-strategies)).
- Reporting of effect sizes and uncertainty (e.g., confidence intervals), rather than relying on statistical significance alone.

---

## Treatment of Confounding Factors

Candidate confounders to consider and, where feasible, control for or stratify by:

- Day of week and time of day.
- Season / month / holidays.
- Weather (see [02_DATA_SOURCES.md](02_DATA_SOURCES.md) — currently a potential, unconfirmed data source).
- Other concurrent events or venues in NYC (e.g., concerts, other sports events) that could independently affect taxi demand.
- Broader citywide demand trends unrelated to any single event.

Confounders that cannot be reasonably controlled for with available data will be documented as limitations rather than ignored.

---

## Association vs. Causality

This is an **observational study**, not a randomized experiment. Yankee home games are not randomly assigned, and many factors correlate with game days (day of week, season, other concurrent events). Accordingly:

- Findings will be described using association-oriented language ("associated with," "observed change," "estimated impact") by default.
- Causal language will only be used if the analysis provides sufficiently strong supporting evidence (e.g., well-matched controls, robustness across specifications, a plausible mechanism, and no obvious confounding explanation) — and even then, it will be explicitly scoped and caveated.
- The project treats "no clear or meaningful association observed" as a legitimate and acceptable outcome, not a failure of the analysis.

---

## Robustness / Sensitivity Analysis

Planned in principle, to be made concrete once a primary analytical approach is selected:

- Sensitivity of results to the chosen event window definition.
- Sensitivity of results to the chosen baseline and control group definitions.
- Consistency of results across individual games, months, or subsets of the season.
- Sensitivity to outliers and known data quality issues in the trip data.

---

## Optional Extensions

- **H5 / attendance analysis** — explicitly optional. Contingent on validating the availability and quality of game-level attendance data (see [02_DATA_SOURCES.md](02_DATA_SOURCES.md)). If attendance data cannot be validated to an acceptable quality, H5 will be documented as untested rather than pursued with unreliable data.
- **Weather-adjusted analysis** — only pursued if a later PR's exploratory analysis indicates weather is a material confounder that available data can address.

---

## Analytical Limitations

- Observational design: no randomization, so causal claims are inherently limited (see [Association vs. Causality](#association-vs-causality)).
- Taxi trip data is a partial proxy for mobility — it excludes subway, bus, for-hire vehicle/rideshare, and pedestrian activity.
- Spatial analysis is bounded by taxi zone granularity rather than exact coordinates, which limits the precision of distance-based claims (H3) until zone geometry is validated.
- Attendance and weather data availability and quality are unverified at this stage.
- The analysis covers a single season (2019); findings may not generalize to other years.
- Not all potential confounders (e.g., every concurrent NYC event) can be exhaustively enumerated or controlled for in advance.

---

## Related Documents

- [00_PROJECT_CHARTER.md](00_PROJECT_CHARTER.md)
- [02_DATA_SOURCES.md](02_DATA_SOURCES.md)
- [PR-002 — Project Definition](../execution/PR-002_PROJECT_DEFINITION.md)

---

## Changelog

### 1.0.0
Initial version, created under PR-002 (Project Definition).
