from datetime import datetime, timezone, timedelta

import pytest

from core.enums import CRState, DroneState
from core.models import DroneTicket, ProjectMetadata
from core.rules import (
    is_in_deployment_window,
    should_auto_start_cr,
    should_auto_start_drone,
    validate_prod_ready_to_implemented_transition,
    validate_t10,
    validate_uat_to_prod_ready_transition,
)

NOW = datetime(2026, 6, 3, 10, 0, tzinfo=timezone.utc)
START = datetime(2026, 6, 10, 10, 0, tzinfo=timezone.utc)
END = datetime(2026, 6, 10, 12, 0, tzinfo=timezone.utc)
WINDOW_START = datetime(2026, 6, 3, 10, 0, tzinfo=timezone.utc)
WINDOW_END = datetime(2026, 6, 3, 12, 0, tzinfo=timezone.utc)
WINDOW_NOW = datetime(2026, 6, 3, 11, 0, tzinfo=timezone.utc)
T10_PROOF = START - timedelta(days=10)
LATE_T10_PROOF = START - timedelta(days=9)


def _prod_ready_metadata(**overrides: object) -> ProjectMetadata:
    values = {
        "start_datetime": START,
        "end_datetime": END,
        "cr_link": "https://itsm.example.local/orderDetails?CRNumber=CR202604209900114",
        "cr_state": CRState.APPROVED,
        "cr_pending_approval_at": T10_PROOF,
        "drone_tickets": [],
    }
    values.update(overrides)
    return ProjectMetadata(**values)


def _implemented_metadata(**overrides: object) -> ProjectMetadata:
    values = {
        "start_datetime": START,
        "end_datetime": END,
        "cr_state": CRState.FINISHED,
        "drone_tickets": [],
    }
    values.update(overrides)
    return ProjectMetadata(**values)


@pytest.mark.parametrize(
    "cr_state",
    [
        CRState.PENDING_APPROVAL,
        CRState.APPROVED,
        CRState.IN_PROGRESS,
        CRState.FINISHED,
        CRState.POSTPONED,
        CRState.CANCELED,
    ],
)
def test_t10_missing_proof_fails_for_states_beyond_pending_submission(cr_state: CRState) -> None:
    metadata = ProjectMetadata(start_datetime=START, cr_state=cr_state, cr_pending_approval_at=None)

    result = validate_t10(metadata)

    assert result.passed is False
    assert result.reason is not None
    assert "cannot prove T-10" in result.reason


def test_t10_missing_proof_passes_neutral_for_pending_submission() -> None:
    metadata = ProjectMetadata(
        start_datetime=START,
        cr_state=CRState.PENDING_SUBMISSION,
        cr_pending_approval_at=None,
    )

    result = validate_t10(metadata)

    assert result.passed is True


def test_t10_on_time_proof_passes() -> None:
    metadata = ProjectMetadata(
        start_datetime=START,
        cr_state=CRState.APPROVED,
        cr_pending_approval_at=T10_PROOF,
    )

    result = validate_t10(metadata)

    assert result.passed is True


def test_t10_late_proof_fails() -> None:
    metadata = ProjectMetadata(
        start_datetime=START,
        cr_state=CRState.APPROVED,
        cr_pending_approval_at=LATE_T10_PROOF,
    )

    result = validate_t10(metadata)

    assert result.passed is False
    assert result.reason is not None
    assert "after T-10 deadline" in result.reason


def test_uat_to_prod_ready_valid_metadata_with_no_drone_tickets_passes() -> None:
    metadata = _prod_ready_metadata()

    result = validate_uat_to_prod_ready_transition(metadata, current_time=NOW)

    assert result.allowed is True
    assert result.failed_guards == []


def test_uat_to_prod_ready_missing_start_fails() -> None:
    metadata = _prod_ready_metadata(start_datetime=None)

    result = validate_uat_to_prod_ready_transition(metadata, current_time=NOW)

    assert result.allowed is False
    assert "Start datetime is required" in result.failed_guards


def test_uat_to_prod_ready_missing_end_fails() -> None:
    metadata = _prod_ready_metadata(end_datetime=None)

    result = validate_uat_to_prod_ready_transition(metadata, current_time=NOW)

    assert result.allowed is False
    assert "End datetime is required" in result.failed_guards


