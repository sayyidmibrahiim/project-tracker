"""Task 9.3 — Unit tests for file operations (create / template / open / rename / delete).

Named ``test_project_*`` so it sorts after the ``test_phase_c_*`` import-isolation
tests: importing ``app_web`` (which imports ``webview``) must not pollute
``sys.modules`` before those tests assert ``webview`` is absent.


These tests exercise the wired ``JsApi`` (via ``create_js_api``) and its
``_FileServiceAdapter`` route through ``infrastructure/filesystem.py`` helpers
and ``SafeDeleteService``, entirely against ``tmp_path``.

Covered behaviour (Req 6.3, 6.5, 6.7, 6.9, 6.10):
- invalid name rejection on create / rename (FILE_CREATE_FAILED /
  FILE_RENAME_FAILED, folder contents unchanged)
- duplicate / existing name rejection on create, create-from-template, and
  rename (existing file never overwritten / clobbered)
- off-Windows ``file_open`` returns a dev-skipped ``ok=true`` and never invokes
  ``os.startfile``
- ``send2trash`` failure on delete (monkeypatched ``SafeDeleteService``)
  preserves the file and returns ``ok=false``
- filesystem failure preservation on rename (missing source) leaves folder
  contents unchanged and returns ``ok=false``
- lock enforcement: create / rename / delete rejected while the project is in
  ``PROD_READY`` or ``IMPLEMENTED`` (no delete route reached, contents unchanged)

All destructive operations run only against ``tmp_path`` and every delete is
routed through a monkeypatched ``SafeDeleteService`` so no real Recycle Bin /
``send2trash`` is ever used.
"""

from __future__ import annotations

import os
import sys
from dataclasses import replace
from pathlib import Path

import pytest

from project_tracker.infrastructure import filesystem as infra_fs
from project_tracker.infrastructure.settings_store import SettingsStore


# ── helpers / fixtures ────────────────────────────────────────────────────


@pytest.fixture
def env(tmp_path):
    """Configured root + template folder + wired JsApi, all under tmp_path."""
    from project_tracker import app_web

    root = tmp_path / "root"
    root.mkdir()
    templates = tmp_path / "templates"
    templates.mkdir()

    settings = SettingsStore(config_dir=tmp_path / "config")
    settings.write(
        replace(settings.read(), root_folder=root, file_template_folder=templates)
    )

    js_api = app_web.create_js_api(db_path=tmp_path / "cache.db", settings_store=settings)

    return {
        "root": root,
        "templates": templates,
        "js_api": js_api,
    }


def _project_folder(root: Path, state: str, name: str = "proj", year: str = "2025") -> Path:
    """Create and return a project folder under ``root/year/state/name``."""
    folder = root / year / state / name
    folder.mkdir(parents=True)
    return folder


# ── create: invalid name rejection (Req 6.3/6.9) ──────────────────────────


def test_create_invalid_name_rejected_folder_unchanged(env):
    folder = _project_folder(env["root"], "UAT_PREPARE")

    result = env["js_api"].file_create(str(folder), "bad:name?")

    assert result["ok"] is False
    assert result["error"]["code"] == "FILE_CREATE_FAILED"
    assert list(folder.iterdir()) == []  # nothing created


# ── create: existing name rejection, never overwrite (Req 6.3) ────────────


def test_create_existing_name_rejected_not_overwritten(env):
    folder = _project_folder(env["root"], "UAT_PREPARE")
    existing = folder / "evidence.txt"
    existing.write_text("original", encoding="utf-8")

    result = env["js_api"].file_create(str(folder), "evidence.txt")

    assert result["ok"] is False
    assert result["error"]["code"] == "FILE_CREATE_FAILED"
    assert existing.read_text(encoding="utf-8") == "original"  # untouched


def test_create_success_makes_file(env):
    folder = _project_folder(env["root"], "UAT_PREPARE")

    result = env["js_api"].file_create(str(folder), "new.txt")

    assert result["ok"] is True
    assert (folder / "new.txt").is_file()


# ── create-from-template: existing name rejection (Req 6.3) ────────────────


def test_create_from_template_existing_name_rejected(env):
    folder = _project_folder(env["root"], "UAT_PREPARE")
    (env["templates"] / "tmpl.txt").write_text("template body", encoding="utf-8")
    existing = folder / "tmpl.txt"
    existing.write_text("original", encoding="utf-8")

    result = env["js_api"].file_create_from_template(str(folder), "tmpl.txt")

    assert result["ok"] is False
    assert result["error"]["code"] == "FILE_CREATE_FROM_TEMPLATE_FAILED"
    assert existing.read_text(encoding="utf-8") == "original"  # untouched


# ── rename: invalid name rejection (Req 6.7/6.9) ──────────────────────────


def test_rename_invalid_name_rejected_file_unchanged(env):
    folder = _project_folder(env["root"], "UAT_PREPARE")
    source = folder / "report.txt"
    source.write_text("data", encoding="utf-8")

    result = env["js_api"].file_rename(str(source), "bad:name?")

    assert result["ok"] is False
    assert result["error"]["code"] == "FILE_RENAME_FAILED"
    assert source.is_file()  # original preserved
    assert source.read_text(encoding="utf-8") == "data"


# ── rename: existing destination rejection, never clobber (Req 6.7) ───────


