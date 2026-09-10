import csv
import zipfile

import pytest
import requests

from event_impact.ingestion import yankees_schedule as ys


def issue(report, check_name):
    return next(i for i in report.issues if i.check == check_name)


def make_row(
    date="20190328",
    game_number="0",
    day_of_week="Thu",
    visiting="BAL",
    home="NYA",
    day_night="D",
    park_id="NYC21",
    attendance="46928",
    duration="186",
):
    # A minimal but positionally-correct 19-field row covering every field this module reads
    # (indices 0-18); real Retrosheet rows have 161 fields, but only these positions matter.
    row = ["" for _ in range(19)]
    row[ys._FIELD_DATE] = date
    row[ys._FIELD_GAME_NUMBER] = game_number
    row[ys._FIELD_DAY_OF_WEEK] = day_of_week
    row[ys._FIELD_VISITING_TEAM] = visiting
    row[ys._FIELD_HOME_TEAM] = home
    row[ys._FIELD_DAY_NIGHT] = day_night
    row[ys._FIELD_PARK_ID] = park_id
    row[ys._FIELD_ATTENDANCE] = attendance
    row[ys._FIELD_GAME_DURATION_MINUTES] = duration
    return row


def test_parse_row_extracts_expected_fields():
    game = ys._parse_row(make_row())
    assert game.date == "2019-03-28"
    assert game.game_number == 0
    assert game.home_team == "NYA"
    assert game.visiting_team == "BAL"
    assert game.park_id == "NYC21"
    assert game.attendance == 46928
    assert game.game_duration_minutes == 186


def test_parse_row_handles_blank_attendance_as_none():
    game = ys._parse_row(make_row(attendance=""))
    assert game.attendance is None


def test_parse_row_rejects_short_malformed_date():
    # A short date like "2019" must not silently slice into "2019--" (a corrupted date that
    # would still pass the date_outside_2019 startswith("2019-") check).
    with pytest.raises(ValueError, match="YYYYMMDD"):
        ys._parse_row(make_row(date="2019"))


def test_parse_row_rejects_non_numeric_date():
    with pytest.raises(ValueError, match="YYYYMMDD"):
        ys._parse_row(make_row(date="2019AB28"))


def test_yankees_home_games_filters_by_home_team():
    games = [
        ys._parse_row(make_row(home="NYA", visiting="BOS")),
        ys._parse_row(make_row(home="BOS", visiting="NYA")),
        ys._parse_row(make_row(home="NYA", visiting="TBA")),
    ]
    home_games = ys.yankees_home_games(games)
    assert len(home_games) == 2
    assert all(g.home_team == "NYA" for g in home_games)


def test_validate_schedule_rejects_empty_list():
    report = ys.validate_schedule([])
    assert report.has_errors()
    assert issue(report, "home_games_found").severity.value == "error"


def test_validate_schedule_passes_clean_single_venue_schedule():
    games = [ys._parse_row(make_row(date=d)) for d in ("20190328", "20190330", "20190331")]
    report = ys.validate_schedule(games)
    assert not report.has_errors()
    assert issue(report, "multiple_venues").severity.value == "info"
    assert issue(report, "home_games_found").message == "3 Yankees home games found"


def test_validate_schedule_flags_multiple_venues():
    games = [
        ys._parse_row(make_row(date="20190328", park_id="NYC21")),
        ys._parse_row(make_row(date="20190330", park_id="LON01")),
    ]
    report = ys.validate_schedule(games)
    venue_issue = issue(report, "multiple_venues")
    assert venue_issue.count == 2
    assert venue_issue.severity.value == "warning"


def test_validate_schedule_flags_missing_or_zero_attendance():
    games = [
        ys._parse_row(make_row(date="20190515", game_number="1", attendance="0")),
        ys._parse_row(make_row(date="20190515", game_number="2", attendance="41138")),
    ]
    report = ys.validate_schedule(games)
    attendance_issue = issue(report, "missing_or_zero_attendance")
    assert attendance_issue.count == 1
    assert attendance_issue.severity.value == "info"


def test_validate_schedule_flags_date_outside_2019():
    games = [ys._parse_row(make_row(date="20180328"))]
    report = ys.validate_schedule(games)
    date_issue = issue(report, "date_outside_2019")
    assert date_issue.count == 1
    assert date_issue.severity.value == "error"


