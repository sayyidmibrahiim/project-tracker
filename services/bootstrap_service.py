"""Root folder bootstrap: create default root or migrate existing data."""
from __future__ import annotations

from pathlib import Path

DEFAULT_ROOT_NAME = "Project Tracker"


def default_root() -> Path:
    """The canonical data root: ~/Documents/Project Tracker."""
    return Path.home() / "Documents" / DEFAULT_ROOT_NAME


def rewrite_path(path: Path | None, old_root: Path, new_root: Path) -> Path | None:
    """Rewrite *path* if it lives inside *old_root* to point inside *new_root*.

    Paths outside *old_root* are returned unchanged. ``None`` stays ``None``.
    """
    if path is None:
        return None
    try:
        if path.is_relative_to(old_root):
            return new_root / path.relative_to(old_root)
    except ValueError:
        pass
    return path
