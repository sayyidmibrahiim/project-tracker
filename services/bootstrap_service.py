"""Root folder bootstrap: create default root or migrate existing data."""
from __future__ import annotations

import copy
from pathlib import Path

from core.models import AppSettings

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


def rewrite_settings_paths(settings: AppSettings, old_root: Path, new_root: Path) -> AppSettings:
    """Return a deep copy of *settings* with all in-root paths relocated."""
    result = copy.deepcopy(settings)
    result.root_folder = rewrite_path(settings.root_folder, old_root, new_root)
    result.second_brain_folder = rewrite_path(settings.second_brain_folder, old_root, new_root)
    result.file_template_folder = rewrite_path(settings.file_template_folder, old_root, new_root)
    if result.email is not None:
        result.email.template_folder_path = rewrite_path(
            settings.email.template_folder_path, old_root, new_root
        )
    if result.teams is not None and result.teams.automations:
        rewritten = []
        for auto in result.teams.automations:
            auto.attachment_paths = [
                rewrite_path(p, old_root, new_root)
                for p in auto.attachment_paths
            ]
            rewritten.append(auto)
        result.teams.automations = rewritten
    return result
