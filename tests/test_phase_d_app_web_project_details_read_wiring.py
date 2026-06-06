"""Phase D.15a — Project Details read-path production wiring tests.

TDD RED: tests fail because create_js_api() returns SERVICE_UNAVAILABLE
for project_get, subproject_list, file_list, notes_get, and year_list.
"""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

from project_tracker.core.enums import CRState, ProjectState
from project_tracker.core.models import ProjectMetadata
from project_tracker.infrastructure.metadata_store import MetadataStore
from project_tracker.infrastructure.settings_store import SettingsStore


# ── Helpers ────────────────────────────────────────────────────────────

@pytest.fixture
def temp_project():
    """Create a temp project dir with project_data.json for real testing."""
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        year_dir = root / "2024"
        state_dir = year_dir / "UAT_PREPARE"
        proj_dir = state_dir / "test-project"
        proj_dir.mkdir(parents=True)

        metadata = ProjectMetadata(
            project_name="test-project",
            cr_link="https://cr.example.com/CR-999",
            cr_state=CRState.APPROVED,
        )
        store = MetadataStore()
        store.write(proj_dir, metadata)

        # Create a subproject dir
        (proj_dir / "sub1").mkdir()
        # Create a file
        (proj_dir / "notes.md").write_text("hello world")

        # SettingsStore pointing to temp root
        settings = SettingsStore(config_dir=root / "config")
        settings.write(settings.read())  # ensure dir exists

        yield {
            "root": root,
            "project_path": proj_dir,
            "metadata": metadata,
            "settings_store": settings,
        }


@pytest.fixture
def js_api(temp_project):
    """JsApi from create_js_api with temp settings and root folder."""
    from project_tracker import app_web

    settings = temp_project["settings_store"]
    # Set root_folder on the settings
    current = settings.read()
    from dataclasses import replace

    updated = replace(current, root_folder=temp_project["root"])
    settings.write(updated)

    return app_web.create_js_api(settings_store=settings)


# ── RED 1: year_list no longer SERVICE_UNAVAILABLE ─────────────────────

def test_year_list_wired_and_returns_ok(js_api):
    """year_list returns ok with year list, not SERVICE_UNAVAILABLE."""
    result = js_api.year_list()
    assert isinstance(result, dict), f"Expected dict, got {type(result)}"
    assert result.get("ok") is True, (
        f"year_list must return ok=True, got {result}"
    )
    assert isinstance(result.get("data"), list), f"data must be list: {result}"


def test_year_list_discovers_years_from_root_folder(js_api, temp_project):
    """year_list discovers year dirs from SettingsStore.root_folder."""
    result = js_api.year_list()
    assert result["ok"] is True
    years = result["data"]
    assert "2024" in years, f"Expected 2024 in years, got {years}"


# ── RED 2: project_get no longer SERVICE_UNAVAILABLE ───────────────────

def test_project_get_wired_and_returns_ok(js_api, temp_project):
    """project_get returns ok with project detail, not SERVICE_UNAVAILABLE."""
    path = str(temp_project["project_path"])
    result = js_api.project_get(path)
    assert isinstance(result, dict), f"Expected dict, got {type(result)}"
    assert result.get("ok") is True, (
        f"project_get must return ok=True, got {result}"
    )


def test_project_get_returns_detail_fields(js_api, temp_project):
    """project_get returns expected detail fields from real metadata."""
    path = str(temp_project["project_path"])
    result = js_api.project_get(path)
    data = result["data"]
    assert data["project_name"] == "test-project"
    assert data["project_state"] == "UAT_PREPARE"
    # cr_number extracted via extract_cr_number from cr_link.
    # The fixture cr_link="https://cr.example.com/CR-999" does not match
    # the CRNumber= query-param pattern, so cr_number will be empty string.
    assert isinstance(data["cr_number"], str), f"cr_number must be str: {data['cr_number']}"
    assert data["cr_state"] == "APPROVED"
    assert isinstance(data["drone_ticket_count"], int)


# ── RED 3: subproject_list no longer SERVICE_UNAVAILABLE ───────────────

