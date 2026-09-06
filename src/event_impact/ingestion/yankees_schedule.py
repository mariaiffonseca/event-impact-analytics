"""New York Yankees 2019 regular-season home game schedule — acquisition and validation.

Primary source: Retrosheet's 2019 regular-season game logs (confirmed regular-season-only,
and confirmed to exclude a game start-time clock field — see
docs/project/03_DATA_ACQUISITION.md). Secondary source for cross-validation: Baseball
Almanac — Baseball-Reference (PR-002's preferred secondary source) returns HTTP 403 to a
realistic browser User-Agent, confirmed both during PR-003 planning and again here.
"""

from __future__ import annotations

import csv
import io
import zipfile
from dataclasses import dataclass
from io import StringIO
from pathlib import Path

import pandas as pd
import requests

from event_impact.config import (
    BASEBALL_ALMANAC_SCHEDULE_URL_TEMPLATE,
    DEFAULT_USER_AGENT,
    RETROSHEET_GAMELOG_URL_TEMPLATE,
    YANKEES_SCHEDULE_RAW_DIR,
)
from event_impact.ingestion.common.provenance import download_and_record
from event_impact.ingestion.common.validation import Severity, ValidationReport, check_count

# A team's regular-season home game count varies somewhat year to year (rainouts, makeup
# games, rare ties) but stays well within this range; used to sanity-check that a secondary
# source's HTML structure hasn't silently changed under the hardcoded table/column/row
# assumptions in `fetch_baseball_almanac_home_dates`.
_PLAUSIBLE_HOME_GAME_COUNT_RANGE = (70, 90)

YANKEES_TEAM_CODE = "NYA"

# Field positions (0-indexed) in a Retrosheet game log record. The game log has 161 fields
# total; only the ones this project needs are named. Confirmed against the real 2019 file
# during PR-005 (see docs/project/03_DATA_ACQUISITION.md) — not assumed from documentation
# alone.
_FIELD_DATE = 0
_FIELD_GAME_NUMBER = 1
_FIELD_DAY_OF_WEEK = 2
_FIELD_VISITING_TEAM = 3
_FIELD_HOME_TEAM = 6
_FIELD_DAY_NIGHT = 12
_FIELD_PARK_ID = 16
_FIELD_ATTENDANCE = 17
_FIELD_GAME_DURATION_MINUTES = 18


@dataclass(frozen=True)
class Game:
    date: str  # YYYY-MM-DD
    game_number: int  # 0 = single game that day, 1/2 = doubleheader game 1/2
    day_of_week: str
    visiting_team: str
    home_team: str
    day_night: str
    park_id: str
    attendance: int | None
    game_duration_minutes: int | None


def gamelog_url(year: str = "2019") -> str:
    return RETROSHEET_GAMELOG_URL_TEMPLATE.format(year=year)


def gamelog_zip_path(year: str = "2019") -> Path:
    return YANKEES_SCHEDULE_RAW_DIR / f"gl{year}.zip"


def download_gamelog(year: str = "2019") -> Path:
    return download_and_record(gamelog_url(year), gamelog_zip_path(year))


def _parse_optional_int(value: str) -> int | None:
    value = value.strip()
    return int(value) if value else None


def _parse_row(row: list[str]) -> Game:
    raw_date = row[_FIELD_DATE]
    if len(raw_date) != 8 or not raw_date.isdigit():
        # Slicing a short/malformed string doesn't raise (e.g. "2019"[4:6] == ""), so an
        # 8-digit YYYYMMDD shape is checked explicitly instead of trusting the slice to fail
        # loudly on bad input.
        raise ValueError(f"expected an 8-digit YYYYMMDD date, got {raw_date!r}")
    return Game(
        date=f"{raw_date[0:4]}-{raw_date[4:6]}-{raw_date[6:8]}",
        game_number=int(row[_FIELD_GAME_NUMBER]),
        day_of_week=row[_FIELD_DAY_OF_WEEK],
        visiting_team=row[_FIELD_VISITING_TEAM],
        home_team=row[_FIELD_HOME_TEAM],
        day_night=row[_FIELD_DAY_NIGHT],
        park_id=row[_FIELD_PARK_ID],
        attendance=_parse_optional_int(row[_FIELD_ATTENDANCE]),
        game_duration_minutes=_parse_optional_int(row[_FIELD_GAME_DURATION_MINUTES]),
    )


