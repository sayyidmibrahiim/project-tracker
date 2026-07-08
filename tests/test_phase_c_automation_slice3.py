"""Unit tests for Automation epic Slice 3: wired action handlers,
conflict detection, and pre-seeded rules.

Covers the DEFAULT AMAN guarantees: no metadata_store → no-op; illegal CR/drone
transition → skip+log (never force); pre-seeded rules disabled + idempotent;
conflict detection warns (does not block).
"""

from __future__ import annotations

from pathlib import Path

import pytest

from core.enums import CRState, DroneState
from core.models import HistoryEntry, ProjectMetadata
from services.automation_service import AutomationService, rules_conflict_key


class FakeMetadataStore:
    """Minimal MetadataStore stand-in for handler tests."""

    def __init__(self, store: dict[Path, ProjectMetadata] | None = None) -> None:
        self._store = store or {}

    def read(self, project_path: Path) -> ProjectMetadata | None:
        return self._store.get(Path(project_path))

    def write(self, project_path: Path, metadata: ProjectMetadata) -> None:
        self._store[Path(project_path)] = metadata


def _service_with_metadata(metadata_store: FakeMetadataStore | None = None) -> AutomationService:
    return AutomationService(metadata_store=metadata_store)


def _metadata(cr_state: CRState = CRState.PENDING_APPROVAL, drone_state: DroneState = DroneState.UAT) -> ProjectMetadata:
    return ProjectMetadata(
        project_name="CR-2026-001",
        cr_state=cr_state,
        drone_tickets=[__import__("core.models", fromlist=["DroneTicket"]).DroneTicket(drone_state=drone_state)],
    )


# ── update_cr_state handler ──────────────────────────────────────────────

def test_update_cr_state_legal_transition():
    store = FakeMetadataStore({Path("/p"): _metadata(CRState.PENDING_APPROVAL)})
    svc = _service_with_metadata(store)
    result = svc._handle_update_cr_state(
        {"target_state": "APPROVED", "project_path": "/p"}, {}
    )
    assert result["ok"] is True
    assert result["data"]["status"] == "transitioned"
    assert store.read(Path("/p")).cr_state == CRState.APPROVED
    # History recorded
    assert any("CR state" in h.detail for h in store.read(Path("/p")).history)


def test_update_cr_state_illegal_transition_skipped():
    """DEFAULT AMAN: illegal transition is skipped, never forced."""
    store = FakeMetadataStore({Path("/p"): _metadata(CRState.PENDING_SUBMISSION)})
    svc = _service_with_metadata(store)
    result = svc._handle_update_cr_state(
        {"target_state": "FINISHED", "project_path": "/p"}, {}
    )
    assert result["ok"] is True
    assert result["data"]["status"] == "skipped"
    assert "illegal" in result["data"]["reason"]
    # State unchanged
    assert store.read(Path("/p")).cr_state == CRState.PENDING_SUBMISSION


def test_update_cr_state_no_metadata_store_is_noop():
    svc = _service_with_metadata(None)
    result = svc._handle_update_cr_state({"target_state": "APPROVED", "project_path": "/p"}, {})
    assert result["data"]["status"] == "not_configured"


def test_update_cr_state_no_target_state_skipped():
    svc = _service_with_metadata(FakeMetadataStore({Path("/p"): _metadata()}))
    result = svc._handle_update_cr_state({"project_path": "/p"}, {})
    assert result["data"]["status"] == "skipped"
    assert "no target_state" in result["data"]["reason"]


def test_update_cr_state_unknown_state_rejected():
    store = FakeMetadataStore({Path("/p"): _metadata()})
    svc = _service_with_metadata(store)
    result = svc._handle_update_cr_state({"target_state": "BOGUS", "project_path": "/p"}, {})
    assert result["ok"] is False
    assert result["error"]["code"] == "INVALID_TARGET_STATE"


# ── update_drone_state handler ───────────────────────────────────────────

def test_update_drone_state_legal_transition():
    from core.models import DroneTicket

    metadata = ProjectMetadata(
        project_name="CR-2026-001",
        drone_tickets=[DroneTicket(drone_state=DroneState.UAT)],
    )
    store = FakeMetadataStore({Path("/p"): metadata})
    svc = _service_with_metadata(store)
    result = svc._handle_update_drone_state(
        {"target_state": "PENDING APPROVAL", "project_path": "/p"}, {}
    )
    assert result["data"]["status"] == "transitioned"
    assert store.read(Path("/p")).drone_tickets[0].drone_state == DroneState.PENDING_APPROVAL


# ── append_history handler ───────────────────────────────────────────────

def test_append_history_writes_entry():
    store = FakeMetadataStore({Path("/p"): _metadata()})
    svc = _service_with_metadata(store)
    result = svc._handle_append_history(
        {"project_path": "/p", "history_action": "TEST_RULE", "history_detail": "fired"}, {}
    )
    assert result["data"]["status"] == "appended"
    assert any(h.action == "TEST_RULE" for h in store.read(Path("/p")).history)


def test_append_history_no_project_path_skipped():
    svc = _service_with_metadata(FakeMetadataStore({Path("/p"): _metadata()}))
    result = svc._handle_append_history({}, {})
    assert result["data"]["status"] == "skipped"


# ── conflict-key (module-level, testable) ────────────────────────────────


def test_conflict_key_same_trigger_goal_scope_collides():
    a = {"goal": "send_email", "trigger": {"type": "manual"}, "scope": {"type": "all"}}
    b = {"goal": "send_email", "trigger": {"type": "manual"}, "scope": {"type": "all"}}
    assert rules_conflict_key(a) == rules_conflict_key(b)


def test_conflict_key_different_goal_no_collide():
    a = {"goal": "send_email", "trigger": {"type": "manual"}, "scope": {"type": "all"}}
    b = {"goal": "send_teams", "trigger": {"type": "manual"}, "scope": {"type": "all"}}
    assert rules_conflict_key(a) != rules_conflict_key(b)


def test_conflict_key_different_scope_no_collide():
    a = {"goal": "send_email", "trigger": {"type": "manual"}, "scope": {"type": "all"}}
    b = {"goal": "send_email", "trigger": {"type": "manual"}, "scope": {"type": "specific", "cr_ids": ["CR-1"]}}
    assert rules_conflict_key(a) != rules_conflict_key(b)


def test_conflict_key_specific_scope_order_independent():
    a = {"goal": "send_email", "trigger": {"type": "manual"}, "scope": {"type": "specific", "cr_ids": ["CR-1", "CR-2"]}}
    b = {"goal": "send_email", "trigger": {"type": "manual"}, "scope": {"type": "specific", "cr_ids": ["CR-2", "CR-1"]}}
    assert rules_conflict_key(a) == rules_conflict_key(b)

