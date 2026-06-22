"""Automation service foundation and rules-engine execution.

In addition to provider-backed rule evaluation, this module hosts the rules
engine *execution* path (Req 11.3-11.9): a rule runs as trigger -> conditions ->
actions in that order, actions are skipped when conditions are unmet, and exactly
the eight supported action types are dispatched in their defined order, halting on
the first action failure. Each execution writes a single ``automation_rule_logs``
row capturing the actions that completed and any failure.

The engine stays decoupled from concrete integrations: each action type maps to an
injectable handler (``ActionHandler``) returning a Bridge_Response-shaped dict.
The built-in defaults for Outlook/Teams actions reuse the guarded
``outlook_client`` / ``teams_client`` infrastructure (Draft_First / Preview_First),
so no COM/``pyautogui`` ever runs off-Windows (Req 11.6).
"""

from __future__ import annotations

import json
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from project_tracker.core.models import local_now
from project_tracker.core.signal import Signal
from project_tracker.infrastructure.cache_db import AutomationRuleLogRow

if TYPE_CHECKING:
    from project_tracker.infrastructure.cache_db import CacheDb

#: A Bridge_Response-shaped result of executing a single action.
BridgeResponse = dict[str, Any]
#: Signature of an action handler: ``(params, context) -> Bridge_Response``.
ActionHandler = Callable[[dict[str, object], dict[str, object]], BridgeResponse]

#: Exactly the eight supported action types (Req 11.5). The engine rejects any
#: action whose ``type`` is not a member of this set.
SUPPORTED_ACTION_TYPES: frozenset[str] = frozenset(
    {
        "download_email",
        "save_attachment",
        "update_cr_state",
        "update_drone_state",
        "send_outlook_email",
        "send_teams_message",
        "in_app_notification",
        "append_history",
    }
)


@dataclass(frozen=True)
class AutomationRuleResult:
    """Result of evaluating an automation rule."""

    rule_id: str
    rule_name: str
    passed: bool = False
    skipped: bool = False
    matched_conditions: list[dict[str, object]] = field(default_factory=list)


