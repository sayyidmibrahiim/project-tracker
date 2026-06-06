"""Phase E.1 — Notes persistence via notes.md file (PRD-correct).

Tests prove:
- notes_get reads from notes.md file, not from project_data.json
- notes_update writes to notes.md file and persists
- missing notes.md returns empty string
- update creates notes.md if absent
- unrelated mutations remain unavailable
"""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

from project_tracker.core.enums import CRState
from project_tracker.core.models import ProjectMetadata
from project_tracker.infrastructure.metadata_store import MetadataStore
from project_tracker.infrastructure.settings_store import SettingsStore


@pytest.fixture
def temp_project():
    """Temp project with notes.md file."""
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

        # Create notes.md with content
        (proj_dir / "notes.md").write_text("existing notes content")

        settings = SettingsStore(config_dir=root / "config")
        from dataclasses import replace

        updated = replace(settings.read(), root_folder=root)
        settings.write(updated)

        yield {
            "root": root,
            "project_path": proj_dir,
            "settings_store": settings,
        }


@pytest.fixture
def temp_project_no_notes():
    """Temp project WITHOUT notes.md file."""
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        year_dir = root / "2024"
        state_dir = year_dir / "UAT_PREPARE"
        proj_dir = state_dir / "test-project-no-notes"
        proj_dir.mkdir(parents=True)

        metadata = ProjectMetadata(project_name="test-project-no-notes")
        store = MetadataStore()
        store.write(proj_dir, metadata)

        settings = SettingsStore(config_dir=root / "config")
        from dataclasses import replace

        updated = replace(settings.read(), root_folder=root)
        settings.write(updated)

        yield {
            "root": root,
            "project_path": proj_dir,
            "settings_store": settings,
        }


@pytest.fixture
def js_api(temp_project):
    """JsApi from create_js_api with temp settings."""
    from project_tracker import app_web

    return app_web.create_js_api(settings_store=temp_project["settings_store"])


@pytest.fixture
def js_api_no_notes(temp_project_no_notes):
    """JsApi from create_js_api for project without notes.md."""
    from project_tracker import app_web

    return app_web.create_js_api(settings_store=temp_project_no_notes["settings_store"])


# ── notes_get reads from notes.md file ──────────────────────────────────


def test_notes_get_reads_from_notes_md_file(js_api, temp_project):
    """notes_get must read content from notes.md, not from project_data.json."""
    path = str(temp_project["project_path"])
    result = js_api.notes_get(path)
    assert result["ok"] is True
    assert result["data"] == "existing notes content"


def test_notes_get_returns_empty_when_no_notes_md(js_api_no_notes, temp_project_no_notes):
    """notes_get returns empty string when notes.md does not exist."""
    path = str(temp_project_no_notes["project_path"])
    result = js_api_no_notes.notes_get(path)
    assert result["ok"] is True
    assert result["data"] == ""


# ── notes_update writes to notes.md file ─────────────────────────────────


def test_notes_update_no_longer_service_unavailable(js_api, temp_project):
    """notes_update must not return SERVICE_UNAVAILABLE."""
    path = str(temp_project["project_path"])
    result = js_api.notes_update(path, "new notes")
    assert result["ok"] is True, f"Expected ok=True, got {result}"


def test_notes_update_persists_to_notes_md(js_api, temp_project):
    """notes_update writes content to notes.md file."""
    path = str(temp_project["project_path"])
    js_api.notes_update(path, "updated content")

    notes_file = temp_project["project_path"] / "notes.md"
    assert notes_file.read_text() == "updated content"


def test_notes_update_creates_notes_md_if_absent(js_api_no_notes, temp_project_no_notes):
    """notes_update creates notes.md if it does not exist."""
    path = str(temp_project_no_notes["project_path"])
    result = js_api_no_notes.notes_update(path, "brand new notes")
    assert result["ok"] is True

    notes_file = temp_project_no_notes["project_path"] / "notes.md"
    assert notes_file.exists()
    assert notes_file.read_text() == "brand new notes"


def test_notes_update_round_trip(js_api, temp_project):
    """notes_update followed by notes_get returns same content."""
    path = str(temp_project["project_path"])
    js_api.notes_update(path, "round trip test")
    result = js_api.notes_get(path)
    assert result["ok"] is True
    assert result["data"] == "round trip test"


# ── unrelated mutations remain unavailable ────────────────────────────────


def test_folder_move_still_deferred(js_api):
    """Folder moves remain SERVICE_UNAVAILABLE."""
    result = js_api.folder_move_to_prod_ready("/tmp/x")
    assert result["ok"] is False


def test_file_open_still_deferred(js_api):
    """File open remains SERVICE_UNAVAILABLE."""
    result = js_api.file_open("/tmp/x")
    assert result["ok"] is False
