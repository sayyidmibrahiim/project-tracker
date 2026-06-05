"""Phase C.12 — SecondBrainService foundation tests (TDD: RED first)."""

from datetime import datetime, timezone
from pathlib import Path

import pytest

from project_tracker.services.second_brain_service import (
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
