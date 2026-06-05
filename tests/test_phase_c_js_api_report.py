"""Phase C.7 — JsApi report facade tests (TDD: RED first)."""

import importlib
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from project_tracker.core.enums import CRState, ProjectState
from project_tracker.web import js_api
from project_tracker.web.js_api import JsApi


@dataclass(frozen=True)
class FakeProject:
    year: str
    project_name: str
    project_state: ProjectState
    cr_number: str
    cr_state: CRState
    start_datetime: datetime
    end_datetime: None
    t10_status: str
    drone_ticket_count: int
    project_path: Path


class FakeReportService:
    def __init__(self) -> None:
        self.calls: list[tuple[str, tuple[object, ...]]] = []
        self.project = FakeProject(
            year="2026",
            project_name="Alpha",
            project_state=ProjectState.UAT_PREPARE,
            cr_number="CR-1",
            cr_state=CRState.APPROVED,
            start_datetime=datetime(2026, 1, 2, 3, 4, 5, tzinfo=timezone.utc),
            end_datetime=None,
            t10_status="READY",
            drone_ticket_count=2,
            project_path=Path("/tmp/2026/Alpha"),
        )

    def filter_projects(
        self,
        year=None,
        project_state=None,
        cr_state=None,
        search=None,
    ) -> list[FakeProject]:
        self.calls.append(("filter_projects", (year, project_state, cr_state, search)))
        return [self.project]

    def export_csv(self, projects) -> str:
        self.calls.append(("export_csv", tuple(projects)))
        return "year,project_name\n2026,Alpha\n"


class ExplodingReportService(FakeReportService):
    def filter_projects(self, year=None, project_state=None, cr_state=None, search=None):
        raise RuntimeError("report unavailable")


def test_report_filter_projects_returns_converted_projects():
    service = FakeReportService()
    api = JsApi(dashboard_service=None, report_service=service)

    response = api.report_filter_projects(year="2026", project_state=ProjectState.UAT_PREPARE)

    assert response["ok"] is True
    assert response["error"] is None
    assert response["data"] == [
        {
            "year": "2026",
            "project_name": "Alpha",
            "project_state": "UAT_PREPARE",
            "cr_number": "CR-1",
            "cr_state": "APPROVED",
            "start_datetime": "2026-01-02T03:04:05+00:00",
            "end_datetime": None,
            "t10_status": "READY",
            "drone_ticket_count": 2,
            "project_path": "/tmp/2026/Alpha",
        }
    ]
    assert service.calls == [("filter_projects", ("2026", ProjectState.UAT_PREPARE, None, None))]


def test_report_export_csv_filters_then_exports_csv():
    service = FakeReportService()
    api = JsApi(dashboard_service=None, report_service=service)

    response = api.report_export_csv(cr_state=CRState.APPROVED, search="alpha")

    assert response == {"ok": True, "data": "year,project_name\n2026,Alpha\n", "error": None}
    assert service.calls[0] == ("filter_projects", (None, None, CRState.APPROVED, "alpha"))
    assert service.calls[1][0] == "export_csv"
    assert service.calls[1][1][0].project_name == "Alpha"


def test_report_filter_exception_returns_fail():
    api = JsApi(dashboard_service=None, report_service=ExplodingReportService())

    response = api.report_filter_projects()

    assert response == {
        "ok": False,
        "data": None,
        "error": {
            "code": "REPORT_FILTER_PROJECTS_FAILED",
            "message": "report unavailable",
            "details": None,
        },
    }


def test_report_export_exception_returns_fail():
    api = JsApi(dashboard_service=None, report_service=ExplodingReportService())

    response = api.report_export_csv()

    assert response == {
        "ok": False,
        "data": None,
        "error": {
            "code": "REPORT_EXPORT_CSV_FAILED",
            "message": "report unavailable",
            "details": None,
        },
    }


def test_js_api_report_import_does_not_require_pywebview():
    assert "webview" not in sys.modules
    importlib.reload(js_api)
    assert "webview" not in sys.modules
