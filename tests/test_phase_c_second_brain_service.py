"""Phase C.12 — SecondBrainService foundation tests (TDD: RED first)."""

import json
import unicodedata
from datetime import datetime, timezone
from pathlib import Path

import pytest

from core.exceptions import FileTargetExistsError
from infrastructure.cache_db import CacheDb
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

    assert [item.id for item in result] == ["note-2", "note-1"]


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


def test_tags_normalize_persist_and_upgrade_v1_sidecar(tmp_path: Path):
    folder = tmp_path / "notes"
    folder.mkdir()
    (folder / ".project_tracker_index.json").write_text(
        json.dumps(
            {
                "version": 1,
                "items": {"note-1": {"pinned": True, "favorite": False}},
            }
        ),
        encoding="utf-8",
    )
    service = SecondBrainService(items_provider=_items, folder_provider=lambda: folder)

    initial = service.get_item("note-1")
    updated = service.set_tags("note-1", [" Ops ", "ops", "DB", "db", ""])

    assert initial is not None and initial.pinned is True and initial.tags == ()
    assert updated.tags == ("Ops", "DB")
    saved = json.loads((folder / ".project_tracker_index.json").read_text(encoding="utf-8"))
    assert saved["version"] == 2
    assert saved["items"]["note-1"]["tags"] == ["Ops", "DB"]
    reloaded = SecondBrainService(items_provider=_items, folder_provider=lambda: folder)
    assert reloaded.get_item("note-1").tags == ("Ops", "DB")


def test_set_tags_collapses_nfc_and_nfd_duplicates(tmp_path: Path):
    """Precomposed vs combining-character spellings of one word must dedupe."""
    folder = tmp_path / "notes"
    folder.mkdir()
    service = SecondBrainService(items_provider=_items, folder_provider=lambda: folder)

    nfc_cafe = unicodedata.normalize("NFC", "café")
    nfd_cafe = unicodedata.normalize("NFD", "café")
    assert nfc_cafe != nfd_cafe  # sanity: genuinely distinct code point sequences

    updated = service.set_tags("note-1", [nfc_cafe, nfd_cafe])

    assert updated.tags == (nfc_cafe,)


def test_related_breaks_equal_scores_by_title_casefold():
    current = SecondBrainItem(
        id="current",
        title="Current",
        path=Path("/other/current.md"),
        item_type="note",
        tags=("ops",),
    )
    items = [
        current,
        SecondBrainItem(
            id="b-item", title="Bravo", path=Path("/other/b.md"), item_type="note", tags=("OPS",)
        ),
        SecondBrainItem(
            id="a-item", title="alpha", path=Path("/other/a.md"), item_type="note", tags=("Ops",)
        ),
    ]
    service = SecondBrainService(items_provider=lambda: items)

    related = service.related("current")

    assert [row["item"].id for row in related] == ["a-item", "b-item"]
    assert related[0]["reason"] == related[1]["reason"] == "shared_tag"
    assert related[0]["score"] == related[1]["score"]


def test_search_invalid_sort_raises_value_error():
    service = SecondBrainService(items_provider=_items)

    with pytest.raises(ValueError):
        service.search("", sort="bogus")


def test_search_invalid_date_filter_raises_value_error():
    service = SecondBrainService(items_provider=_items)

    with pytest.raises(ValueError):
        service.search("", date_filter="not-a-date")