def test_rename_existing_destination_rejected(env):
    folder = _project_folder(env["root"], "UAT_PREPARE")
    source = folder / "a.txt"
    source.write_text("a-body", encoding="utf-8")
    other = folder / "b.txt"
    other.write_text("b-body", encoding="utf-8")

    result = env["js_api"].file_rename(str(source), "b.txt")

    assert result["ok"] is False
    assert result["error"]["code"] == "FILE_RENAME_FAILED"
    assert source.is_file()  # source preserved
    assert other.read_text(encoding="utf-8") == "b-body"  # destination unclobbered


# ── rename: filesystem failure preservation (Req 6.9) ─────────────────────


def test_rename_filesystem_failure_preserves_contents(env):
    folder = _project_folder(env["root"], "UAT_PREPARE")
    # Source does not exist: name/containment guards pass, but the rename fails
    # at the filesystem level, leaving the folder contents unchanged.
    missing = folder / "ghost.txt"

    result = env["js_api"].file_rename(str(missing), "renamed.txt")

    assert result["ok"] is False
    assert result["error"]["code"] == "FILE_RENAME_FAILED"
    assert list(folder.iterdir()) == []  # nothing created or moved


# ── file_open: off-Windows dev-skip, never calls os.startfile (Req 6.5) ───


def test_file_open_off_windows_dev_skipped_no_startfile(env, tmp_path, monkeypatch):
    if sys.platform == "win32":  # pragma: no cover - Linux CI path
        pytest.skip("dev-skip behaviour only asserted off-Windows")

    target = tmp_path / "doc.txt"
    target.write_text("x", encoding="utf-8")

    def _boom(_path):  # pragma: no cover - must never be called off-Windows
        raise AssertionError("os.startfile must not be called off-Windows")

    # os.startfile does not exist on Linux; register it so a stray call is caught.
    monkeypatch.setattr(os, "startfile", _boom, raising=False)

    result = env["js_api"].file_open(str(target))

    assert result["ok"] is True


# ── delete: send2trash failure preserves the file (Req 6.9) ───────────────


def test_delete_send2trash_failure_preserves_file(env, monkeypatch):
    folder = _project_folder(env["root"], "UAT_PREPARE")
    target = folder / "keep.txt"
    target.write_text("payload", encoding="utf-8")

    def _raise(self, path):
        raise RuntimeError("send2trash unavailable")

    monkeypatch.setattr(infra_fs, "send_to_recycle_bin", _raise)

    result = env["js_api"].file_delete(str(target))

    assert result["ok"] is False
    assert result["error"]["code"] == "FILE_DELETE_FAILED"
    assert target.is_file()  # file preserved in place
    assert target.read_text(encoding="utf-8") == "payload"


def test_delete_success_routes_to_safe_delete(env, tmp_path, monkeypatch):
    folder = _project_folder(env["root"], "UAT_PREPARE")
    target = folder / "gone.txt"
    target.write_text("bye", encoding="utf-8")

    trash = tmp_path / "trash"
    trash.mkdir()

    def _fake_trash(path):
        Path(path).replace(trash / Path(path).name)

    monkeypatch.setattr(infra_fs, "send_to_recycle_bin", _fake_trash)

    result = env["js_api"].file_delete(str(target))

    assert result["ok"] is True
    assert not target.exists()  # routed to (fake) recycle bin


# ── lock enforcement: create / rename / delete rejected when locked (Req 6.10) ─


@pytest.mark.parametrize("state", ["PROD_READY", "IMPLEMENTED"])
def test_create_rejected_when_locked(env, state):
    folder = _project_folder(env["root"], state)

    result = env["js_api"].file_create(str(folder), "new.txt")

    assert result["ok"] is False
    assert result["error"]["code"] == "FILE_CREATE_FAILED"
    assert state.lower() in result["error"]["message"].lower()
    assert not (folder / "new.txt").exists()  # nothing created


@pytest.mark.parametrize("state", ["PROD_READY", "IMPLEMENTED"])
def test_rename_rejected_when_locked(env, state):
    folder = _project_folder(env["root"], state)
    source = folder / "doc.txt"
    source.write_text("data", encoding="utf-8")

    result = env["js_api"].file_rename(str(source), "renamed.txt")

    assert result["ok"] is False
    assert result["error"]["code"] == "FILE_RENAME_FAILED"
    assert state.lower() in result["error"]["message"].lower()
    assert source.is_file()  # unchanged
    assert not (folder / "renamed.txt").exists()


@pytest.mark.parametrize("state", ["PROD_READY", "IMPLEMENTED"])
def test_delete_rejected_when_locked(env, state, monkeypatch):
    # The lock guard must reject before any deletion route is reached.
    def _boom(path):  # pragma: no cover - must never be called
        raise AssertionError("send_to_recycle_bin must not be called for a locked project")

    monkeypatch.setattr(infra_fs, "send_to_recycle_bin", _boom)

    folder = _project_folder(env["root"], state)
    target = folder / "doc.txt"
    target.write_text("data", encoding="utf-8")

    result = env["js_api"].file_delete(str(target))

    assert result["ok"] is False
    assert result["error"]["code"] == "FILE_DELETE_FAILED"
    assert state.lower() in result["error"]["message"].lower()
    assert target.is_file()  # file preserved in place