def parse_gamelog(zip_path: Path, year: str = "2019") -> list[Game]:
    """Parse every game record from a Retrosheet regular-season game log zip. Retrosheet
    distributes postseason logs as separate archives, so every record here is regular
    season."""
    with zipfile.ZipFile(zip_path) as zf:
        [name] = [n for n in zf.namelist() if n.lower() == f"gl{year}.txt"]
        with zf.open(name) as raw:
            text = io.TextIOWrapper(raw, encoding="latin-1", newline="")
            return [_parse_row(row) for row in csv.reader(text)]


def yankees_home_games(games: list[Game]) -> list[Game]:
    return [g for g in games if g.home_team == YANKEES_TEAM_CODE]


def validate_schedule(games: list[Game]) -> ValidationReport:
    """Source-quality validation only — no cleaning or record removal. `games` is expected to
    already be filtered to Yankees home games."""
    report = ValidationReport(source="yankees_2019_home_schedule")
    total = len(games)
    if total == 0:
        report.add("home_games_found", Severity.ERROR, "no Yankees home games found")
        return report
    report.add("home_games_found", Severity.INFO, f"{total} Yankees home games found")

    distinct_park_ids = {g.park_id for g in games}
    check_count(
        report,
        "multiple_venues",
        0 if len(distinct_park_ids) == 1 else total,
        total=total,
        ok_message=f"all home games at a single venue (park ID {next(iter(distinct_park_ids))})",
        problem_message=f"home games span multiple park IDs: {sorted(distinct_park_ids)}",
        severity=Severity.WARNING,
    )

    check_count(
        report,
        "missing_or_zero_attendance",
        sum(1 for g in games if g.attendance is None or g.attendance == 0),
        total=total,
        ok_message="attendance recorded (non-zero) for every home game",
        problem_message="home games with missing or zero attendance",
        severity=Severity.INFO,
    )

    check_count(
        report,
        "date_outside_2019",
        sum(1 for g in games if not g.date.startswith("2019-")),
        total=total,
        ok_message="all home games dated in 2019",
        problem_message="home games with a date outside 2019",
        severity=Severity.ERROR,
    )

    return report


def fetch_baseball_almanac_home_dates(year: str = "2019") -> set[str] | None:
    """Best-effort secondary-source cross-check. Returns the set of home-game dates
    (YYYY-MM-DD) Baseball Almanac lists for the Yankees that season, or `None` if the fetch
    or parse fails — a network timeout, non-200 response, unparseable page, or a page
    structure that no longer matches the hardcoded table/column/row assumptions below
    degrades this best-effort cross-check instead of crashing the whole acquisition run.

    Baseball Almanac's schedule table labels doubleheader games with a Roman-numeral suffix
    (e.g. "41-I", "42-II") instead of a plain integer — confirmed against the real page during
    PR-005 — so the row filter matches both plain and suffixed game numbers, not just digits.
    """
    url = BASEBALL_ALMANAC_SCHEDULE_URL_TEMPLATE.format(year=year)
    try:
        response = requests.get(url, headers={"User-Agent": DEFAULT_USER_AGENT}, timeout=30)
        response.raise_for_status()

        table = pd.read_html(StringIO(response.text))[0]
        table.columns = ["game_num", "date", "opponent", "score", "decision", "record", "unused"]
        rows = table.iloc[3:]  # first 3 rows are the site's repeated navigation/header content
        valid_games = rows[rows["game_num"].astype(str).str.match(r"^\d+(-I{1,2})?$")]
        home_games = valid_games[valid_games["opponent"].astype(str).str.startswith("vs ")]
        parsed_dates = pd.to_datetime(
            home_games["date"], format="%m-%d-%Y"
        ).dt.strftime("%Y-%m-%d")
        dates = set(parsed_dates)

        lo, hi = _PLAUSIBLE_HOME_GAME_COUNT_RANGE
        if not (lo <= len(dates) <= hi):
            # The table/column/row assumptions above are only confirmed against the 2019
            # page; a differently-laid-out page (a different year, or a future site change)
            # would silently return a wrong/incomplete date set with no other signal to
            # catch it, so an implausible count is treated as a parse failure.
            raise ValueError(
                f"parsed {len(dates)} home-game dates from Baseball Almanac for {year}, "
                f"outside the plausible range {_PLAUSIBLE_HOME_GAME_COUNT_RANGE} for an MLB "
                "regular season — the page structure may have changed"
            )
        return dates
    except (requests.RequestException, ValueError, KeyError, IndexError):
        return None