def test_cross_validate_home_dates_reports_no_discrepancies_when_matching():
    dates = {"2019-03-28", "2019-03-30", "2019-03-31"}
    report = ys.cross_validate_home_dates(dates, dates)
    assert not report.has_errors()
    assert issue(report, "dates_only_in_primary_source").severity.value == "info"
    assert issue(report, "dates_only_in_secondary_source").severity.value == "info"


def test_cross_validate_home_dates_reports_discrepancies_both_directions():
    primary = {"2019-03-28", "2019-03-30"}
    secondary = {"2019-03-28", "2019-04-01"}
    report = ys.cross_validate_home_dates(primary, secondary)

    only_primary = issue(report, "dates_only_in_primary_source")
    assert only_primary.count == 1
    assert "2019-03-30" in only_primary.message
    assert only_primary.severity.value == "warning"

    only_secondary = issue(report, "dates_only_in_secondary_source")
    assert only_secondary.count == 1
    assert "2019-04-01" in only_secondary.message
    assert only_secondary.severity.value == "warning"


def test_cross_validate_home_dates_escalates_to_error_when_secondary_source_unavailable():
    report = ys.cross_validate_home_dates({"2019-03-28"}, None)
    assert report.has_errors()
    assert issue(report, "secondary_source_unavailable").severity.value == "error"


def test_cross_validate_home_dates_escalates_to_error_on_majority_mismatch():
    # A secondary source missing most of the primary's dates looks like a broken fetch/parse,
    # not a handful of genuine discrepancies, so this must fail has_errors() rather than pile
    # up as WARNING-level noise.
    primary = {f"2019-04-{d:02d}" for d in range(1, 11)}  # 10 dates
    secondary = {"2019-04-01"}  # only 1 of 10 matches -> 9/10 missing
    report = ys.cross_validate_home_dates(primary, secondary)
    assert report.has_errors()
    assert issue(report, "dates_only_in_primary_source").severity.value == "error"


def test_fetch_baseball_almanac_home_dates_returns_none_on_request_failure(monkeypatch):
    def fake_get(*args, **kwargs):
        raise requests.ConnectionError("simulated network failure")

    monkeypatch.setattr(ys.requests, "get", fake_get)
    assert ys.fetch_baseball_almanac_home_dates() is None


def test_fetch_baseball_almanac_home_dates_returns_none_on_implausible_page_structure(
    monkeypatch,
):
    """A page whose structure no longer matches the hardcoded table/column/row assumptions
    should degrade to None (best-effort) rather than crash or silently return a wrong/empty
    result — simulated here via an HTML table shaped nothing like the real schedule page."""

    class FakeResponse:
        text = "<table><tr><td>unexpected content</td></tr></table>"

        def raise_for_status(self):
            pass

    monkeypatch.setattr(ys.requests, "get", lambda *a, **k: FakeResponse())
    assert ys.fetch_baseball_almanac_home_dates() is None


def test_run_schedule_acquisition_wires_the_full_pipeline(tmp_path, monkeypatch):
    """Regression test for this module having no committed caller chaining download -> parse
    -> filter -> validate -> cross-validate together — exercises the same chain the PR's
    headline numbers are claimed to come from."""
    text_path = tmp_path / "gl2019.txt"
    with open(text_path, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(make_row(date="20190328", home="NYA", visiting="BAL"))
        writer.writerow(make_row(date="20190329", home="BOS", visiting="NYA"))  # not a home game
    zip_path = tmp_path / "gl2019.zip"
    with zipfile.ZipFile(zip_path, "w") as zf:
        zf.write(text_path, arcname="gl2019.txt")

    monkeypatch.setattr(ys, "download_gamelog", lambda year="2019": zip_path)
    monkeypatch.setattr(
        ys, "fetch_baseball_almanac_home_dates", lambda year="2019": {"2019-03-28"}
    )

    home_games, schedule_report, cross_validation_report = ys.run_schedule_acquisition()

    assert len(home_games) == 1
    assert home_games[0].date == "2019-03-28"
    assert not schedule_report.has_errors()
    assert not cross_validation_report.has_errors()
