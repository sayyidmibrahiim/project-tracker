"""Unit tests for the Auto Update CR State engine (Automation epic Slice 4).

Covers DEFAULT AMAN guarantees: no patterns → no-op; disabled flag → no-op;
illegal transition → skip+log (never force); pattern match + legal transition →
state changes + History.
"""

from __future__ import annotations

from core.enums import CRState
from core.models import ProjectMetadata
from services.cr_state_engine import apply_transition, match_email, patterns_configured


def _metadata(
    cr_state: CRState = CRState.PENDING_APPROVAL,
    enabled: bool = True,
    patterns: dict | None = None,
) -> ProjectMetadata:
    m = ProjectMetadata(project_name="CR-2026-001", cr_state=cr_state)
    m.auto_update_cr_state = enabled
    if patterns is not None:
        m.auto_update_patterns = patterns
    return m


def test_no_patterns_is_noop():
    """DEFAULT AMAN: no patterns configured → engine never acts."""
    m = _metadata(patterns={})
    result = apply_transition(m, subject="anything")
    assert not result.acted
    assert "no patterns" in result.reason
    assert m.cr_state == CRState.PENDING_APPROVAL


def test_disabled_flag_is_noop_even_with_patterns():
    m = _metadata(enabled=False, patterns={"subject": "approved", "target_state": "APPROVED"})
    result = apply_transition(m, subject="approved")
    assert not result.acted
    assert "disabled" in result.reason


def test_no_target_state_in_patterns_skips():
    m = _metadata(patterns={"subject": "approved"})  # no target_state
    result = apply_transition(m, subject="approved")
    assert not result.acted
    assert "target_state" in result.reason


def test_pattern_match_legal_transition_applies():
    m = _metadata(cr_state=CRState.PENDING_APPROVAL, patterns={"subject": "approved", "target_state": "APPROVED"})
    result = apply_transition(m, subject="CR approved by lead")
    assert result.acted
    assert result.new_state == "APPROVED"
    assert m.cr_state == CRState.APPROVED
    assert any("CR state" in h.detail for h in m.history)


def test_pattern_match_illegal_transition_skips():
    """DEFAULT AMAN: illegal transition skipped + logged, never forced."""
    m = _metadata(cr_state=CRState.PENDING_SUBMISSION, patterns={"subject": "done", "target_state": "FINISHED"})
    result = apply_transition(m, subject="done")
    assert not result.acted
    assert "illegal" in result.reason
    assert m.cr_state == CRState.PENDING_SUBMISSION  # unchanged
    assert any("BLOCKED" in h.action for h in m.history)


def test_pattern_no_match_skips():
    m = _metadata(patterns={"subject": "approved", "target_state": "APPROVED"})
    result = apply_transition(m, subject="random unrelated subject")
    assert not result.acted
    assert "did not match" in result.reason


def test_multiple_patterns_all_must_match():
    m = _metadata(patterns={"from": "lead@.*", "subject": "approved", "target_state": "APPROVED"})
    # subject matches but from doesn't → no match
    result = apply_transition(m, sender="other@x.com", subject="approved")
    assert not result.acted


def test_invalid_regex_treated_as_no_match():
    m = _metadata(patterns={"subject": "[unclosed", "target_state": "APPROVED"})
    result = apply_transition(m, subject="anything")
    assert not result.acted
    assert "did not match" in result.reason


def test_patterns_configured_helper():
    assert not patterns_configured(_metadata(patterns={}))
    assert patterns_configured(_metadata(patterns={"subject": "x"}))


def test_match_email_helper():
    m = _metadata(patterns={"subject": "approved"})
    assert match_email(m, subject="it is approved") is True
    assert match_email(m, subject="no match here") is False
    # no patterns → False
    assert match_email(_metadata(patterns={}), subject="approved") is False
