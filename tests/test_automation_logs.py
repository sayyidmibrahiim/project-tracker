"""Slice 5 tests for cross-module automation_logs and rule-log clearing."""

from __future__ import annotations

from datetime import datetime, timezone

from infrastructure.cache_db import AutomationLogRow, AutomationRuleLogRow, CacheDb


def _cache(tmp_path):
    cache = CacheDb(tmp_path / "cache.sqlite3")
    cache.initialize()
    return cache


def test_append_and_list_automation_logs_filters(tmp_path):
    cache = _cache(tmp_path)
    cache.append_log(AutomationLogRow(module="outlook", cr_id="2026-001", event_type="DRAFT", detail="draft opened", timestamp=datetime(2026, 1, 1, tzinfo=timezone.utc)))
    cache.append_log(AutomationLogRow(module="teams", cr_id="2026-002", event_type="PREVIEW", detail="preview", timestamp=datetime(2026, 1, 2, tzinfo=timezone.utc)))

    assert [r.module for r in cache.list_logs()] == ["teams", "outlook"]  # newest first by id
    assert [r.cr_id for r in cache.list_logs(module="outlook")] == ["2026-001"]
    assert [r.module for r in cache.list_logs(cr_id="2026-002")] == ["teams"]


def test_purge_logs_for_cr_only_deletes_cross_module_rows(tmp_path):
    cache = _cache(tmp_path)
    cache.append_log(AutomationLogRow(module="outlook", cr_id="2026-001", event_type="X"))
    cache.append_log(AutomationLogRow(module="teams", cr_id="2026-002", event_type="Y"))
    cache.append_rule_log(AutomationRuleLogRow(rule_id="r1", success=True))

    assert cache.purge_logs_for_cr("2026-001") == 1
    assert [r.cr_id for r in cache.list_logs()] == ["2026-002"]
    # Backward-compatible rules-only table untouched.
    assert [r.rule_id for r in cache.list_rule_logs()] == ["r1"]


def test_clear_all_logs_only_deletes_cross_module_logs(tmp_path):
    cache = _cache(tmp_path)
    cache.append_log(AutomationLogRow(module="outlook", cr_id="2026-001", event_type="X"))
    cache.append_log(AutomationLogRow(module="teams", cr_id="2026-002", event_type="Y"))
    cache.append_rule_log(AutomationRuleLogRow(rule_id="r1", success=True))

    assert cache.clear_all_logs() == 2
    assert cache.list_logs() == []
    assert len(cache.list_rule_logs()) == 1


def test_clear_rule_logs_only_deletes_one_rule(tmp_path):
    cache = _cache(tmp_path)
    cache.append_rule_log(AutomationRuleLogRow(rule_id="r1", success=True))
    cache.append_rule_log(AutomationRuleLogRow(rule_id="r2", success=True))

    assert cache.clear_rule_logs("r1") == 1
    assert [r.rule_id for r in cache.list_rule_logs()] == ["r2"]
