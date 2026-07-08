"""Auto Update CR State engine — pattern-gated email → CR transition.

Automation epic Slice 4. **DEFAULT AMAN**: with no patterns configured the
engine performs NO transition. Only user-configured from/subject/body patterns
trigger a transition, and only legal transitions (per ``core.state_machine``)
are applied — illegal matches are logged + skipped, never forced.

Patterns live per-project on ``ProjectMetadata.auto_update_patterns`` (new field):
``{"from": "<regex>", "subject": "<regex>", "body": "<regex>", "target_state": "APPROVED"}``.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from typing import Any

from core.enums import CRState
from core.exceptions import InvalidTransitionError
from core.models import HistoryEntry, ProjectMetadata, local_now
from core.state_machine import validate_cr_transition

_log = logging.getLogger(__name__)


@dataclass(slots=True)
class EngineResult:
    """Outcome of one engine invocation."""

    acted: bool
    reason: str
    new_state: str | None = None


def patterns_configured(metadata: ProjectMetadata) -> bool:
    """True if the project has any auto-update patterns set (DEFAULT AMAN gate)."""
    p = metadata.auto_update_patterns
    if not isinstance(p, dict):
        return False
    return any(str(p.get(k, "")).strip() for k in ("from", "subject", "body"))


def match_email(metadata: ProjectMetadata, *, sender: str = "", subject: str = "", body: str = "") -> bool:
    """Return True if the email matches ALL configured patterns.

    An empty pattern field is treated as "not configured" and skipped (not as
    a wildcard) — so a partial config only constrains further, never loosens.
    """
    p = metadata.auto_update_patterns
    if not isinstance(p, dict) or not patterns_configured(metadata):
        return False
    fields = {"from": sender, "subject": subject, "body": body}
    for key, text in fields.items():
        pattern = str(p.get(key, "")).strip()
        if not pattern:
            continue
        try:
            if not re.search(pattern, text, re.IGNORECASE):
                return False
        except re.error as exc:
            _log.warning("Invalid %s pattern %r: %s — treating as no-match", key, pattern, exc)
            return False
    return True


def apply_transition(
    metadata: ProjectMetadata,
    *,
    sender: str = "",
    subject: str = "",
    body: str = "",
    user: str = "",
) -> EngineResult:
    """Match + transition. Mutates metadata in place (caller persists).

    Returns an EngineResult describing whether anything happened and why.
    Never raises on illegal transitions — logs + skips.
    """
    if not metadata.auto_update_cr_state:
        return EngineResult(acted=False, reason="auto_update_cr_state disabled")
    if not patterns_configured(metadata):
        return EngineResult(acted=False, reason="no patterns configured")
    if not match_email(metadata, sender=sender, subject=subject, body=body):
        return EngineResult(acted=False, reason="email did not match patterns")

    target_raw = str(metadata.auto_update_patterns.get("target_state", "")).strip()
    if not target_raw:
        return EngineResult(acted=False, reason="no target_state in patterns")
    try:
        target = CRState(target_raw)
    except ValueError:
        return EngineResult(acted=False, reason=f"unknown target_state: {target_raw!r}")

    try:
        validate_cr_transition(metadata.cr_state, target)
    except InvalidTransitionError as exc:
        metadata.history.append(
            HistoryEntry(
                timestamp=local_now(),
                action="AUTO_UPDATE_CR_STATE_BLOCKED",
                detail=f"Pattern matched but transition illegal: {exc}",
                user=user,
            )
        )
        return EngineResult(acted=False, reason=f"illegal transition: {exc}")

    metadata.cr_state = target
    metadata.cr_state_updated_at = local_now()
    metadata.updated_at = local_now()
    metadata.history.append(
        HistoryEntry(
            timestamp=local_now(),
            action="AUTO_UPDATE_CR_STATE",
            detail=f"Email pattern matched → CR state {target.value}",
            user=user,
        )
    )
    return EngineResult(acted=True, reason="transitioned", new_state=target.value)
