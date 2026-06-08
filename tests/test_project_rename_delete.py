"""Task 7.4 — Unit tests for project rename / delete + subproject delete.

These tests exercise the wired ``JsApi`` (via ``create_js_api``) and the
``ProjectService``/``SafeDeleteService`` route, entirely against ``tmp_path``.

Covered behaviour (Req 5.2, 5.3, 5.5, 5.8):
- invalid Windows folder-name rejection on rename (folder unchanged)
- case-insensitive sibling-duplicate rejection on rename (folder unchanged)
- locked-state rejection for rename/delete in PROD_READY and IMPLEMENTED
  (folder unchanged, no cache update)
- ``send2trash`` failure on delete / subproject-delete preserves the folder,
  returns ``ok=false`` and skips the cache update
- cache update on a successful rename and a successful delete

All deletion is routed through a monkeypatched ``SafeDeleteService`` so no real
Recycle Bin / ``send2trash`` is ever used.
"""

from __future__ import annotations

import shutil
from dataclasses import replace
from pathlib import Path

import pytest

from project_tracker.core.models import ProjectMetadata, local_now
from project_tracker.infrastructure.cache_db import CacheDb
from project_tracker.infrastructure.metadata_store import MetadataStore
from project_tracker.infrastructure.settings_store import SettingsStore
from project_tracker.services.safe_delete_service import SafeDeleteService


# ── helpers / fixtures ────────────────────────────────────────────────────


def _make_project(root: Path, state: str, name: str, store: MetadataStore, year: str = "2025") -> Path:
    """Create a project folder + metadata under ``root/year/state/name``."""
    project_dir = root / year / state / name
    project_dir.mkdir(parents=True)
    now = local_now()
    store.write(project_dir, ProjectMetadata(project_name=name, created_at=now, updated_at=now))
    return project_dir


@pytest.fixture
def env(tmp_path):
    """Configured root + isolated cache db + wired JsApi, all under tmp_path."""
    from project_tracker import app_web

    root = tmp_path / "root"
    root.mkdir()

    settings = SettingsStore(config_dir=tmp_path / "config")
    settings.write(replace(settings.read(), root_folder=root))

    db_path = tmp_path / "cache.db"
    store = MetadataStore()
    js_api = app_web.create_js_api(db_path=db_path, settings_store=settings)

    return {
        "root": root,
        "db_path": db_path,
        "store": store,
        "js_api": js_api,
    }


def _cache_names(db_path: Path, year: str = "2025") -> list[str]:
    """Read project names currently in the cache for a year."""
    cache = CacheDb(db_path)
    cache.initialize()
    return [row.project_name for row in cache.list_projects(year)]


# ── rename: invalid / duplicate name rejection (Req 5.2) ───────────────────


def test_rename_invalid_name_rejected_folder_unchanged(env):
    project = _make_project(env["root"], "UAT_PREPARE", "my-project", env["store"])

    result = env["js_api"].project_rename(str(project), "bad:name?")

    assert result["ok"] is False
    assert result["error"]["code"] == "PROJECT_RENAME_FAILED"
    assert project.is_dir()  # original folder unchanged


def test_rename_duplicate_sibling_rejected_case_insensitive(env):
    project = _make_project(env["root"], "UAT_PREPARE", "my-project", env["store"])
    sibling = _make_project(env["root"], "UAT_PREPARE", "other", env["store"])

    # Rename to a case-variant of the existing sibling name.
    result = env["js_api"].project_rename(str(project), "OTHER")

    assert result["ok"] is False
    assert result["error"]["code"] == "PROJECT_RENAME_FAILED"
    assert project.is_dir()  # original unchanged
    assert sibling.is_dir()  # sibling unchanged


# ── rename: locked-state rejection (Req 5.3) ───────────────────────────────


@pytest.mark.parametrize("state", ["PROD_READY", "IMPLEMENTED"])
def test_rename_rejected_when_locked(env, state):
    project = _make_project(env["root"], state, "locked-project", env["store"])

    result = env["js_api"].project_rename(str(project), "new-name")

    assert result["ok"] is False
    assert result["error"]["code"] == "PROJECT_RENAME_FAILED"
    assert state.lower() in result["error"]["message"].lower()
    assert project.is_dir()  # folder unchanged
    assert not (env["root"] / "2025" / state / "new-name").exists()


# ── delete: locked-state rejection (Req 5.5) ───────────────────────────────


