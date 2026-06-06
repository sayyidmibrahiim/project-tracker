"""Phase F.1 — Guarded drone state update via create_js_api() runtime.

Tests prove:
- drone_update with valid transition (UAT -> PENDING_APPROVAL) succeeds + persists
- drone_update with invalid transition (UAT -> FINISHED) fails (controlled)
- drone_update with empty drone_link + drone_state fails (guard requirement)
- drone_update IN-PROGRESS as manual target from APPROVED fails (auto-only)
- drone_update WITHOUT drone_state still works (E.2 backward compat)
- drone_state_updated_at set on successful state change
"""

from __future__ import annotations

import tempfile
from dataclasses import replace
from pathlib import Path

import pytest

from project_tracker.core.enums import CRState, DroneState
from project_tracker.core.models import DroneTicket, ProjectMetadata
from project_tracker.infrastructure.metadata_store import MetadataStore
from project_tracker.infrastructure.settings_store import SettingsStore


@pytest.fixture
def temp_project_with_drones():
    """Temp project with drone tickets in varied states."""
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        proj_dir = root / "2024" / "UAT_PREPARE" / "test-drones"
        proj_dir.mkdir(parents=True)

        metadata = ProjectMetadata(
            project_name="test-drones",
            cr_state=CRState.APPROVED,
            drone_tickets=[
                DroneTicket(
                    subfolder_name="sub1",
                    drone_link="https://drone.test/D-100",
                    drone_state=DroneState.UAT,
                    owner="Alice",
                ),
                DroneTicket(
                    subfolder_name="sub2",
                    drone_link="https://drone.test/D-200",
                    drone_state=DroneState.APPROVED,
                    owner="Bob",
                ),
                DroneTicket(
                    subfolder_name="sub3",
                    drone_link="",
                    drone_state=DroneState.UAT,
                    owner="Carol",
                ),
            ],
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
def js_api(temp_project_with_drones):
    from project_tracker import app_web

    return app_web.create_js_api(settings_store=temp_project_with_drones["settings_store"])


# ── valid transition ────────────────────────────────────────────────────


def test_valid_transition_succeeds_and_persists(js_api, temp_project_with_drones):
    """UAT -> PENDING_APPROVAL succeeds and new state persists."""
    path = str(temp_project_with_drones["project_path"])
    result = js_api.drone_update(path, 0, {"drone_state": "PENDING APPROVAL"})
    assert result["ok"] is True, f"Expected ok=True, got {result}"

    store = temp_project_with_drones["metadata_store"]
    metadata = store.read(temp_project_with_drones["project_path"])
    assert metadata.drone_tickets[0].drone_state == DroneState.PENDING_APPROVAL


def test_state_updated_at_set_on_success(js_api, temp_project_with_drones):
    """drone_state_updated_at populated on successful state change."""
    path = str(temp_project_with_drones["project_path"])
    js_api.drone_update(path, 0, {"drone_state": "PENDING APPROVAL"})

    store = temp_project_with_drones["metadata_store"]
    metadata = store.read(temp_project_with_drones["project_path"])
    assert metadata.drone_tickets[0].drone_state_updated_at is not None


# ── invalid transition ──────────────────────────────────────────────────


def test_invalid_transition_fails_controlled(js_api, temp_project_with_drones):
    """UAT -> FINISHED is not allowed; controlled failure, no state change."""
    path = str(temp_project_with_drones["project_path"])
    result = js_api.drone_update(path, 0, {"drone_state": "FINISHED"})
    assert result["ok"] is False

    store = temp_project_with_drones["metadata_store"]
    metadata = store.read(temp_project_with_drones["project_path"])
    assert metadata.drone_tickets[0].drone_state == DroneState.UAT


def test_empty_link_with_state_fails(js_api, temp_project_with_drones):
    """drone_state change requires non-empty drone_link (guard)."""
    path = str(temp_project_with_drones["project_path"])
    # index 2 has empty drone_link, state UAT
    result = js_api.drone_update(path, 2, {"drone_state": "PENDING APPROVAL"})
    assert result["ok"] is False

    store = temp_project_with_drones["metadata_store"]
    metadata = store.read(temp_project_with_drones["project_path"])
    assert metadata.drone_tickets[2].drone_state == DroneState.UAT


def test_in_progress_manual_target_fails(js_api, temp_project_with_drones):
    """APPROVED -> IN-PROGRESS is automatic-only; manual target rejected."""
    path = str(temp_project_with_drones["project_path"])
    # index 1 has state APPROVED
    result = js_api.drone_update(path, 1, {"drone_state": "IN-PROGRESS"})
    assert result["ok"] is False

    store = temp_project_with_drones["metadata_store"]
    metadata = store.read(temp_project_with_drones["project_path"])
    assert metadata.drone_tickets[1].drone_state == DroneState.APPROVED


# ── E.2 backward compat ──────────────────────────────────────────────────


def test_update_without_state_still_works(js_api, temp_project_with_drones):
    """Field-only update (no drone_state) behaves as E.2 and leaves state."""
    path = str(temp_project_with_drones["project_path"])
    result = js_api.drone_update(path, 0, {"drone_link": "https://drone.test/D-101", "owner": "Zoe"})
    assert result["ok"] is True

    store = temp_project_with_drones["metadata_store"]
    metadata = store.read(temp_project_with_drones["project_path"])
    assert metadata.drone_tickets[0].drone_link == "https://drone.test/D-101"
    assert metadata.drone_tickets[0].owner == "Zoe"
    assert metadata.drone_tickets[0].drone_state == DroneState.UAT
    assert metadata.drone_tickets[0].drone_state_updated_at is None
