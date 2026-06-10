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

import sys
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


@pytest.fixture(autouse=True)
def _purge_webview_imports():
    """Restore ``sys.modules`` so import-purity tests stay order-independent.

    Importing ``app_web`` / calling ``create_js_api`` may pull ``webview``
    (pywebview) into ``sys.modules`` on platforms where it is installed. Other
    tests (test_phase_c_*) assert ``"webview" not in sys.modules``; since this
    module sorts before them, leaving the import would make the suite fail by
    collection order. Mirrors the guard in test_bridge_contract_guard.py.
    """
    before = set(sys.modules)
    try:
        yield
    finally:
        added = [name for name in sys.modules if name not in before]
        for name in added:
            if name == "webview" or name.startswith("webview."):
                sys.modules.pop(name, None)
        sys.modules.pop("project_tracker.app_web", None)
        pkg = sys.modules.get("project_tracker")
        if pkg is not None and hasattr(pkg, "app_web"):
            try:
                delattr(pkg, "app_web")
            except AttributeError:
                pass


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


def test_apply_auto_move_blocked_guard_returns_banner_and_does_not_move(
    adapter, temp_project_approved_uat
):
    """A blocked structural guard returns a banner reason and the folder stays put."""
    store = temp_project_approved_uat["metadata_store"]
    proj_dir = temp_project_approved_uat["project_path"]
    root = temp_project_approved_uat["root"]

    # CR APPROVED -> resolve_auto_move returns PROD_READY, but blanking the
    # cr_link and dropping the dates makes the prod-ready structural guard fail.
    metadata = store.read(proj_dir)
    metadata.cr_state = CRState.APPROVED
    metadata.cr_link = ""
    metadata.start_datetime = None
    metadata.end_datetime = None
    metadata.drone_tickets = []
    store.write(proj_dir, metadata)

    result = adapter._apply_auto_move(proj_dir)

    assert result is not None
    assert "banner" in result
    assert result["banner"], "Banner reason must be a non-empty string"

    # Folder did NOT move: still in UAT_PREPARE, nothing in PROD_READY.
    assert proj_dir.is_dir(), "Project must remain in UAT_PREPARE when blocked"
    new_path = root / "2024" / ProjectState.PROD_READY.value / proj_dir.name
    assert not new_path.is_dir(), "Project must not appear in PROD_READY when blocked"

    # No AUTO_MOVE event pushed.
    assert not any(e["type"] == "AUTO_MOVE" for e in drain_events())


# ── Task 7 — wiring G1 + history + auto-move into the inline updates ──


from project_tracker.core.enums import DroneState  # noqa: E402
from project_tracker.core.models import DroneTicket  # noqa: E402


@pytest.fixture
def temp_project_pending_uat():
    """Project in UAT_PREPARE, CR PENDING_APPROVAL, move-ready dates.

    No drones by default; tests mutate metadata as needed. Mirrors
    ``temp_project_approved_uat`` but leaves CR short of APPROVED so the
    inline transition itself can be exercised.
    """
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        proj_dir = root / "2024" / "UAT_PREPARE" / "pending-proj"
        proj_dir.mkdir(parents=True)

        start = local_now() + timedelta(days=1)
        end = start + timedelta(days=2)
        metadata = ProjectMetadata(
            project_name="pending-proj",
            cr_link="https://cr.example.com/CR-700",
            cr_state=CRState.PENDING_APPROVAL,
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
def adapter_pending(temp_project_pending_uat):
    """Reach the inner _ProjectServiceAdapter for the pending-CR project."""
    from project_tracker import app_web

    api = app_web.create_js_api(
        settings_store=temp_project_pending_uat["settings_store"]
    )
    return api._project_service


def test_g1_blocks_cr_approved_with_unapproved_drone(
    adapter_pending, temp_project_pending_uat
):
    """G1: CR cannot go APPROVED while a drone is not APPROVED; no move."""
    store = temp_project_pending_uat["metadata_store"]
    proj_dir = temp_project_pending_uat["project_path"]
    root = temp_project_pending_uat["root"]

    metadata = store.read(proj_dir)
    metadata.drone_tickets = [
        DroneTicket(
            subfolder_name="drone-a",
            drone_link="https://drone.example.com/D-1",
            drone_state=DroneState.UAT,
        )
    ]
    store.write(proj_dir, metadata)

    with pytest.raises(ValueError) as exc:
        adapter_pending.update_cr_state(proj_dir, CRState.APPROVED.value)
    assert "drone" in str(exc.value).lower()

    # Folder did NOT move and CR state was not persisted as APPROVED.
    assert proj_dir.is_dir(), "Project must remain in UAT_PREPARE when G1 blocks"
    new_path = root / "2024" / ProjectState.PROD_READY.value / proj_dir.name
    assert not new_path.is_dir()
    assert store.read(proj_dir).cr_state == CRState.PENDING_APPROVAL


def test_cr_state_change_appends_history(adapter_pending, temp_project_pending_uat):
    """A no-move transition appends a CR_STATE_CHANGE history entry."""
    store = temp_project_pending_uat["metadata_store"]
    proj_dir = temp_project_pending_uat["project_path"]

    # Start from PENDING_SUBMISSION so the transition to PENDING_APPROVAL is a
    # genuine (non-moving) state change and stamps cr_pending_approval_at.
    metadata = store.read(proj_dir)
    metadata.cr_state = CRState.PENDING_SUBMISSION
    metadata.cr_pending_approval_at = None
    store.write(proj_dir, metadata)

    adapter_pending.update_cr_state(proj_dir, CRState.PENDING_APPROVAL.value)

    metadata = store.read(proj_dir)
    assert any(h.action == "CR_STATE_CHANGE" for h in metadata.history)
    assert metadata.cr_pending_approval_at is not None
    # Folder did not move (PENDING_APPROVAL has no auto-move target).
    assert proj_dir.is_dir()


def test_cr_link_paste_appends_history(adapter_pending, temp_project_pending_uat):
    """update_cr_link appends a CR_LINK history entry."""
    store = temp_project_pending_uat["metadata_store"]
    proj_dir = temp_project_pending_uat["project_path"]

    adapter_pending.update_cr_link(proj_dir, "https://cr.example.com/CR-999")

    metadata = store.read(proj_dir)
    assert any(h.action == "CR_LINK" for h in metadata.history)
    assert metadata.cr_link == "https://cr.example.com/CR-999"


def test_cr_approved_no_drones_auto_moves_and_history(
    adapter_pending, temp_project_pending_uat
):
    """CR PENDING_APPROVAL -> APPROVED with no drones moves to PROD_READY.

    End-to-end proof that update_cr_state now calls _apply_auto_move.
    """
    store = temp_project_pending_uat["metadata_store"]
    proj_dir = temp_project_pending_uat["project_path"]
    root = temp_project_pending_uat["root"]

    adapter_pending.update_cr_state(proj_dir, CRState.APPROVED.value)

    new_path = root / "2024" / ProjectState.PROD_READY.value / "pending-proj"
    assert new_path.is_dir(), f"Project not moved to PROD_READY: {new_path}"
    assert not proj_dir.is_dir(), "Old UAT_PREPARE folder still exists"

    # History persisted at the moved location.
    metadata = store.read(new_path)
    assert any(h.action == "CR_STATE_CHANGE" for h in metadata.history)

    # AUTO_MOVE event pushed by _apply_auto_move.
    assert any(e["type"] == "AUTO_MOVE" for e in drain_events())