def test_uat_to_prod_ready_naive_datetimes_fail_via_failed_guards() -> None:
    metadata = _prod_ready_metadata(
        start_datetime=datetime(2026, 6, 10, 10, 0),
        end_datetime=datetime(2026, 6, 10, 12, 0),
    )

    result = validate_uat_to_prod_ready_transition(metadata, current_time=datetime(2026, 6, 3, 10, 0))

    assert result.allowed is False
    assert "Start datetime must be timezone-aware" in result.failed_guards
    assert "End datetime must be timezone-aware" in result.failed_guards
    assert "Current time must be timezone-aware" in result.failed_guards


def test_uat_to_prod_ready_end_before_or_equal_start_fails() -> None:
    metadata = _prod_ready_metadata(end_datetime=START)

    result = validate_uat_to_prod_ready_transition(metadata, current_time=NOW)

    assert result.allowed is False
    assert "End datetime must be after start datetime" in result.failed_guards


def test_uat_to_prod_ready_backdated_start_and_end_fail() -> None:
    metadata = _prod_ready_metadata(
        start_datetime=NOW - timedelta(hours=2),
        end_datetime=NOW - timedelta(hours=1),
    )

    result = validate_uat_to_prod_ready_transition(metadata, current_time=NOW)

    assert result.allowed is False
    assert "Start datetime cannot be backdated" in result.failed_guards
    assert "End datetime cannot be backdated" in result.failed_guards


def test_uat_to_prod_ready_blank_cr_link_fails() -> None:
    metadata = _prod_ready_metadata(cr_link="   ")

    result = validate_uat_to_prod_ready_transition(metadata, current_time=NOW)

    assert result.allowed is False
    assert "CR link is required" in result.failed_guards


def test_uat_to_prod_ready_cr_not_approved_fails() -> None:
    metadata = _prod_ready_metadata(cr_state=CRState.PENDING_APPROVAL)

    result = validate_uat_to_prod_ready_transition(metadata, current_time=NOW)

    assert result.allowed is False
    assert "CR state must be APPROVED" in result.failed_guards


def test_uat_to_prod_ready_missing_t10_proof_no_longer_blocks() -> None:
    # T-10 is now a non-blocking H-10 reminder; missing T-10 proof must not
    # block the UAT->PROD_READY guard. (standalone validate_t10 still flags it.)
    metadata = _prod_ready_metadata(cr_pending_approval_at=None)

    result = validate_uat_to_prod_ready_transition(metadata, current_time=NOW)

    assert result.allowed is True
    assert all("T-10" not in guard for guard in result.failed_guards)


def test_uat_to_prod_ready_drone_ticket_blank_link_fails() -> None:
    metadata = _prod_ready_metadata(
        drone_tickets=[DroneTicket(drone_link=" ", drone_state=DroneState.APPROVED)]
    )

    result = validate_uat_to_prod_ready_transition(metadata, current_time=NOW)

    assert result.allowed is False
    assert "Drone ticket 1 link is required" in result.failed_guards


def test_uat_to_prod_ready_drone_ticket_with_link_but_not_approved_fails() -> None:
    metadata = _prod_ready_metadata(
        drone_tickets=[DroneTicket(drone_link="https://drone.example.local/deployment/D-SSIDBI-159", drone_state=DroneState.UAT)]
    )

    result = validate_uat_to_prod_ready_transition(metadata, current_time=NOW)

    assert result.allowed is False
    assert "Drone ticket 1 must be APPROVED" in result.failed_guards


def test_uat_to_prod_ready_all_linked_drone_tickets_approved_passes() -> None:
    metadata = _prod_ready_metadata(
        drone_tickets=[
            DroneTicket(drone_link="https://drone.example.local/deployment/D-SSIDBI-159", drone_state=DroneState.APPROVED),
            DroneTicket(
                subfolder_name="script_change",
                drone_link="https://drone.example.local/deployment/D-SSIDBI-160",
                drone_state=DroneState.APPROVED,
            ),
        ]
    )

    result = validate_uat_to_prod_ready_transition(metadata, current_time=NOW)

    assert result.allowed is True
    assert result.failed_guards == []


