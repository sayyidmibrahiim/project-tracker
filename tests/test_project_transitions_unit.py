"""Unit tests for ProjectService folder-state transitions (Task 5.4).

Each test builds a temporary year/state folder tree under ``tmp_path`` with a
real ``project_data.json`` and exercises a single transition path:

- A project starting within the old T-10 window now moves to PROD_READY
  (T-10 is a non-blocking H-10 reminder, not a hard guard).
- override_t10 is moot now that T-10 no longer blocks the move.
- ``move_to_implemented`` guard failure leaves the project in PROD_READY.
- IMPLEMENTED projects reject POSTPONED/CANCELED transitions.
- A successful transition is reflected in the Cache_Db after a rebuild.

All filesystem mutations target ``tmp_path`` only; no real folders are touched.

Covers Requirements 4.2, 4.3, 4.4, 4.5, 4.10, 4.11.
"""

from __future__ import annotations

from datetime import timedelta
from pathlib import Path

import pytest

from project_tracker.core.enums import CRState, DroneState, ProjectState
from project_tracker.core.exceptions import InvalidTransitionError
from project_tracker.core.models import (
    AppSettings,
    DroneTicket,
    ProjectMetadata,
    local_now,
)
from project_tracker.core.rules import TransitionGuardResult
from project_tracker.infrastructure.cache_db import CacheDb, rebuild_year_cache
from project_tracker.infrastructure.metadata_store import MetadataStore
from project_tracker.services.project_service import ProjectService

YEAR = "2026"
PROJECT_NAME = "PROJECT_A"
SETTINGS = AppSettings(display_name="Tester")


def _create_project(
    tmp_path: Path,
    folder_state: ProjectState,
    metadata: ProjectMetadata,
) -> Path:
    """Materialize a project folder tree (year/state/name) with metadata."""
    project_path = tmp_path / YEAR / folder_state.value / PROJECT_NAME
    project_path.mkdir(parents=True)
    MetadataStore().save(project_path, metadata)
    return project_path


def _uat_metadata_within_t10_window() -> ProjectMetadata:
    """Metadata where every UAT→PROD_READY guard passes.

    ``cr_pending_approval_at`` is later than ``start_datetime - 10 days``, i.e.
    the project starts within the old T-10 window. T-10 is no longer a hard
    guard (it is a non-blocking H-10 reminder), so the move must now succeed.
    """
    now = local_now()
    return ProjectMetadata(
        project_name=PROJECT_NAME,
        start_datetime=now + timedelta(days=5),
        end_datetime=now + timedelta(days=6),
        cr_link="https://cr.test/?CRNumber=CR123",
        cr_state=CRState.APPROVED,
        cr_pending_approval_at=now,  # within old T-10 window; no longer blocks
    )


def _uat_metadata_all_pass() -> ProjectMetadata:
    """Metadata where every UAT→PROD_READY guard, including T-10, passes."""
    now = local_now()
    return ProjectMetadata(
        project_name=PROJECT_NAME,
        start_datetime=now + timedelta(days=15),
        end_datetime=now + timedelta(days=16),
        cr_link="https://cr.test/?CRNumber=CR123",
        cr_state=CRState.APPROVED,
        cr_pending_approval_at=now,  # <= (start - 10d) → T-10 passes
    )


def test_within_t10_window_no_longer_blocks_move_to_prod_ready(tmp_path: Path) -> None:
    """T-10 is now a non-blocking H-10 reminder; the move succeeds (Req 4.3)."""
    project_path = _create_project(
        tmp_path, ProjectState.UAT_PREPARE, _uat_metadata_within_t10_window()
    )
    service = ProjectService(MetadataStore())
    now = local_now()

    moved_path = service.move_to_prod_ready(project_path, SETTINGS, now, threshold_days=10)

    # The move now succeeds: PROD_READY folder is created, source is gone.
    assert isinstance(moved_path, Path)
    assert moved_path == tmp_path / YEAR / ProjectState.PROD_READY.value / PROJECT_NAME
    assert not project_path.exists()