@dataclass(frozen=True)
class AutomationExecutionResult:
    """Result of *executing* an automation rule (trigger -> conditions -> actions).

    ``ok`` is ``False`` only when an action failed (or an unsupported action type
    was encountered); a disabled rule (``skipped``) or unmet conditions
    (``conditions_met=False``) are not failures and leave ``ok=True`` with no
    actions executed. ``actions_executed`` lists the action types that completed
    successfully, in order, up to (but excluding) any failure recorded in
    ``failed_action`` / ``error_message``.
    """

    rule_id: str
    rule_name: str
    ok: bool = True
    skipped: bool = False
    conditions_met: bool = True
    actions_executed: list[str] = field(default_factory=list)
    failed_action: str | None = None
    error_message: str | None = None


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
        cache: CacheDb | None = None,
        *,
        action_handlers: Mapping[str, ActionHandler] | None = None,
        notification_service: object | None = None,
        outlook_draft: Callable[..., BridgeResponse] | None = None,
        teams_send: Callable[..., BridgeResponse] | None = None,
    ) -> None:
        self._rules_provider = rules_provider or list
        self._cache = cache
        self.log_write_failed = Signal()  # emits (AutomationRuleResult, Exception)
        # Execution dependencies. All optional so existing call sites and tests
        # that only evaluate rules keep working unchanged; task 21.2 wires the
        # real services into these slots.
        self._notification_service = notification_service
        self._outlook_draft = outlook_draft
        self._teams_send = teams_send
        # Action dispatch table: built-in guarded defaults overlaid with any
        # caller-supplied handlers (the latter win).
        self._action_handlers: dict[str, ActionHandler] = self._build_default_handlers()
        if action_handlers:
            self._action_handlers.update(action_handlers)

    def list_rules(self) -> list[dict[str, object]]:
        """Return all rules."""
        return list(self._rules_provider())

    def evaluate_rule(
        self,
        rule_id: str,
        context: dict[str, object],
        *,
        trigger_type: str = "",
        persist: bool = True,
    ) -> AutomationRuleResult:
        """Evaluate a single rule against context.

        Each execution result is persisted to the ``automation_rule_logs``
        cache table when a cache is configured. If the persistence write
        fails, the in-memory result is retained and an error is surfaced via
        the ``log_write_failed`` signal rather than raising.
        """
        rules = {r["id"]: r for r in self._rules_provider()}
        rule = rules.get(rule_id)
        if rule is None:
            raise KeyError(f"Rule not found: {rule_id}")

        if not rule.get("enabled", True):
            result = AutomationRuleResult(
                rule_id=rule_id,
                rule_name=str(rule.get("name", "")),
                skipped=True,
            )
            if persist:
                self._persist_result(result, trigger_type)
            return result

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
        result = AutomationRuleResult(
            rule_id=rule_id,
            rule_name=str(rule.get("name", "")),
            passed=passed if condition_list else False,
            matched_conditions=matched,
        )
        if persist:
            self._persist_result(result, trigger_type)
        return result

    def evaluate_all(
        self,
        context: dict[str, object],
        *,
        trigger_type: str = "",
    ) -> list[AutomationRuleResult]:
        """Evaluate all rules against context."""
        return [
            self.evaluate_rule(str(rule["id"]), context, trigger_type=trigger_type)
            for rule in self._rules_provider()
        ]

    # ── Rules-engine execution (Req 11.3-11.9) ───────────────────────────────

    def execute_rule(
        self,
        rule_id: str,
        context: dict[str, object],
        *,
        trigger_type: str = "",
        action_handlers: Mapping[str, ActionHandler] | None = None,
        persist: bool = True,
    ) -> AutomationExecutionResult:
        """Execute a rule as trigger -> conditions -> actions, in that order.

        Behavior (Req 11.3-11.9):

        * A disabled rule is skipped: no conditions are checked and no actions
          run (``skipped=True``, ``ok=True``).
        * Conditions are evaluated before any action. If they are not all met,
          the actions are **not** executed (``conditions_met=False``, ``ok=True``;
          Req 11.4).
        * Actions run in their defined order (Req 11.8). Only the eight
          :data:`SUPPORTED_ACTION_TYPES` are accepted; an unsupported type is a
          failure (Req 11.5).
        * On the first action failure, execution halts; the actions that
          completed plus the failure are recorded and ``ok=False`` is returned
          (Req 11.9).
        * Exactly one ``automation_rule_logs`` row is written per execution,
          capturing the completed actions and any failure (Req 11.7). A log-write
          failure is surfaced via :attr:`log_write_failed` and never crashes
          execution.

        ``action_handlers`` optionally overrides the configured handlers for this
        single call (used by tests); otherwise the service's handler table is
        used.
        """
        rules = {r["id"]: r for r in self._rules_provider()}
        rule = rules.get(rule_id)
        if rule is None:
            raise KeyError(f"Rule not found: {rule_id}")

        rule_name = str(rule.get("name", ""))

        # Disabled rules are skipped entirely (no conditions, no actions).
        if not rule.get("enabled", True):
            result = AutomationExecutionResult(
                rule_id=rule_id, rule_name=rule_name, skipped=True
            )
            if persist:
                self._persist_execution(result, trigger_type, conditions_passed=0)
            return result

        condition_list = self._condition_list(rule)
        matched = [c for c in condition_list if _evaluate_condition(c, context)]
        conditions_met = len(matched) == len(condition_list)

        # Conditions gate: when unmet, do NOT execute actions (Req 11.4).
        if not conditions_met:
            result = AutomationExecutionResult(
                rule_id=rule_id,
                rule_name=rule_name,
                conditions_met=False,
            )
            if persist:
                self._persist_execution(
                    result, trigger_type, conditions_passed=len(matched)
                )
            return result

        handlers = dict(self._action_handlers)
        if action_handlers:
            handlers.update(action_handlers)

        executed: list[str] = []
        failed_action: str | None = None
        error_message: str | None = None

        for action in self._action_list(rule):
            action_type = str(action.get("type", ""))
            params = action.get("params")
            params_dict = params if isinstance(params, dict) else {}

            # Reject any action that is not one of the eight supported types.
            if action_type not in SUPPORTED_ACTION_TYPES:
                failed_action = action_type
                error_message = f"Unsupported action type: {action_type or '(missing)'}"
                break

            handler = handlers.get(action_type)
            if handler is None:  # pragma: no cover - defaults cover all 8 types
                failed_action = action_type
                error_message = f"No handler configured for action: {action_type}"
                break

            try:
                response = handler(params_dict, context)
            except Exception as exc:  # noqa: BLE001 - surfaced as ok=false
                failed_action = action_type
                error_message = str(exc) or exc.__class__.__name__
                break

            if not (isinstance(response, dict) and response.get("ok") is True):
                failed_action = action_type
                error_message = self._error_message_of(response)
                break

            executed.append(action_type)

        ok = failed_action is None
        result = AutomationExecutionResult(
            rule_id=rule_id,
            rule_name=rule_name,
            ok=ok,
            actions_executed=executed,
            failed_action=failed_action,
            error_message=error_message,
        )
        if persist:
            self._persist_execution(result, trigger_type, conditions_passed=len(matched))
        return result

    @staticmethod
    def _condition_list(rule: dict[str, object]) -> list[dict[str, object]]:
        """Extract the rule's condition dicts (ignoring malformed entries)."""
        conditions = rule.get("conditions", [])
        if not isinstance(conditions, list):
            return []
        return [c for c in conditions if isinstance(c, dict)]

    @staticmethod
    def _action_list(rule: dict[str, object]) -> list[dict[str, object]]:
        """Extract the rule's action dicts in their defined order."""
        actions = rule.get("actions", [])
        if not isinstance(actions, list):
            return []
        return [a for a in actions if isinstance(a, dict)]

    @staticmethod
    def _error_message_of(response: object) -> str:
        """Pull a human-readable message out of a failed Bridge_Response."""
        if isinstance(response, dict):
            error = response.get("error")
            if isinstance(error, dict):
                message = error.get("message")
                if isinstance(message, str) and message:
                    return message
        return "Action failed"

    # ── Built-in action handlers (guarded; reused by execution) ──────────────

    def _build_default_handlers(self) -> dict[str, ActionHandler]:
        """Return the default handler for each of the eight action types.

        Outlook/Teams handlers reuse the guarded infrastructure clients so they
        default to Draft_First / Preview_First and never run native automation
        off-Windows (Req 11.6). The remaining handlers delegate to injected
        services where available, and otherwise return a guarded no-op success so
        the engine stays import-clean and testable until task 21.2 wires them.
        """
        return {
            "download_email": self._handle_download_email,
            "save_attachment": self._handle_save_attachment,
            "update_cr_state": self._handle_update_cr_state,
            "update_drone_state": self._handle_update_drone_state,
            "send_outlook_email": self._handle_send_outlook_email,
            "send_teams_message": self._handle_send_teams_message,
            "in_app_notification": self._handle_in_app_notification,
            "append_history": self._handle_append_history,
        }

    @staticmethod
    def _ok(data: object | None = None) -> BridgeResponse:
        return {"ok": True, "data": data, "error": None}

    @staticmethod
    def _noop(action: str) -> BridgeResponse:
        """Guarded no-op success for an action with no service wired yet."""
        return {
            "ok": True,
            "data": {"status": "not_configured", "action": action},
            "error": None,
        }

    def _handle_send_outlook_email(
        self, params: dict[str, object], context: dict[str, object]
    ) -> BridgeResponse:
        """Draft_First Outlook email via the guarded client (dev-skipped off-Windows)."""
        draft = self._outlook_draft
        if draft is None:
            from project_tracker.infrastructure.outlook_client import create_draft_email

            draft = create_draft_email
        return draft(
            str(params.get("to", "") or ""),
            str(params.get("cc", "") or ""),
            str(params.get("subject", "") or ""),
            str(params.get("body", "") or ""),
        )

    def _handle_send_teams_message(
        self, params: dict[str, object], context: dict[str, object]
    ) -> BridgeResponse:
        """Preview_First Teams message via the guarded client (dev-skipped off-Windows)."""
        send = self._teams_send
        if send is None:
            from project_tracker.infrastructure.teams_client import send_teams_message

            send = send_teams_message
        return send(str(params.get("message", "") or ""), teams_auto_send=False)

    def _handle_download_email(
        self, params: dict[str, object], context: dict[str, object]
    ) -> BridgeResponse:
        return self._noop("download_email")

    def _handle_save_attachment(
        self, params: dict[str, object], context: dict[str, object]
    ) -> BridgeResponse:
        return self._noop("save_attachment")

    def _handle_update_cr_state(
        self, params: dict[str, object], context: dict[str, object]
    ) -> BridgeResponse:
        return self._noop("update_cr_state")

    def _handle_update_drone_state(
        self, params: dict[str, object], context: dict[str, object]
    ) -> BridgeResponse:
        return self._noop("update_drone_state")

    def _handle_append_history(
        self, params: dict[str, object], context: dict[str, object]
    ) -> BridgeResponse:
        return self._noop("append_history")

    def _handle_in_app_notification(
        self, params: dict[str, object], context: dict[str, object]
    ) -> BridgeResponse:
        """Deliver an in-app notification through the injected service, if any."""
        service = self._notification_service
        if service is None or not hasattr(service, "add"):
            return self._noop("in_app_notification")
        from pathlib import Path

        raw_path = params.get("project_path")
        project_path = Path(str(raw_path)) if raw_path else None
        service.add(
            str(params.get("notification_type", params.get("type", "info"))),
            str(params.get("title", "") or ""),
            str(params.get("message", "") or ""),
            project_path,
        )
        return self._ok({"status": "notified"})

    def _persist_execution(
        self,
        result: AutomationExecutionResult,
        trigger_type: str,
        *,
        conditions_passed: int,
    ) -> None:
        """Write exactly one ``automation_rule_logs`` row for an execution.

        Captures the actions that completed (as a JSON array) and any failure
        message. On write failure the in-memory result is retained and the error
        surfaced via :attr:`log_write_failed` rather than raising (Req 12.3), so a
        cache problem never crashes rule execution.
        """
        if self._cache is None:
            return
        row = AutomationRuleLogRow(
            rule_id=result.rule_id,
            rule_name=result.rule_name,
            trigger_type=trigger_type,
            conditions_passed=conditions_passed,
            actions_executed=json.dumps(result.actions_executed),
            success=result.ok and not result.skipped,
            error_message=result.error_message,
            timestamp=local_now(),
        )
        try:
            self._cache.append_rule_log(row)
        except Exception as exc:  # noqa: BLE001 - retain result, surface error
            self.log_write_failed.emit(result, exc)

    def _persist_result(
        self,
        result: AutomationRuleResult,
        trigger_type: str,
    ) -> None:
        """Write a rule execution result to the rebuildable cache.

        On write failure the in-memory result is retained (the caller already
        holds it) and the failure is surfaced via ``log_write_failed`` without
        raising, so a cache problem never crashes rule evaluation.
        """
        if self._cache is None:
            return
        row = AutomationRuleLogRow(
            rule_id=result.rule_id,
            rule_name=result.rule_name,
            trigger_type=trigger_type,
            conditions_passed=len(result.matched_conditions),
            actions_executed="[]",
            success=result.passed and not result.skipped,
            error_message=None,
            timestamp=local_now(),
        )
        try:
            self._cache.append_rule_log(row)
        except Exception as exc:  # noqa: BLE001 - retain result, surface error
            self.log_write_failed.emit(result, exc)
