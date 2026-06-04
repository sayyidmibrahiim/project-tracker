"""Phase C.3c2 — ProjectService auto IN-PROGRESS cleanup tests."""

from datetime import datetime, timedelta, timezone
from pathlib import Path

from project_tracker.core.enums import CRState, DroneState
from project_tracker.core.models import AppSettings, DroneTicket, ProjectMetadata
from project_tracker.services.project_service import ProjectService


class FakeMetadataStore:
    def __init__(self, metadata: ProjectMetadata) -> None:
        self.metadata = metadata
        self.saved: list[tuple[Path, ProjectMetadata]] = []

    def load(self, project_path: Path) -> ProjectMetadata:
        return self.metadata

    def save(self, project_path: Path, metadata: ProjectMetadata) -> None:
        self.saved.append((project_path, metadata))


def _metadata(
    *,
    start_datetime: datetime,
    end_datetime: datetime,
    cr_state: CRState = CRState.APPROVED,
    drone_tickets: list[DroneTicket] | None = None,
) -> ProjectMetadata:
    return ProjectMetadata(
        project_name="PROJECT_A",
        start_datetime=start_datetime,
        end_datetime=end_datetime,
        cr_state=cr_state,
        drone_tickets=drone_tickets or [],
    )


def _service(metadata: ProjectMetadata) -> tuple[ProjectService, FakeMetadataStore]:
    store = FakeMetadataStore(metadata)
    return ProjectService(metadata_store=store), store


def test_cr_approved_at_end_boundary_auto_starts_and_saves_history():
    now = datetime(2026, 1, 2, 3, 4, tzinfo=timezone.utc)
    metadata = _metadata(
        start_datetime=now - timedelta(hours=1),
        end_datetime=now,
        cr_state=CRState.APPROVED,
    )
    service, store = _service(metadata)

    changed = service.auto_transition_in_progress(Path("/tmp/project"), AppSettings(), current_time=now)

    assert changed is True
    assert metadata.cr_state == CRState.IN_PROGRESS
    assert metadata.cr_state_updated_at == now
    assert metadata.updated_at == now
    assert len(metadata.history) == 1
    assert metadata.history[0].action == "AUTO_TRANSITION"
    assert metadata.history[0].detail == "APPROVED → IN-PROGRESS"
    assert metadata.history[0].user == "System"
    assert store.saved == [(Path("/tmp/project"), metadata)]


def test_drone_approved_with_link_auto_starts_even_when_cr_not_approved():
    now = datetime(2026, 1, 2, 3, 4, tzinfo=timezone.utc)
    drone = DroneTicket(
        subfolder_name="api",
        drone_link="https://drone.local/D-SSIDBI-1",
        drone_state=DroneState.APPROVED,
    )
    metadata = _metadata(
        start_datetime=now,
        end_datetime=now + timedelta(hours=1),
        cr_state=CRState.IN_PROGRESS,
        drone_tickets=[drone],
    )
    service, store = _service(metadata)

    changed = service.auto_transition_in_progress(Path("/tmp/project"), AppSettings(), current_time=now)

    assert changed is True
    assert metadata.cr_state == CRState.IN_PROGRESS
    assert drone.drone_state == DroneState.IN_PROGRESS
    assert drone.drone_state_updated_at == now
    assert metadata.history[0].detail == "Drone api: APPROVED → IN-PROGRESS"
    assert len(store.saved) == 1


def test_drone_approved_without_link_does_not_auto_start_or_save():
    now = datetime(2026, 1, 2, 3, 4, tzinfo=timezone.utc)
    drone = DroneTicket(
        subfolder_name="api",
        drone_link="   ",
        drone_state=DroneState.APPROVED,
    )
    metadata = _metadata(
        start_datetime=now,
        end_datetime=now + timedelta(hours=1),
        cr_state=CRState.IN_PROGRESS,
        drone_tickets=[drone],
    )
    service, store = _service(metadata)

    changed = service.auto_transition_in_progress(Path("/tmp/project"), AppSettings(), current_time=now)

    assert changed is False
    assert drone.drone_state == DroneState.APPROVED
    assert metadata.history == []
    assert store.saved == []


def test_outside_deployment_window_returns_false_without_save():
    now = datetime(2026, 1, 2, 3, 4, tzinfo=timezone.utc)
    metadata = _metadata(
        start_datetime=now + timedelta(minutes=1),
        end_datetime=now + timedelta(hours=1),
        cr_state=CRState.APPROVED,
    )
    service, store = _service(metadata)

    changed = service.auto_transition_in_progress(Path("/tmp/project"), AppSettings(), current_time=now)

    assert changed is False
    assert metadata.cr_state == CRState.APPROVED
    assert metadata.history == []
    assert store.saved == []


def test_no_eligible_cr_or_drone_returns_false_without_save():
    now = datetime(2026, 1, 2, 3, 4, tzinfo=timezone.utc)
    drone = DroneTicket(
        subfolder_name="api",
        drone_link="https://drone.local/D-SSIDBI-1",
        drone_state=DroneState.UAT,
    )
    metadata = _metadata(
        start_datetime=now,
        end_datetime=now + timedelta(hours=1),
        cr_state=CRState.PENDING_APPROVAL,
        drone_tickets=[drone],
    )
    service, store = _service(metadata)

    changed = service.auto_transition_in_progress(Path("/tmp/project"), AppSettings(), current_time=now)

    assert changed is False
    assert metadata.history == []
    assert store.saved == []


def test_multiple_changes_share_one_history_entry_and_one_save():
    now = datetime(2026, 1, 2, 3, 4, tzinfo=timezone.utc)
    drone = DroneTicket(
        subfolder_name=None,
        drone_link="https://drone.local/D-SSIDBI-1",
        drone_state=DroneState.APPROVED,
    )
    metadata = _metadata(
        start_datetime=now,
        end_datetime=now + timedelta(hours=1),
        cr_state=CRState.APPROVED,
        drone_tickets=[drone],
    )
    service, store = _service(metadata)

    changed = service.auto_transition_in_progress(Path("/tmp/project"), AppSettings(), current_time=now)

    assert changed is True
    assert metadata.cr_state == CRState.IN_PROGRESS
    assert drone.drone_state == DroneState.IN_PROGRESS
    assert len(metadata.history) == 1
    assert metadata.history[0].detail == "CR: APPROVED → IN-PROGRESS | Drone ticket 1: APPROVED → IN-PROGRESS"
    assert len(store.saved) == 1
