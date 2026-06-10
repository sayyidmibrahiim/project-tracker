from datetime import datetime, timedelta, timezone

from project_tracker.core.enums import CRState, DroneState
from project_tracker.core.models import DroneTicket, ProjectMetadata
from project_tracker.core.rules import (
    compute_h10,
    h10_reminder_due,
    validate_cr_approved_requires_drones,
)

H10_TZ = timezone(timedelta(hours=7))


def _drone(state: DroneState) -> DroneTicket:
    return DroneTicket(drone_link="https://drone/x", drone_state=state)


def test_g1_no_drones_allows_approved():
    result = validate_cr_approved_requires_drones([])
    assert result.allowed is True
    assert result.failed_guards == []


def test_g1_all_drones_approved_allows():
    result = validate_cr_approved_requires_drones(
        [_drone(DroneState.APPROVED), _drone(DroneState.APPROVED)]
    )
    assert result.allowed is True


def test_g1_one_drone_not_approved_blocks():
    result = validate_cr_approved_requires_drones(
        [_drone(DroneState.APPROVED), _drone(DroneState.IN_PROGRESS)]
    )
    assert result.allowed is False
    assert "1 drone" in result.failed_guards[0]


def test_g1_multiple_not_approved_counts():
    result = validate_cr_approved_requires_drones(
        [_drone(DroneState.UAT), _drone(DroneState.PENDING_APPROVAL)]
    )
    assert result.allowed is False
    assert "2 drone" in result.failed_guards[0]


def _h10_md(start, cr_state, drones=None):
    return ProjectMetadata(
        project_name="X",
        start_datetime=start,
        cr_state=cr_state,
        drone_tickets=drones or [],
    )


def test_compute_h10_none_when_no_start():
    assert compute_h10(_h10_md(None, CRState.PENDING_APPROVAL), reminder_days=10) is None


def test_compute_h10_subtracts_days():
    start = datetime(2026, 6, 20, 9, 0, tzinfo=H10_TZ)
    assert compute_h10(_h10_md(start, CRState.PENDING_APPROVAL), reminder_days=10) == datetime(
        2026, 6, 10, 9, 0, tzinfo=H10_TZ
    )


def test_h10_due_when_past_and_cr_not_approved():
    start = datetime(2026, 6, 15, 9, 0, tzinfo=H10_TZ)  # H-10 = Jun 5
    now = datetime(2026, 6, 10, 9, 0, tzinfo=H10_TZ)
    assert h10_reminder_due(_h10_md(start, CRState.PENDING_APPROVAL), now=now, reminder_days=10) is True


def test_h10_not_due_before_h10():
    start = datetime(2026, 6, 30, 9, 0, tzinfo=H10_TZ)  # H-10 = Jun 20
    now = datetime(2026, 6, 10, 9, 0, tzinfo=H10_TZ)
    assert h10_reminder_due(_h10_md(start, CRState.PENDING_APPROVAL), now=now, reminder_days=10) is False


def test_h10_not_due_when_cr_and_drones_approved():
    start = datetime(2026, 6, 15, 9, 0, tzinfo=H10_TZ)
    now = datetime(2026, 6, 10, 9, 0, tzinfo=H10_TZ)
    md = _h10_md(start, CRState.APPROVED, [DroneTicket(drone_link="x", drone_state=DroneState.APPROVED)])
    assert h10_reminder_due(md, now=now, reminder_days=10) is False


def test_h10_due_when_cr_approved_but_drone_not():
    start = datetime(2026, 6, 15, 9, 0, tzinfo=H10_TZ)
    now = datetime(2026, 6, 10, 9, 0, tzinfo=H10_TZ)
    md = _h10_md(start, CRState.APPROVED, [DroneTicket(drone_link="x", drone_state=DroneState.UAT)])
    assert h10_reminder_due(md, now=now, reminder_days=10) is True


def test_h10_not_due_when_no_start():
    now = datetime(2026, 6, 10, 9, 0, tzinfo=H10_TZ)
    assert h10_reminder_due(_h10_md(None, CRState.PENDING_APPROVAL), now=now, reminder_days=10) is False


def test_h10_due_exactly_at_h10_boundary():
    # now == H-10 is inclusive ("now >= H-10") -> due
    start = datetime(2026, 6, 20, 9, 0, tzinfo=H10_TZ)
    now = datetime(2026, 6, 10, 9, 0, tzinfo=H10_TZ)  # exactly H-10
    assert h10_reminder_due(
        _h10_md(start, CRState.PENDING_APPROVAL), now=now, reminder_days=10
    ) is True