def test_search_reports_match_reason_filters_then_sorts():
    items = [
        SecondBrainItem(
            id="personal-md",
            title="Alpha Runbook",
            path=Path("/brain/alpha.md"),
            item_type="note",
            # Local noon, converted via .astimezone() the same way production
            # code's _matches_date() does -- keeps the wall-clock date fixed at
            # 2026-01-02 on any host timezone (avoids UTC-day-boundary drift).
            updated_at=datetime(2026, 1, 2, 12, 0, 0).astimezone(),
            excerpt="rollback procedure lives here",
            source="personal",
            open_mode="markdown",
            file_format="md",
            tags=("Operations",),
        ),
        SecondBrainItem(
            id="project-docx",
            title="Release Pack",
            path=Path("/projects/release.docx"),
            item_type="file",
            updated_at=datetime(2026, 2, 3, 9),
            source="project",
            open_mode="docx",
            file_format="docx",
            appcode="PAY",
            year="2026",
            project_name="Payment Upgrade",
            project_state="PROD_READY",
        ),
    ]
    service = SecondBrainService(items_provider=lambda: items)

    assert service.search("alpha")[0].match_reason == "title"
    assert service.search("rollback")[0].match_reason == "content"
    assert service.search("operations")[0].match_reason == "tag"
    assert service.search("payment upgrade")[0].match_reason == "context"
    assert [item.id for item in service.search("", source_filter="project")] == ["project-docx"]
    assert [item.id for item in service.search("", type_filter="markdown")] == ["personal-md"]
    assert [item.id for item in service.search("", date_filter="2026-01-02")] == ["personal-md"]
    assert [item.id for item in service.search("", sort="oldest")] == ["personal-md", "project-docx"]
    assert [item.id for item in service.search("", sort="az")] == ["personal-md", "project-docx"]
    assert [item.id for item in service.search("", sort="type")] == ["project-docx", "personal-md"]


def test_related_ranks_wiki_tag_drone_then_project_deterministically():
    project_path = Path("/projects/Payments")
    items = [
        SecondBrainItem(
            id="current",
            title="Current",
            path=project_path / "DR-1" / "current.md",
            item_type="note",
            excerpt="See [[Wiki.md]]",
            source="project",
            project_path=project_path,
            project_name="Payments",
            drone_name="DR-1",
            tags=("ops",),
        ),
        SecondBrainItem(id="wiki", title="Wiki", path=Path("/other/Wiki.md"), item_type="note"),
        SecondBrainItem(id="tag", title="Tagged", path=Path("/other/tag.md"), item_type="note", tags=("OPS",)),
        SecondBrainItem(
            id="drone",
            title="Drone peer",
            path=project_path / "DR-1" / "peer.md",
            item_type="note",
            source="project",
            project_path=project_path,
            drone_name="DR-1",
        ),
        SecondBrainItem(
            id="project",
            title="Project peer",
            path=project_path / "peer.md",
            item_type="note",
            source="project",
            project_path=project_path,
        ),
        SecondBrainItem(id="other", title="Other", path=Path("/other/nope.md"), item_type="note"),
    ]
    service = SecondBrainService(items_provider=lambda: items)

    related = service.related("current")

    assert [(row["item"].id, row["reason"]) for row in related] == [
        ("wiki", "wiki_link"),
        ("tag", "shared_tag"),
        ("drone", "same_drone"),
        ("project", "same_project"),
    ]
    assert [row["score"] for row in related] == sorted(
        [row["score"] for row in related], reverse=True
    )


def test_switching_personal_override_reloads_correct_sidecar(tmp_path: Path):
    first = tmp_path / "first"
    second = tmp_path / "second"
    first.mkdir()
    second.mkdir()
    (first / ".project_tracker_index.json").write_text(
        json.dumps(
            {"version": 2, "items": {"note-1": {"pinned": True, "favorite": False, "tags": ["first"]}}}
        ),
        encoding="utf-8",
    )
    (second / ".project_tracker_index.json").write_text(
        json.dumps(
            {"version": 2, "items": {"note-1": {"pinned": False, "favorite": True, "tags": ["second"]}}}
        ),
        encoding="utf-8",
    )
    active = [first]
    service = SecondBrainService(items_provider=_items, folder_provider=lambda: active[0])

    first_item = service.get_item("note-1")
    active[0] = second
    second_item = service.get_item("note-1")

    assert first_item is not None and (first_item.pinned, first_item.tags) == (True, ("first",))
    assert second_item is not None and (second_item.favorite, second_item.tags) == (True, ("second",))


def test_public_invalidate_rebuilds_provider_cache():
    source = _items()
    service = SecondBrainService(items_provider=lambda: source)
    assert len(service.list_items()) == 2
    source.append(
        SecondBrainItem(id="note-3", title="New", path=Path("/tmp/new.md"), item_type="note")
    )
    assert len(service.list_items()) == 2

    service.invalidate()

    assert len(service.list_items()) == 3


