"""Task 6 — `_apply_auto_move` helper on the AppAPI adapter layer.

Proves the reusable helper, in isolation (Task 7 wires it into
update_cr_state), performs the auto-move after an inline CR state persist:

- when CR state is APPROVED in UAT_PREPARE, the project folder physically
  moves to the PROD_READY state folder (new path is a dir; old path is not),
- an "AUTO_MOVE" event is pushed onto the module-global EventQueue.

The helper is reached through the JsApi facade's inner adapter instance
(``js_api._project_service``), matching how the existing adapter tests reach
inner methods.
"""

from __future__ import annotations

import tempfile
from dataclasses import replace
from datetime import timedelta
from pathlib import Path

import pytest

from project_tracker.core.enums import CRState, ProjectState
from project_tracker.core.models import ProjectMetadata, local_now
from project_tracker.infrastructure.metadata_store import MetadataStore
from project_tracker.infrastructure.settings_store import SettingsStore
from project_tracker.web.event_queue import clear_events, drain_events


@pytest.fixture(autouse=True)
def _isolate_event_queue():
    """The EventQueue is module-global; clear it around every test."""
    clear_events()
    yield
    clear_events()


@pytest.fixture
def temp_project_approved_uat():
    """Project in UAT_PREPARE, CR APPROVED, no drones, move-ready dates."""
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        proj_dir = root / "2024" / "UAT_PREPARE" / "auto-move-proj"
        proj_dir.mkdir(parents=True)

        start = local_now() + timedelta(days=1)
        end = start + timedelta(days=2)
        metadata = ProjectMetadata(
            project_name="auto-move-proj",
            cr_link="https://cr.example.com/CR-500",
            cr_state=CRState.APPROVED,
            start_datetime=start,
            end_datetime=end,
        )
        store = MetadataStore()
        store.write(proj_dir, metadata)

        settings = SettingsStore(config_dir=root / "config")
        settings.write(replace(settings.read(), root_folder=root))

        yield {
            "root": root,
            "project_path": proj_dir,
            "metadata_store": store,
            "settings_store": settings,
        }


@pytest.fixture
def adapter(temp_project_approved_uat):
    """Reach the inner _ProjectServiceAdapter through the JsApi facade."""
    from project_tracker import app_web

    api = app_web.create_js_api(
        settings_store=temp_project_approved_uat["settings_store"]
    )
    return api._project_service


def test_apply_auto_move_moves_folder_to_prod_ready(adapter, temp_project_approved_uat):
    """_apply_auto_move physically moves the folder UAT_PREPARE -> PROD_READY."""
    proj_dir = temp_project_approved_uat["project_path"]
    root = temp_project_approved_uat["root"]

    result = adapter._apply_auto_move(proj_dir)

    # No structural-guard block: helper returns None on a successful move.
    assert result is None, f"Expected None on successful move, got {result}"

    old_path = proj_dir
    new_path = root / "2024" / ProjectState.PROD_READY.value / "auto-move-proj"
    assert new_path.is_dir(), f"Project not found in PROD_READY: {new_path}"
    assert not old_path.is_dir(), f"Old UAT_PREPARE folder still exists: {old_path}"


def test_apply_auto_move_pushes_auto_move_event(adapter, temp_project_approved_uat):
    """_apply_auto_move pushes an AUTO_MOVE event onto the EventQueue."""
    proj_dir = temp_project_approved_uat["project_path"]

    adapter._apply_auto_move(proj_dir)

    events = drain_events()
    auto_move = [e for e in events if e["type"] == "AUTO_MOVE"]
    assert len(auto_move) == 1, f"Expected one AUTO_MOVE event, got {events}"
    payload = auto_move[0]["payload"]
    assert payload["from_state"] == ProjectState.UAT_PREPARE.value
    assert payload["to_state"] == ProjectState.PROD_READY.value


def test_apply_auto_move_no_target_is_noop(adapter, temp_project_approved_uat):
    """When CR state implies no move, the helper is a no-op (no move, no event)."""
    store = temp_project_approved_uat["metadata_store"]
    proj_dir = temp_project_approved_uat["project_path"]

    # PENDING_SUBMISSION has no folder target -> resolve_auto_move returns None.
    metadata = store.read(proj_dir)
    metadata.cr_state = CRState.PENDING_SUBMISSION
    store.write(proj_dir, metadata)

    result = adapter._apply_auto_move(proj_dir)

    assert result is None
    assert proj_dir.is_dir(), "Folder must not move when there is no target"
    assert drain_events() == []
