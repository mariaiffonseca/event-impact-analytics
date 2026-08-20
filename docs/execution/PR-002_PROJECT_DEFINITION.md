# PR-002: Project Definition

| Field | Value |
|--------|-------|
| Name | PR-002 — Project Definition |
| Version | 1.1.0 |
| Status | Draft |
| Last Updated | 2026-08-20 |

---

## Purpose

Define the project — its research question, scope, hypotheses, and candidate analytical approach, and its data sources — before any implementation or data acquisition begins. This PR produces the documentation that later PRs (data acquisition, exploratory analysis, statistical analysis, reporting) will be built against and evaluated against. It introduces no code, no downloaded data, and no analysis.

---

## Context

[PR-001 (Repository & Common Foundation)](../foundation/07_REPOSITORY_CONVENTIONS.md) established the repository's shared documentation, conventions, and engineering context. With that foundation in place, this PR defines the project itself: **Event Impact Analytics**, a Data Science portfolio project studying urban mobility.

The current project direction:

- **Domain:** Urban mobility.
- **Main dataset candidate:** NYC Yellow Taxi trip data.
- **Initial period:** 2019.
- **Event case study:** New York Yankees home games at Yankee Stadium.
- **Main research question:** *How do New York Yankees home games affect taxi demand and travel patterns around Yankee Stadium?*

The project is an **observational** Data Science / analytics project. Causality is not claimed or implied unless the analysis later provides sufficient evidence to support it; the project defaults to language such as "associated with," "observed change," or "estimated impact."

---

## Objective

Produce three project-specific documents that together define the project clearly enough for implementation to begin in later PRs, without prematurely locking in implementation details that should instead be justified by the actual data:

1. `docs/project/00_PROJECT_CHARTER.md`
2. `docs/project/01_ANALYTICAL_PLAN.md`
3. `docs/project/02_DATA_SOURCES.md`

---

## Scope

**In scope:**

- Writing the three project-definition documents listed above.
- Defining the research question, objectives, scope, and non-goals for the project.
- Documenting initial hypotheses (H1–H4) as core working hypotheses, plus H5 as an optional extension contingent on the availability and quality of game-level attendance data — all treated as working hypotheses, not established facts.
- Describing candidate analytical approaches (temporal analysis, spatial analysis, baselines, comparison/control strategies, statistical methods) at the level of documented options and trade-offs, explicitly distinguishing planned, candidate, and data-dependent decisions.
- Inventorying all currently known data sources, documenting what is known and explicitly flagging what remains unverified.

**Out of scope:**

- Any data acquisition or dataset download.
- Any exploratory data analysis (EDA).
- Any statistical analysis or modeling implementation.
- Any notebooks.
- Any pipeline, script, or application code.
- Finalizing implementation-level parameters (e.g., a specific event window, baseline, control group, statistical test, or causal inference method) — these are explicitly deferred to later PRs, to be chosen and justified once real data is available.

---

## Deliverables and Requirements

### 1. `docs/project/00_PROJECT_CHARTER.md`

Must define:

- Project context
- Problem statement
- Research question
- Objectives
- Scope
- Non-goals
- Expected analytical outputs
- Portfolio purpose
- Initial assumptions
- Initial limitations
- Success criteria

The charter must describe this as a Data Science research/analytics project, not a product application.

### 2. `docs/project/01_ANALYTICAL_PLAN.md`

Must define:

- Main research question
- Analytical questions
- Initial hypotheses (H1–H4, plus H5 as an optional extension)
- Unit(s) of analysis
- Candidate metrics
- Temporal analysis
- Spatial analysis
- Event windows
- Baseline strategies
- Comparison/control strategies
- Candidate statistical approaches
- Treatment of confounding factors
- Distinction between association and causality
- Robustness/sensitivity analysis
- Optional extensions
- Analytical limitations

Hypotheses must be presented as working hypotheses to be investigated, not established facts. H1–H4 are the core working hypotheses; H5 is an optional extension contingent on the availability and quality of game-level attendance data. The document must not prematurely lock in a fixed event window, a specific baseline, a specific control group, a specific statistical test, or a specific causal inference method — these are documented as candidates or as dependent on later data validation.

### 3. `docs/project/02_DATA_SOURCES.md`

Must contain a structured inventory of all currently known data sources:

1. NYC Taxi & Limousine Commission Yellow Taxi Trip Records
2. NYC Taxi Zone Lookup / geographic data
3. New York Yankees 2019 regular-season home-game schedule
4. Weather data, as a potential source, deferred pending later validation of necessity

For each source, document where possible: source name, provider, purpose, URL, data format, temporal coverage, spatial coverage, relevant fields, expected granularity, acquisition method, licensing/usage considerations, limitations, and validation status. The document must clearly distinguish confirmed sources, candidate sources, and information that still requires validation. No dataset field or source capability may be asserted without a basis in publicly available documentation; anything not directly verified is explicitly marked as requiring validation.

---

## Acceptance Criteria

This PR is complete when:

- [ ] All three documents exist at their specified paths.
- [ ] The project's research question is explicitly defined.
- [ ] Scope and non-goals are clear.
- [ ] Initial hypotheses (H1–H4) are documented as core hypotheses, and H5 is documented as an optional extension contingent on attendance data availability and quality — none presented as established facts.
- [ ] The analytical strategy is described without prematurely locking in implementation details (fixed event window, baseline, control group, statistical test, or causal method).
- [ ] Candidate baselines and comparison/control strategies are documented.
- [ ] Temporal and spatial analysis approaches are covered.
- [ ] Causal limitations are explicitly documented (association vs. causality is addressed directly).
- [ ] All currently known data sources are documented in `02_DATA_SOURCES.md`.
- [ ] Unknown or unverified information is clearly marked as requiring validation.
- [ ] The three documents are internally consistent with each other and with this PR specification.
- [ ] The research question, analytical questions, hypotheses, and project objectives are internally consistent with one another.
- [ ] No implementation code or downloaded datasets are introduced by this PR.

---

## Suggested Commits

1. `docs: add project charter`
2. `docs: add analytical plan`
3. `docs: document data sources`
4. `docs: add project definition PR specification`

---

## Related Documents

- [00_PROJECT_CHARTER.md](../project/00_PROJECT_CHARTER.md)
- [01_ANALYTICAL_PLAN.md](../project/01_ANALYTICAL_PLAN.md)
- [02_DATA_SOURCES.md](../project/02_DATA_SOURCES.md)
- [Repository Conventions](../foundation/07_REPOSITORY_CONVENTIONS.md)

---

## Changelog

### 1.1.0
Clarified H5 as an optional extension dependent on attendance data availability and quality (Scope, Deliverables, Acceptance Criteria); added an acceptance criterion requiring internal consistency across the research question, analytical questions, hypotheses, and objectives.

### 1.0.0
Initial version.
