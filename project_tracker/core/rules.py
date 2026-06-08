from __future__ import annotations

import getpass
import re
from datetime import datetime, timedelta
from pathlib import Path
from typing import NamedTuple

from project_tracker.core.enums import CRState, DroneState
from project_tracker.core.exceptions import InvalidFolderNameError
from project_tracker.core.models import AppSettings, DroneTicket, ProjectMetadata

WINDOWS_INVALID_FOLDER_CHARS = frozenset('\\/:*?"<>|')
WINDOWS_RESERVED_NAMES = frozenset(
    {"CON", "PRN", "AUX", "NUL"}
    | {f"COM{number}" for number in range(1, 10)}
    | {f"LPT{number}" for number in range(1, 10)}
)
ORGANIZATIONAL_FOLDER_NAMES = frozenset(
    {
        "doc",
        "docs",
        "document",
        "documents",
        "bak",
        "backup",
        "before",
        "after",
        "script",
        "scripts",
        "cicd",
        "log",
        "logs",
        "temp",
        "tmp",
        "archive",
    }
)


class T10ValidationResult(NamedTuple):
    passed: bool
    reason: str | None = None


class TransitionGuardResult(NamedTuple):
    allowed: bool
    failed_guards: list[str]


def is_organizational_folder(path: Path) -> bool:
    return path.name.casefold() in ORGANIZATIONAL_FOLDER_NAMES


def extract_cr_number(url: str) -> str | None:
    if not url.strip():
        return None
    match = re.search(r"[?&]CRNumber=(CR\d+)(?:&|$)", url)
    if match is None:
        return None
    return match.group(1)


def extract_drone_ticket(url: str) -> str | None:
    if not url.strip():
        return None
    match = re.search(r"/(D-[A-Z0-9-]+)/?$", url)
    if match is None:
        return None
    return match.group(1)


def validate_windows_folder_name(name: str) -> None:
    if not name:
        raise InvalidFolderNameError("Folder name cannot be empty")
    if len(name) > 255:
        raise InvalidFolderNameError("Folder name cannot exceed 255 characters")
    if name[-1] in {" ", "."}:
        raise InvalidFolderNameError("Folder name cannot end with a space or dot")
    invalid_characters = sorted({character for character in name if character in WINDOWS_INVALID_FOLDER_CHARS})
    if invalid_characters:
        raise InvalidFolderNameError(f"Folder name contains invalid character: {invalid_characters[0]}")
    stem = name.split(".", 1)[0].upper()
    if stem in WINDOWS_RESERVED_NAMES:
        raise InvalidFolderNameError(f"Folder name is reserved on Windows: {stem}")


def _is_timezone_aware(value: datetime) -> bool:
    return value.tzinfo is not None and value.tzinfo.utcoffset(value) is not None


def is_in_deployment_window(
    start_datetime: datetime | None,
    end_datetime: datetime | None,
    now: datetime,
) -> bool:
    if start_datetime is None or end_datetime is None:
        return False
    if not _is_timezone_aware(start_datetime):
        return False
    if not _is_timezone_aware(end_datetime):
        return False
    if not _is_timezone_aware(now):
        return False
    return start_datetime <= now <= end_datetime


def should_auto_start_cr(metadata: ProjectMetadata, now: datetime) -> bool:
    return metadata.cr_state == CRState.APPROVED and is_in_deployment_window(
        metadata.start_datetime,
        metadata.end_datetime,
        now,
    )


def should_auto_start_drone(ticket: DroneTicket, metadata: ProjectMetadata, now: datetime) -> bool:
    return (
        ticket.drone_state == DroneState.APPROVED
        and bool(ticket.drone_link.strip())
        and is_in_deployment_window(metadata.start_datetime, metadata.end_datetime, now)
    )


def validate_t10(metadata: ProjectMetadata, *, threshold_days: int = 10) -> T10ValidationResult:
    """
    Validate T-10 rule: CR must reach PENDING APPROVAL no later than threshold_days before start_datetime.

    PRD Section 7.7:
    - cr_pending_approval_at <= start_datetime - threshold_days
    - If cr_pending_approval_at missing and CR beyond PENDING SUBMISSION, cannot prove T-10
    """
    if metadata.start_datetime is None:
        return T10ValidationResult(passed=True, reason="No start datetime set")

    if metadata.cr_pending_approval_at is None:
        if metadata.cr_state != CRState.PENDING_SUBMISSION:
            return T10ValidationResult(
                passed=False,
                reason="CR state is beyond PENDING SUBMISSION but cr_pending_approval_at is missing; cannot prove T-10",
            )
        return T10ValidationResult(passed=True, reason="No cr_pending_approval_at and CR not beyond PENDING SUBMISSION")

    t10_deadline = metadata.start_datetime - timedelta(days=threshold_days)
    if metadata.cr_pending_approval_at <= t10_deadline:
        return T10ValidationResult(passed=True)

    days_late = (metadata.cr_pending_approval_at - t10_deadline).days
    day_word = "day" if days_late == 1 else "days"
    return T10ValidationResult(
        passed=False,
        reason=f"CR reached PENDING APPROVAL {days_late} {day_word} after T-10 deadline",
    )


def _drone_ticket_label(ticket: DroneTicket, index: int) -> str:
    if ticket.subfolder_name:
        return f"Drone ticket for {ticket.subfolder_name}"
    return f"Drone ticket {index + 1}"