def test_prod_ready_to_implemented_cr_finished_with_no_drone_tickets_passes_outside_time_window() -> None:
    metadata = _implemented_metadata()
    outside_window = START + timedelta(days=1)

    result = validate_prod_ready_to_implemented_transition(metadata, current_time=outside_window)

    assert result.allowed is True
    assert result.failed_guards == []


def test_prod_ready_to_implemented_cr_not_finished_fails() -> None:
    metadata = _implemented_metadata(cr_state=CRState.IN_PROGRESS)

    result = validate_prod_ready_to_implemented_transition(metadata, current_time=NOW)

    assert result.allowed is False
    assert "CR state must be FINISHED" in result.failed_guards


def test_prod_ready_to_implemented_drone_ticket_not_finished_fails_even_when_link_blank() -> None:
    metadata = _implemented_metadata(
        drone_tickets=[DroneTicket(drone_link="", drone_state=DroneState.APPROVED)]
    )

    result = validate_prod_ready_to_implemented_transition(metadata, current_time=NOW)

    assert result.allowed is False
    assert "Drone ticket 1 must be FINISHED" in result.failed_guards


def test_prod_ready_to_implemented_all_drone_tickets_finished_passes() -> None:
    metadata = _implemented_metadata(
        drone_tickets=[
            DroneTicket(drone_link="", drone_state=DroneState.FINISHED),
            DroneTicket(
                subfolder_name="script_change",
                drone_link="https://drone.example.local/deployment/D-SSIDBI-160",
                drone_state=DroneState.FINISHED,
            ),
        ]
    )

    result = validate_prod_ready_to_implemented_transition(metadata, current_time=NOW)

    assert result.allowed is True
    assert result.failed_guards == []


def test_deployment_window_inside_window_returns_true() -> None:
    assert is_in_deployment_window(WINDOW_START, WINDOW_END, WINDOW_NOW) is True


def test_deployment_window_exactly_at_start_returns_true() -> None:
    assert is_in_deployment_window(WINDOW_START, WINDOW_END, WINDOW_START) is True


def test_deployment_window_exactly_at_end_returns_true() -> None:
    assert is_in_deployment_window(WINDOW_START, WINDOW_END, WINDOW_END) is True


def test_deployment_window_before_start_returns_false() -> None:
    assert is_in_deployment_window(WINDOW_START, WINDOW_END, WINDOW_START - timedelta(seconds=1)) is False


def test_deployment_window_after_end_returns_false() -> None:
    assert is_in_deployment_window(WINDOW_START, WINDOW_END, WINDOW_END + timedelta(seconds=1)) is False


def test_deployment_window_missing_start_returns_false() -> None:
    assert is_in_deployment_window(None, WINDOW_END, WINDOW_NOW) is False


def test_deployment_window_missing_end_returns_false() -> None:
    assert is_in_deployment_window(WINDOW_START, None, WINDOW_NOW) is False


def test_deployment_window_naive_start_returns_false() -> None:
    naive_start = datetime(2026, 6, 3, 10, 0)

    assert is_in_deployment_window(naive_start, WINDOW_END, WINDOW_NOW) is False


def test_deployment_window_naive_end_returns_false() -> None:
    naive_end = datetime(2026, 6, 3, 12, 0)

    assert is_in_deployment_window(WINDOW_START, naive_end, WINDOW_NOW) is False


def test_deployment_window_naive_now_returns_false() -> None:
    naive_now = datetime(2026, 6, 3, 11, 0)

    assert is_in_deployment_window(WINDOW_START, WINDOW_END, naive_now) is False


def test_deployment_window_end_before_start_returns_false() -> None:
    assert is_in_deployment_window(WINDOW_END, WINDOW_START, WINDOW_NOW) is False


def test_should_auto_start_cr_approved_inside_window_returns_true() -> None:
    metadata = ProjectMetadata(start_datetime=WINDOW_START, end_datetime=WINDOW_END, cr_state=CRState.APPROVED)

    assert should_auto_start_cr(metadata, WINDOW_NOW) is True


def test_should_auto_start_cr_approved_outside_window_returns_false() -> None:
    metadata = ProjectMetadata(start_datetime=WINDOW_START, end_datetime=WINDOW_END, cr_state=CRState.APPROVED)

    assert should_auto_start_cr(metadata, WINDOW_END + timedelta(seconds=1)) is False