# ── Task 5: capped recent-activity ledger ───────────────────────────────────


def _activity_cache(tmp_path: Path) -> CacheDb:
    cache = CacheDb(tmp_path / "activity_cache.sqlite3")
    cache.initialize()
    return cache


def test_record_activity_rejects_unsupported_action(tmp_path: Path):
    service = SecondBrainService(items_provider=_items, cache=_activity_cache(tmp_path))

    with pytest.raises(ValueError, match="Unsupported Second Brain activity action"):
        service.record_activity("note-1", "deleted")


def test_record_activity_is_noop_without_cache():
    service = SecondBrainService(items_provider=_items)

    assert service.record_activity("note-1", "opened") is None
    assert service.list_activity() == []


def test_record_activity_returns_none_for_unknown_item(tmp_path: Path):
    service = SecondBrainService(items_provider=_items, cache=_activity_cache(tmp_path))

    assert service.record_activity("missing", "opened") is None


def test_record_activity_persists_and_list_activity_reads_back(tmp_path: Path):
    cache = _activity_cache(tmp_path)
    service = SecondBrainService(items_provider=_items, cache=cache)

    recorded = service.record_activity("note-1", "opened")

    assert recorded is not None
    assert recorded.item_id == "note-1"
    assert recorded.action == "opened"
    assert recorded.title == "Deployment Notes"
    listed = service.list_activity("note-1")
    assert [row.action for row in listed] == ["opened"]


def test_record_activity_dedupes_repeated_opens_for_same_item(tmp_path: Path):
    cache = _activity_cache(tmp_path)
    service = SecondBrainService(items_provider=_items, cache=cache)

    service.record_activity("note-1", "opened")
    service.record_activity("note-2", "opened")
    service.record_activity("note-1", "opened")

    all_rows = service.list_activity()
    assert len(all_rows) == 2
    assert all_rows[0].item_id == "note-1"  # repeated open moved back to newest


def test_list_activity_without_cache_returns_empty():
    service = SecondBrainService(items_provider=_items)

    assert service.list_activity() == []


def test_create_note_records_created_activity(tmp_path: Path):
    folder = tmp_path / "notes"
    folder.mkdir()
    cache = _activity_cache(tmp_path)
    service = SecondBrainService(folder_provider=lambda: folder, cache=cache)

    service.create_note(folder, "todo.md", content="hello")

    rows = cache.list_second_brain_activity()
    assert [row.action for row in rows] == ["created"]
    assert rows[0].title == "todo"


def test_create_note_existing_target_does_not_record_activity(tmp_path: Path):
    folder = tmp_path / "notes"
    folder.mkdir()
    (folder / "todo.md").write_text("existing", encoding="utf-8")
    cache = _activity_cache(tmp_path)
    service = SecondBrainService(folder_provider=lambda: folder, cache=cache)

    with pytest.raises(FileTargetExistsError):
        service.create_note(folder, "todo.md")

    assert cache.list_second_brain_activity() == []


def test_create_folder_records_created_activity(tmp_path: Path):
    folder = tmp_path / "notes"
    folder.mkdir()
    cache = _activity_cache(tmp_path)
    service = SecondBrainService(folder_provider=lambda: folder, cache=cache)

    service.create_folder(folder, "Projects")

    rows = cache.list_second_brain_activity()
    assert [row.action for row in rows] == ["created"]
    assert rows[0].title == "Projects"


def test_create_file_records_created_activity(tmp_path: Path):
    folder = tmp_path / "notes"
    folder.mkdir()
    cache = _activity_cache(tmp_path)
    service = SecondBrainService(folder_provider=lambda: folder, cache=cache)

    service.create_file(folder, "notes.txt")

    rows = cache.list_second_brain_activity()
    assert [row.action for row in rows] == ["created"]


