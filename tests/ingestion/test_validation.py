from event_impact.ingestion.common.validation import (
    Severity,
    ValidationReport,
    check_count,
    check_required_columns,
)


def test_check_required_columns_all_present():
    report = ValidationReport(source="test")
    check_required_columns(report, ["a", "b", "c"], ["a", "b"])
    assert not report.has_errors()
    assert report.issues[-1].severity == Severity.INFO


def test_check_required_columns_missing():
    report = ValidationReport(source="test")
    check_required_columns(report, ["a"], ["a", "b"])
    assert report.has_errors()
    issue = report.issues[-1]
    assert issue.severity == Severity.ERROR
    assert "b" in issue.message


def test_check_count_no_problems_reports_info_with_no_count():
    report = ValidationReport(source="test")
    check_count(report, "my_check", 0, total=100, ok_message="ok", problem_message="bad")
    issue = report.issues[-1]
    assert issue.severity == Severity.INFO
    assert issue.count is None
    assert not report.has_errors()


def test_check_count_with_problems_reports_count_and_severity():
    report = ValidationReport(source="test")
    check_count(
        report,
        "my_check",
        5,
        total=100,
        ok_message="ok",
        problem_message="bad",
        severity=Severity.ERROR,
    )
    issue = report.issues[-1]
    assert issue.severity == Severity.ERROR
    assert issue.count == 5
    assert report.has_errors()


def test_summary_includes_source_and_issues():
    report = ValidationReport(source="test-source")
    check_required_columns(report, ["a"], ["a"])
    text = report.summary()
    assert "test-source" in text
    assert "required_columns" in text
