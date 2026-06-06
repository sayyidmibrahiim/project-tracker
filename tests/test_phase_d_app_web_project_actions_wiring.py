"""Phase D.15b — CR Link update end-to-end runtime wiring tests.

TDD RED: tests fail because _ProjectServiceAdapter.update_cr_link = None
returns SERVICE_UNAVAILABLE at runtime.
"""

from __future__ import annotations

import tempfile
from dataclasses import replace
from pathlib import Path

import pytest

from project_tracker.core.enums import CRState
from project_tracker.core.models import ProjectMetadata
from project_tracker.infrastructure.metadata_store import MetadataStore
from project_tracker.infrastructure.settings_store import SettingsStore


@pytest.fixture
def temp_project():
    """Create temp project with project_data.json and real MetadataStore."""
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        year_dir = root / "2024"
        state_dir = year_dir / "UAT_PREPARE"
        proj_dir = state_dir / "my-proj"
        proj_dir.mkdir(parents=True)

        metadata = ProjectMetadata(
            project_name="my-proj",
            cr_link="https://cr.example.com/CR-100",
            cr_state=CRState.APPROVED,
        )
        store = MetadataStore()
        store.write(proj_dir, metadata)

        settings_store = SettingsStore(config_dir=root / "config")
        current = settings_store.read()
        updated = replace(current, root_folder=root)
        settings_store.write(updated)

        yield {
            "root": root,
            "project_path": proj_dir,
            "metadata": metadata,
            "settings_store": settings_store,
        }


@pytest.fixture
def js_api(temp_project):
    """JsApi from create_js_api with temp settings."""
    from project_tracker import app_web
    return app_web.create_js_api(settings_store=temp_project["settings_store"])


# ── RED 1: cr_update_link wired (not SERVICE_UNAVAILABLE) ──────────────

def test_cr_update_link_wired_and_returns_ok(js_api, temp_project):
    """cr_update_link returns ok=True, not SERVICE_UNAVAILABLE."""
    path = str(temp_project["project_path"])
    result = js_api.cr_update_link(path, "https://cr.example.com/CR-200")
    assert result.get("ok") is True, (
        f"cr_update_link must return ok=True, got {result}"
    )


# ── RED 2: cr_update_link persists new CR link in metadata ─────────────

def test_cr_update_link_persists_in_metadata(js_api, temp_project):
    """After cr_update_link, metadata has new cr_link value."""
    path = str(temp_project["project_path"])
    new_link = "https://cr.example.com/CR-999"
    js_api.cr_update_link(path, new_link)

    # Read back metadata directly
    store = MetadataStore()
    metadata = store.read(temp_project["project_path"])
    assert metadata is not None
    assert metadata.cr_link == new_link, (
        f"Expected cr_link={new_link}, got {metadata.cr_link}"
    )


# ── RED 3: response shape matches JsApi contract ───────────────────────

def test_cr_update_link_response_has_expected_fields(js_api, temp_project):
    """cr_update_link response includes project_path, project_state, cr_state."""
    path = str(temp_project["project_path"])
    result = js_api.cr_update_link(path, "https://cr.example.com/CR-300")
    data = result["data"]
    assert "project_path" in data
    assert "project_state" in data
    assert "cr_state" in data


# ── RED 4: other mutations remain deferred ─────────────────────────────

def test_cr_update_state_still_deferred(js_api):
    """cr_update_state still returns SERVICE_UNAVAILABLE."""
    result = js_api.cr_update_state("/tmp/x", "APPROVED")
    assert result["ok"] is False
    assert result["error"] is not None


def test_folder_move_still_deferred(js_api):
    """folder_move_to_prod_ready still returns SERVICE_UNAVAILABLE."""
    result = js_api.folder_move_to_prod_ready("/tmp/x")
    assert result["ok"] is False
    assert result["error"] is not None
