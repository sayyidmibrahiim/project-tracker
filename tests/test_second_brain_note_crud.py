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

from project_tracker.core.exceptions import (
    FileTargetExistsError,
    PathOutsideBaseError,
)
from project_tracker.services import second_brain_service as sbs_module
from project_tracker.services.second_brain_service import (
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
