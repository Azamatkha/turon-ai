import pytest

from src.reports.enums import ReportKind, ReportStatus
from src.reports.schemas import UpdateReportModel


def test_update_report_accepts_known_statuses() -> None:
    for status in ReportStatus.values():
        assert UpdateReportModel(status=status).status == status


def test_update_report_rejects_unknown_status() -> None:
    with pytest.raises(ValueError):
        UpdateReportModel(status="done")


def test_report_kind_values() -> None:
    assert ReportKind.values() == {"problem", "suggestion"}
