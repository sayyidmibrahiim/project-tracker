from __future__ import annotations

from dataclasses import dataclass

from project_tracker.core.enums import CRState, ProjectState
from project_tracker.core.exceptions import InvalidTransitionError

REOPEN_ALLOWED_FROM = frozenset({CRState.APPROVED, CRState.PENDING_APPROVAL})
POSTPONED_RESUME_TARGETS = frozenset({ProjectState.UAT_PREPARE})


@dataclass(frozen=True, slots=True)
class ReopenResult:
    folder_state: ProjectState
    recorded_state: CRState
    next_cr_state: CRState
    history_action: str


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
    if cr_state == CRState.CANCELED:
        return ProjectState.POSTPONED
    if cr_state == CRState.APPROVED:
        return ProjectState.PROD_READY
    if cr_state == CRState.FINISHED:
        return ProjectState.IMPLEMENTED
    return None


def can_resume_postponed(target_state: ProjectState) -> bool:
    return target_state in POSTPONED_RESUME_TARGETS


def validate_postponed_resume(target_state: ProjectState) -> None:
    if not can_resume_postponed(target_state):
        raise InvalidTransitionError("POSTPONED projects may resume only to UAT_PREPARE")


def validate_cr_transition(current_state: CRState, target_state: CRState, *, automatic: bool = False) -> None:
    if target_state == CRState.REOPEN:
        validate_reopen_cr(current_state)
        return
    if target_state == CRState.IN_PROGRESS and not automatic:
        raise InvalidTransitionError("CR IN-PROGRESS transition is automatic only")
    if target_state == CRState.FINISHED and current_state != CRState.IN_PROGRESS:
        raise InvalidTransitionError("CR FINISHED is allowed only from IN-PROGRESS")
