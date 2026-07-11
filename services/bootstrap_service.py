"""Root folder bootstrap: create default root or migrate existing data."""
from __future__ import annotations

import copy
import json
import logging
import shutil
from dataclasses import dataclass
from pathlib import Path

from core.models import AppCodeConfig, AppSettings
from infrastructure.cache_db import CacheDb
from infrastructure.settings_store import SettingsStore

DEFAULT_ROOT_NAME = "Project Tracker"

logger = logging.getLogger(__name__)


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


@dataclass(frozen=True, slots=True)
class BootstrapResult:
    action: str  # "created" | "none" | "migrated" | "created_orphan" | "failed"
    old: Path | None = None
    new: Path | None = None
    error: str | None = None


def bootstrap_root(
    settings_store: SettingsStore,
    cache_db: CacheDb,
    scanner: object,
) -> BootstrapResult:
    """Ensure root_folder is at the default path, migrating if needed.

    Called from app_web.run() before webview.start().
    """
    target = default_root()
    settings = settings_store.read()
    current = settings.root_folder

    # Case 1: no root set — create default.
    if current is None:
        target.mkdir(parents=True, exist_ok=True)
        settings.root_folder = target
        settings_store.write(settings)
        return BootstrapResult(action="created", new=target)

    current_resolved = current.resolve()
    target_resolved = target.resolve()

    # Case 2: already at default — nothing to do.
    if current_resolved == target_resolved:
        return BootstrapResult(action="none", new=target)

    # Case 3: old root missing — create empty default, clear cache.
    if not current.exists():
        target.mkdir(parents=True, exist_ok=True)
        settings.root_folder = target
        settings_store.write(settings)
        with cache_db._connect() as conn:
            conn.execute("DELETE FROM project_index")
            conn.execute("DELETE FROM drone_tickets")
            conn.execute("DELETE FROM scan_warnings")
            conn.execute("DELETE FROM notifications")
            conn.execute("DELETE FROM approval_polling_jobs")
        return BootstrapResult(action="created_orphan", old=current, new=target)

    # Case 4: migrate old root to default.
    try:
        if not target.exists():
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(current), str(target))
            new_root = target
        else:
            for item in current.iterdir():
                shutil.move(str(item), str(target / item.name))
            current.rmdir()
            new_root = target
    except (OSError, shutil.Error) as exc:
        logger.error("Root migration failed, keeping old root: %s", exc)
        return BootstrapResult(action="failed", old=current, new=current, error=str(exc))

    settings = rewrite_settings_paths(settings, current, new_root)
    rewrite_appcode_configs(new_root, current)
    migrate_cache(cache_db, current, new_root)

    try:
        for appcode_child in sorted(new_root.iterdir()):
            if not appcode_child.is_dir():
                continue
            for year_child in sorted(appcode_child.iterdir()):
                if year_child.is_dir() and year_child.name.isdigit():
                    scanner.rebuild_year(year_child)
    except Exception:  # noqa: BLE001 — scan failure must not block startup
        logger.warning("Cache rescan after migration failed; cache will rebuild on next access")

    settings.root_folder = new_root
    settings_store.write(settings)
    return BootstrapResult(action="migrated", old=current, new=new_root)
