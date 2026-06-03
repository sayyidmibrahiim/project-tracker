import pytest

from project_tracker.core.enums import CRState, DroneState, ProjectState
from project_tracker.core.exceptions import InvalidTransitionError
from project_tracker.core.state_machine import (
    target_project_state_for_cr_state,
    valid_next_cr_states,
    valid_next_drone_states,
    valid_next_project_states,
    validate_cr_transition,
    validate_drone_state_change_allowed,
    validate_drone_transition,
    validate_project_state_transition,
)


def test_manual_valid_next_cr_states_exclude_reopen_and_in_progress() -> None:
    next_states = valid_next_cr_states(CRState.APPROVED)

    assert CRState.REOPEN not in next_states
    assert CRState.IN_PROGRESS not in next_states


def test_manual_cr_linear_transitions_are_allowed() -> None:
    validate_cr_transition(CRState.PENDING_SUBMISSION, CRState.PENDING_APPROVAL)
    validate_cr_transition(CRState.PENDING_APPROVAL, CRState.APPROVED)
    validate_cr_transition(CRState.IN_PROGRESS, CRState.FINISHED)


def test_active_cr_states_can_transition_to_postponed_and_canceled() -> None:
    active_states = {
        CRState.PENDING_SUBMISSION,
        CRState.PENDING_APPROVAL,
        CRState.APPROVED,
        CRState.IN_PROGRESS,
    }

    for current_state in active_states:
        validate_cr_transition(current_state, CRState.POSTPONED)
        validate_cr_transition(current_state, CRState.CANCELED)


def test_terminal_cr_states_have_no_normal_outgoing_transitions() -> None:
    assert valid_next_cr_states(CRState.FINISHED) == frozenset()
    assert valid_next_cr_states(CRState.POSTPONED) == frozenset()
    assert valid_next_cr_states(CRState.CANCELED) == frozenset()


def test_manual_cr_approved_to_in_progress_is_rejected() -> None:
    with pytest.raises(InvalidTransitionError, match="CR transition"):
        validate_cr_transition(CRState.APPROVED, CRState.IN_PROGRESS)


def test_automatic_cr_approved_to_in_progress_is_allowed() -> None:
    validate_cr_transition(CRState.APPROVED, CRState.IN_PROGRESS, automatic=True)


def test_reopen_is_rejected_as_persistent_cr_transition_target() -> None:
    with pytest.raises(InvalidTransitionError, match="REOPEN"):
        validate_cr_transition(CRState.CANCELED, CRState.REOPEN)


def test_manual_valid_next_drone_states_exclude_in_progress() -> None:
    assert DroneState.IN_PROGRESS not in valid_next_drone_states(DroneState.APPROVED)


def test_manual_drone_linear_transitions_are_allowed() -> None:
    validate_drone_transition(DroneState.UAT, DroneState.PENDING_APPROVAL)
    validate_drone_transition(DroneState.PENDING_APPROVAL, DroneState.APPROVED)
    validate_drone_transition(DroneState.IN_PROGRESS, DroneState.FINISHED)


def test_manual_drone_approved_to_in_progress_is_rejected() -> None:
    with pytest.raises(InvalidTransitionError, match="Drone transition"):
        validate_drone_transition(DroneState.APPROVED, DroneState.IN_PROGRESS)


def test_automatic_drone_approved_to_in_progress_is_allowed() -> None:
    validate_drone_transition(DroneState.APPROVED, DroneState.IN_PROGRESS, automatic=True)


def test_terminal_drone_states_have_no_outgoing_transitions() -> None:
    assert valid_next_drone_states(DroneState.FINISHED) == frozenset()
    assert valid_next_drone_states(DroneState.CANCELED) == frozenset()


def test_validate_drone_state_change_allowed_rejects_empty_or_blank_link() -> None:
    for drone_link in ("", "   "):
        with pytest.raises(InvalidTransitionError, match="drone_link"):
            validate_drone_state_change_allowed(
                drone_link,
                DroneState.UAT,
                DroneState.PENDING_APPROVAL,
            )


def test_project_state_valid_transitions_are_allowed() -> None:
    for target_state in {ProjectState.PROD_READY, ProjectState.POSTPONED, ProjectState.CANCELED}:
        validate_project_state_transition(ProjectState.UAT_PREPARE, target_state)

    for target_state in {ProjectState.IMPLEMENTED, ProjectState.POSTPONED, ProjectState.CANCELED}:
        validate_project_state_transition(ProjectState.PROD_READY, target_state)

    for target_state in {ProjectState.UAT_PREPARE, ProjectState.CANCELED}:
        validate_project_state_transition(ProjectState.POSTPONED, target_state)

    for target_state in {ProjectState.UAT_PREPARE, ProjectState.POSTPONED}:
        validate_project_state_transition(ProjectState.CANCELED, target_state)


def test_implemented_project_state_has_no_outgoing_transitions() -> None:
    assert valid_next_project_states(ProjectState.IMPLEMENTED) == frozenset()


def test_invalid_project_state_transition_is_rejected() -> None:
    with pytest.raises(InvalidTransitionError, match="Project state transition"):
        validate_project_state_transition(ProjectState.IMPLEMENTED, ProjectState.UAT_PREPARE)

    with pytest.raises(InvalidTransitionError, match="Project state transition"):
        validate_project_state_transition(ProjectState.UAT_PREPARE, ProjectState.IMPLEMENTED)


def test_target_project_state_for_cr_state_maps_folder_moving_states() -> None:
    assert target_project_state_for_cr_state(CRState.APPROVED) == ProjectState.PROD_READY
    assert target_project_state_for_cr_state(CRState.FINISHED) == ProjectState.IMPLEMENTED
    assert target_project_state_for_cr_state(CRState.POSTPONED) == ProjectState.POSTPONED
    assert target_project_state_for_cr_state(CRState.CANCELED) == ProjectState.CANCELED


@pytest.mark.parametrize(
    "cr_state",
    [
        CRState.PENDING_SUBMISSION,
        CRState.PENDING_APPROVAL,
        CRState.IN_PROGRESS,
        CRState.REOPEN,
    ],
)
def test_target_project_state_for_cr_state_returns_none_for_non_folder_moving_states(cr_state: CRState) -> None:
    assert target_project_state_for_cr_state(cr_state) is None
