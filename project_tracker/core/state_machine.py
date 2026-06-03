from __future__ import annotations

from dataclasses import dataclass

from project_tracker.core.enums import CRState, DroneState, ProjectState
from project_tracker.core.exceptions import InvalidTransitionError

REOPEN_ALLOWED_FROM = frozenset({CRState.APPROVED, CRState.PENDING_APPROVAL})
POSTPONED_RESUME_TARGETS = frozenset({ProjectState.UAT_PREPARE})

CR_MANUAL_TRANSITIONS: dict[CRState, frozenset[CRState]] = {
    CRState.PENDING_SUBMISSION: frozenset({CRState.PENDING_APPROVAL, CRState.POSTPONED, CRState.CANCELED}),
    CRState.PENDING_APPROVAL: frozenset({CRState.APPROVED, CRState.POSTPONED, CRState.CANCELED}),
    CRState.APPROVED: frozenset({CRState.POSTPONED, CRState.CANCELED}),
    CRState.IN_PROGRESS: frozenset({CRState.FINISHED, CRState.POSTPONED, CRState.CANCELED}),
    CRState.FINISHED: frozenset(),
    CRState.POSTPONED: frozenset(),
    CRState.CANCELED: frozenset(),
    CRState.REOPEN: frozenset(),
}

CR_AUTOMATIC_TRANSITIONS: dict[CRState, frozenset[CRState]] = {
    CRState.APPROVED: frozenset({CRState.IN_PROGRESS}),
}

DRONE_MANUAL_TRANSITIONS: dict[DroneState, frozenset[DroneState]] = {
    DroneState.UAT: frozenset({DroneState.PENDING_APPROVAL, DroneState.CANCELED}),
    DroneState.PENDING_APPROVAL: frozenset({DroneState.APPROVED, DroneState.CANCELED}),
    DroneState.APPROVED: frozenset({DroneState.CANCELED}),
    DroneState.IN_PROGRESS: frozenset({DroneState.FINISHED, DroneState.CANCELED}),
    DroneState.FINISHED: frozenset(),
    DroneState.CANCELED: frozenset(),
}

DRONE_AUTOMATIC_TRANSITIONS: dict[DroneState, frozenset[DroneState]] = {
    DroneState.APPROVED: frozenset({DroneState.IN_PROGRESS}),
}

PROJECT_STATE_TRANSITIONS: dict[ProjectState, frozenset[ProjectState]] = {
    ProjectState.UAT_PREPARE: frozenset({ProjectState.PROD_READY, ProjectState.POSTPONED, ProjectState.CANCELED}),
    ProjectState.PROD_READY: frozenset({ProjectState.IMPLEMENTED, ProjectState.POSTPONED, ProjectState.CANCELED}),
    ProjectState.IMPLEMENTED: frozenset(),
    ProjectState.POSTPONED: frozenset({ProjectState.UAT_PREPARE, ProjectState.CANCELED}),
    ProjectState.CANCELED: frozenset({ProjectState.UAT_PREPARE, ProjectState.POSTPONED}),
}


@dataclass(frozen=True, slots=True)
class ReopenResult:
    folder_state: ProjectState
    recorded_state: CRState
    next_cr_state: CRState
    history_action: str


def valid_next_cr_states(current_state: CRState, *, automatic: bool = False) -> frozenset[CRState]:
    if automatic:
        return CR_AUTOMATIC_TRANSITIONS.get(current_state, frozenset())
    return CR_MANUAL_TRANSITIONS[current_state]


def can_transition_cr(current_state: CRState, target_state: CRState, *, automatic: bool = False) -> bool:
    return target_state in valid_next_cr_states(current_state, automatic=automatic)


def validate_cr_transition(current_state: CRState, target_state: CRState, *, automatic: bool = False) -> None:
    if target_state == CRState.REOPEN:
        raise InvalidTransitionError("REOPEN is an action/event, not a persistent CR transition target")
    if not can_transition_cr(current_state, target_state, automatic=automatic):
        raise InvalidTransitionError(f"Invalid CR transition: {current_state.value} -> {target_state.value}")


def valid_next_drone_states(current_state: DroneState, *, automatic: bool = False) -> frozenset[DroneState]:
    if automatic:
        return DRONE_AUTOMATIC_TRANSITIONS.get(current_state, frozenset())
    return DRONE_MANUAL_TRANSITIONS[current_state]


def can_transition_drone(current_state: DroneState, target_state: DroneState, *, automatic: bool = False) -> bool:
    return target_state in valid_next_drone_states(current_state, automatic=automatic)


def validate_drone_transition(current_state: DroneState, target_state: DroneState, *, automatic: bool = False) -> None:
    if not can_transition_drone(current_state, target_state, automatic=automatic):
        raise InvalidTransitionError(f"Invalid Drone transition: {current_state.value} -> {target_state.value}")


def validate_drone_state_change_allowed(
    drone_link: str,
    current_state: DroneState,
    target_state: DroneState,
    *,
    automatic: bool = False,
) -> None:
    if not drone_link.strip():
        raise InvalidTransitionError("Drone state cannot change without drone_link")
    validate_drone_transition(current_state, target_state, automatic=automatic)


def valid_next_project_states(current_state: ProjectState) -> frozenset[ProjectState]:
    return PROJECT_STATE_TRANSITIONS[current_state]


def can_transition_project_state(current_state: ProjectState, target_state: ProjectState) -> bool:
    return target_state in valid_next_project_states(current_state)


def validate_project_state_transition(current_state: ProjectState, target_state: ProjectState) -> None:
    if not can_transition_project_state(current_state, target_state):
        raise InvalidTransitionError(f"Invalid Project state transition: {current_state.value} -> {target_state.value}")


def can_reopen_cr(current_state: CRState) -> bool:
    return current_state in REOPEN_ALLOWED_FROM


def validate_reopen_cr(current_state: CRState) -> None:
    if not can_reopen_cr(current_state):
        raise InvalidTransitionError(f"Cannot REOPEN CR from {current_state.value}")


def reopen_cr(current_state: CRState) -> ReopenResult:
    validate_reopen_cr(current_state)
    return ReopenResult(
        folder_state=ProjectState.UAT_PREPARE,
        recorded_state=CRState.REOPEN,
        next_cr_state=CRState.PENDING_SUBMISSION,
        history_action="REOPEN",
    )


def target_project_state_for_cr_state(cr_state: CRState) -> ProjectState | None:
    if cr_state == CRState.APPROVED:
        return ProjectState.PROD_READY
    if cr_state == CRState.FINISHED:
        return ProjectState.IMPLEMENTED
    if cr_state == CRState.POSTPONED:
        return ProjectState.POSTPONED
    if cr_state == CRState.CANCELED:
        return ProjectState.CANCELED
    return None


def can_resume_postponed(target_state: ProjectState) -> bool:
    return target_state in POSTPONED_RESUME_TARGETS


def validate_postponed_resume(target_state: ProjectState) -> None:
    if not can_resume_postponed(target_state):
        raise InvalidTransitionError("POSTPONED projects may resume only to UAT_PREPARE")
