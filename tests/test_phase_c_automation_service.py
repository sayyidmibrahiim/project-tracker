"""Phase C.14 — AutomationService foundation tests (TDD: RED first)."""

import pytest

from services.automation_service import (
    AutomationRuleResult,
    AutomationService,
)


def _rules() -> list[dict[str, object]]:
    return [
        {
            "id": "r-1",
            "name": "CR Approved",
            "enabled": True,
            "conditions": [
                {"field": "cr_state", "operator": "equals", "value": "APPROVED"},
            ],
        },
        {
            "id": "r-2",
            "name": "Project Name Check",
            "enabled": True,
            "conditions": [
                {"field": "project_name", "operator": "contains", "value": "Alpha"},
            ],
        },
        {
            "id": "r-3",
            "name": "Has Drone",
            "enabled": True,
            "conditions": [
                {"field": "drone_count", "operator": "exists"},
            ],
        },
        {
            "id": "r-4",
            "name": "Disabled Rule",
            "enabled": False,
            "conditions": [
                {"field": "project_name", "operator": "equals", "value": "Beta"},
            ],
        },
        {
            "id": "r-5",
            "name": "Multi Condition",
            "enabled": True,
            "conditions": [
                {"field": "cr_state", "operator": "equals", "value": "APPROVED"},
                {"field": "project_state", "operator": "not_equals", "value": "IMPLEMENTED"},
            ],
        },
    ]


def test_list_rules_returns_provider_rules():
    service = AutomationService(rules_provider=_rules)
    rules = service.list_rules()
    assert len(rules) == 5
    assert rules[0]["id"] == "r-1"
    assert rules[3]["enabled"] is False


def test_evaluate_equals_success():
    service = AutomationService(rules_provider=_rules)
    result = service.evaluate_rule("r-1", {"cr_state": "APPROVED"})
    assert result.rule_id == "r-1"
    assert result.passed is True
    assert result.skipped is False
    assert len(result.matched_conditions) == 1


def test_evaluate_equals_failure():
    service = AutomationService(rules_provider=_rules)
    result = service.evaluate_rule("r-1", {"cr_state": "CANCELED"})
    assert result.passed is False


def test_evaluate_not_equals():
    service = AutomationService(rules_provider=_rules)
    result = service.evaluate_rule("r-5", {"cr_state": "APPROVED", "project_state": "UAT_PREPARE"})
    assert result.passed is True


def test_evaluate_contains():
    service = AutomationService(rules_provider=_rules)
    result = service.evaluate_rule("r-2", {"project_name": "Project Alpha Test"})
    assert result.passed is True


def test_evaluate_exists():
    service = AutomationService(rules_provider=_rules)
    has = service.evaluate_rule("r-3", {"drone_count": 3})
    missing = service.evaluate_rule("r-3", {})
    assert has.passed is True
    assert missing.passed is False


def test_disabled_rule_is_skipped():
    service = AutomationService(rules_provider=_rules)
    result = service.evaluate_rule("r-4", {"project_name": "Beta"})
    assert result.skipped is True
    assert result.passed is False


def test_missing_rule_raises_key_error():
    service = AutomationService(rules_provider=_rules)
    with pytest.raises(KeyError, match="Rule not found: nonexistent"):
        service.evaluate_rule("nonexistent", {})


def test_evaluate_all():
    service = AutomationService(rules_provider=_rules)
    results = service.evaluate_all({"cr_state": "APPROVED", "project_name": "Alpha", "drone_count": 1, "project_state": "UAT_PREPARE"})

    assert len(results) == 5
    passed = [r for r in results if r.passed]
    skipped = [r for r in results if r.skipped]
    assert len(passed) == 4  # r-1, r-2, r-3, r-5
    assert len(skipped) == 1  # r-4