def cross_validate_home_dates(
    primary_dates: set[str], secondary_dates: set[str] | None
) -> ValidationReport:
    """Compare Retrosheet's (primary) home-game dates against a secondary source's. Any
    discrepancy is reported, not silently resolved in either source's favor.

    A handful of genuine discrepancies is WARNING-level. A secondary source that's missing
    entirely, empty, or wildly divergent from the primary source (more likely a broken
    fetch/parse than dozens of real per-date mismatches) is escalated to ERROR, so
    `has_errors()` actually catches a failed cross-check instead of reporting a clean pass
    while silently losing the entire cross-check's value.
    """
    report = ValidationReport(source="schedule_cross_validation")
    if secondary_dates is None:
        report.add(
            "secondary_source_unavailable",
            Severity.ERROR,
            "Baseball Almanac cross-check could not be performed (fetch or parse failed)",
        )
        return report

    only_primary = sorted(primary_dates - secondary_dates)
    only_secondary = sorted(secondary_dates - primary_dates)

    # More than half of one source's dates missing from the other indicates the secondary
    # source itself failed (empty/garbled page), not a plausible number of genuine
    # date-level discrepancies.
    primary_mismatch_severity = (
        Severity.ERROR
        if primary_dates and len(only_primary) > len(primary_dates) / 2
        else Severity.WARNING
    )
    secondary_mismatch_severity = (
        Severity.ERROR
        if secondary_dates and len(only_secondary) > len(secondary_dates) / 2
        else Severity.WARNING
    )

    check_count(
        report,
        "dates_only_in_primary_source",
        len(only_primary),
        total=len(primary_dates),
        ok_message="every primary-source home-game date also appears in the secondary source",
        problem_message=f"dates present in the primary source but not the secondary: {only_primary}",
        severity=primary_mismatch_severity,
    )
    check_count(
        report,
        "dates_only_in_secondary_source",
        len(only_secondary),
        total=len(secondary_dates),
        ok_message="every secondary-source home-game date also appears in the primary source",
        problem_message=f"dates present in the secondary source but not the primary: {only_secondary}",
        severity=secondary_mismatch_severity,
    )

    return report


def run_schedule_acquisition(
    year: str = "2019",
) -> tuple[list[Game], ValidationReport, ValidationReport]:
    """Download (if needed), parse, filter, and validate the season's home-game schedule,
    then cross-validate it against Baseball Almanac — the single reproducible entry point for
    the numbers documented in docs/project/03_DATA_ACQUISITION.md.

    Returns `(home_games, schedule_report, cross_validation_report)`.
    """
    zip_path = download_gamelog(year)
    games = parse_gamelog(zip_path, year)
    home_games = yankees_home_games(games)
    schedule_report = validate_schedule(home_games)

    primary_dates = {g.date for g in home_games}
    secondary_dates = fetch_baseball_almanac_home_dates(year)
    cross_validation_report = cross_validate_home_dates(primary_dates, secondary_dates)

    return home_games, schedule_report, cross_validation_report


if __name__ == "__main__":
    home_games, schedule_report, cross_validation_report = run_schedule_acquisition()
    print(f"{len(home_games)} Yankees home games found")
    print()
    print(schedule_report.summary())
    print()
    print(cross_validation_report.summary())
