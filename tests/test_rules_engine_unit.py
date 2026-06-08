"""Unit tests for rules CRUD + execution + P8 ordering property (Tasks 21.3/21.4).

Covers:

* P8: Rule action ordering halts on failure -- actions execute in their defined
  order, stop at the first failure, and the completed actions plus the failure
  are recorded in ``automation_rule_logs`` (Req 11.8/11.9). Validated with a
  deterministic seeded random generator (no new dependency, mirroring the other
  property tests in this spec).
* Rules CRUD validation: name required, action ``type`` whitelist enforced,
  invalid input leaves the durable store unchanged.
* Unmet-condition skip: a rule whose conditions are not met executes no actions.
* Each of the eight supported action types is dispatched.
* Exactly one ``automation_rule_logs`` row is written per execution, capturing
  the completed actions and any failure.

All tests run with a real ``CacheDb`` and ``SettingsStore`` pointed at
``tmp_path`` (no real config dir, no real Outlook/Teams).
"""

from __future__ import annotations

import json
import random

import pytest

from project_tracker.infrastructure.cache_db import CacheDb
from project_tracker.infrastructure.settings_store import SettingsStore
from project_tracker.services.automation_service import (
    SUPPORTED_ACTION_TYPES,
    AutomationService,
)
from project_tracker.web.js_api import JsApi


# ---------------------------------------------------------------------------
# _RulesAdapter import — re-construct it from app_web's create_js_api closure.
# Rather than expose it, we exercise it through the JsApi rules_* facade since
# the JsApi surface is the actual contract under test.
# ---------------------------------------------------------------------------


def _api_with_rules(tmp_path) -> tuple[JsApi, CacheDb, SettingsStore]:
    """Build a JsApi wired to a real _RulesAdapter (via create_js_api)."""
    from project_tracker import app_web

    db_path = tmp_path / "cache.sqlite"
    settings_store = SettingsStore(config_dir=tmp_path)
    api = app_web.create_js_api(db_path=db_path, settings_store=settings_store)
    cache = CacheDb(db_path)
    return api, cache, settings_store


# --- CRUD validation ---------------------------------------------------------

def test_rules_create_rejects_invalid_action_type(tmp_path) -> None:
    api, _, store = _api_with_rules(tmp_path)
    resp = api.rules_create({"name": "x", "actions": [{"type": "ping"}]})
    assert resp["ok"] is False
    assert resp["error"]["code"] == "RULES_CREATE_FAILED"
    assert store.read().automation.rules_engine.get("rules", []) == []


def test_rules_create_requires_name(tmp_path) -> None:
    api, _, store = _api_with_rules(tmp_path)
    resp = api.rules_create({"name": "  ", "actions": []})
    assert resp["ok"] is False
    assert store.read().automation.rules_engine.get("rules", []) == []


def test_rules_create_round_trip_persists(tmp_path) -> None:
    api, _, store = _api_with_rules(tmp_path)
    payload = {"name": "r1", "actions": [{"type": "in_app_notification"}]}
    created = api.rules_create(payload)
    assert created["ok"] is True
    rule_id = created["data"]["id"]

    persisted = store.read().automation.rules_engine.get("rules", [])
    assert len(persisted) == 1 and persisted[0]["id"] == rule_id

    # Toggle, update, delete round-trip.
    toggled = api.rules_toggle(rule_id, False)
    assert toggled["ok"] is True and toggled["data"]["enabled"] is False

    updated = api.rules_update(rule_id, {"name": "r1-renamed"})
    assert updated["ok"] is True and updated["data"]["name"] == "r1-renamed"

    deleted = api.rules_delete(rule_id)
    assert deleted["ok"] is True
    assert store.read().automation.rules_engine.get("rules", []) == []


def test_rules_get_logs_returns_only_matching_rule(tmp_path) -> None:
    api, cache, _ = _api_with_rules(tmp_path)
    # Create two rules so we can confirm log filtering.
    a = api.rules_create({"name": "A", "actions": [{"type": "in_app_notification"}]})
    b = api.rules_create({"name": "B", "actions": [{"type": "in_app_notification"}]})
    aid, bid = a["data"]["id"], b["data"]["id"]

    # Drive an execution per rule via AutomationService directly using shared cache.
    svc = AutomationService(
        rules_provider=lambda: [{"id": aid, "name": "A", "enabled": True, "actions": [{"type": "in_app_notification"}]},
                                 {"id": bid, "name": "B", "enabled": True, "actions": [{"type": "in_app_notification"}]}],
        cache=cache,
        notification_service=_StubNotifications(),
    )
    svc.execute_rule(aid, {})
    svc.execute_rule(bid, {})
    svc.execute_rule(aid, {})

    logs = api.rules_get_logs(aid, 10)
    assert logs["ok"] is True
    rule_ids = {row["rule_id"] for row in logs["data"]}
    assert rule_ids == {aid}
    assert len(logs["data"]) == 2  # two executions for A only


