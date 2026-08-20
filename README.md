# Event Impact Analytics

How do New York Yankees home games affect taxi demand and travel patterns around Yankee
Stadium? A Data Science / analytics portfolio project using NYC TLC Yellow Taxi trip data
and the 2019 Yankees regular-season home schedule as an observational case study.

This is a research/analytics project, not a product application — see
[`docs/project/00_PROJECT_CHARTER.md`](docs/project/00_PROJECT_CHARTER.md) for the full
research question, scope, and non-goals.

## Project documentation

- [`docs/project/00_PROJECT_CHARTER.md`](docs/project/00_PROJECT_CHARTER.md) — research
  question, scope, objectives, non-goals.
- [`docs/project/01_ANALYTICAL_PLAN.md`](docs/project/01_ANALYTICAL_PLAN.md) — hypotheses and
  candidate analytical approach.
- [`docs/project/02_DATA_SOURCES.md`](docs/project/02_DATA_SOURCES.md) — data source
  inventory as identified at the project-definition stage.
- [`docs/project/03_DATA_ACQUISITION.md`](docs/project/03_DATA_ACQUISITION.md) — actual
  acquisition decisions, validation findings, and reproducibility instructions.
- [`docs/execution/`](docs/execution) — per-PR execution records.

## Setup

Dependencies are managed with [uv](https://docs.astral.sh/uv/).

```bash
uv sync
```

## Running tests

```bash
uv run pytest
```

Tests are deterministic and do not require network access.

## Data

Raw, interim, and processed datasets live under `data/` and are never committed to Git — see
[`docs/project/03_DATA_ACQUISITION.md`](docs/project/03_DATA_ACQUISITION.md) for how to
reproduce their acquisition.
