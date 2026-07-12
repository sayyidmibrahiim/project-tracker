"""Phase C.13 — JsApi Second Brain facade tests (TDD: RED first)."""

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

import pytest

from core.enums import ProjectState
from web.js_api import JsApi


@dataclass(frozen=True)
class FakeSecondBrainItem:
    id: str
    title: str
    path: Path
    item_type: str
    updated_at: datetime
    pinned: bool
    favorite: bool
    state: ProjectState


class FakeSecondBrainService:
    def __init__(self) -> None:
        self.calls: list[tuple[str, tuple[object, ...]]] = []
        self.item = FakeSecondBrainItem(
            id="note-1",
            title="Deployment Notes",
            path=Path("/tmp/brain/deploy.md"),
            item_type="file",
            updated_at=datetime(2026, 1, 2, 3, 4, 5, tzinfo=timezone.utc),
            pinned=False,
            favorite=True,
            state=ProjectState.UAT_PREPARE,
        )

    def list_items(self) -> list[FakeSecondBrainItem]:
        self.calls.append(("list_items", ()))
        return [self.item]

    def search(
        self,
        query: str,
        date_filter: str = "",
        sort: str = "newest",
        type_filter: str = "all",
        source_filter: str = "all",
    ) -> list[FakeSecondBrainItem]:
        self.calls.append(
            ("search", (query, date_filter, sort, type_filter, source_filter))
        )
        return [self.item]

    def get_item(self, item_id: str) -> FakeSecondBrainItem | None:
        self.calls.append(("get_item", (item_id,)))
        return self.item

    def pin_item(self, item_id: str) -> FakeSecondBrainItem:
        self.calls.append(("pin_item", (item_id,)))
        return self.item

    def favorite_item(self, item_id: str) -> FakeSecondBrainItem:
        self.calls.append(("favorite_item", (item_id,)))
        return self.item

    def workspace(self) -> dict[str, object]:
        self.calls.append(("workspace", ()))
        return {
            "items": [self.item],
            "warnings": [],
            "personal_root": "/tmp/brain",
            "project_root": None,
            "personal_status": "ready",
        }

    def set_tags(self, item_id: str, tags: list[str]) -> FakeSecondBrainItem:
        self.calls.append(("set_tags", (item_id, tags)))
        return self.item

    def related(self, item_id: str, limit: int = 20) -> list[dict[str, object]]:
        self.calls.append(("related", (item_id,)))
        return [{"item": self.item, "reason": "shared_tag", "score": 3}]

    def create_file(self, parent: Path, filename: str, content: str = "") -> Path:
        self.calls.append(("create_file", (parent, filename, content)))
        return parent / filename

    def rename_item(self, filepath: Path, new_name: str) -> FakeSecondBrainItem:
        self.calls.append(("rename_item", (filepath, new_name)))
        return self.item

    def recycle_item(self, filepath: Path) -> None:
        self.calls.append(("recycle_item", (filepath,)))

    def read_image(self, filepath: Path) -> dict[str, object]:
        self.calls.append(("read_image", (filepath,)))
        return {"data_uri": "data:image/png;base64,Zg==", "name": "diagram.png"}

    def mark_saved(self, filepath: Path) -> None:
        self.calls.append(("mark_saved", (filepath,)))

    def use_default_folder(self) -> Path:
        self.calls.append(("use_default_folder", ()))
        return Path("/tmp/brain/Second Brain")

    def refresh(self) -> dict[str, object]:
        self.calls.append(("refresh", ()))
        return {
            "items": [self.item],
            "warnings": [],
            "personal_root": "/tmp/brain",
            "project_root": None,
            "personal_status": "ready",
        }


class ExplodingSecondBrainService(FakeSecondBrainService):
    def list_items(self) -> list[FakeSecondBrainItem]:
        raise RuntimeError("brain unavailable")


def _expected_item() -> dict[str, object]:
    return {
        "id": "note-1",
        "title": "Deployment Notes",
        "path": "/tmp/brain/deploy.md",
        "item_type": "file",
        "updated_at": "2026-01-02T03:04:05+00:00",
        "pinned": False,
        "favorite": True,
        "state": "UAT_PREPARE",
    }


def test_second_brain_list_delegates_and_converts_items():
    service = FakeSecondBrainService()
    api = JsApi(dashboard_service=None, second_brain_service=service)

    response = api.second_brain_list()

    assert response == {"ok": True, "data": [_expected_item()], "error": None}
    assert service.calls == [("list_items", ())]


def test_second_brain_search_get_pin_favorite_delegate_and_convert_items():
    service = FakeSecondBrainService()
    api = JsApi(dashboard_service=None, second_brain_service=service)

    search = api.second_brain_search("deploy")
    got = api.second_brain_get("note-1")
    pinned = api.second_brain_pin("note-1")
    favorite = api.second_brain_favorite("note-1")

    assert search == {"ok": True, "data": [_expected_item()], "error": None}
    assert got == {"ok": True, "data": _expected_item(), "error": None}
    assert pinned == {"ok": True, "data": _expected_item(), "error": None}
    assert favorite == {"ok": True, "data": _expected_item(), "error": None}
    assert service.calls == [
        ("search", ("deploy", "", "newest", "all", "all")),
        ("get_item", ("note-1",)),
        ("pin_item", ("note-1",)),
        ("favorite_item", ("note-1",)),
    ]


def test_second_brain_missing_service_returns_service_unavailable():
    api = JsApi(dashboard_service=None)

    response = api.second_brain_list()

    assert response == {
        "ok": False,
        "data": None,
        "error": {
            "code": "SERVICE_UNAVAILABLE",
            "message": "second_brain_service is not configured",
            "details": None,
        },
    }