def test_within_t10_window_move_succeeds_without_override_flag(tmp_path: Path) -> None:
    """With T-10 removed, override_t10 is moot; move succeeds and is not flagged (Req 4.4)."""
    project_path = _create_project(
        tmp_path, ProjectState.UAT_PREPARE, _uat_metadata_within_t10_window()
    )
    service = ProjectService(MetadataStore())
    now = local_now()

    moved_path = service.move_to_prod_ready(
        project_path, SETTINGS, now, threshold_days=10, override_t10=True
    )

    assert isinstance(moved_path, Path)
    assert moved_path == tmp_path / YEAR / ProjectState.PROD_READY.value / PROJECT_NAME
    assert not project_path.exists()

    metadata = MetadataStore().load(moved_path)
    last = metadata.history[-1]
    assert last.action == "STATE_CHANGE"
    # No T-10 failure means the override path is never taken.
    assert last.override is False
    assert "T-10 override" not in last.detail
    assert last.user == "Tester"


def test_move_to_implemented_guard_failure_leaves_prod_ready(tmp_path: Path) -> None:
    """move_to_implemented blocks when CR state is not FINISHED (Req 4.5)."""
    metadata = ProjectMetadata(
        project_name=PROJECT_NAME,
        cr_state=CRState.APPROVED,  # not FINISHED → guard fails
        drone_tickets=[
            DroneTicket(drone_link="https://drone.test/D-1", drone_state=DroneState.APPROVED)
        ],
    )
    project_path = _create_project(tmp_path, ProjectState.PROD_READY, metadata)
    service = ProjectService(MetadataStore())

    result = service.move_to_implemented(project_path, SETTINGS, local_now())

    assert isinstance(result, TransitionGuardResult)
    assert result.allowed is False
    assert any("FINISHED" in guard for guard in result.failed_guards)
    # Project remains in PROD_READY; IMPLEMENTED folder was never created.
    assert project_path.exists()
    assert not (tmp_path / YEAR / ProjectState.IMPLEMENTED.value / PROJECT_NAME).exists()


@pytest.mark.parametrize("transition", ["postpone_project", "cancel_project"])
def test_implemented_rejects_postpone_and_cancel(tmp_path: Path, transition: str) -> None:
    """IMPLEMENTED is a terminal state; POSTPONE/CANCEL are rejected (Req 4.10)."""
    project_path = _create_project(
        tmp_path,
        ProjectState.IMPLEMENTED,
        ProjectMetadata(project_name=PROJECT_NAME, cr_state=CRState.FINISHED),
    )
    service = ProjectService(MetadataStore())
    method = getattr(service, transition)

    with pytest.raises(InvalidTransitionError):
        method(project_path, SETTINGS)

    # State unchanged: still in IMPLEMENTED, no POSTPONED/CANCELED folder created.
    assert project_path.exists()
    assert not (tmp_path / YEAR / ProjectState.POSTPONED.value / PROJECT_NAME).exists()
    assert not (tmp_path / YEAR / ProjectState.CANCELED.value / PROJECT_NAME).exists()


def test_cache_updated_after_successful_transition(tmp_path: Path) -> None:
    """A successful transition is reflected in the Cache_Db on rebuild (Req 4.11)."""
    project_path = _create_project(
        tmp_path, ProjectState.UAT_PREPARE, _uat_metadata_all_pass()
    )
    service = ProjectService(MetadataStore())
    cache = CacheDb(tmp_path / "cache.db")
    cache.initialize()
    year_path = tmp_path / YEAR

    # Seed the cache from the pre-move tree: project shows UAT_PREPARE.
    rebuild_year_cache(cache, year_path, MetadataStore())
    before = {row.project_name: row.project_state for row in cache.list_projects(YEAR)}
    assert before[PROJECT_NAME] == ProjectState.UAT_PREPARE

    moved_path = service.move_to_prod_ready(
        project_path, SETTINGS, local_now(), threshold_days=10
    )
    assert isinstance(moved_path, Path)

    # Rebuild the year cache as the adapter does on success.
    rebuild_year_cache(cache, year_path, MetadataStore())
    after = {row.project_name: row.project_state for row in cache.list_projects(YEAR)}
    assert after[PROJECT_NAME] == ProjectState.PROD_READY
