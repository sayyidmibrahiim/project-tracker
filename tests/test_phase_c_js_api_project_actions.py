"""Phase C.8c-C.8e — JsApi project action facades tests (TDD: RED first)."""

import importlib
import sys
from dataclasses import dataclass
from pathlib import Path

from core.enums import CRState, ProjectState
from web import js_api
from web.js_api import JsApi


@dataclass(frozen=True)
class FakeActionResult:
    project_path: Path
    project_state: ProjectState
    cr_state: CRState


class FakeProjectService:
    def __init__(self) -> None:
        self.calls: list[tuple[str, tuple[object, ...]]] = []
        self.result = FakeActionResult(
            project_path=Path("/tmp/2026/PROD_READY/Alpha"),
            project_state=ProjectState.PROD_READY,
            cr_state=CRState.APPROVED,
        )

    def update_cr_link(self, project_path: Path, cr_link: str) -> FakeActionResult:
        self.calls.append(("update_cr_link", (project_path, cr_link)))
        return self.result

    def update_cr_state(self, project_path: Path, cr_state: str) -> FakeActionResult:
        self.calls.append(("update_cr_state", (project_path, cr_state)))
        return self.result

    def add_drone(self, project_path: Path, data: dict[str, object]) -> FakeActionResult:
        self.calls.append(("add_drone", (project_path, data)))
        return self.result

    def update_drone(self, project_path: Path, drone_index: int, data: dict[str, object]) -> FakeActionResult:
        self.calls.append(("update_drone", (project_path, drone_index, data)))
        return self.result

    def delete_drone(self, project_path: Path, drone_index: int) -> FakeActionResult:
        self.calls.append(("delete_drone", (project_path, drone_index)))
        return self.result

    def move_to_prod_ready(self, project_path: Path) -> FakeActionResult:
        self.calls.append(("move_to_prod_ready", (project_path,)))
        return self.result

    def move_to_implemented(self, project_path: Path) -> FakeActionResult:
        self.calls.append(("move_to_implemented", (project_path,)))
        return self.result

    def postpone_project(self, project_path: Path) -> FakeActionResult:
        self.calls.append(("postpone_project", (project_path,)))
        return self.result

    def resume_project(self, project_path: Path) -> FakeActionResult:
        self.calls.append(("resume_project", (project_path,)))
        return self.result

    def cancel_project(self, project_path: Path) -> FakeActionResult:
        self.calls.append(("cancel_project", (project_path,)))
        return self.result

    def reopen_project(self, project_path: Path) -> FakeActionResult:
        self.calls.append(("reopen_project", (project_path,)))
        return self.result


class ExplodingProjectService(FakeProjectService):
    def update_cr_link(self, project_path: Path, cr_link: str) -> FakeActionResult:
        raise RuntimeError("cr link failed")

    def update_cr_state(self, project_path: Path, cr_state: str) -> FakeActionResult:
        raise RuntimeError("cr state failed")

    def add_drone(self, project_path: Path, data: dict[str, object]) -> FakeActionResult:
        raise RuntimeError("drone add failed")

    def update_drone(self, project_path: Path, drone_index: int, data: dict[str, object]) -> FakeActionResult:
        raise RuntimeError("drone update failed")

    def delete_drone(self, project_path: Path, drone_index: int) -> FakeActionResult:
        raise RuntimeError("drone delete failed")

    def move_to_prod_ready(self, project_path: Path) -> FakeActionResult:
        raise RuntimeError("prod ready failed")

    def move_to_implemented(self, project_path: Path) -> FakeActionResult:
        raise RuntimeError("implemented failed")

    def postpone_project(self, project_path: Path) -> FakeActionResult:
        raise RuntimeError("postpone failed")

    def resume_project(self, project_path: Path) -> FakeActionResult:
        raise RuntimeError("resume failed")

    def cancel_project(self, project_path: Path) -> FakeActionResult:
        raise RuntimeError("cancel failed")

    def reopen_project(self, project_path: Path) -> FakeActionResult:
        raise RuntimeError("reopen failed")


def assert_converted(response: dict[str, object]) -> None:
    assert response["ok"] is True
    assert response["error"] is None
    assert response["data"] == {
        "project_path": "/tmp/2026/PROD_READY/Alpha",
        "project_state": "PROD_READY",
        "cr_state": "APPROVED",
    }


