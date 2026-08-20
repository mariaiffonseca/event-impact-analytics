# Project Charter

| Field | Value |
|--------|-------|
| Name | Event Impact Analytics — Project Charter |
| Version | 1.0.0 |
| Status | Draft |
| Last Updated | 2026-08-20 |

---

## Purpose

Define the reason this project exists, the question it sets out to answer, its boundaries, and the criteria by which it will be judged complete and successful. This charter is the reference point for every later PR: implementation choices should trace back to the objectives, scope, and non-goals defined here.

This project is a **Data Science research / analytics project**, not a product application. There is no end-user-facing software deliverable. The deliverable is a rigorous, well-documented analysis and the reasoning behind it.

---

## Project Context

**Domain:** Urban mobility.

**Main dataset candidate:** NYC Yellow Taxi trip records, published by the NYC Taxi & Limousine Commission (TLC).

**Initial period:** 2019 (full calendar year, chosen as a stable, well-documented, pre-pandemic reference period; the final period boundaries remain subject to confirmation once the data is acquired and validated).

**Event case study:** New York Yankees home games at Yankee Stadium (Bronx, NY), 2019 season.

Large recurring public events — such as professional sporting events — are commonly assumed to draw noticeable local transportation demand, but the actual magnitude, timing, and spatial extent of that demand is not obvious without empirical analysis grounded in real trip-level data. This project uses Yankee Stadium home games as a case study to investigate that question using publicly available taxi trip data.

---

## Problem Statement

It is not currently known, in a data-grounded way for this project, whether — and to what extent — New York Yankees home games are associated with observable changes in taxi activity in the vicinity of Yankee Stadium, how that association evolves over time relative to the game, or how it varies with distance from the venue. This project exists to investigate that gap using observational trip-level taxi data.

---

## Research Question

> **How do New York Yankees home games affect taxi demand and travel patterns around Yankee Stadium?**

This question is used as the guiding framing for the project. It is stated in plain language for readability; it is **not** a claim that a causal effect exists or will be established. As detailed in [01_ANALYTICAL_PLAN.md](01_ANALYTICAL_PLAN.md), this is an observational study, and findings will be reported using language such as "associated with," "observed change," or "estimated impact" unless the analysis later provides sufficient evidence to justify stronger causal language.

---

## Objectives

1. Determine whether taxi activity around Yankee Stadium shows an observable, associated change during periods surrounding home games, compared to comparable non-game periods.
2. Characterize the temporal pattern of any observed change (e.g., how it evolves before and after a game).
3. Characterize the spatial pattern of any observed change (e.g., whether it decreases with distance from the stadium).
4. Characterize whether trip characteristics (duration, distance, fare) change around home games.
5. As an optional extension, explore whether game attendance is associated with the magnitude of any observed change, contingent on validating suitable attendance data.
6. Produce a transparent, reproducible analysis with explicitly documented assumptions, limitations, and confounders — suitable as a Data Science portfolio artifact.

---

## Scope

**In scope:**

- NYC Yellow Taxi trip records for the 2019 calendar year (or a validated subset thereof).
- Taxi zones in the vicinity of Yankee Stadium and a set of comparison/control zones.
- The 2019 Yankees home-game schedule at Yankee Stadium.
- Descriptive and inferential analysis of taxi demand and trip characteristics relative to game timing and location.
- Documentation of the analytical approach, assumptions, and limitations at each stage.
- Optionally, game attendance data and/or weather data, if later validated as available and relevant.

**Out of scope (initially):**

- Other NYC vehicle-for-hire data (green taxis, for-hire vehicles / rideshare) unless a future PR justifies adding them.
- Other stadiums, teams, or event types.
- Years other than 2019, unless a future PR justifies extending the period.
- Real-time or streaming data.

---

## Non-Goals

- This project does **not** aim to build a production application, API, or dashboard for end users.
- This project does **not** aim to prove causality. Any causal language will only be used if the analysis provides sufficient evidence, and even then it will be scoped and caveated explicitly.
- This project does **not** aim to comprehensively model all NYC mobility or all events city-wide — Yankees home games are a deliberately chosen, bounded case study.
- This project does **not** aim to produce a general-purpose forecasting or predictive system.
- This project does **not** aim to cover multiple seasons or a longitudinal, multi-year study in its initial scope.

