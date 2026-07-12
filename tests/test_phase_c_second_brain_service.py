"""Phase C.12 — SecondBrainService foundation tests (TDD: RED first)."""

from datetime import datetime, timezone
from pathlib import Path

import pytest

from services.second_brain_service import (
    SecondBrainItem,
    SecondBrainService,
)


def _items() -> list[SecondBrainItem]:
    return [
        SecondBrainItem(
            id="note-1",
            title="Deployment Notes",
            path=Path("/tmp/brain/deploy.md"),
            item_type="file",
            updated_at=datetime(2026, 1, 2, 3, 4, 5, tzinfo=timezone.utc),
            pinned=False,
            favorite=False,
            excerpt="Production deployment checklist",
        ),
        SecondBrainItem(
            id="note-2",
            title="Contacts",
            path=Path("/tmp/brain/contacts.md"),
            item_type="file",
            updated_at=datetime(2026, 2, 3, 4, 5, 6, tzinfo=timezone.utc),
            pinned=True,
            favorite=False,
            excerpt="DBS support contacts",
        ),
    ]


def test_list_items_returns_provider_items_without_mutating_source():
    source = _items()
    service = SecondBrainService(items_provider=lambda: source)

    result = service.list_items()

    assert result == source
    assert result is not source


def test_search_is_case_insensitive_across_title_path_and_excerpt():
    service = SecondBrainService(items_provider=_items)

    title_matches = service.search("deployment")
    path_matches = service.search("CONTACTS.MD")
    excerpt_matches = service.search("support")

    assert [item.id for item in title_matches] == ["note-1"]
    assert [item.id for item in path_matches] == ["note-2"]
    assert [item.id for item in excerpt_matches] == ["note-2"]


def test_blank_search_returns_all_items():
    service = SecondBrainService(items_provider=_items)

    result = service.search("  ")

    assert [item.id for item in result] == ["note-1", "note-2"]


def test_get_item_returns_matching_item_or_none():
    service = SecondBrainService(items_provider=_items)

    assert service.get_item("note-1").title == "Deployment Notes"
    assert service.get_item("missing") is None


def test_pin_and_favorite_return_updated_in_memory_item():
    service = SecondBrainService(items_provider=_items)

    pinned = service.pin_item("note-1")
    favorite = service.favorite_item("note-1")

    assert pinned.pinned is True
    assert favorite.favorite is True
    assert service.get_item("note-1").pinned is True
    assert service.get_item("note-1").favorite is True


def test_pin_and_favorite_missing_item_raise_key_error():
    service = SecondBrainService(items_provider=_items)

    with pytest.raises(KeyError, match="Second Brain item not found: missing"):
        service.pin_item("missing")

    with pytest.raises(KeyError, match="Second Brain item not found: missing"):
        service.favorite_item("missing")


@pytest.mark.parametrize(
    ("folder_factory", "expected"),
    [
        (lambda tmp: None, "unset"),
        (lambda tmp: tmp / "missing", "missing"),
        (lambda tmp: tmp / "configured-file", "invalid"),
        (lambda tmp: tmp / "notes", "ready"),
    ],
)
def test_workspace_reports_personal_folder_status(tmp_path: Path, folder_factory, expected: str):
    folder = folder_factory(tmp_path)
    if expected == "invalid":
        assert folder is not None
        folder.write_text("not a directory", encoding="utf-8")
    elif expected == "ready":
        assert folder is not None
        folder.mkdir()

    service = SecondBrainService(folder_provider=lambda: folder)
    workspace = service.workspace()

    assert workspace["personal_status"] == expected
    assert workspace["personal_root"] == folder


def test_workspace_reports_unreadable_root_without_fallback(tmp_path: Path, monkeypatch):
    folder = tmp_path / "notes"
    folder.mkdir()
    original_scandir = __import__("os").scandir

    def fail_root(path):
        if Path(path) == folder:
            raise PermissionError("denied")
        return original_scandir(path)

    monkeypatch.setattr("services.second_brain_service.os.scandir", fail_root)
    service = SecondBrainService(folder_provider=lambda: folder)

    workspace = service.workspace()

    assert workspace["personal_status"] == "unreadable"
    assert workspace["personal_root"] == folder
    assert workspace["items"] == []
    assert any("denied" in warning.casefold() or "unreadable" in warning.casefold() for warning in workspace["warnings"])


def test_full_text_search_is_separate_from_capped_excerpt(tmp_path: Path):
    folder = tmp_path / "notes"
    folder.mkdir()
    (folder / "long.md").write_text("x" * 250 + " deep-keyword", encoding="utf-8")
    service = SecondBrainService(folder_provider=lambda: folder)

    matches = service.search("deep-keyword")

    assert [item.title for item in matches] == ["long"]
    assert len(matches[0].excerpt) == 200
    assert not hasattr(matches[0], "content")


def test_unreadable_personal_file_warns_but_keeps_other_items(tmp_path: Path, monkeypatch):
    folder = tmp_path / "notes"
    folder.mkdir()
    good = folder / "good.md"
    bad = folder / "bad.md"
    good.write_text("green-content-token", encoding="utf-8")
    bad.write_text("blocked", encoding="utf-8")
    original_read_text = Path.read_text

    def guarded_read_text(self, *args, **kwargs):
        if self == bad:
            raise PermissionError("blocked file")
        return original_read_text(self, *args, **kwargs)

    monkeypatch.setattr(Path, "read_text", guarded_read_text)
    service = SecondBrainService(folder_provider=lambda: folder)

    workspace = service.workspace()

    assert {item.title for item in workspace["items"]} == {"good", "bad"}
    assert service.search("green-content-token")[0].title == "good"
    assert any("bad.md" in warning for warning in workspace["warnings"])
