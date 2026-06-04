"""Phase C.5c — JsApi dashboard read method tests (TDD: RED first)."""

import importlib
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from project_tracker.core.enums import CRState, ProjectState
from project_tracker.services.dashboard_service import DashboardData, DashboardSummary
from project_tracker.web import js_api
from project_tracker.web.js_api import JsApi


@dataclass(frozen=True)
class FakeProject:
    project_path: Path
    project_state: ProjectState
    cr_state: CRState
    updated_at: datetime


class FakeDashboardService:
    def __init__(self) -> None:
        self.calls: list[tuple[str, str | None]] = []
        self.project = FakeProject(
            project_path=Path("/tmp/projects/2026/UAT_PREPARE/P-1"),
            project_state=ProjectState.UAT_PREPARE,
            cr_state=CRState.APPROVED,
            updated_at=datetime(2026, 1, 2, 3, 4, 5, tzinfo=timezone.utc),
        )
        self.summary = DashboardSummary(
            total_projects=1,
            by_project_state={ProjectState.UAT_PREPARE: 1},
            by_cr_state={CRState.APPROVED: 1},
            by_t10_status={"READY": 1},
            total_drone_tickets=2,
        )

    def list_projects(self, year: str | None = None) -> list[FakeProject]:
        self.calls.append(("list_projects", year))
        return [self.project]

    def get_summary(self, year: str | None = None) -> DashboardSummary:
        self.calls.append(("get_summary", year))
        return self.summary

    def get_dashboard(self, year: str | None = None) -> DashboardData:
        self.calls.append(("get_dashboard", year))
        return DashboardData(projects=(self.project,), summary=self.summary)  # type: ignore[arg-type]


class ExplodingDashboardService(FakeDashboardService):
    def list_projects(self, year: str | None = None) -> list[FakeProject]:
        raise RuntimeError("dashboard unavailable")

    def get_summary(self, year: str | None = None) -> DashboardSummary:
        raise RuntimeError("summary unavailable")

    def get_dashboard(self, year: str | None = None) -> DashboardData:
        raise RuntimeError("data unavailable")


def test_dashboard_list_projects_returns_ok_shape_and_safe_values():
    service = FakeDashboardService()
    api = JsApi(dashboard_service=service)

    response = api.dashboard_list_projects(year="2026")

    assert response["ok"] is True
    assert response["error"] is None
    assert response["data"] == [
        {
            "project_path": "/tmp/projects/2026/UAT_PREPARE/P-1",
            "project_state": "UAT_PREPARE",
            "cr_state": "APPROVED",
            "updated_at": "2026-01-02T03:04:05+00:00",
        }
    ]
    assert service.calls == [("list_projects", "2026")]


def test_dashboard_summary_returns_ok_shape_and_string_keys():
    service = FakeDashboardService()
    api = JsApi(dashboard_service=service)

    response = api.dashboard_summary()

    assert response == {
        "ok": True,
        "data": {
            "total_projects": 1,
            "by_project_state": {"UAT_PREPARE": 1},
            "by_cr_state": {"APPROVED": 1},
            "by_t10_status": {"READY": 1},
            "total_drone_tickets": 2,
        },
        "error": None,
    }
    assert service.calls == [("get_summary", None)]


def test_dashboard_data_returns_ok_shape():
    service = FakeDashboardService()
    api = JsApi(dashboard_service=service)

    response = api.dashboard_data(year="2026")

    assert response["ok"] is True
    assert response["error"] is None
    assert response["data"]["projects"][0]["project_state"] == "UAT_PREPARE"
    assert response["data"]["summary"]["by_cr_state"] == {"APPROVED": 1}
    assert service.calls == [("get_dashboard", "2026")]


def test_dashboard_exceptions_return_fail_response():
    api = JsApi(dashboard_service=ExplodingDashboardService())

    response = api.dashboard_list_projects()

    assert response == {
        "ok": False,
        "data": None,
        "error": {
            "code": "DASHBOARD_LIST_PROJECTS_FAILED",
            "message": "dashboard unavailable",
            "details": None,
        },
    }


def test_js_api_import_does_not_require_pywebview():
    assert "webview" not in sys.modules
    importlib.reload(js_api)
    assert "webview" not in sys.modules