---

## Expected Analytical Outputs

- Descriptive statistics and visualizations comparing taxi activity around game days versus comparable non-game periods.
- A documented characterization of the temporal window(s) during which any observed change occurs.
- A documented characterization of how the observed change varies with distance from Yankee Stadium.
- A comparison of trip-level characteristics (duration, distance, fare) between game-related and non-game periods.
- Statistical analysis results (e.g., estimated effect sizes, comparisons, or model outputs) with explicit uncertainty and limitations, using an approach justified by the data rather than fixed in advance.
- A written summary of findings, including an honest account of what the data does and does not support.
- Optionally, an analysis of the association between game attendance and observed mobility change.

---

## Portfolio Purpose

This is a personal Data Science portfolio project. Its purpose is to demonstrate applied analytical capability: problem framing, data acquisition and validation, exploratory data analysis, spatial and temporal reasoning, statistically grounded comparison, and clear, honest communication of results and their limitations — rather than to ship a product. Rigor and transparency about uncertainty are prioritized over strong or attention-grabbing claims.

---

## Initial Assumptions

These are working assumptions made at the project-definition stage. They are **not yet validated** and must be checked as data is acquired in later PRs:

- NYC Yellow Taxi trip records for 2019 are publicly accessible and sufficiently complete and reliable to support this analysis.
- Trip pickup/drop-off location data is granular enough (taxi zone level) to meaningfully distinguish the area around Yankee Stadium from surrounding and more distant areas.
- A sufficiently accurate 2019 Yankees home-game schedule (dates and start times) can be obtained from a public source.
- Taxi activity is a reasonable, if partial and imperfect, proxy for local mobility demand around the stadium.
- Non-game periods that are reasonably comparable to game periods can be identified to serve as a baseline.

---

## Initial Limitations

- Taxi trip data captures only one mode of transportation. It excludes subway, bus, for-hire vehicle/rideshare, and pedestrian traffic, and therefore reflects only a partial view of mobility around the stadium.
- Spatial resolution is bounded by TLC taxi zones rather than exact coordinates, which limits the precision of any "distance from stadium" analysis.
- Other concurrent factors — weather, holidays, day-of-week effects, other events, or general seasonal trends — may confound any observed association and are not yet enumerated or controlled for.
- The availability and quality of game-level attendance data is unverified at this stage; the attendance-related objective is explicitly optional as a result.
- The analysis is limited to a single season (2019); findings may not generalize to other years or eras of stadium/venue attendance and mobility behavior.
- As an observational study, the project cannot rule out confounding by design; it can only attempt to identify, discuss, and where feasible, control for it.

---

## Success Criteria

This project's definition stage (this PR) is successful when:

- The project charter, analytical plan, and data source inventory exist, are internally consistent, and give later PRs enough direction to proceed without ambiguity.
- The research question, objectives, scope, and non-goals are explicit enough to prevent scope creep during implementation.
- Initial hypotheses and candidate analytical approaches are documented without prematurely locking in implementation details that should be justified by real data.

The project overall is successful when:

- It produces a defensible, well-documented answer to the research question — including the possibility that no clear or meaningful association is observed — supported by traceable analysis.
- The analysis explicitly distinguishes association from causality throughout.
- Assumptions, limitations, and confounders are documented rather than glossed over.
- The result is presentable as a coherent, credible Data Science portfolio artifact.

---

## Related Documents

- [01_ANALYTICAL_PLAN.md](01_ANALYTICAL_PLAN.md)
- [02_DATA_SOURCES.md](02_DATA_SOURCES.md)
- [PR-002 — Project Definition](../execution/PR-002_PROJECT_DEFINITION.md)
- [Repository Conventions](../foundation/07_REPOSITORY_CONVENTIONS.md)

---

## Changelog

### 1.0.0
Initial version, created under PR-002 (Project Definition).
