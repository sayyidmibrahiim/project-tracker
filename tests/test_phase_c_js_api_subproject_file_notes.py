"""Phase C.10 — JsApi subproject/file/notes facades tests (TDD: RED first)."""

from dataclasses import dataclass
from pathlib import Path

from web.js_api import JsApi


@dataclass(frozen=True)
class FakeFileRow:
    name: str
    path: Path


class FakeProjectService:
    def __init__(self) -> None:
        self.calls: list[tuple[str, tuple[object, ...]]] = []

    def list_subprojects(self, project_path: Path) -> list[Path]:
        self.calls.append(("list_subprojects", (project_path,)))
        return [project_path / "api"]

    def create_subproject(self, project_path: Path, name: str) -> Path:
        self.calls.append(("create_subproject", (project_path, name)))
        return project_path / name

    def delete_subproject(self, project_path: Path, name: str) -> dict[str, object]:
        self.calls.append(("delete_subproject", (project_path, name)))
        return {"deleted": True, "path": project_path / name}


class FakeFileService:
    def __init__(self) -> None:
        self.calls: list[tuple[str, tuple[object, ...]]] = []

    def list_files(self, path: Path) -> list[FakeFileRow]:
        self.calls.append(("list_files", (path,)))
        return [FakeFileRow(name="notes.md", path=path / "notes.md")]

    def open_file(self, path: Path) -> None:
        self.calls.append(("open_file", (path,)))

    def open_folder(self, path: Path) -> None:
        self.calls.append(("open_folder", (path,)))


class FakeNotesService:
    def __init__(self) -> None:
        self.calls: list[tuple[str, tuple[object, ...]]] = []

    def get_notes(self, project_path: Path) -> str:
        self.calls.append(("get_notes", (project_path,)))
        return "hello"

    def update_notes(self, project_path: Path, notes: str) -> dict[str, object]:
        self.calls.append(("update_notes", (project_path, notes)))
        return {"project_path": project_path, "notes": notes}


class ExplodingProjectService(FakeProjectService):
    def list_subprojects(self, project_path: Path) -> list[Path]:
        raise RuntimeError("subproject unavailable")


class ExplodingFileService(FakeFileService):
    def list_files(self, path: Path) -> list[FakeFileRow]:
        raise RuntimeError("file unavailable")


class ExplodingNotesService(FakeNotesService):
    def get_notes(self, project_path: Path) -> str:
        raise RuntimeError("notes unavailable")


def test_subproject_facades_delegate_and_convert_results():
    service = FakeProjectService()
    api = JsApi(dashboard_service=None, project_service=service)

    listed = api.subproject_list("/tmp/Alpha")
    created = api.subproject_create("/tmp/Alpha", "api")
    deleted = api.subproject_delete("/tmp/Alpha", "api")

    assert listed == {"ok": True, "data": ["/tmp/Alpha/api"], "error": None}
    assert created == {"ok": True, "data": "/tmp/Alpha/api", "error": None}
    assert deleted == {"ok": True, "data": {"deleted": True, "path": "/tmp/Alpha/api"}, "error": None}
    assert service.calls == [
        ("list_subprojects", (Path("/tmp/Alpha"),)),
        ("create_subproject", (Path("/tmp/Alpha"), "api")),
        ("delete_subproject", (Path("/tmp/Alpha"), "api")),
    ]


def test_file_facades_delegate_and_convert_results():
    service = FakeFileService()
    api = JsApi(dashboard_service=None, file_service=service)

    listed = api.file_list("/tmp/Alpha")
    opened_file = api.file_open("/tmp/Alpha/notes.md")
    opened_folder = api.folder_open("/tmp/Alpha")

    assert listed == {
        "ok": True,
        "data": [{"name": "notes.md", "path": "/tmp/Alpha/notes.md"}],
        "error": None,
    }
    assert opened_file == {"ok": True, "data": None, "error": None}
    assert opened_folder == {"ok": True, "data": None, "error": None}
    assert service.calls == [
        ("list_files", (Path("/tmp/Alpha"),)),
        ("open_file", (Path("/tmp/Alpha/notes.md"),)),
        ("open_folder", (Path("/tmp/Alpha"),)),
    ]


def test_notes_facades_delegate_and_convert_results():
    service = FakeNotesService()
    api = JsApi(dashboard_service=None, notes_service=service)

    got = api.notes_get("/tmp/Alpha")
    updated = api.notes_update("/tmp/Alpha", "new notes")

    assert got == {"ok": True, "data": "hello", "error": None}
    assert updated == {
        "ok": True,
        "data": {"project_path": "/tmp/Alpha", "notes": "new notes"},
        "error": None,
    }
    assert service.calls == [
        ("get_notes", (Path("/tmp/Alpha"),)),
        ("update_notes", (Path("/tmp/Alpha"), "new notes")),
    ]


def test_missing_services_return_service_unavailable_fail():
    api = JsApi(dashboard_service=None)

    assert api.subproject_list("/tmp/Alpha")["error"]["code"] == "SERVICE_UNAVAILABLE"
    assert api.file_list("/tmp/Alpha")["error"]["code"] == "SERVICE_UNAVAILABLE"
    assert api.notes_get("/tmp/Alpha")["error"]["code"] == "SERVICE_UNAVAILABLE"


def test_exceptions_return_fail():
    api = JsApi(
        dashboard_service=None,
        project_service=ExplodingProjectService(),
        file_service=ExplodingFileService(),
        notes_service=ExplodingNotesService(),
    )

    assert api.subproject_list("/tmp/Alpha")["error"] == {
        "code": "SUBPROJECT_LIST_FAILED",
        "message": "subproject unavailable",
        "details": None,
    }
    assert api.file_list("/tmp/Alpha")["error"] == {
        "code": "FILE_LIST_FAILED",
        "message": "file unavailable",
        "details": None,
    }
    assert api.notes_get("/tmp/Alpha")["error"] == {
        "code": "NOTES_GET_FAILED",
        "message": "notes unavailable",
        "details": None,
    }
