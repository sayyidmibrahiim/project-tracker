"""Phase G.3 — read-only Second Brain filesystem index.

Tests prove create_js_api() wires SecondBrainService to a read-only
filesystem provider from AppSettings.second_brain_folder.
"""

from __future__ import annotations

import tempfile
from dataclasses import replace
from pathlib import Path

import pytest

from project_tracker.infrastructure.settings_store import SettingsStore


@pytest.fixture
def temp_settings_store():
    with tempfile.TemporaryDirectory() as tmp:
        yield SettingsStore(config_dir=Path(tmp) / "config")


def _api(settings_store: SettingsStore):
    from project_tracker import app_web

    return app_web.create_js_api(settings_store=settings_store)


def _configure_second_brain(settings_store: SettingsStore, folder: Path | None) -> None:
    settings_store.write(replace(settings_store.read(), second_brain_folder=folder))


def _items(result: dict[str, object]) -> list[dict[str, object]]:
    assert result["ok"] is True
    data = result["data"]
    assert isinstance(data, list)
    return data


def test_list_empty_when_folder_not_configured(temp_settings_store):
    api = _api(temp_settings_store)

    assert _items(api.second_brain_list()) == []


def test_list_empty_when_folder_missing(temp_settings_store):
    missing = Path(tempfile.gettempdir()) / "missing-second-brain-folder-for-test"
    _configure_second_brain(temp_settings_store, missing)
    api = _api(temp_settings_store)

    assert _items(api.second_brain_list()) == []


def test_list_returns_md_files(temp_settings_store):
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        (root / "Runbook.md").write_text("Deploy steps", encoding="utf-8")
        _configure_second_brain(temp_settings_store, root)
        api = _api(temp_settings_store)

        items = _items(api.second_brain_list())

    assert [item["title"] for item in items] == ["Runbook"]
    assert items[0]["path"].endswith("Runbook.md")


def test_stable_id_across_fresh_create_js_api_calls_for_same_path(temp_settings_store):
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        (root / "stable.md").write_text("same note", encoding="utf-8")
        _configure_second_brain(temp_settings_store, root)

        first = _items(_api(temp_settings_store).second_brain_list())[0]["id"]
        second = _items(_api(temp_settings_store).second_brain_list())[0]["id"]

    assert first == second
    assert isinstance(first, str)
    assert len(first) == 16


def test_md_txt_type_note_other_file_type_file(temp_settings_store):
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        (root / "a.md").write_text("a", encoding="utf-8")
        (root / "b.txt").write_text("b", encoding="utf-8")
        (root / "c.pdf").write_bytes(b"pdf")
        _configure_second_brain(temp_settings_store, root)
        api = _api(temp_settings_store)

        by_title = {item["title"]: item for item in _items(api.second_brain_list())}

    assert by_title["a"]["item_type"] == "note"
    assert by_title["b"]["item_type"] == "note"
    assert by_title["c"]["item_type"] == "file"


def test_excerpt_for_text(temp_settings_store):
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        body = "Alpha excerpt body " * 20
        (root / "excerpt.txt").write_text(body, encoding="utf-8")
        _configure_second_brain(temp_settings_store, root)
        api = _api(temp_settings_store)

        item = _items(api.second_brain_list())[0]

    assert item["excerpt"].startswith("Alpha excerpt body")
    assert len(item["excerpt"]) <= 200


def test_hidden_files_skipped(temp_settings_store):
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        (root / ".secret.md").write_text("hidden", encoding="utf-8")
        (root / "visible.md").write_text("shown", encoding="utf-8")
        _configure_second_brain(temp_settings_store, root)
        api = _api(temp_settings_store)

        titles = [item["title"] for item in _items(api.second_brain_list())]

    assert titles == ["visible"]


def test_nested_files_discovered(temp_settings_store):
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        nested = root / "ops" / "uat"
        nested.mkdir(parents=True)
        (nested / "nested.md").write_text("nested body", encoding="utf-8")
        _configure_second_brain(temp_settings_store, root)
        api = _api(temp_settings_store)

        items = _items(api.second_brain_list())

    assert len(items) == 1
    assert items[0]["path"].endswith("ops/uat/nested.md")


def test_search_by_title_and_excerpt(temp_settings_store):
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        (root / "Deploy Checklist.md").write_text("ordinary text", encoding="utf-8")
        (root / "random.txt").write_text("contains rollback keyword", encoding="utf-8")
        _configure_second_brain(temp_settings_store, root)
        api = _api(temp_settings_store)

        title_hits = _items(api.second_brain_search("checklist"))
        excerpt_hits = _items(api.second_brain_search("rollback"))

    assert [item["title"] for item in title_hits] == ["Deploy Checklist"]
    assert [item["title"] for item in excerpt_hits] == ["random"]


def test_get_by_id_returns_item(temp_settings_store):
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        (root / "lookup.md").write_text("lookup body", encoding="utf-8")
        _configure_second_brain(temp_settings_store, root)
        api = _api(temp_settings_store)

        listed = _items(api.second_brain_list())[0]
        result = api.second_brain_get(listed["id"])

    assert result["ok"] is True
    assert result["data"]["id"] == listed["id"]
    assert result["data"]["title"] == "lookup"
