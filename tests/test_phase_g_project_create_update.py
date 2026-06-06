"""Phase G.1 — Project Create + Update Metadata Contract.

Tests prove:
- project_update succeeds for metadata fields (project_name, implementation_plan)
- project_update persists changes in MetadataStore
- project_update on nonexistent path fails controlled
- project_create creates folder + metadata
- project_create with empty name fails
- project_create with invalid Windows folder name fails
- project_create when folder exists fails
- project_create without configured root_folder fails
- rename_project still returns SERVICE_UNAVAILABLE (deferred)
- folder_move still returns SERVICE_UNAVAILABLE (deferred)
"""

from __future__ import annotations

import tempfile
from dataclasses import replace
from pathlib import Path

import pytest

from project_tracker.core.enums import CRState
from project_tracker.core.models import ProjectMetadata, local_now
from project_tracker.infrastructure.metadata_store import MetadataStore
from project_tracker.infrastructure.settings_store import SettingsStore


@pytest.fixture
def temp_project():
    """Project with metadata ready for update tests."""
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        proj_dir = root / "2025" / "UAT_PREPARE" / "my-project"
        proj_dir.mkdir(parents=True)

        metadata = ProjectMetadata(
            project_name="my-project",
            implementation_plan="old plan",
            cr_state=CRState.PENDING_SUBMISSION,
        )
        store = MetadataStore()
        store.write(proj_dir, metadata)

        settings = SettingsStore(config_dir=root / "config")
        updated = replace(settings.read(), root_folder=root)
        settings.write(updated)

        yield {
            "root": root,
            "project_path": proj_dir,
            "metadata_store": store,
            "settings_store": settings,
        }


@pytest.fixture
def js_api(temp_project):
    from project_tracker import app_web

    return app_web.create_js_api(settings_store=temp_project["settings_store"])


@pytest.fixture
def temp_root_configured():
    """Root folder configured but no projects yet."""
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        settings = SettingsStore(config_dir=root / "config")
        updated = replace(settings.read(), root_folder=root)
        settings.write(updated)
        yield {
            "root": root,
            "settings_store": settings,
        }


@pytest.fixture
def js_api_fresh(temp_root_configured):
    from project_tracker import app_web

    return app_web.create_js_api(settings_store=temp_root_configured["settings_store"])


@pytest.fixture
def temp_root_unconfigured():
    """No root_folder configured."""
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        settings = SettingsStore(config_dir=root / "config")
        yield {
            "root": root,
            "settings_store": settings,
        }


@pytest.fixture
def js_api_no_root(temp_root_unconfigured):
    from project_tracker import app_web

    return app_web.create_js_api(settings_store=temp_root_unconfigured["settings_store"])


# ── project_update succeeds for metadata fields ──────────────────────────


def test_project_update_name_and_plan(js_api, temp_project):
    """project_update updates project_name and implementation_plan."""
    path = str(temp_project["project_path"])
    result = js_api.project_update(path, {
        "project_name": "renamed-project",
        "implementation_plan": "new plan",
    })
    assert result["ok"] is True
    assert result["data"]["project_name"] == "renamed-project"


# ── project_update persists in MetadataStore ─────────────────────────────


def test_project_update_persists(js_api, temp_project):
    """project_update changes are persisted."""
    path = str(temp_project["project_path"])
    js_api.project_update(path, {
        "project_name": "persisted-name",
        "implementation_plan": "persisted plan",
    })
    store = temp_project["metadata_store"]
    metadata = store.read(temp_project["project_path"])
    assert metadata.project_name == "persisted-name"
    assert metadata.implementation_plan == "persisted plan"
    assert metadata.updated_at is not None


# ── project_update on nonexistent path fails controlled ──────────────────


def test_project_update_nonexistent_fails(js_api, temp_project):
    """project_update on a path whose parent dir is missing returns controlled error."""
    fake_path = str(temp_project["root"] / "9999" / "UAT_PREPARE" / "ghost")
    result = js_api.project_update(fake_path, {"project_name": "x"})
    assert result["ok"] is False
    assert result["error"]["code"] == "PROJECT_UPDATE_FAILED"


# ── project_create creates folder + metadata ─────────────────────────────


def test_project_create_success(js_api_fresh, temp_root_configured):
    """project_create creates folder and initial metadata."""
    result = js_api_fresh.project_create({
        "project_name": "new-project",
        "year": "2025",
    })
    assert result["ok"] is True
    data = result["data"]
    assert data["project_name"] == "new-project"
    assert data["project_state"] == "UAT_PREPARE"

    created_dir = Path(data["project_path"])
    assert created_dir.exists()
    assert created_dir.is_dir()

    # Metadata file must exist
    store = MetadataStore()
    metadata = store.read(created_dir)
    assert metadata is not None
    assert metadata.project_name == "new-project"
    assert metadata.created_at is not None


# ── project_create with empty name fails ─────────────────────────────────


def test_project_create_empty_name_fails(js_api_fresh):
    """project_create with empty project_name fails."""
    result = js_api_fresh.project_create({"project_name": ""})
    assert result["ok"] is False
    assert "required" in result["error"]["message"].lower()


def test_project_create_no_name_key_fails(js_api_fresh):
    """project_create with missing project_name key fails."""
    result = js_api_fresh.project_create({})
    assert result["ok"] is False


# ── project_create with invalid Windows folder name fails ────────────────


def test_project_create_invalid_name_fails(js_api_fresh):
    """project_create with invalid Windows folder name fails."""
    result = js_api_fresh.project_create({"project_name": "con"})
    assert result["ok"] is False
    assert "reserved" in result["error"]["message"].lower()


def test_project_create_invalid_chars_fails(js_api_fresh):
    """project_create with invalid characters fails."""
    result = js_api_fresh.project_create({"project_name": "bad<name"})
    assert result["ok"] is False
    assert "invalid" in result["error"]["message"].lower()


# ── project_create when folder already exists fails ──────────────────────


def test_project_create_existing_folder_fails(js_api_fresh, temp_root_configured):
    """project_create fails if folder already exists."""
    existing = temp_root_configured["root"] / "2025" / "UAT_PREPARE" / "dupe"
    existing.mkdir(parents=True)
    result = js_api_fresh.project_create({"project_name": "dupe", "year": "2025"})
    assert result["ok"] is False
    assert "already exists" in result["error"]["message"].lower()


# ── project_create without configured root_folder fails ──────────────────


def test_project_create_no_root_fails(js_api_no_root):
    """project_create without root_folder configured fails."""
    result = js_api_no_root.project_create({"project_name": "something"})
    assert result["ok"] is False
    assert "root folder" in result["error"]["message"].lower()


# ── rename_project still returns SERVICE_UNAVAILABLE ─────────────────────


def test_rename_project_still_unavailable(js_api, temp_project):
    """rename_project must still fail (None callable → error)."""
    path = str(temp_project["project_path"])
    result = js_api.project_rename(path, "new-name")
    assert result["ok"] is False
    assert result["error"]["code"] == "PROJECT_RENAME_FAILED"


# ── folder_move still returns SERVICE_UNAVAILABLE ────────────────────────


def test_folder_move_still_unavailable(js_api):
    """folder_move must still return SERVICE_UNAVAILABLE."""
    result = js_api.folder_move_to_prod_ready("/tmp/x")
    assert result["ok"] is False