@pytest.mark.parametrize("cr_state", [CRState.PENDING_APPROVAL, CRState.IN_PROGRESS])
def test_should_auto_start_cr_non_approved_inside_window_returns_false(cr_state: CRState) -> None:
    metadata = ProjectMetadata(start_datetime=WINDOW_START, end_datetime=WINDOW_END, cr_state=cr_state)

    assert should_auto_start_cr(metadata, WINDOW_NOW) is False


def test_should_auto_start_cr_missing_dates_returns_false() -> None:
    metadata = ProjectMetadata(cr_state=CRState.APPROVED)

    assert should_auto_start_cr(metadata, WINDOW_NOW) is False


def test_should_auto_start_cr_naive_dates_or_now_returns_false() -> None:
    metadata = ProjectMetadata(
        start_datetime=datetime(2026, 6, 3, 10, 0),
        end_datetime=datetime(2026, 6, 3, 12, 0),
        cr_state=CRState.APPROVED,
    )

    assert should_auto_start_cr(metadata, WINDOW_NOW) is False
    assert should_auto_start_cr(
        ProjectMetadata(start_datetime=WINDOW_START, end_datetime=WINDOW_END, cr_state=CRState.APPROVED),
        datetime(2026, 6, 3, 11, 0),
    ) is False


def test_should_auto_start_drone_approved_linked_inside_window_returns_true() -> None:
    metadata = ProjectMetadata(start_datetime=WINDOW_START, end_datetime=WINDOW_END)
    ticket = DroneTicket(
        drone_link="https://drone.example.local/deployment/D-SSIDBI-159",
        drone_state=DroneState.APPROVED,
    )

    assert should_auto_start_drone(ticket, metadata, WINDOW_NOW) is True


def test_should_auto_start_drone_approved_blank_link_inside_window_returns_false() -> None:
    metadata = ProjectMetadata(start_datetime=WINDOW_START, end_datetime=WINDOW_END)
    ticket = DroneTicket(drone_link="   ", drone_state=DroneState.APPROVED)

    assert should_auto_start_drone(ticket, metadata, WINDOW_NOW) is False


@pytest.mark.parametrize(
    "drone_state",
    [
        DroneState.UAT,
        DroneState.PENDING_APPROVAL,
        DroneState.FINISHED,
        DroneState.CANCELED,
    ],
)
def test_should_auto_start_drone_non_approved_linked_inside_window_returns_false(drone_state: DroneState) -> None:
    metadata = ProjectMetadata(start_datetime=WINDOW_START, end_datetime=WINDOW_END)
    ticket = DroneTicket(
        drone_link="https://drone.example.local/deployment/D-SSIDBI-159",
        drone_state=drone_state,
    )

    assert should_auto_start_drone(ticket, metadata, WINDOW_NOW) is False


def test_should_auto_start_drone_approved_linked_outside_window_returns_false() -> None:
    metadata = ProjectMetadata(start_datetime=WINDOW_START, end_datetime=WINDOW_END)
    ticket = DroneTicket(
        drone_link="https://drone.example.local/deployment/D-SSIDBI-159",
        drone_state=DroneState.APPROVED,
    )

    assert should_auto_start_drone(ticket, metadata, WINDOW_END + timedelta(seconds=1)) is False


def test_should_auto_start_drone_missing_or_naive_metadata_times_returns_false() -> None:
    linked_ticket = DroneTicket(
        drone_link="https://drone.example.local/deployment/D-SSIDBI-159",
        drone_state=DroneState.APPROVED,
    )

    assert should_auto_start_drone(linked_ticket, ProjectMetadata(), WINDOW_NOW) is False
    assert should_auto_start_drone(
        linked_ticket,
        ProjectMetadata(
            start_datetime=datetime(2026, 6, 3, 10, 0),
            end_datetime=datetime(2026, 6, 3, 12, 0),
        ),
        WINDOW_NOW,
    ) is False
    assert should_auto_start_drone(
        linked_ticket,
        ProjectMetadata(start_datetime=WINDOW_START, end_datetime=WINDOW_END),
        datetime(2026, 6, 3, 11, 0),
    ) is False
