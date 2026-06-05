"""Automation service foundation."""

from collections.abc import Callable
from dataclasses import dataclass, field


@dataclass(frozen=True)
class AutomationRuleResult:
    """Result of evaluating an automation rule."""

    rule_id: str
    rule_name: str
    passed: bool = False
    skipped: bool = False
    matched_conditions: list[dict[str, object]] = field(default_factory=list)


def _evaluate_condition(
    condition: dict[str, object],
    context: dict[str, object],
) -> bool:
    """Evaluate a single condition against context."""
    field = str(condition["field"])
    operator = str(condition["operator"])

    if operator == "exists":
        return field in context

    if field not in context:
        return False

    value = context[field]
    cond_value = condition.get("value")

    if operator == "equals":
        return str(value) == str(cond_value)
    elif operator == "not_equals":
        return str(value) != str(cond_value)
    elif operator == "contains":
        return str(cond_value).casefold() in str(value).casefold()

    raise ValueError(f"Unknown operator: {operator}")


class AutomationService:
    """Provider-backed rule evaluation service."""

    def __init__(
        self,
        rules_provider: Callable[[], list[dict[str, object]]] | None = None,
    ) -> None:
        self._rules_provider = rules_provider or list

    def list_rules(self) -> list[dict[str, object]]:
        """Return all rules."""
        return list(self._rules_provider())

    def evaluate_rule(
        self,
        rule_id: str,
        context: dict[str, object],
    ) -> AutomationRuleResult:
        """Evaluate a single rule against context."""
        rules = {r["id"]: r for r in self._rules_provider()}
        rule = rules.get(rule_id)
        if rule is None:
            raise KeyError(f"Rule not found: {rule_id}")

        if not rule.get("enabled", True):
            return AutomationRuleResult(
                rule_id=rule_id,
                rule_name=str(rule.get("name", "")),
                skipped=True,
            )

        conditions = rule.get("conditions", [])
        if isinstance(conditions, list):
            condition_list: list[dict[str, object]] = []
            for c in conditions:
                if isinstance(c, dict):
                    condition_list.append(c)
        else:
            condition_list = []

        matched: list[dict[str, object]] = []
        for condition in condition_list:
            if _evaluate_condition(condition, context):
                matched.append(condition)

        passed = len(matched) == (len(condition_list) if condition_list else 0)
        return AutomationRuleResult(
            rule_id=rule_id,
            rule_name=str(rule.get("name", "")),
            passed=passed if condition_list else False,
            matched_conditions=matched,
        )

    def evaluate_all(
        self,
        context: dict[str, object],
    ) -> list[AutomationRuleResult]:
        """Evaluate all rules against context."""
        return [
            self.evaluate_rule(str(rule["id"]), context)
            for rule in self._rules_provider()
        ]
