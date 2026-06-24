"""Phase C.8b — JsApi project mutation facade tests (TDD: RED first)."""

import importlib
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from core.enums import CRState, ProjectState
from web import js_api
from web.js_api import JsApi


@dataclass(frozen=True)
class FakeProjectResult:
    project_name: str
    project_path: Path
    project_state: ProjectState
    cr_state: CRState
    updated_at: datetime


class FakeProjectService:
    def __init__(self) -> None:
        self.calls: list[tuple[str, tuple[object, ...]]] = []
        self.result = FakeProjectResult(
            project_name="Alpha Renamed",
            project_path=Path("/tmp/2026/UAT_PREPARE/Alpha Renamed"),
            project_state=ProjectState.UAT_PREPARE,
            cr_state=CRState.APPROVED,
            updated_at=datetime(2026, 4, 5, 6, 7, 8, tzinfo=timezone.utc),
        )

    def create_project(self, data: dict[str, object]) -> FakeProjectResult:
        self.calls.append(("create_project", (data,)))
        return self.result

    def update_project(self, project_path: Path, data: dict[str, object]) -> FakeProjectResult:
        self.calls.append(("update_project", (project_path, data)))
        return self.result

    def rename_project(self, project_path: Path, new_name: str) -> FakeProjectResult:
        self.calls.append(("rename_project", (project_path, new_name)))
        return self.result


class ExplodingProjectService(FakeProjectService):
    def create_project(self, data: dict[str, object]) -> FakeProjectResult:
        raise RuntimeError("create failed")

    def update_project(self, project_path: Path, data: dict[str, object]) -> FakeProjectResult:
        raise RuntimeError("update failed")

    def rename_project(self, project_path: Path, new_name: str) -> FakeProjectResult:
        raise RuntimeError("rename failed")


def test_project_create_delegates_data_and_returns_converted_result():
    service = FakeProjectService()
    api = JsApi(dashboard_service=None, project_service=service)
    data = {"project_name": "Alpha", "year": "2026"}

    response = api.project_create(data)

    assert response["ok"] is True
    assert response["error"] is None
    assert response["data"] == {
        "project_name": "Alpha Renamed",
        "project_path": "/tmp/2026/UAT_PREPARE/Alpha Renamed",
        "project_state": "UAT_PREPARE",
        "cr_state": "APPROVED",
        "updated_at": "2026-04-05T06:07:08+00:00",
    }
    assert service.calls == [("create_project", (data,))]


def test_project_update_delegates_path_and_data_and_returns_converted_result():
    service = FakeProjectService()
    api = JsApi(dashboard_service=None, project_service=service)
    data = {"cr_link": "https://example.test/cr"}

    response = api.project_update("/tmp/2026/UAT_PREPARE/Alpha", data)

    assert response["ok"] is True
    assert response["data"]["project_state"] == "UAT_PREPARE"
    assert response["data"]["updated_at"] == "2026-04-05T06:07:08+00:00"
    assert service.calls == [
        ("update_project", (Path("/tmp/2026/UAT_PREPARE/Alpha"), data))
    ]


def test_project_rename_delegates_path_and_name_and_returns_converted_result():
    service = FakeProjectService()
    api = JsApi(dashboard_service=None, project_service=service)

    response = api.project_rename("/tmp/2026/UAT_PREPARE/Alpha", "Alpha Renamed")

    assert response["ok"] is True
    assert response["data"]["project_name"] == "Alpha Renamed"
    assert response["data"]["project_path"] == "/tmp/2026/UAT_PREPARE/Alpha Renamed"
    assert service.calls == [
        ("rename_project", (Path("/tmp/2026/UAT_PREPARE/Alpha"), "Alpha Renamed"))
    ]


def test_project_create_exception_returns_fail():
    api = JsApi(dashboard_service=None, project_service=ExplodingProjectService())

    response = api.project_create({"project_name": "Alpha"})

    assert response == {
        "ok": False,
        "data": None,
        "error": {"code": "PROJECT_CREATE_FAILED", "message": "create failed", "details": None},
    }


def test_project_update_exception_returns_fail():
    api = JsApi(dashboard_service=None, project_service=ExplodingProjectService())

    response = api.project_update("/tmp/Alpha", {"project_name": "Beta"})

    assert response == {
        "ok": False,
        "data": None,
        "error": {"code": "PROJECT_UPDATE_FAILED", "message": "update failed", "details": None},
    }


def test_project_rename_exception_returns_fail():
    api = JsApi(dashboard_service=None, project_service=ExplodingProjectService())

    response = api.project_rename("/tmp/Alpha", "Beta")

    assert response == {
        "ok": False,
        "data": None,
        "error": {"code": "PROJECT_RENAME_FAILED", "message": "rename failed", "details": None},
    }


def test_js_api_project_mutation_import_does_not_require_pywebview():
    assert "webview" not in sys.modules
    importlib.reload(js_api)
    assert "webview" not in sys.modules
