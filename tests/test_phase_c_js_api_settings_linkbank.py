"""Phase C.11 — JsApi settings/link bank facades tests (TDD: RED first)."""

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from web.js_api import JsApi


@dataclass(frozen=True)
class FakeLink:
    id: str
    title: str
    path: Path
    updated_at: datetime


class FakeSettingsDependency:
    def __init__(self) -> None:
        self.calls: list[tuple[str, tuple[object, ...]]] = []

    def get_settings(self) -> dict[str, object]:
        self.calls.append(("get_settings", ()))
        return {"root_folder": Path("/tmp/projects"), "display_name": "Sayyid"}

    def update_settings(self, data: dict[str, object]) -> dict[str, object]:
        self.calls.append(("update_settings", (data,)))
        return {"saved": True, "data": data}


class FakeLinkBankDependency:
    def __init__(self) -> None:
        self.calls: list[tuple[str, tuple[object, ...]]] = []
        self.link = FakeLink(
            id="l-1",
            title="Docs",
            path=Path("/tmp/docs"),
            updated_at=datetime(2026, 5, 1, 2, 3, 4, tzinfo=timezone.utc),
        )

    def get_linkbank(self) -> dict[str, object]:
        self.calls.append(("get_linkbank", ()))
        return {"links": [self.link]}

    def update_linkbank(self, data: dict[str, object]) -> dict[str, object]:
        self.calls.append(("update_linkbank", (data,)))
        return {"updated": True, "data": data}

    def add_link(self, data: dict[str, object]) -> FakeLink:
        self.calls.append(("add_link", (data,)))
        return self.link

    def archive_link(self, link_id: str) -> dict[str, object]:
        self.calls.append(("archive_link", (link_id,)))
        return {"archived": True, "id": link_id}

    def restore_link(self, link_id: str) -> dict[str, object]:
        self.calls.append(("restore_link", (link_id,)))
        return {"restored": True, "id": link_id}

    def category_restore(self, name: str) -> dict[str, object]:
        self.calls.append(("category_restore", (name,)))
        return {"restored": True, "name": name}

    def open_link(self, link_id: str) -> dict[str, object]:
        self.calls.append(("open_link", (link_id,)))
        return {"opened": True, "id": link_id}

    def export_file(self, fmt: str) -> dict[str, object]:
        self.calls.append(("export_file", (fmt,)))
        return {"format": fmt, "content": "..."}

    def preview_import(self, payload: dict[str, object]) -> dict[str, object]:
        self.calls.append(("preview_import", (payload,)))
        return {"added": 1, "updated": 0, "conflicts": 0, "invalid": 0, "skipped": []}

    def merge_import(self, payload: dict[str, object]) -> dict[str, object]:
        self.calls.append(("merge_import", (payload,)))
        return {"added": 1, "updated": 0, "conflicts": 0, "invalid": 0, "skipped": []}


class ExplodingSettingsDependency(FakeSettingsDependency):
    def get_settings(self) -> dict[str, object]:
        raise RuntimeError("settings unavailable")


class ExplodingLinkBankDependency(FakeLinkBankDependency):
    def get_linkbank(self) -> dict[str, object]:
        raise RuntimeError("linkbank unavailable")


def test_settings_get_and_update_delegate_and_convert_results():
    service = FakeSettingsDependency()
    api = JsApi(dashboard_service=None, settings_service=service)
    data = {"display_name": "New"}

    got = api.settings_get()
    updated = api.settings_update(data)

    assert got == {
        "ok": True,
        "data": {"root_folder": "/tmp/projects", "display_name": "Sayyid"},
        "error": None,
    }
    assert updated == {"ok": True, "data": {"saved": True, "data": data}, "error": None}
    assert service.calls == [("get_settings", ()), ("update_settings", (data,))]


def test_settings_store_alias_is_supported():
    store = FakeSettingsDependency()
    api = JsApi(dashboard_service=None, settings_store=store)

    response = api.settings_get()

    assert response["ok"] is True
    assert store.calls == [("get_settings", ())]