# --- Unmet-condition skip + per-action-type dispatch ------------------------

class _StubNotifications:
    def add(self, *args, **kwargs):
        pass


def _service(rule: dict[str, object], cache: CacheDb, *, handlers=None) -> AutomationService:
    return AutomationService(
        rules_provider=lambda: [rule],
        cache=cache,
        notification_service=_StubNotifications(),
        action_handlers=handlers,
    )


def test_unmet_condition_skips_actions_and_logs_one_row(tmp_path) -> None:
    cache = CacheDb(tmp_path / "c.sqlite")
    cache.initialize()
    rule = {
        "id": "r",
        "name": "r",
        "enabled": True,
        "conditions": [{"field": "missing", "operator": "exists"}],  # always fails
        "actions": [{"type": "in_app_notification"}],
    }
    svc = _service(rule, cache)
    res = svc.execute_rule("r", {})
    assert res.ok is True and res.actions_executed == [] and res.conditions_met is False
    rows = cache.list_rule_logs()
    assert len(rows) == 1 and rows[0].rule_id == "r"


def test_each_supported_action_type_is_dispatched(tmp_path) -> None:
    cache = CacheDb(tmp_path / "c.sqlite")
    cache.initialize()
    seen: list[str] = []

    def make_handler(name: str):
        def handler(_params, _ctx):
            seen.append(name)
            return {"ok": True, "data": None, "error": None}
        return handler

    handlers = {action: make_handler(action) for action in SUPPORTED_ACTION_TYPES}
    rule = {
        "id": "r",
        "name": "r",
        "enabled": True,
        "actions": [{"type": t} for t in SUPPORTED_ACTION_TYPES],
    }
    svc = _service(rule, cache, handlers=handlers)
    res = svc.execute_rule("r", {})
    assert res.ok is True
    assert set(res.actions_executed) == set(SUPPORTED_ACTION_TYPES)
    assert set(seen) == set(SUPPORTED_ACTION_TYPES)


# --- P8: action ordering halts on failure -----------------------------------

def test_property_action_ordering_halts_on_failure(tmp_path) -> None:
    """P8: actions run in defined order; stop at first failure; log the cut.

    For 200 random orderings of action types, at most one is set to fail. The
    rule's recorded ``actions_executed`` must equal the prefix of the order up
    to (but not including) the first failing action; ``failed_action`` matches;
    a single log row is written per execution.
    """
    cache = CacheDb(tmp_path / "c.sqlite")
    cache.initialize()
    types = list(SUPPORTED_ACTION_TYPES)

    for seed in range(200):
        rng = random.Random(seed)
        order = rng.sample(types, k=rng.randint(2, len(types)))
        # Maybe inject a failure at a random position.
        fail_at = rng.randrange(-1, len(order))  # -1 means no failure
        failing_type = order[fail_at] if fail_at >= 0 else None

        def make_handler(failing: str | None):
            def handler(_params, _ctx, *, _t: str = ""):
                if _t == failing:
                    return {"ok": False, "data": None, "error": {"code": "X", "message": "boom"}}
                return {"ok": True, "data": None, "error": None}
            return handler

        # Bind the action type into each handler via default arg.
        handlers = {
            t: (lambda p, c, _t=t, _f=failing_type: (
                {"ok": False, "data": None, "error": {"code": "X", "message": "boom"}}
                if _t == _f
                else {"ok": True, "data": None, "error": None}
            ))
            for t in types
        }

        rule = {
            "id": f"r{seed}",
            "name": "r",
            "enabled": True,
            "actions": [{"type": t} for t in order],
        }
        # Use a single AutomationService whose provider returns this rule.
        svc = AutomationService(
            rules_provider=lambda r=rule: [r],
            cache=cache,
            action_handlers=handlers,
            notification_service=_StubNotifications(),
        )
        before = len(cache.list_rule_logs())
        res = svc.execute_rule(rule["id"], {})
        after = len(cache.list_rule_logs())
        assert after - before == 1, f"seed={seed}: expected exactly one log row"

        if failing_type is None:
            assert res.ok is True, f"seed={seed}: unexpected failure {res!r}"
            assert res.actions_executed == order
            assert res.failed_action is None
        else:
            assert res.ok is False, f"seed={seed}: expected failure"
            assert res.failed_action == failing_type
            assert res.actions_executed == order[:fail_at]

        # The latest row's actions_executed JSON matches.
        last = cache.list_rule_logs()[-1]
        assert last.rule_id == rule["id"]
        executed_json = json.loads(last.actions_executed)
        expected = order if failing_type is None else order[:fail_at]
        assert executed_json == expected, f"seed={seed}: log mismatch {executed_json!r} vs {expected!r}"
