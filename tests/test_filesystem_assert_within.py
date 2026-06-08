"""Unit tests for the ``assert_within`` Temp_Root containment guard."""

from __future__ import annotations

from pathlib import Path

import pytest

from project_tracker.core.exceptions import PathOutsideBaseError
from project_tracker.infrastructure import filesystem


def test_target_strictly_within_base_is_returned_verbatim(tmp_path: Path) -> None:
    target = tmp_path / "child" / "grandchild"
    result = filesystem.assert_within(tmp_path, target)
    # Returned verbatim (not resolved) so path strings are preserved.
    assert result == target


def test_base_itself_is_rejected_as_not_strictly_within(tmp_path: Path) -> None:
    with pytest.raises(PathOutsideBaseError):
        filesystem.assert_within(tmp_path, tmp_path)


def test_parent_traversal_escape_is_rejected(tmp_path: Path) -> None:
    base = tmp_path / "root"
    base.mkdir()
    escape = base / ".." / "outside"
    with pytest.raises(PathOutsideBaseError):
        filesystem.assert_within(base, escape)


def test_sibling_path_outside_base_is_rejected(tmp_path: Path) -> None:
    base = tmp_path / "root"
    base.mkdir()
    sibling = tmp_path / "other" / "file.txt"
    with pytest.raises(PathOutsideBaseError):
        filesystem.assert_within(base, sibling)


def test_create_directory_within_base_succeeds(tmp_path: Path) -> None:
    target = tmp_path / "a" / "b"
    result = filesystem.create_directory(tmp_path, target)
    assert result == target
    assert target.is_dir()


def test_create_directory_outside_base_is_rejected(tmp_path: Path) -> None:
    base = tmp_path / "root"
    base.mkdir()
    outside = tmp_path / "elsewhere"
    with pytest.raises(PathOutsideBaseError):
        filesystem.create_directory(base, outside)
    assert not outside.exists()


def test_move_path_outside_base_leaves_source_unchanged(tmp_path: Path) -> None:
    base = tmp_path / "root"
    base.mkdir()
    source = base / "f.txt"
    source.write_text("data", encoding="utf-8")
    destination = tmp_path / "outside.txt"
    with pytest.raises(PathOutsideBaseError):
        filesystem.move_path(base, source, destination)
    assert source.read_text(encoding="utf-8") == "data"
    assert not destination.exists()


def test_rename_path_within_base_succeeds(tmp_path: Path) -> None:
    base = tmp_path / "root"
    base.mkdir()
    source = base / "old.txt"
    source.write_text("x", encoding="utf-8")
    destination = base / "new.txt"
    result = filesystem.rename_path(base, source, destination)
    assert result == destination
    assert destination.read_text(encoding="utf-8") == "x"
    assert not source.exists()


def test_send_to_recycle_bin_outside_base_is_rejected_before_deletion(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    base = tmp_path / "root"
    base.mkdir()
    outside = tmp_path / "keep.txt"
    outside.write_text("safe", encoding="utf-8")

    called: list[str] = []

    import send2trash

    monkeypatch.setattr(send2trash, "send2trash", lambda p: called.append(p))

    with pytest.raises(PathOutsideBaseError):
        filesystem.send_to_recycle_bin(outside, base=base)

    assert called == []
    assert outside.read_text(encoding="utf-8") == "safe"
