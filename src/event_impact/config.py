"""Project-wide configuration: data paths and source URLs.

Plain module-level constants, overridable via environment variables where useful.
No settings framework or config-validation layer — not justified at this project's scale.
"""

from __future__ import annotations

import os
from pathlib import Path

# Repository root, derived from this file's location so paths work regardless of CWD.
PROJECT_ROOT = Path(__file__).resolve().parents[2]

_data_dir_env = os.environ.get("EVENT_IMPACT_DATA_DIR")
DATA_DIR = Path(_data_dir_env) if _data_dir_env else PROJECT_ROOT / "data"
RAW_DIR = DATA_DIR / "raw"
INTERIM_DIR = DATA_DIR / "interim"
PROCESSED_DIR = DATA_DIR / "processed"

TAXI_RAW_DIR = RAW_DIR / "taxi"
TAXI_ZONES_RAW_DIR = RAW_DIR / "taxi_zones"
YANKEES_SCHEDULE_RAW_DIR = RAW_DIR / "yankees_schedule"

# NYC TLC Yellow Taxi trip data. Confirmed available as Parquet directly from the canonical
# CloudFront distribution for 2019 files (see docs/project/03_DATA_ACQUISITION.md).
TAXI_TRIP_DATA_URL_TEMPLATE = (
    "https://d37ci6vzurychx.cloudfront.net/trip-data/yellow_tripdata_{year_month}.parquet"
)

# Taxi zone lookup table and zone geometry. Confirmed reachable during PR-003 planning;
# acquired starting PR-005.
TAXI_ZONE_LOOKUP_URL = "https://d37ci6vzurychx.cloudfront.net/misc/taxi_zone_lookup.csv"
TAXI_ZONE_GEOMETRY_URL = "https://d37ci6vzurychx.cloudfront.net/misc/taxi_zones.zip"

# Retrosheet regular-season game logs — the project's preferred/primary schedule source
# (see docs/project/02_DATA_SOURCES.md), confirmed regular-season-only. Acquired PR-005.
RETROSHEET_GAMELOG_URL_TEMPLATE = "https://www.retrosheet.org/gamelogs/gl{year}.zip"

# Secondary source for schedule cross-validation. Baseball-Reference (PR-002's preferred
# secondary source) returns HTTP 403 to a realistic browser User-Agent even with a proper
# header — confirmed during both PR-003 planning and PR-005. Baseball Almanac, PR-002's
# named fallback, responds normally and is used instead (see 03_DATA_ACQUISITION.md).
BASEBALL_ALMANAC_SCHEDULE_URL_TEMPLATE = (
    "https://www.baseball-almanac.com/teamstats/schedule.php?y={year}&t=NYA"
)

# TLC's and Baseball-Reference's HTML landing pages return HTTP 403 to a default library
# user agent; the underlying data files are unaffected either way. Using a realistic UA
# everywhere for consistency (see docs/project/03_DATA_ACQUISITION.md).
DEFAULT_USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
)


def taxi_trip_data_url(year_month: str) -> str:
    """Build the download URL for one month of trip data, e.g. year_month='2019-01'."""
    return TAXI_TRIP_DATA_URL_TEMPLATE.format(year_month=year_month)
