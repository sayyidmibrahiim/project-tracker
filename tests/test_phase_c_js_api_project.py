"""Phase C.8a — JsApi project read-only facade tests (TDD: RED first)."""

import importlib
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from project_tracker.core.enums import CRState, ProjectState
from project_tracker.web import js_api
from project_tracker.web.js_api import JsApi


@dataclass(frozen=True)
class FakeProjectDetail:
    project_name: str
    project_path: Path
    project_state: ProjectState
    cr_number: str
    cr_state: CRState
    start_datetime: datetime
    end_datetime: datetime | None
    t10_status: str
    drone_ticket_count: int


@dataclass(frozen=True)
class FakeProjectRow:
    project_name: str
    project_path: Path
    project_state: ProjectState
    cr_number: str
    cr_state: CRState


class FakeProjectService:
    def __init__(self) -> None:
        self.calls: list[tuple[str, tuple[object, ...]]] = []
        self.detail = FakeProjectDetail(
            project_name="Alpha",
            project_path=Path("/tmp/2026/UAT_PREPARE/Alpha"),
            project_state=ProjectState.UAT_PREPARE,
            cr_number="CR-100",
            cr_state=CRState.APPROVED,
            start_datetime=datetime(2026, 3, 1, 9, 0, 0, tzinfo=timezone.utc),
            end_datetime=None,
            t10_status="READY",
            drone_ticket_count=2,
        )
        self.rows = [
            FakeProjectRow(
                project_name="Alpha",
                project_path=Path("/tmp/2026/UAT_PREPARE/Alpha"),
                project_state=ProjectState.UAT_PREPARE,
                cr_number="CR-100",
                cr_state=CRState.APPROVED,
            ),
            FakeProjectRow(
                project_name="Beta",
                project_path=Path("/tmp/2026/PROD_READY/Beta"),
                project_state=ProjectState.PROD_READY,
                cr_number="CR-200",
                cr_state=CRState.FINISHED,
            ),
        ]

    def get_project(self, project_path: Path) -> FakeProjectDetail:
        self.calls.append(("get_project", (project_path,)))
        return self.detail

    def list_projects(self, year: str | None = None) -> list[FakeProjectRow]:
        self.calls.append(("list_projects", (year,)))
        return self.rows

    def open_folder(self, project_path: Path) -> None:
        self.calls.append(("open_folder", (project_path,)))


class ExplodingProjectService(FakeProjectService):
    def get_project(self, project_path: Path) -> FakeProjectDetail:
        raise RuntimeError("project not found")

    def list_projects(self, year: str | None = None) -> list[FakeProjectRow]:
        raise RuntimeError("list failed")

    def open_folder(self, project_path: Path) -> None:
        raise RuntimeError("open failed")


def test_project_get_returns_converted_detail():
    service = FakeProjectService()
    api = JsApi(dashboard_service=None, project_service=service)

    response = api.project_get("/tmp/2026/UAT_PREPARE/Alpha")

    assert response["ok"] is True
    assert response["error"] is None
    data = response["data"]
    assert data["project_name"] == "Alpha"
    assert data["project_path"] == "/tmp/2026/UAT_PREPARE/Alpha"
    assert data["project_state"] == "UAT_PREPARE"
    assert data["cr_state"] == "APPROVED"
    assert data["start_datetime"] == "2026-03-01T09:00:00+00:00"
    assert data["end_datetime"] is None
    # Verify Path conversion happened (str arg → Path for service)
    assert service.calls == [("get_project", (Path("/tmp/2026/UAT_PREPARE/Alpha"),))]


def test_project_list_returns_converted_rows():
    service = FakeProjectService()
    api = JsApi(dashboard_service=None, project_service=service)

    response = api.project_list(year="2026")

    assert response["ok"] is True
    assert response["error"] is None
    assert len(response["data"]) == 2
    assert response["data"][0]["project_name"] == "Alpha"
    assert response["data"][0]["project_state"] == "UAT_PREPARE"
    assert response["data"][1]["project_name"] == "Beta"
    assert response["data"][1]["project_path"] == "/tmp/2026/PROD_READY/Beta"
    assert service.calls == [("list_projects", ("2026",))]


def test_project_list_no_year_passes_none():
    service = FakeProjectService()
    api = JsApi(dashboard_service=None, project_service=service)

    response = api.project_list()

    assert response["ok"] is True
    assert service.calls == [("list_projects", (None,))]


def test_project_open_folder_success():
    service = FakeProjectService()
    api = JsApi(dashboard_service=None, project_service=service)

    response = api.project_open_folder("/tmp/2026/UAT_PREPARE/Alpha")

    assert response == {"ok": True, "data": None, "error": None}
    assert service.calls == [("open_folder", (Path("/tmp/2026/UAT_PREPARE/Alpha"),))]


def test_project_get_exception_returns_fail():
    api = JsApi(dashboard_service=None, project_service=ExplodingProjectService())

    response = api.project_get("/tmp/nonexistent")

    assert response == {
        "ok": False,
        "data": None,
        "error": {
            "code": "PROJECT_GET_FAILED",
            "message": "project not found",
            "details": None,
        },
    }


def test_project_list_exception_returns_fail():
    api = JsApi(dashboard_service=None, project_service=ExplodingProjectService())

    response = api.project_list()

    assert response == {
        "ok": False,
        "data": None,
        "error": {
            "code": "PROJECT_LIST_FAILED",
            "message": "list failed",
            "details": None,
        },
    }


def test_project_open_folder_exception_returns_fail():
    api = JsApi(dashboard_service=None, project_service=ExplodingProjectService())

    response = api.project_open_folder("/tmp/bad")

    assert response == {
        "ok": False,
        "data": None,
        "error": {
            "code": "PROJECT_OPEN_FOLDER_FAILED",
            "message": "open failed",
            "details": None,
        },
    }


def test_js_api_project_import_does_not_require_pywebview():
    assert "webview" not in sys.modules
    importlib.reload(js_api)
    assert "webview" not in sys.modules