@pytest.mark.parametrize("state", ["PROD_READY", "IMPLEMENTED"])
def test_delete_rejected_when_locked(env, state, monkeypatch):
    # Guard should reject before any deletion route is reached.
    def _boom(self, path):  # pragma: no cover - must never be called
        raise AssertionError("delete_to_trash must not be called for a locked project")

    monkeypatch.setattr(SafeDeleteService, "delete_to_trash", _boom)
    project = _make_project(env["root"], state, "locked-project", env["store"])

    result = env["js_api"].project_delete(str(project))

    assert result["ok"] is False
    assert result["error"]["code"] == "PROJECT_DELETE_FAILED"
    assert state.lower() in result["error"]["message"].lower()
    assert project.is_dir()  # folder unchanged


# ── delete: send2trash failure preserves folder + skips cache (Req 5.8) ────


def test_delete_send2trash_failure_preserves_folder_and_cache(env, monkeypatch):
    project = _make_project(env["root"], "UAT_PREPARE", "doomed", env["store"])

    # Seed the cache so we can prove a failed delete does NOT update it.
    seed = env["js_api"].project_rename(str(project), "doomed")  # no-op rename rebuilds cache
    assert seed["ok"] is True
    assert "doomed" in _cache_names(env["db_path"])

    def _raise(self, path):
        raise RuntimeError("send2trash unavailable")

    monkeypatch.setattr(SafeDeleteService, "delete_to_trash", _raise)

    result = env["js_api"].project_delete(str(project))

    assert result["ok"] is False
    assert result["error"]["code"] == "PROJECT_DELETE_FAILED"
    assert project.is_dir()  # folder preserved in place
    assert "doomed" in _cache_names(env["db_path"])  # cache update skipped


# ── delete: cache update on success (Req 5.8) ──────────────────────────────


def test_delete_success_updates_cache(env, tmp_path, monkeypatch):
    project = _make_project(env["root"], "UAT_PREPARE", "to-delete", env["store"])

    seed = env["js_api"].project_rename(str(project), "to-delete")  # seed cache
    assert seed["ok"] is True
    assert "to-delete" in _cache_names(env["db_path"])

    trash = tmp_path / "trash"
    trash.mkdir()

    def _fake_trash(self, path):
        shutil.move(str(path), str(trash / Path(path).name))

    monkeypatch.setattr(SafeDeleteService, "delete_to_trash", _fake_trash)

    result = env["js_api"].project_delete(str(project))

    assert result["ok"] is True
    assert not project.exists()  # folder removed from its location
    assert "to-delete" not in _cache_names(env["db_path"])  # cache rebuilt


# ── rename: cache update on success (Req 5.2) ──────────────────────────────


def test_rename_success_updates_cache(env):
    project = _make_project(env["root"], "UAT_PREPARE", "old-name", env["store"])

    result = env["js_api"].project_rename(str(project), "fresh-name")

    assert result["ok"] is True
    assert result["data"]["project_name"] == "fresh-name"

    renamed = env["root"] / "2025" / "UAT_PREPARE" / "fresh-name"
    assert renamed.is_dir()
    assert not project.exists()

    names = _cache_names(env["db_path"])
    assert "fresh-name" in names
    assert "old-name" not in names


# ── subproject delete (Req 5.8) ────────────────────────────────────────────


def test_subproject_delete_success(env, tmp_path, monkeypatch):
    project = _make_project(env["root"], "UAT_PREPARE", "parent", env["store"])
    subproject = project / "sub-a"
    subproject.mkdir()

    trash = tmp_path / "trash"
    trash.mkdir()

    def _fake_trash(self, path):
        shutil.move(str(path), str(trash / Path(path).name))

    monkeypatch.setattr(SafeDeleteService, "delete_to_trash", _fake_trash)

    result = env["js_api"].subproject_delete(str(project), "sub-a")

    assert result["ok"] is True
    assert not subproject.exists()  # subproject removed
    assert project.is_dir()  # parent untouched


def test_subproject_delete_send2trash_failure_preserves_folder(env, monkeypatch):
    project = _make_project(env["root"], "UAT_PREPARE", "parent", env["store"])
    subproject = project / "sub-a"
    subproject.mkdir()

    def _raise(self, path):
        raise RuntimeError("send2trash unavailable")

    monkeypatch.setattr(SafeDeleteService, "delete_to_trash", _raise)

    result = env["js_api"].subproject_delete(str(project), "sub-a")

    assert result["ok"] is False
    assert result["error"]["code"] == "SUBPROJECT_DELETE_FAILED"
    assert subproject.is_dir()  # folder preserved in place