def validate_uat_to_prod_ready_transition(
    metadata: ProjectMetadata, *, current_time: datetime, threshold_days: int = 10
) -> TransitionGuardResult:
    failed_guards: list[str] = []

    current_time_is_aware = _is_timezone_aware(current_time)
    if not current_time_is_aware:
        failed_guards.append("Current time must be timezone-aware")

    start_datetime_is_aware = True
    end_datetime_is_aware = True
    if metadata.start_datetime is None:
        failed_guards.append("Start datetime is required")
    else:
        start_datetime_is_aware = _is_timezone_aware(metadata.start_datetime)
        if not start_datetime_is_aware:
            failed_guards.append("Start datetime must be timezone-aware")

    if metadata.end_datetime is None:
        failed_guards.append("End datetime is required")
    else:
        end_datetime_is_aware = _is_timezone_aware(metadata.end_datetime)
        if not end_datetime_is_aware:
            failed_guards.append("End datetime must be timezone-aware")

    dates_are_comparable = (
        metadata.start_datetime is not None
        and metadata.end_datetime is not None
        and start_datetime_is_aware
        and end_datetime_is_aware
    )
    if dates_are_comparable:
        if metadata.end_datetime <= metadata.start_datetime:
            failed_guards.append("End datetime must be after start datetime")
        if current_time_is_aware:
            if metadata.start_datetime < current_time:
                failed_guards.append("Start datetime cannot be backdated")
            if metadata.end_datetime < current_time:
                failed_guards.append("End datetime cannot be backdated")

    if not metadata.cr_link.strip():
        failed_guards.append("CR link is required")
    if metadata.cr_state != CRState.APPROVED:
        failed_guards.append("CR state must be APPROVED")

    for index, ticket in enumerate(metadata.drone_tickets):
        if not ticket.drone_link.strip():
            failed_guards.append(f"{_drone_ticket_label(ticket, index)} link is required")
        if ticket.drone_state != DroneState.APPROVED:
            failed_guards.append(f"{_drone_ticket_label(ticket, index)} must be APPROVED")

    if metadata.start_datetime is None or start_datetime_is_aware:
        t10_result = validate_t10(metadata, threshold_days=threshold_days)
        if not t10_result.passed:
            failed_guards.append(t10_result.reason or "T-10 rule failed")

    return TransitionGuardResult(allowed=not failed_guards, failed_guards=failed_guards)


def validate_prod_ready_to_implemented_transition(
    metadata: ProjectMetadata, *, current_time: datetime | None = None
) -> TransitionGuardResult:
    failed_guards: list[str] = []

    if metadata.cr_state != CRState.FINISHED:
        failed_guards.append("CR state must be FINISHED")

    for index, ticket in enumerate(metadata.drone_tickets):
        if ticket.drone_state != DroneState.FINISHED:
            failed_guards.append(f"{_drone_ticket_label(ticket, index)} must be FINISHED")

    return TransitionGuardResult(allowed=not failed_guards, failed_guards=failed_guards)


def current_user(settings: AppSettings) -> str:
    display_name = settings.display_name.strip()
    if display_name:
        return display_name
    return getpass.getuser()


def ensure_timezone_aware(value: datetime) -> None:
    if value.tzinfo is None or value.tzinfo.utcoffset(value) is None:
        raise ValueError("Datetime must be timezone-aware")


class ConditionResult(NamedTuple):
    passed: bool
    reason: str


def evaluate_automation_condition(
    condition: "AutomationCondition", metadata: ProjectMetadata, project_path: Path
) -> ConditionResult:
    """Evaluate a single automation condition against project metadata.
    
    Supported condition types:
    - cr_state: Check CR state (operators: equals, not_equals)
    - drone_state: Check Drone state (operators: equals, not_equals)
    - folder_state: Check folder state (operators: equals, not_equals)
    - file_exists: Check if file exists in project folder (operators: equals true/false)
    """
    from project_tracker.core.models import AutomationCondition

    cond_type = condition.type
    operator = condition.operator
    value = condition.value

    # CR state condition
    if cond_type == "cr_state":
        actual = metadata.cr_state.value
        if operator == "equals":
            passed = actual == value
            reason = f"CR state is {actual}" + ("" if passed else f", expected {value}")
        elif operator == "not_equals":
            passed = actual != value
            reason = f"CR state is {actual}" + ("" if passed else f", must not be {value}")
        else:
            return ConditionResult(False, f"Unknown operator: {operator}")
        return ConditionResult(passed, reason)

    # Drone state condition
    elif cond_type == "drone_state":
        if not metadata.drone_tickets:
            return ConditionResult(False, "No drone tickets")
        actual = metadata.drone_tickets[0].drone_state.value
        if operator == "equals":
            passed = actual == value
            reason = f"Drone state is {actual}" + ("" if passed else f", expected {value}")
        elif operator == "not_equals":
            passed = actual != value
            reason = f"Drone state is {actual}" + ("" if passed else f", must not be {value}")
        else:
            return ConditionResult(False, f"Unknown operator: {operator}")
        return ConditionResult(passed, reason)

    # Folder state condition
    elif cond_type == "folder_state":
        actual = project_path.parent.name
        if operator == "equals":
            passed = actual == value
            reason = f"Folder state is {actual}" + ("" if passed else f", expected {value}")
        elif operator == "not_equals":
            passed = actual != value
            reason = f"Folder state is {actual}" + ("" if passed else f", must not be {value}")
        else:
            return ConditionResult(False, f"Unknown operator: {operator}")
        return ConditionResult(passed, reason)

    # File exists condition
    elif cond_type == "file_exists":
        file_path = project_path / value
        exists = file_path.exists()
        if operator == "equals":
            passed = exists
            reason = f"File {value} " + ("exists" if exists else "does not exist")
        elif operator == "not_equals":
            passed = not exists
            reason = f"File {value} " + ("exists" if exists else "does not exist")
        else:
            return ConditionResult(False, f"Unknown operator: {operator}")
        return ConditionResult(passed, reason)

    else:
        return ConditionResult(False, f"Unknown condition type: {cond_type}")