def test_cr_facade_delegates_and_converts_results():
    service = FakeProjectService()
    api = JsApi(dashboard_service=None, project_service=service)

    assert_converted(api.cr_update_link("/tmp/Alpha", "https://cr.test/1"))
    assert_converted(api.cr_update_state("/tmp/Alpha", "APPROVED"))

    assert service.calls == [
        ("update_cr_link", (Path("/tmp/Alpha"), "https://cr.test/1")),
        ("update_cr_state", (Path("/tmp/Alpha"), "APPROVED")),
    ]


def test_drone_facade_delegates_and_converts_results():
    service = FakeProjectService()
    api = JsApi(dashboard_service=None, project_service=service)
    data = {"drone_link": "https://drone.test/D-1"}

    assert_converted(api.drone_add("/tmp/Alpha", data))
    assert_converted(api.drone_update("/tmp/Alpha", 0, data))
    assert_converted(api.drone_delete("/tmp/Alpha", 0))

    assert service.calls == [
        ("add_drone", (Path("/tmp/Alpha"), data)),
        ("update_drone", (Path("/tmp/Alpha"), 0, data)),
        ("delete_drone", (Path("/tmp/Alpha"), 0)),
    ]


def test_folder_transition_facade_delegates_and_converts_results():
    service = FakeProjectService()
    api = JsApi(dashboard_service=None, project_service=service)

    for response in [
        api.folder_move_to_prod_ready("/tmp/Alpha"),
        api.folder_move_to_implemented("/tmp/Alpha"),
        api.folder_postpone("/tmp/Alpha"),
        api.folder_resume("/tmp/Alpha"),
        api.folder_cancel("/tmp/Alpha"),
        api.folder_reopen("/tmp/Alpha"),
    ]:
        assert_converted(response)

    assert service.calls == [
        ("move_to_prod_ready", (Path("/tmp/Alpha"),)),
        ("move_to_implemented", (Path("/tmp/Alpha"),)),
        ("postpone_project", (Path("/tmp/Alpha"),)),
        ("resume_project", (Path("/tmp/Alpha"),)),
        ("cancel_project", (Path("/tmp/Alpha"),)),
        ("reopen_project", (Path("/tmp/Alpha"),)),
    ]


def test_action_exceptions_return_fail():
    api = JsApi(dashboard_service=None, project_service=ExplodingProjectService())

    cases = [
        (api.cr_update_link("/tmp/Alpha", "x"), "CR_UPDATE_LINK_FAILED", "cr link failed"),
        (api.cr_update_state("/tmp/Alpha", "APPROVED"), "CR_UPDATE_STATE_FAILED", "cr state failed"),
        (api.drone_add("/tmp/Alpha", {}), "DRONE_ADD_FAILED", "drone add failed"),
        (api.drone_update("/tmp/Alpha", 0, {}), "DRONE_UPDATE_FAILED", "drone update failed"),
        (api.drone_delete("/tmp/Alpha", 0), "DRONE_DELETE_FAILED", "drone delete failed"),
        (api.folder_move_to_prod_ready("/tmp/Alpha"), "FOLDER_MOVE_TO_PROD_READY_FAILED", "prod ready failed"),
        (api.folder_move_to_implemented("/tmp/Alpha"), "FOLDER_MOVE_TO_IMPLEMENTED_FAILED", "implemented failed"),
        (api.folder_postpone("/tmp/Alpha"), "FOLDER_POSTPONE_FAILED", "postpone failed"),
        (api.folder_resume("/tmp/Alpha"), "FOLDER_RESUME_FAILED", "resume failed"),
        (api.folder_cancel("/tmp/Alpha"), "FOLDER_CANCEL_FAILED", "cancel failed"),
        (api.folder_reopen("/tmp/Alpha"), "FOLDER_REOPEN_FAILED", "reopen failed"),
    ]

    for response, code, message in cases:
        assert response == {
            "ok": False,
            "data": None,
            "error": {"code": code, "message": message, "details": None},
        }


def test_js_api_project_actions_import_does_not_require_pywebview():
    assert "webview" not in sys.modules
    importlib.reload(js_api)
    assert "webview" not in sys.modules
