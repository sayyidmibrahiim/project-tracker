import pytest
from core.enums import NonCrState
from core.exceptions import InvalidTransitionError
from core.state_machine import (
    NON_CR_TRANSITIONS,
    valid_next_non_cr_states,
    can_transition_non_cr,
    validate_non_cr_transition,
)

def test_planning_can_go_to_in_progress_and_done():
    assert NonCrState.IN_PROGRESS in valid_next_non_cr_states(NonCrState.PLANNING)
    assert NonCrState.DONE in valid_next_non_cr_states(NonCrState.PLANNING)

def test_in_progress_can_go_to_done_and_planning():
    assert NonCrState.DONE in valid_next_non_cr_states(NonCrState.IN_PROGRESS)
    assert NonCrState.PLANNING in valid_next_non_cr_states(NonCrState.IN_PROGRESS)

def test_done_can_go_to_in_progress():
    assert NonCrState.IN_PROGRESS in valid_next_non_cr_states(NonCrState.DONE)

def test_done_cannot_go_to_planning():
    assert NonCrState.PLANNING not in valid_next_non_cr_states(NonCrState.DONE)

def test_can_transition_non_cr_true():
    assert can_transition_non_cr(NonCrState.PLANNING, NonCrState.IN_PROGRESS) is True

def test_can_transition_non_cr_false():
    assert can_transition_non_cr(NonCrState.DONE, NonCrState.PLANNING) is False

def test_validate_non_cr_transition_valid():
    validate_non_cr_transition(NonCrState.PLANNING, NonCrState.IN_PROGRESS)

def test_validate_non_cr_transition_invalid_raises():
    with pytest.raises(InvalidTransitionError):
        validate_non_cr_transition(NonCrState.DONE, NonCrState.PLANNING)
