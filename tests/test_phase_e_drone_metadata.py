"""Phase E.2 — Drone metadata CRUD via create_js_api() production runtime.

Tests prove:
- project_get exposes drone_tickets list (not just count)
- drone_add appends to metadata and persists
- drone_update edits fields at index and persists
- drone_delete removes at index and persists
- drone_state is NOT changed by drone_update (state guards respected)
- folder moves remain deferred
"""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

from project_tracker.core.enums import CRState, DroneState
from project_tracker.core.models import DroneTicket, ProjectMetadata
from project_tracker.infrastructure.metadata_store import MetadataStore
from project_tracker.infrastructure.settings_store import SettingsStore


@pytest.fixture
def temp_project_with_drones():
    """Temp project with 2 existing drone tickets."""
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
                    drone_state=DroneState.PENDING_APPROVAL,
                    owner="Bob",
                ),
            ],
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
def js_api(temp_project_with_drones):
    from project_tracker import app_web

    return app_web.create_js_api(settings_store=temp_project_with_drones["settings_store"])


# ── project_get exposes drone_tickets list ─────────────────────────────


def test_project_get_includes_drone_tickets_list(js_api, temp_project_with_drones):
    """project_get data must include drone_tickets array, not just count."""
    path = str(temp_project_with_drones["project_path"])
    result = js_api.project_get(path)
    assert result["ok"] is True
    data = result["data"]
    assert "drone_tickets" in data, f"Expected drone_tickets in data: {data.keys()}"
    assert isinstance(data["drone_tickets"], list)
    assert len(data["drone_tickets"]) == 2


def test_project_get_drone_ticket_shape(js_api, temp_project_with_drones):
    """drone_tickets entries have expected fields."""
    path = str(temp_project_with_drones["project_path"])
    result = js_api.project_get(path)
    ticket = result["data"]["drone_tickets"][0]
    assert ticket["subfolder_name"] == "sub1"
    assert ticket["drone_link"] == "https://drone.test/D-100"
    assert ticket["drone_state"] == "UAT"
    assert ticket["owner"] == "Alice"


# ── drone_add ──────────────────────────────────────────────────────────


def test_drone_add_no_longer_unavailable(js_api, temp_project_with_drones):
    """drone_add must not return SERVICE_UNAVAILABLE."""
    path = str(temp_project_with_drones["project_path"])
    result = js_api.drone_add(path, {"drone_link": "https://drone.test/D-300", "owner": "Charlie"})
    assert result["ok"] is True, f"Expected ok=True, got {result}"


def test_drone_add_persists(js_api, temp_project_with_drones):
    """drone_add appends ticket and persists in metadata."""
    path = str(temp_project_with_drones["project_path"])
    js_api.drone_add(path, {"drone_link": "https://drone.test/D-300", "subfolder_name": "sub3", "owner": "Charlie"})

    store = temp_project_with_drones["metadata_store"]
    metadata = store.read(temp_project_with_drones["project_path"])
    assert len(metadata.drone_tickets) == 3
    assert metadata.drone_tickets[2].drone_link == "https://drone.test/D-300"
    assert metadata.drone_tickets[2].subfolder_name == "sub3"
    assert metadata.drone_tickets[2].owner == "Charlie"
    assert metadata.drone_tickets[2].drone_state == DroneState.UAT


# ── drone_update ────────────────────────────────────────────────────────


def test_drone_update_no_longer_unavailable(js_api, temp_project_with_drones):
    """drone_update must not return SERVICE_UNAVAILABLE."""
    path = str(temp_project_with_drones["project_path"])
    result = js_api.drone_update(path, 0, {"drone_link": "https://drone.test/D-101"})
    assert result["ok"] is True, f"Expected ok=True, got {result}"


def test_drone_update_persists_fields(js_api, temp_project_with_drones):
    """drone_update edits drone_link/owner/subfolder at index and persists."""
    path = str(temp_project_with_drones["project_path"])
    js_api.drone_update(path, 0, {"drone_link": "https://drone.test/D-101", "owner": "Zoe", "subfolder_name": "sub-new"})

    store = temp_project_with_drones["metadata_store"]
    metadata = store.read(temp_project_with_drones["project_path"])
    assert metadata.drone_tickets[0].drone_link == "https://drone.test/D-101"
    assert metadata.drone_tickets[0].owner == "Zoe"
    assert metadata.drone_tickets[0].subfolder_name == "sub-new"


def test_drone_update_does_not_change_state(js_api, temp_project_with_drones):
    """drone_update must NOT change drone_state even if passed."""
    path = str(temp_project_with_drones["project_path"])
    js_api.drone_update(path, 0, {"drone_state": "FINISHED"})

    store = temp_project_with_drones["metadata_store"]
    metadata = store.read(temp_project_with_drones["project_path"])
    assert metadata.drone_tickets[0].drone_state == DroneState.UAT


# ── drone_delete ────────────────────────────────────────────────────────


def test_drone_delete_no_longer_unavailable(js_api, temp_project_with_drones):
    """drone_delete must not return SERVICE_UNAVAILABLE."""
    path = str(temp_project_with_drones["project_path"])
    result = js_api.drone_delete(path, 1)
    assert result["ok"] is True, f"Expected ok=True, got {result}"


def test_drone_delete_removes_at_index(js_api, temp_project_with_drones):
    """drone_delete removes ticket at index and persists."""
    path = str(temp_project_with_drones["project_path"])
    js_api.drone_delete(path, 0)

    store = temp_project_with_drones["metadata_store"]
    metadata = store.read(temp_project_with_drones["project_path"])
    assert len(metadata.drone_tickets) == 1
    assert metadata.drone_tickets[0].drone_link == "https://drone.test/D-200"


# ── unrelated mutations still deferred ──────────────────────────────────


def test_folder_move_still_deferred(js_api):
    """Folder moves remain SERVICE_UNAVAILABLE."""
    result = js_api.folder_move_to_prod_ready("/tmp/x")
    assert result["ok"] is False


def test_cr_update_state_still_deferred(js_api):
    """CR state update still deferred (needs guarded service)."""
    result = js_api.cr_update_state("/tmp/x", "APPROVED")
    assert result["ok"] is False
