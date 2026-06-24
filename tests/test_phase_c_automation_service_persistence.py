"""Task 11.3 — AutomationService persists rule executions to the cache.

These tests cover the persistence hook only (write a log per execution, and
retain the in-memory result while surfacing an error on write failure). The
broader rules execution engine and dedicated persistence coverage live in
later tasks.
"""

from pathlib import Path

from infrastructure.cache_db import CacheDb
from services.automation_service import AutomationService


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
            "id": "r-4",
            "name": "Disabled Rule",
            "enabled": False,
            "conditions": [
                {"field": "project_name", "operator": "equals", "value": "Beta"},
            ],
        },
    ]


def _cache(tmp_path: Path) -> CacheDb:
    cache = CacheDb(tmp_path / "cache.sqlite3")
    cache.initialize()
    return cache


def test_evaluate_rule_persists_execution_result(tmp_path: Path) -> None:
    cache = _cache(tmp_path)
    service = AutomationService(rules_provider=_rules, cache=cache)

    result = service.evaluate_rule("r-1", {"cr_state": "APPROVED"}, trigger_type="manual")

    logs = cache.list_rule_logs()
    assert len(logs) == 1
    log = logs[0]
    assert log.rule_id == "r-1"
    assert log.rule_name == "CR Approved"
    assert log.trigger_type == "manual"
    assert log.success is True
    assert log.timestamp is not None
    # In-memory result is still returned to the caller.
    assert result.passed is True


def test_evaluate_rule_persists_failed_outcome(tmp_path: Path) -> None:
    cache = _cache(tmp_path)
    service = AutomationService(rules_provider=_rules, cache=cache)

    service.evaluate_rule("r-1", {"cr_state": "CANCELED"})

    logs = cache.list_rule_logs()
    assert len(logs) == 1
    assert logs[0].success is False


def test_evaluate_all_writes_one_log_per_rule(tmp_path: Path) -> None:
    cache = _cache(tmp_path)
    service = AutomationService(rules_provider=_rules, cache=cache)

    service.evaluate_all({"cr_state": "APPROVED"})

    logs = cache.list_rule_logs()
    assert {log.rule_id for log in logs} == {"r-1", "r-4"}
    assert len(logs) == 2


def test_no_cache_means_no_persistence_and_no_crash() -> None:
    service = AutomationService(rules_provider=_rules)
    # Should not raise even though no cache is configured.
    result = service.evaluate_rule("r-1", {"cr_state": "APPROVED"})
    assert result.passed is True


def test_write_failure_retains_result_and_surfaces_error(tmp_path: Path) -> None:
    class FailingCache:
        def append_rule_log(self, row: object) -> int:
            raise RuntimeError("disk full")

    service = AutomationService(rules_provider=_rules, cache=FailingCache())
    surfaced: list[tuple[object, Exception]] = []
    service.log_write_failed.connect(lambda result, exc: surfaced.append((result, exc)))

    # Evaluation must not crash when the cache write fails.
    result = service.evaluate_rule("r-1", {"cr_state": "APPROVED"})

    assert result.passed is True  # in-memory result retained
    assert len(surfaced) == 1
    assert isinstance(surfaced[0][1], RuntimeError)