def test_linkbank_facades_delegate_and_convert_results():
    service = FakeLinkBankDependency()
    api = JsApi(dashboard_service=None, linkbank_service=service)
    data = {"title": "Docs"}

    got = api.linkbank_get()
    updated = api.linkbank_update(data)
    added = api.linkbank_add_link(data)
    archived = api.linkbank_archive_link("l-1")

    assert got == {
        "ok": True,
        "data": {
            "links": [
                {
                    "id": "l-1",
                    "title": "Docs",
                    "path": "/tmp/docs",
                    "updated_at": "2026-05-01T02:03:04+00:00",
                }
            ]
        },
        "error": None,
    }
    assert updated == {"ok": True, "data": {"updated": True, "data": data}, "error": None}
    assert added["data"]["path"] == "/tmp/docs"
    assert archived == {"ok": True, "data": {"archived": True, "id": "l-1"}, "error": None}
    assert service.calls == [
        ("get_linkbank", ()),
        ("update_linkbank", (data,)),
        ("add_link", (data,)),
        ("archive_link", ("l-1",)),
    ]


def test_linkbank_store_alias_is_supported():
    store = FakeLinkBankDependency()
    api = JsApi(dashboard_service=None, linkbank_store=store)

    response = api.linkbank_get()

    assert response["ok"] is True
    assert store.calls == [("get_linkbank", ())]


def test_linkbank_new_facades_delegate_and_convert_results():
    service = FakeLinkBankDependency()
    api = JsApi(dashboard_service=None, linkbank_service=service)

    restored = api.linkbank_restore_link("l-1")
    cat_restored = api.linkbank_category_restore("Ops")
    opened = api.linkbank_open_link("l-1")
    exported = api.linkbank_export_file("csv")
    previewed = api.linkbank_preview_import({"format": "json", "content": "{}"})
    merged = api.linkbank_merge_import({"format": "json", "content": "{}"})

    assert restored == {"ok": True, "data": {"restored": True, "id": "l-1"}, "error": None}
    assert cat_restored == {"ok": True, "data": {"restored": True, "name": "Ops"}, "error": None}
    assert opened == {"ok": True, "data": {"opened": True, "id": "l-1"}, "error": None}
    assert exported == {"ok": True, "data": {"format": "csv", "content": "..."}, "error": None}
    assert previewed["data"]["added"] == 1
    assert merged["data"]["added"] == 1
    assert service.calls == [
        ("restore_link", ("l-1",)),
        ("category_restore", ("Ops",)),
        ("open_link", ("l-1",)),
        ("export_file", ("csv",)),
        ("preview_import", ({"format": "json", "content": "{}"},)),
        ("merge_import", ({"format": "json", "content": "{}"},)),
    ]


def test_linkbank_new_facades_missing_dependency_returns_service_unavailable():
    api = JsApi(dashboard_service=None)

    assert api.linkbank_restore_link("l-1")["error"]["code"] == "SERVICE_UNAVAILABLE"
    assert api.linkbank_category_restore("Ops")["error"]["code"] == "SERVICE_UNAVAILABLE"
    assert api.linkbank_open_link("l-1")["error"]["code"] == "SERVICE_UNAVAILABLE"
    assert api.linkbank_export_file()["error"]["code"] == "SERVICE_UNAVAILABLE"
    assert api.linkbank_preview_import({})["error"]["code"] == "SERVICE_UNAVAILABLE"
    assert api.linkbank_merge_import({})["error"]["code"] == "SERVICE_UNAVAILABLE"


def test_missing_dependencies_return_service_unavailable():
    api = JsApi(dashboard_service=None)

    assert api.settings_get()["error"]["code"] == "SERVICE_UNAVAILABLE"
    assert api.linkbank_get()["error"]["code"] == "SERVICE_UNAVAILABLE"


def test_exceptions_return_fail():
    api = JsApi(
        dashboard_service=None,
        settings_service=ExplodingSettingsDependency(),
        linkbank_service=ExplodingLinkBankDependency(),
    )

    assert api.settings_get()["error"] == {
        "code": "SETTINGS_GET_FAILED",
        "message": "settings unavailable",
        "details": None,
    }
    assert api.linkbank_get()["error"] == {
        "code": "LINKBANK_GET_FAILED",
        "message": "linkbank unavailable",
        "details": None,
    }
