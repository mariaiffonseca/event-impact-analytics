"""Small, generic source-validation helpers shared across ingestion modules.

Deliberately minimal: a result container plus checks that are genuinely the same
regardless of source (missing columns, a "how many rows fail this condition" count).
Source-specific checks (e.g. taxi timestamp ordering, zone geometry validity) belong in
each source's own module, not here — this is not a general validation framework.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class Severity(str, Enum):
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"


@dataclass(frozen=True)
class ValidationIssue:
    check: str
    severity: Severity
    message: str
    count: int | None = None


@dataclass
class ValidationReport:
    source: str
    issues: list[ValidationIssue] = field(default_factory=list)

    def add(self, check: str, severity: Severity, message: str, count: int | None = None) -> None:
        self.issues.append(ValidationIssue(check=check, severity=severity, message=message, count=count))

    def has_errors(self) -> bool:
        return any(issue.severity == Severity.ERROR for issue in self.issues)

    def summary(self) -> str:
        lines = [f"Validation report for {self.source}:"]
        for issue in self.issues:
            suffix = f" (count={issue.count})" if issue.count is not None else ""
            lines.append(f"  [{issue.severity.value}] {issue.check}: {issue.message}{suffix}")
        return "\n".join(lines)


def check_required_columns(report: ValidationReport, actual_columns: list[str], required: list[str]) -> None:
    missing = [c for c in required if c not in actual_columns]
    if missing:
        report.add("required_columns", Severity.ERROR, f"missing required columns: {missing}")
    else:
        report.add("required_columns", Severity.INFO, "all required columns present")


def check_count(
    report: ValidationReport,
    check_name: str,
    count: int,
    *,
    total: int,
    ok_message: str,
    problem_message: str,
    severity: Severity = Severity.WARNING,
) -> None:
    """Record how many rows (out of `total`) failed a named condition."""
    if count > 0:
        pct = (count / total * 100) if total else 0.0
        report.add(check_name, severity, f"{problem_message} ({pct:.4f}% of rows)", count=count)
    else:
        report.add(check_name, Severity.INFO, ok_message)
