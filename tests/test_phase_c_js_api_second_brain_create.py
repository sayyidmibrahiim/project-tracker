"""Phase C — Second Brain ``create_folder`` / ``create_file`` bridges.

The prototype's Notes stack exposes "Add Folder" and "Add File" (for non-`.md`
text-like files). These map to two new Second Brain service operations:

- ``create_folder(parent, name)`` — create a subfolder within the Second Brain
  root (or within ``parent``), validating the name and rejecting an existing
  target.
- ``create_file(parent, filename, content)`` — generic text-like file create
  (``.md/.txt/.py/.sql/.json`` etc.), mirroring ``create_note`` but for any
  allowlisted text extension.

Both must validate the target resolves within the Second Brain root and must
not overwrite an existing entry.
"""

from pathlib import Path

import pytest

from core.exceptions import InvalidFileNameError
from services.second_brain_service import SecondBrainService
from web.js_api import JsApi


def _service_with_root(tmp_root: Path) -> SecondBrainService:
    """Build a SecondBrainService backed by a real tmp folder.

    create_folder/create_file only need _require_folder(); the items provider
    is irrelevant for these mutation tests.
    """
    return SecondBrainService(folder_provider=lambda: tmp_root)


# ── service: create_folder ───────────────────────────────────────────────────

def test_service_create_folder_makes_subfolder_within_root(tmp_path):
    root = tmp_path / "sb"
    root.mkdir()
    svc = _service_with_root(root)
    result = svc.create_folder(root, "ideas")
    assert result == (root / "ideas")
    assert (root / "ideas").is_dir()


def test_service_create_folder_rejects_existing(tmp_path):
    root = tmp_path / "sb"
    root.mkdir(parents=True)
    (root / "dup").mkdir()
    svc = _service_with_root(root)
    with pytest.raises(Exception):
        svc.create_folder(root, "dup")


def test_service_create_folder_rejects_escape(tmp_path):
    root = tmp_path / "sb"
    root.mkdir()
    outside = tmp_path / "outside"
    svc = _service_with_root(root)
    with pytest.raises(Exception):
        # name with traversal must not escape the root
        svc.create_folder(root, "../escape")


@pytest.mark.parametrize("name", ["nested/child", r"nested\child"])
def test_service_create_folder_rejects_path_separators_before_creation(tmp_path, name):
    root = tmp_path / "sb"
    root.mkdir()
    svc = _service_with_root(root)

    with pytest.raises(InvalidFileNameError):
        svc.create_folder(root, name)

    assert list(root.iterdir()) == []


# ── service: create_file (generic text) ──────────────────────────────────────

def test_service_create_file_writes_text_content(tmp_path):
    root = tmp_path / "sb"
    root.mkdir()
    svc = _service_with_root(root)
    result = svc.create_file(root, "notes.txt", "hello world")
    assert result == (root / "notes.txt")
    assert (root / "notes.txt").read_text(encoding="utf-8") == "hello world"


def test_service_create_file_rejects_existing(tmp_path):
    root = tmp_path / "sb"
    root.mkdir(parents=True)
    (root / "dup.py").write_text("x", encoding="utf-8")
    svc = _service_with_root(root)
    with pytest.raises(Exception):
        svc.create_file(root, "dup.py", "y")


def test_service_create_file_rejects_non_text_extension(tmp_path):
    root = tmp_path / "sb"
    root.mkdir()
    svc = _service_with_root(root)
    with pytest.raises(Exception):
        svc.create_file(root, "payload.exe", "binary?")


# ── bridge wiring ────────────────────────────────────────────────────────────

def _api_with_service(svc) -> JsApi:
    return JsApi(dashboard_service=None, second_brain_service=svc)


def test_bridge_second_brain_folder_create_exists_and_round_trips(tmp_path, monkeypatch):
    root = tmp_path / "sb"
    root.mkdir()
    svc = _service_with_root(root)
    api = _api_with_service(svc)
    assert callable(getattr(api, "second_brain_folder_create", None))
    result = api.second_brain_folder_create(str(root), "deep")
    assert result["ok"] is True
    # _to_frontend_safe serializes the Path to a string.
    assert "deep" in str(result["data"])
    assert (root / "deep").is_dir()


def test_bridge_second_brain_file_create_exists_and_round_trips(tmp_path):
    root = tmp_path / "sb"
    root.mkdir()
    svc = _service_with_root(root)
    api = _api_with_service(svc)
    assert callable(getattr(api, "second_brain_file_create", None))
    result = api.second_brain_file_create(str(root), "todo.md", "# TODO")
    assert result["ok"] is True
    assert "todo.md" in str(result["data"])
    assert (root / "todo.md").read_text(encoding="utf-8") == "# TODO"


def test_bridge_second_brain_folder_create_fails_when_service_missing():
    api = JsApi(dashboard_service=None)  # no second_brain_service
    result = api.second_brain_folder_create("/tmp", "x")
    assert result["ok"] is False
    assert result["error"]["code"] == "SERVICE_UNAVAILABLE"


def test_bridge_second_brain_file_create_fails_when_service_missing():
    api = JsApi(dashboard_service=None)  # no second_brain_service
    result = api.second_brain_file_create("/tmp", "x.md", "")
    assert result["ok"] is False
    assert result["error"]["code"] == "SERVICE_UNAVAILABLE"


# ── Task 4: second_brain_create — Notes explorer "+ New" facade ─────────
#
# The Task 8 frontend (SecondBrainNotes.svelte) calls a single
# ``second_brain_create(target, name)`` for its "+ New" note action (the
# ``.md`` default is chosen in the frontend, not here). It reuses the same
# guarded ``create_file`` as ``second_brain_file_create`` above, so the
# text-like-extension allowlist and traversal/duplicate guards apply
# identically; this is a new facade name, additive to (not replacing) the
# legacy folder/file create bridges preserved above.


def test_bridge_second_brain_create_exists_and_round_trips(tmp_path):
    root = tmp_path / "sb"
    root.mkdir()
    svc = _service_with_root(root)
    api = _api_with_service(svc)
    assert callable(getattr(api, "second_brain_create", None))
    result = api.second_brain_create(str(root), "todo.md")
    assert result["ok"] is True
    assert "todo.md" in str(result["data"])
    assert (root / "todo.md").is_file()


def test_bridge_second_brain_create_rejects_non_text_extension(tmp_path):
    root = tmp_path / "sb"
    root.mkdir()
    svc = _service_with_root(root)
    api = _api_with_service(svc)
    result = api.second_brain_create(str(root), "payload.exe")
    assert result["ok"] is False
    assert result["error"]["code"] == "SECOND_BRAIN_CREATE_FAILED"
    assert not (root / "payload.exe").exists()


def test_bridge_second_brain_create_rejects_existing_target(tmp_path):
    root = tmp_path / "sb"
    root.mkdir()
    (root / "dup.md").write_text("original", encoding="utf-8")
    svc = _service_with_root(root)
    api = _api_with_service(svc)
    result = api.second_brain_create(str(root), "dup.md")
    assert result["ok"] is False
    assert (root / "dup.md").read_text(encoding="utf-8") == "original"


def test_bridge_second_brain_create_fails_when_service_missing():
    api = JsApi(dashboard_service=None)  # no second_brain_service
    result = api.second_brain_create("/tmp", "x.md")
    assert result["ok"] is False
    assert result["error"]["code"] == "SERVICE_UNAVAILABLE"
