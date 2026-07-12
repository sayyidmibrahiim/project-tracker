"""Task 13.4 — SecondBrainService note CRUD unit tests.

Covers (all against ``tmp_path`` only, ``send2trash`` monkeypatched):

- ``create_note`` rejects an existing name without overwriting it (Req 13.5).
- ``write_note`` retains the original file content on an induced failure
  (atomic temp-then-replace preservation, Req 13.6/13.8).
- ``delete_note`` routes deletion through ``send2trash`` (Req 13.7 routing) and
  rejects targets outside the Second Brain folder.
- The search/list index reflects create/edit/delete on the next read because
  ``_invalidate`` drops the cached index (Req 13.9).
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from core.exceptions import (
    FileTargetExistsError,
    PathOutsideBaseError,
)
from services import second_brain_service as sbs_module
from services.second_brain_service import (
    SecondBrainItem,
    SecondBrainService,
)


def _folder_scanning_service(folder: Path) -> SecondBrainService:
    """Build a service whose items_provider re-scans ``folder`` on each call.

    Because ``create``/``write``/``delete`` call ``_invalidate``, the next
    ``list_items``/``search`` re-invokes this provider and therefore reflects
    the current set of notes and their content (Req 13.9).
    """

    def items_provider() -> list[SecondBrainItem]:
        items: list[SecondBrainItem] = []
        for path in sorted(folder.rglob("*.md")):
            if not path.is_file():
                continue
            items.append(
                SecondBrainItem(
                    id=str(path),
                    title=path.stem,
                    path=path,
                    item_type="note",
                    excerpt=path.read_text(encoding="utf-8"),
                )
            )
        return items

    return SecondBrainService(
        items_provider=items_provider,
        folder_provider=lambda: folder,
    )


# ── create_note existing-name rejection (Req 13.5) ──────────────────────


def test_create_note_rejects_existing_name_without_overwrite(tmp_path):
    service = SecondBrainService(folder_provider=lambda: tmp_path)
    existing = tmp_path / "note.md"
    existing.write_text("original body", encoding="utf-8")

    with pytest.raises(FileTargetExistsError):
        service.create_note(tmp_path, "note.md", content="new body")

    # The existing file is left untouched (no overwrite).
    assert existing.read_text(encoding="utf-8") == "original body"


def test_create_note_writes_new_file_within_folder(tmp_path):
    service = SecondBrainService(folder_provider=lambda: tmp_path)

    target = service.create_note(tmp_path, "fresh.md", content="hello")

    assert target == tmp_path / "fresh.md"
    assert target.read_text(encoding="utf-8") == "hello"


# ── write_note atomic preservation on failure (Req 13.6 / 13.8) ─────────


def test_write_note_retains_original_content_on_failure(tmp_path, monkeypatch):
    service = SecondBrainService(folder_provider=lambda: tmp_path)
    target = tmp_path / "note.md"
    target.write_text("original content", encoding="utf-8")

    def boom(*_args, **_kwargs):
        raise OSError("induced replace failure")

    # Fail the atomic replace step so the write cannot complete.
    monkeypatch.setattr(sbs_module.os, "replace", boom)

    with pytest.raises(OSError, match="induced replace failure"):
        service.write_note(target, "updated content")

    # The original file content is retained unchanged.
    assert target.read_text(encoding="utf-8") == "original content"
    # No partial temp file is left behind in the folder.
    leftover = list(tmp_path.glob("*.tmp"))
    assert leftover == []


def test_write_note_persists_full_content_on_success(tmp_path):
    service = SecondBrainService(folder_provider=lambda: tmp_path)
    target = tmp_path / "note.md"
    target.write_text("old", encoding="utf-8")

    result = service.write_note(target, "brand new content")

    assert result == target
    assert target.read_text(encoding="utf-8") == "brand new content"


def test_write_note_rejects_target_outside_folder(tmp_path):
    service = SecondBrainService(folder_provider=lambda: tmp_path)
    outside = tmp_path.parent / "outside.md"

    with pytest.raises(PathOutsideBaseError):
        service.write_note(outside, "content")

    assert not outside.exists()


# ── delete_note routes through send2trash (Req 13.7 routing) ────────────


def test_delete_note_routes_through_send2trash(tmp_path, monkeypatch):
    import send2trash

    captured: list[str] = []
    monkeypatch.setattr(send2trash, "send2trash", lambda path: captured.append(path))

    service = SecondBrainService(folder_provider=lambda: tmp_path)
    target = tmp_path / "note.md"
    target.write_text("body", encoding="utf-8")

    service.delete_note(target)

    # Deletion was routed through send2trash (not a real unlink), so the file
    # still exists in tmp_path and the Recycle Bin was never really touched.
    assert captured == [str(target)]
    assert target.exists()


def test_delete_note_rejects_target_outside_folder(tmp_path, monkeypatch):
    import send2trash

    captured: list[str] = []
    monkeypatch.setattr(send2trash, "send2trash", lambda path: captured.append(path))

    service = SecondBrainService(folder_provider=lambda: tmp_path)
    outside = tmp_path.parent / "outside.md"

    with pytest.raises(PathOutsideBaseError):
        service.delete_note(outside)

    assert captured == []


# ── index update on create/edit/delete (Req 13.9) ───────────────────────


def test_index_reflects_create_on_next_read(tmp_path):
    service = _folder_scanning_service(tmp_path)

    assert service.list_items() == []

    service.create_note(tmp_path, "alpha.md", content="alpha body")

    titles = [item.title for item in service.list_items()]
    assert titles == ["alpha"]


def test_index_reflects_edit_on_next_read(tmp_path):
    service = _folder_scanning_service(tmp_path)
    target = service.create_note(tmp_path, "beta.md", content="first")

    # Prime the cache with the original content.
    assert service.list_items()[0].excerpt == "first"

    service.write_note(target, "second")

    # The next read reflects the edited content (index was invalidated).
    assert service.list_items()[0].excerpt == "second"


def test_index_reflects_delete_on_next_read(tmp_path, monkeypatch):
    import send2trash

    # Route delete through send2trash but actually remove the file so the
    # re-scan reflects the removal in tmp_path.
    monkeypatch.setattr(send2trash, "send2trash", lambda path: os.remove(path))

    service = _folder_scanning_service(tmp_path)
    target = service.create_note(tmp_path, "gamma.md", content="gamma body")

    assert [item.title for item in service.list_items()] == ["gamma"]

    service.delete_note(target)

    assert service.list_items() == []


# ── Task 4: rename_item / recycle_item Personal-only guard ──────────────


def _fake_project_item(path: Path) -> SecondBrainItem:
    return SecondBrainItem(
        id="proj-1",
        title=path.stem,
        path=path,
        item_type="note",
        source="project",
        relative_path="doc.md",
        tree_path="APPCODE/2026/CR/UAT_PREPARE/Proj/doc.md",
    )


def test_rename_item_rejects_project_source(tmp_path):
    fake_path = tmp_path / "project" / "doc.md"
    service = SecondBrainService(
        items_provider=lambda: [_fake_project_item(fake_path)],
        folder_provider=lambda: tmp_path,
    )

    with pytest.raises(ValueError, match="Personal"):
        service.rename_item(fake_path, "renamed.md")


def test_recycle_item_rejects_project_source(tmp_path, monkeypatch):
    import send2trash

    captured: list[str] = []
    monkeypatch.setattr(send2trash, "send2trash", lambda path: captured.append(path))

    fake_path = tmp_path / "project" / "doc.md"
    service = SecondBrainService(
        items_provider=lambda: [_fake_project_item(fake_path)],
        folder_provider=lambda: tmp_path,
    )

    with pytest.raises(ValueError, match="Personal"):
        service.recycle_item(fake_path)

    # Guard fires before any recycle-bin call.
    assert captured == []


def test_rename_item_missing_path_raises_key_error(tmp_path):
    service = SecondBrainService(folder_provider=lambda: tmp_path)
    missing = tmp_path / "ghost.md"

    with pytest.raises(KeyError):
        service.rename_item(missing, "new.md")


# ── Task 4: rename_item real-folder behavior (guards + metadata transfer) ─


def test_rename_item_renames_personal_note_and_keeps_own_flags(tmp_path):
    service = SecondBrainService(folder_provider=lambda: tmp_path)
    note = tmp_path / "alpha.md"
    note.write_text("alpha body", encoding="utf-8")

    original = next(item for item in service.list_items() if item.title == "alpha")
    service.favorite_item(original.id)

    renamed = service.rename_item(note, "beta.md")

    assert renamed.path == tmp_path / "beta.md"
    assert renamed.favorite is True
    assert not note.exists()
    assert (tmp_path / "beta.md").is_file()


def test_rename_item_folder_transfers_descendant_pin_favorite_tags(tmp_path):
    service = SecondBrainService(folder_provider=lambda: tmp_path)
    folder = tmp_path / "ideas"
    folder.mkdir()
    child = folder / "child.md"
    child.write_text("child body", encoding="utf-8")

    original_child = next(item for item in service.list_items() if item.title == "child")
    service.pin_item(original_child.id)
    service.set_tags(original_child.id, ["roadmap"])

    service.rename_item(folder, "notions")

    moved_child = next(
        item for item in service.list_items() if item.path == tmp_path / "notions" / "child.md"
    )
    assert moved_child.pinned is True
    assert moved_child.tags == ("roadmap",)
    assert not folder.exists()


def test_rename_item_rejects_reserved_windows_name(tmp_path):
    service = SecondBrainService(folder_provider=lambda: tmp_path)
    note = tmp_path / "alpha.md"
    note.write_text("body", encoding="utf-8")

    with pytest.raises(Exception):
        service.rename_item(note, "CON.md")
    assert note.exists()


def test_rename_item_rejects_duplicate_target(tmp_path):
    service = SecondBrainService(folder_provider=lambda: tmp_path)
    note = tmp_path / "alpha.md"
    note.write_text("body", encoding="utf-8")
    other = tmp_path / "beta.md"
    other.write_text("other body", encoding="utf-8")

    with pytest.raises(Exception):
        service.rename_item(note, "beta.md")
    assert note.exists()
    assert other.read_text(encoding="utf-8") == "other body"


def test_rename_item_rejects_traversal_via_separator(tmp_path):
    service = SecondBrainService(folder_provider=lambda: tmp_path)
    note = tmp_path / "alpha.md"
    note.write_text("body", encoding="utf-8")

    with pytest.raises(Exception):
        service.rename_item(note, "../escape.md")
    assert note.exists()


# ── Task 4: recycle_item real-folder behavior (Personal-only, cleanup) ───


def test_recycle_item_sends_personal_note_via_send2trash_and_drops_flags(tmp_path, monkeypatch):
    import send2trash

    captured: list[str] = []
    monkeypatch.setattr(send2trash, "send2trash", lambda path: captured.append(path))

    service = SecondBrainService(folder_provider=lambda: tmp_path)
    note = tmp_path / "alpha.md"
    note.write_text("body", encoding="utf-8")

    original = next(item for item in service.list_items() if item.title == "alpha")
    service.favorite_item(original.id)

    service.recycle_item(note)

    assert captured == [str(note)]
    # send2trash was faked, so the file remains, but its persisted flags are gone.
    reloaded = next(item for item in service.list_items() if item.title == "alpha")
    assert reloaded.favorite is False


def test_recycle_item_folder_drops_descendant_persisted_flags(tmp_path, monkeypatch):
    import send2trash

    monkeypatch.setattr(send2trash, "send2trash", lambda path: os.remove(path) if Path(path).is_file() else None)

    service = SecondBrainService(folder_provider=lambda: tmp_path)
    folder = tmp_path / "ideas"
    folder.mkdir()
    child = folder / "child.md"
    child.write_text("child body", encoding="utf-8")

    original_child = next(item for item in service.list_items() if item.title == "child")
    service.pin_item(original_child.id)

    service.recycle_item(folder)

    assert original_child.id not in service._persisted


# ── Fix Round 1: sidecar persist failure must not undo the physical action ──


def test_rename_item_survives_metadata_persist_failure(tmp_path, monkeypatch):
    service = SecondBrainService(folder_provider=lambda: tmp_path)
    folder = tmp_path / "ideas"
    folder.mkdir()
    child = folder / "child.md"
    child.write_text("child body", encoding="utf-8")

    original_child = next(item for item in service.list_items() if item.title == "child")
    service.pin_item(original_child.id)
    service.set_tags(original_child.id, ["roadmap"])

    def boom(*_args, **_kwargs):
        raise OSError("induced sidecar write failure")

    # Fail only the sidecar write, after the physical rename has to happen.
    monkeypatch.setattr(sbs_module, "atomic_write_json", boom)

    renamed = service.rename_item(folder, "notions")

    # Physical rename succeeded on disk despite the sidecar write failing.
    assert not folder.exists()
    assert (tmp_path / "notions" / "child.md").is_file()
    assert renamed.path == tmp_path / "notions"

    # Cache was invalidated: the next read reflects the renamed path, not
    # the stale pre-rename state.
    moved_child = next(
        item for item in service.list_items() if item.path == tmp_path / "notions" / "child.md"
    )
    assert moved_child.title == "child"


def test_recycle_item_survives_metadata_persist_failure(tmp_path, monkeypatch):
    import send2trash

    monkeypatch.setattr(send2trash, "send2trash", lambda path: os.remove(path))

    service = SecondBrainService(folder_provider=lambda: tmp_path)
    note = tmp_path / "alpha.md"
    note.write_text("body", encoding="utf-8")

    original = next(item for item in service.list_items() if item.title == "alpha")
    service.favorite_item(original.id)

    def boom(*_args, **_kwargs):
        raise OSError("induced sidecar write failure")

    monkeypatch.setattr(sbs_module, "atomic_write_json", boom)

    service.recycle_item(note)

    # Physical recycle succeeded on disk despite the sidecar write failing.
    assert not note.exists()

    # Cache was invalidated: the recycled item no longer appears in the index.
    assert [item for item in service.list_items() if item.title == "alpha"] == []


# ── Task 4: read_image (index/type guarded) ──────────────────────────────


def test_read_image_returns_data_uri_for_indexed_image_item(tmp_path):
    service = SecondBrainService(folder_provider=lambda: tmp_path)
    image = tmp_path / "diagram.png"
    image.write_bytes(b"\x89PNG\r\n\x1a\nfake-bytes")

    result = service.read_image(image)

    assert result["data_uri"].startswith("data:image/png;base64,")
    assert result["name"] == "diagram.png"


def test_read_image_rejects_non_image_item(tmp_path):
    service = SecondBrainService(folder_provider=lambda: tmp_path)
    note = tmp_path / "alpha.md"
    note.write_text("body", encoding="utf-8")

    with pytest.raises(ValueError):
        service.read_image(note)


def test_read_image_rejects_path_not_in_index(tmp_path):
    service = SecondBrainService(folder_provider=lambda: tmp_path)
    outside = tmp_path.parent / "outside.png"
    outside.write_bytes(b"not-indexed")

    with pytest.raises(ValueError):
        service.read_image(outside)


# ── Task 4: mark_saved (invalidate + reload full-content search) ────────


def test_mark_saved_replaces_stale_search_content(tmp_path):
    # Query only the CONTENT keyword (never the filename/title) so a match
    # can only come from the indexed excerpt/full-text, not the title/path
    # match_reason shortcuts.
    service = SecondBrainService(folder_provider=lambda: tmp_path)
    note = tmp_path / "note.md"
    note.write_text("original-token body", encoding="utf-8")

    assert [item.title for item in service.search("original-token")] == ["note"]

    # Simulate a shared RTE autosave: content changes on disk directly,
    # bypassing SecondBrainService's own write path entirely.
    note.write_text("zzz-unique-token body", encoding="utf-8")

    # Stale cache still reports the pre-save content until mark_saved runs.
    assert [item.title for item in service.search("original-token")] == ["note"]

    service.mark_saved(note)

    assert service.search("original-token") == []
    assert [item.title for item in service.search("zzz-unique-token")] == ["note"]


# ── Task 4: use_default_folder (create-before-persist) ───────────────────


def test_use_default_folder_creates_and_persists_correct_path(tmp_path):
    root = tmp_path / "root"
    persisted: list[Path] = []
    created_before_setter: list[bool] = []

    def folder_setter(path: Path) -> None:
        created_before_setter.append(path.is_dir())
        persisted.append(path)

    service = SecondBrainService(root_provider=lambda: root, folder_setter=folder_setter)

    result = service.use_default_folder()

    assert result == root / "Second Brain"
    assert result.is_dir()
    assert persisted == [root / "Second Brain"]
    assert created_before_setter == [True]


def test_use_default_folder_requires_root(tmp_path):
    service = SecondBrainService(root_provider=lambda: None)

    with pytest.raises(RuntimeError):
        service.use_default_folder()


# ── Task 4: refresh (force reindex) ──────────────────────────────────────


def test_refresh_reflects_externally_added_file(tmp_path):
    service = SecondBrainService(folder_provider=lambda: tmp_path)
    assert service.list_items() == []

    # File appears on disk without going through the service (e.g. OS-level
    # copy); the cached index would not normally notice until invalidated.
    (tmp_path / "external.md").write_text("added externally", encoding="utf-8")

    result = service.refresh()

    assert [item.title for item in service.list_items()] == ["external"]
    assert [item.title for item in result["items"]] == ["external"]
