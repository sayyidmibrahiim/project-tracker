"""Phase E.3 — Guarded CR state update via create_js_api() production runtime.

Tests prove:
- cr_update_state no longer returns SERVICE_UNAVAILABLE
- allowed manual transitions succeed and persist
- disallowed transitions fail with controlled error
- REOPEN rejected as target
- automatic-only IN_PROGRESS rejected as manual target
- no folder moves triggered
- cr_state_updated_at updated on success
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
def temp_project_pending_submission():
    """Project with CR state = PENDING_SUBMISSION."""
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        proj_dir = root / "2024" / "UAT_PREPARE" / "test-cr-state"
        proj_dir.mkdir(parents=True)

        metadata = ProjectMetadata(
            project_name="test-cr-state",
            cr_state=CRState.PENDING_SUBMISSION,
        )
        store = MetadataStore()
        store.write(proj_dir, metadata)

        settings = SettingsStore(config_dir=root / "config")
        from dataclasses import replace
        updated = replace(settings.read(), root_folder=root)
        settings.write(updated)

        yield {
            "root": root,
            "project_path": proj_dir,
            "metadata_store": store,
            "settings_store": settings,
        }


@pytest.fixture
def temp_project_approved():
    """Project with CR state = APPROVED."""
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        proj_dir = root / "2024" / "UAT_PREPARE" / "test-cr-approved"
        proj_dir.mkdir(parents=True)

        metadata = ProjectMetadata(
            project_name="test-cr-approved",
            cr_state=CRState.APPROVED,
        )
        store = MetadataStore()
        store.write(proj_dir, metadata)

        settings = SettingsStore(config_dir=root / "config")
        from dataclasses import replace
        updated = replace(settings.read(), root_folder=root)
        settings.write(updated)

        yield {
            "root": root,
            "project_path": proj_dir,
            "metadata_store": store,
            "settings_store": settings,
        }


@pytest.fixture
def js_api_pending(temp_project_pending_submission):
    from project_tracker import app_web
    return app_web.create_js_api(settings_store=temp_project_pending_submission["settings_store"])


@pytest.fixture
def js_api_approved(temp_project_approved):
    from project_tracker import app_web
    return app_web.create_js_api(settings_store=temp_project_approved["settings_store"])


# ── cr_update_state is wired (not SERVICE_UNAVAILABLE) ────────────────────


def test_cr_update_state_no_longer_unavailable(js_api_pending, temp_project_pending_submission):
    """cr_update_state must not return SERVICE_UNAVAILABLE for valid transition."""
    path = str(temp_project_pending_submission["project_path"])
    result = js_api_pending.cr_update_state(path, "PENDING APPROVAL")
    assert result["ok"] is True, f"Expected ok=True, got {result}"


# ── allowed transitions succeed ───────────────────────────────────────────


def test_pending_submission_to_pending_approval(js_api_pending, temp_project_pending_submission):
    """PENDING_SUBMISSION -> PENDING_APPROVAL is allowed."""
    path = str(temp_project_pending_submission["project_path"])
    result = js_api_pending.cr_update_state(path, "PENDING APPROVAL")
    assert result["ok"] is True

    store = temp_project_pending_submission["metadata_store"]
    metadata = store.read(temp_project_pending_submission["project_path"])
    assert metadata.cr_state == CRState.PENDING_APPROVAL


def test_pending_submission_to_postponed(js_api_pending, temp_project_pending_submission):
    """PENDING_SUBMISSION -> POSTPONED is allowed."""
    path = str(temp_project_pending_submission["project_path"])
    result = js_api_pending.cr_update_state(path, "POSTPONED")
    assert result["ok"] is True

    store = temp_project_pending_submission["metadata_store"]
    metadata = store.read(temp_project_pending_submission["project_path"])
    assert metadata.cr_state == CRState.POSTPONED


def test_pending_submission_to_canceled(js_api_pending, temp_project_pending_submission):
    """PENDING_SUBMISSION -> CANCELED is allowed."""
    path = str(temp_project_pending_submission["project_path"])
    result = js_api_pending.cr_update_state(path, "CANCELED")
    assert result["ok"] is True

    store = temp_project_pending_submission["metadata_store"]
    metadata = store.read(temp_project_pending_submission["project_path"])
    assert metadata.cr_state == CRState.CANCELED


def test_cr_state_updated_at_set_on_success(js_api_pending, temp_project_pending_submission):
    """cr_state_updated_at must be set after successful transition."""
    path = str(temp_project_pending_submission["project_path"])
    js_api_pending.cr_update_state(path, "PENDING APPROVAL")

    store = temp_project_pending_submission["metadata_store"]
    metadata = store.read(temp_project_pending_submission["project_path"])
    assert metadata.cr_state_updated_at is not None


# ── disallowed transitions fail ───────────────────────────────────────────


def test_reopen_rejected_as_target(js_api_pending, temp_project_pending_submission):
    """REOPEN must be rejected as a CR state target."""
    path = str(temp_project_pending_submission["project_path"])
    result = js_api_pending.cr_update_state(path, "REOPEN")
    assert result["ok"] is False
    assert "error" in result and result["error"] is not None


def test_in_progress_rejected_as_manual_target(js_api_approved, temp_project_approved):
    """IN-PROGRESS must be rejected as manual target (automatic-only)."""
    path = str(temp_project_approved["project_path"])
    result = js_api_approved.cr_update_state(path, "IN-PROGRESS")
    assert result["ok"] is False
    assert "error" in result and result["error"] is not None


def test_finished_rejected_from_pending_submission(js_api_pending, temp_project_pending_submission):
    """FINISHED must be rejected from PENDING_SUBMISSION."""
    path = str(temp_project_pending_submission["project_path"])
    result = js_api_pending.cr_update_state(path, "FINISHED")
    assert result["ok"] is False


def test_invalid_cr_state_value_fails(js_api_pending, temp_project_pending_submission):
    """Invalid CR state string must fail."""
    path = str(temp_project_pending_submission["project_path"])
    result = js_api_pending.cr_update_state(path, "BOGUS_STATE")
    assert result["ok"] is False


# ── no folder moves ──────────────────────────────────────────────────────


def test_no_folder_move_on_cr_state_change(js_api_pending, temp_project_pending_submission):
    """CR state change must NOT trigger a folder move."""
    path = str(temp_project_pending_submission["project_path"])
    proj_dir = temp_project_pending_submission["project_path"]
    js_api_pending.cr_update_state(path, "CANCELED")

    # Project folder must still exist at original path
    assert proj_dir.exists()
    # Parent must still be UAT_PREPARE
    assert proj_dir.parent.name == "UAT_PREPARE"


# ── folder moves remain deferred ─────────────────────────────────────────


def test_folder_move_still_deferred(js_api_pending):
    """Folder moves remain SERVICE_UNAVAILABLE."""
    result = js_api_pending.folder_move_to_prod_ready("/tmp/x")
    assert result["ok"] is False