def test_rename_item_records_renamed_activity_under_new_identity(tmp_path: Path):
    folder = tmp_path / "notes"
    folder.mkdir()
    target = folder / "old.md"
    target.write_text("content", encoding="utf-8")
    cache = _activity_cache(tmp_path)
    service = SecondBrainService(folder_provider=lambda: folder, cache=cache)
    original_item = next(item for item in service.list_items() if item.path == target)

    renamed = service.rename_item(target, "new.md")

    rows = cache.list_second_brain_activity()
    assert [row.action for row in rows] == ["renamed"]
    assert rows[0].item_id == renamed.id
    assert rows[0].item_id != original_item.id
    assert rows[0].title == "new"


def test_rename_item_failure_does_not_record_activity(tmp_path: Path):
    folder = tmp_path / "notes"
    folder.mkdir()
    target = folder / "old.md"
    target.write_text("content", encoding="utf-8")
    (folder / "new.md").write_text("dup", encoding="utf-8")
    cache = _activity_cache(tmp_path)
    service = SecondBrainService(folder_provider=lambda: folder, cache=cache)

    with pytest.raises(FileTargetExistsError):
        service.rename_item(target, "new.md")

    assert cache.list_second_brain_activity() == []


def test_recycle_item_records_recycled_activity(tmp_path: Path, monkeypatch):
    import os

    import send2trash

    monkeypatch.setattr(send2trash, "send2trash", lambda path: os.remove(path))
    folder = tmp_path / "notes"
    folder.mkdir()
    target = folder / "gone.md"
    target.write_text("content", encoding="utf-8")
    cache = _activity_cache(tmp_path)
    service = SecondBrainService(folder_provider=lambda: folder, cache=cache)

    service.recycle_item(target)

    rows = cache.list_second_brain_activity()
    assert [row.action for row in rows] == ["recycled"]
    assert rows[0].title == "gone"


def test_recycle_item_rejects_project_item_without_recording_activity(tmp_path: Path):
    project_item = SecondBrainItem(
        id="proj-1",
        title="Proj file",
        path=tmp_path / "proj.md",
        item_type="note",
        source="project",
    )
    folder = tmp_path / "notes"
    folder.mkdir()
    cache = _activity_cache(tmp_path)
    service = SecondBrainService(
        items_provider=lambda: [project_item], folder_provider=lambda: folder, cache=cache
    )

    with pytest.raises(ValueError, match="Only Personal items can be recycled"):
        service.recycle_item(project_item.path)

    assert cache.list_second_brain_activity() == []


def test_create_note_survives_activity_lookup_failure(tmp_path: Path, monkeypatch):
    """record_activity's internal get_item lookup must be inside the best-effort
    try, not just the cache append — else a lookup failure would surface as a
    create_note failure even though the file already landed on disk."""
    folder = tmp_path / "notes"
    folder.mkdir()
    cache = _activity_cache(tmp_path)
    service = SecondBrainService(folder_provider=lambda: folder, cache=cache)

    def _raise(_item_id: str):
        raise RuntimeError("boom")

    monkeypatch.setattr(service, "get_item", _raise)

    target = service.create_note(folder, "todo.md", content="hello")

    assert target.exists()
    assert cache.list_second_brain_activity() == []


def test_create_note_survives_created_lookup_failure(tmp_path: Path, monkeypatch):
    """_record_created's own _find_by_path lookup must be best-effort too —
    else a lookup failure there would surface as a create_note failure even
    though the file already landed on disk."""
    folder = tmp_path / "notes"
    folder.mkdir()
    cache = _activity_cache(tmp_path)
    service = SecondBrainService(folder_provider=lambda: folder, cache=cache)

    def _raise(_target: Path):
        raise RuntimeError("boom")

    monkeypatch.setattr(service, "_find_by_path", _raise)

    target = service.create_note(folder, "todo.md", content="hello")

    assert target.exists()
    assert cache.list_second_brain_activity() == []


def test_mark_saved_records_edited_activity(tmp_path: Path):
    folder = tmp_path / "notes"
    folder.mkdir()
    target = folder / "note.md"
    target.write_text("content", encoding="utf-8")
    cache = _activity_cache(tmp_path)
    service = SecondBrainService(folder_provider=lambda: folder, cache=cache)
    service.list_items()  # warm index before save

    service.mark_saved(target)

    rows = cache.list_second_brain_activity()
    assert [row.action for row in rows] == ["edited"]
    assert rows[0].title == "note"
