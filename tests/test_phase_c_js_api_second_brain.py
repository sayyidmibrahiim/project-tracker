"""Phase C.13 — JsApi Second Brain facade tests (TDD: RED first)."""

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

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

    def search(self, query: str) -> list[FakeSecondBrainItem]:
        self.calls.append(("search", (query,)))
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
        ("search", ("deploy",)),
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