def test_subproject_list_wired_and_returns_ok(js_api, temp_project):
    """subproject_list returns ok with subproject paths."""
    path = str(temp_project["project_path"])
    result = js_api.subproject_list(path)
    assert isinstance(result, dict), f"Expected dict, got {type(result)}"
    assert result.get("ok") is True, (
        f"subproject_list must return ok=True, got {result}"
    )


def test_subproject_list_discovers_subdirs(js_api, temp_project):
    """subproject_list returns real subproject paths from filesystem."""
    path = str(temp_project["project_path"])
    result = js_api.subproject_list(path)
    data = result["data"]
    assert isinstance(data, list)
    # Should include "sub1" subdir
    found = any("sub1" in str(s) for s in data)
    assert found, f"Expected sub1 in subproject list, got {data}"


# ── RED 4: file_list no longer SERVICE_UNAVAILABLE ─────────────────────

def test_file_list_wired_and_returns_ok(js_api, temp_project):
    """file_list returns ok with file entries."""
    path = str(temp_project["project_path"])
    result = js_api.file_list(path)
    assert isinstance(result, dict), f"Expected dict, got {type(result)}"
    assert result.get("ok") is True, (
        f"file_list must return ok=True, got {result}"
    )


def test_file_list_discovers_files(js_api, temp_project):
    """file_list returns real file entries from filesystem directory."""
    path = str(temp_project["project_path"])
    result = js_api.file_list(path)
    data = result["data"]
    assert isinstance(data, list)
    # Should include "notes.md"
    found = any(
        (isinstance(f, dict) and f.get("name") == "notes.md")
        or (isinstance(f, str) and "notes.md" in f)
        for f in data
    )
    assert found, f"Expected notes.md in file list, got {data}"


# ── RED 5: notes_get no longer SERVICE_UNAVAILABLE ─────────────────────

def test_notes_get_wired_and_returns_ok(js_api, temp_project):
    """notes_get returns ok with notes string."""
    path = str(temp_project["project_path"])
    result = js_api.notes_get(path)
    assert isinstance(result, dict), f"Expected dict, got {type(result)}"
    assert result.get("ok") is True, (
        f"notes_get must return ok=True, got {result}"
    )


# ── RED 6: mutations still explicitly deferred ─────────────────────────

def test_project_create_still_deferred(js_api):
    """project_create still returns SERVICE_UNAVAILABLE."""
    result = js_api.project_create({"name": "x"})
    assert result["ok"] is False
    assert result["error"] is not None


def test_cr_update_link_still_deferred(js_api):
    """cr_update_link still returns SERVICE_UNAVAILABLE."""
    result = js_api.cr_update_link("/tmp/x", "http://cr.example.com")
    assert result["ok"] is False
    assert result["error"] is not None


def test_drone_add_wired_phase_e(js_api, temp_project):
    """drone_add is wired in Phase E.2 (metadata-only). No longer deferred."""
    path = str(temp_project["project_path"])
    result = js_api.drone_add(path, {"drone_link": "https://drone.test/D-1"})
    assert result["ok"] is True


def test_folder_move_still_deferred(js_api):
    """folder_move_to_prod_ready still returns SERVICE_UNAVAILABLE."""
    result = js_api.folder_move_to_prod_ready("/tmp/x")
    assert result["ok"] is False
    assert result["error"] is not None


def test_subproject_create_still_deferred(js_api):
    """subproject_create still returns SERVICE_UNAVAILABLE."""
    result = js_api.subproject_create("/tmp/x", "new-sub")
    assert result["ok"] is False
    assert result["error"] is not None


def test_file_open_still_deferred(js_api):
    """file_open still returns SERVICE_UNAVAILABLE."""
    result = js_api.file_open("/tmp/x")
    assert result["ok"] is False
    assert result["error"] is not None


def test_notes_update_wired_phase_e(js_api):
    """notes_update is wired in Phase E.1 (writes notes.md). No longer deferred."""
    result = js_api.notes_update("/tmp/x", "new notes")
    assert result["ok"] is True


# ── RED 7: import safety ───────────────────────────────────────────────

def test_app_web_import_is_linux_safe():
    """app_web.py must import without crash on Linux (no pywebview at import)."""
    from project_tracker import app_web  # noqa: F401