def test_second_brain_exception_returns_fail():
    api = JsApi(dashboard_service=None, second_brain_service=ExplodingSecondBrainService())

    response = api.second_brain_list()

    assert response == {
        "ok": False,
        "data": None,
        "error": {
            "code": "SECOND_BRAIN_LIST_FAILED",
            "message": "brain unavailable",
            "details": None,
        },
    }


# ── Task 4: new bridge facades forward exact args + standard envelope ────


def test_second_brain_search_forwards_filter_options():
    service = FakeSecondBrainService()
    api = JsApi(dashboard_service=None, second_brain_service=service)

    response = api.second_brain_search(
        "deploy",
        {"sort": "az", "source": "personal", "item_type": "md", "date": "2026-01-02"},
    )

    assert response == {"ok": True, "data": [_expected_item()], "error": None}
    assert service.calls == [("search", ("deploy", "2026-01-02", "az", "md", "personal"))]


def test_second_brain_workspace_delegates_and_converts():
    service = FakeSecondBrainService()
    api = JsApi(dashboard_service=None, second_brain_service=service)

    response = api.second_brain_workspace()

    assert response["ok"] is True
    assert response["data"]["items"] == [_expected_item()]
    assert response["data"]["personal_status"] == "ready"
    assert service.calls == [("workspace", ())]


def test_second_brain_tags_forwards_id_and_list():
    service = FakeSecondBrainService()
    api = JsApi(dashboard_service=None, second_brain_service=service)

    response = api.second_brain_tags("note-1", ["roadmap", "urgent"])

    assert response == {"ok": True, "data": _expected_item(), "error": None}
    assert service.calls == [("set_tags", ("note-1", ["roadmap", "urgent"]))]


def test_second_brain_related_forwards_item_id():
    service = FakeSecondBrainService()
    api = JsApi(dashboard_service=None, second_brain_service=service)

    response = api.second_brain_related("note-1")

    assert response["ok"] is True
    assert response["data"] == [{"item": _expected_item(), "reason": "shared_tag", "score": 3}]
    assert service.calls == [("related", ("note-1",))]


def test_second_brain_rename_forwards_path_and_name():
    service = FakeSecondBrainService()
    api = JsApi(dashboard_service=None, second_brain_service=service)

    response = api.second_brain_rename("/tmp/brain/deploy.md", "renamed.md")

    assert response == {"ok": True, "data": _expected_item(), "error": None}
    assert service.calls == [("rename_item", (Path("/tmp/brain/deploy.md"), "renamed.md"))]


def test_second_brain_recycle_forwards_path():
    service = FakeSecondBrainService()
    api = JsApi(dashboard_service=None, second_brain_service=service)

    response = api.second_brain_recycle("/tmp/brain/deploy.md")

    assert response == {"ok": True, "data": None, "error": None}
    assert service.calls == [("recycle_item", (Path("/tmp/brain/deploy.md"),))]


def test_second_brain_image_forwards_path_and_returns_preview():
    service = FakeSecondBrainService()
    api = JsApi(dashboard_service=None, second_brain_service=service)

    response = api.second_brain_image("/tmp/brain/diagram.png")

    assert response == {
        "ok": True,
        "data": {"data_uri": "data:image/png;base64,Zg==", "name": "diagram.png"},
        "error": None,
    }
    assert service.calls == [("read_image", (Path("/tmp/brain/diagram.png"),))]


def test_second_brain_mark_saved_forwards_path():
    service = FakeSecondBrainService()
    api = JsApi(dashboard_service=None, second_brain_service=service)

    response = api.second_brain_mark_saved("/tmp/brain/deploy.md")

    assert response == {"ok": True, "data": None, "error": None}
    assert service.calls == [("mark_saved", (Path("/tmp/brain/deploy.md"),))]


def test_second_brain_use_default_folder_returns_path():
    service = FakeSecondBrainService()
    api = JsApi(dashboard_service=None, second_brain_service=service)

    response = api.second_brain_use_default_folder()

    assert response == {"ok": True, "data": "/tmp/brain/Second Brain", "error": None}
    assert service.calls == [("use_default_folder", ())]


def test_second_brain_refresh_returns_workspace():
    service = FakeSecondBrainService()
    api = JsApi(dashboard_service=None, second_brain_service=service)

    response = api.second_brain_refresh()

    assert response["ok"] is True
    assert response["data"]["items"] == [_expected_item()]
    assert service.calls == [("refresh", ())]


@pytest.mark.parametrize(
    ("method", "args", "code"),
    [
        ("second_brain_workspace", (), "SERVICE_UNAVAILABLE"),
        ("second_brain_tags", ("note-1", []), "SERVICE_UNAVAILABLE"),
        ("second_brain_related", ("note-1",), "SERVICE_UNAVAILABLE"),
        ("second_brain_rename", ("/x.md", "y.md"), "SERVICE_UNAVAILABLE"),
        ("second_brain_recycle", ("/x.md",), "SERVICE_UNAVAILABLE"),
        ("second_brain_image", ("/x.png",), "SERVICE_UNAVAILABLE"),
        ("second_brain_mark_saved", ("/x.md",), "SERVICE_UNAVAILABLE"),
        ("second_brain_use_default_folder", (), "SERVICE_UNAVAILABLE"),
        ("second_brain_refresh", (), "SERVICE_UNAVAILABLE"),
    ],
)
def test_second_brain_new_facades_missing_service_returns_service_unavailable(method, args, code):
    api = JsApi(dashboard_service=None)

    response = getattr(api, method)(*args)

    assert response["ok"] is False
    assert response["error"]["code"] == code
