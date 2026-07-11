"""Root folder bootstrap: create default root or migrate existing data."""
from __future__ import annotations

import copy
import json
from pathlib import Path

from core.models import AppCodeConfig, AppSettings
from infrastructure.cache_db import CacheDb

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


def rewrite_appcode_configs(new_root: Path, old_root: Path) -> int:
    """Walk {new_root}/*/appcode.json, rewrite cicd_shared_path if inside old_root.

    Returns the number of configs modified.
    """
    if not new_root.is_dir():
        return 0
    modified = 0
    for child in sorted(new_root.iterdir()):
        if not child.is_dir():
            continue
        config_path = child / "appcode.json"
        if not config_path.is_file():
            continue
        try:
            data = json.loads(config_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            continue
        config = AppCodeConfig.from_dict(data)
        if config.cicd_shared_path is None:
            continue
        rewritten = rewrite_path(config.cicd_shared_path, old_root, new_root)
        if rewritten != config.cicd_shared_path:
            config.cicd_shared_path = rewritten
            config_path.write_text(
                json.dumps(config.to_dict(), indent=2), encoding="utf-8"
            )
            modified += 1
    return modified


def migrate_cache(cache_db: CacheDb, old_root: Path, new_root: Path) -> None:
    """Rewrite non-rebuildable path columns + delete rebuildable rows.

    Non-rebuildable (preserve user state): notifications, approval_polling_jobs.
    Rebuildable (will be rescanned): project_index, drone_tickets, scan_warnings.
    """
    old_prefix = str(old_root)
    new_prefix = str(new_root)
    with cache_db._connect() as connection:
        connection.execute(
            "UPDATE notifications SET project_path = REPLACE(project_path, ?, ?) "
            "WHERE project_path LIKE ?",
            (old_prefix, new_prefix, old_prefix + "%"),
        )
        connection.execute(
            "UPDATE approval_polling_jobs SET project_path = REPLACE(project_path, ?, ?) "
            "WHERE project_path LIKE ?",
            (old_prefix, new_prefix, old_prefix + "%"),
        )
        connection.execute("DELETE FROM project_index")
        connection.execute("DELETE FROM drone_tickets")
        connection.execute("DELETE FROM scan_warnings")
