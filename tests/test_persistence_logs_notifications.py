"""Task 11.4 — Dedicated persistence suite for automation logs and notifications.

These tests are the durable-persistence coverage for Requirement 12. They use a
temporary SQLite cache (``tmp_path``) only and cover:

- survive-restart load: notifications and rule logs persisted by one service
  instance are read back by a fresh service instance over the same cache file
  (simulated application restart);
- dismissed-state persistence: a dismissed notification reloads as dismissed and
  an undismissed one reloads as undismissed;
- write-failure handling: a failing cache surfaces the error via the service
  signal and retains the in-memory/prior persisted state without partial update;
- rebuild non-authoritativeness: the ``notifications`` and ``automation_rule_logs``
  schemas are recreated on rebuild and do not serve as the source of truth.

Requirements: 12.3, 12.5, 12.6, 12.7, 12.8
"""

from __future__ import annotations

import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from core.models import Notification, local_now
from infrastructure.cache_db import (
    AutomationRuleLogRow,
    CacheDb,
)
from services.automation_service import AutomationService
from services.notification_service import NotificationService


# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #


def _init_cache(db_path: Path) -> CacheDb:
    cache = CacheDb(db_path)
    cache.initialize()
    return cache


def _table_names(db_path: Path) -> set[str]:
    with sqlite3.connect(db_path) as connection:
        rows = connection.execute(
            "SELECT name FROM sqlite_master WHERE type = 'table' AND name NOT LIKE 'sqlite_%'"
        ).fetchall()
    return {row[0] for row in rows}


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
    ]


class _ToggleableCache:
    """Wraps a real CacheDb, allowing specific writes to be forced to fail.

    Used to exercise the write-failure paths while keeping a genuine,
    inspectable persisted state behind the failure so tests can assert that the
    prior persisted state is retained with no partial update.
    """

    def __init__(self, inner: CacheDb) -> None:
        self._inner = inner
        self.fail_insert = False
        self.fail_dismiss = False
        self.fail_append = False

    # Notification API ----------------------------------------------------- #
    def insert_notification(self, notification: Notification) -> None:
        if self.fail_insert:
            raise sqlite3.OperationalError("disk I/O error")
        self._inner.insert_notification(notification)

    def set_notification_dismissed(self, notification_id: str, dismissed: bool = True) -> None:
        if self.fail_dismiss:
            raise sqlite3.OperationalError("disk I/O error")
        self._inner.set_notification_dismissed(notification_id, dismissed)

    def list_notifications(self) -> list[Notification]:
        return self._inner.list_notifications()

    # Rule-log API --------------------------------------------------------- #
    def append_rule_log(self, row: AutomationRuleLogRow) -> int:
        if self.fail_append:
            raise sqlite3.OperationalError("disk I/O error")
        return self._inner.append_rule_log(row)

    def list_rule_logs(self) -> list[AutomationRuleLogRow]:
        return self._inner.list_rule_logs()


# --------------------------------------------------------------------------- #
# Survive-restart load (12.5, 12.8)
# --------------------------------------------------------------------------- #


def test_notifications_survive_simulated_restart(tmp_path: Path) -> None:
    """Notifications persisted by one service instance are visible to a fresh
    instance over the same cache file. **Requirement 12.5**"""
    db_path = tmp_path / "cache.sqlite3"
    _init_cache(db_path)

    service = NotificationService(event_publisher=None, cache=CacheDb(db_path))
    first = service.add("INFO", "First", "Message one")
    second = service.add("WARNING", "Second", "Message two")

    # Simulated restart: brand-new service + cache over the same file.
    reloaded = NotificationService(event_publisher=None, cache=CacheDb(db_path))
    reloaded.load_persisted()

    loaded = reloaded.get_all()
    assert {n.id for n in loaded} == {first.id, second.id}
    assert {n.title for n in loaded} == {"First", "Second"}


def test_rule_logs_survive_simulated_restart(tmp_path: Path) -> None:
    """Rule execution logs persisted by one service instance are readable by a
    fresh instance/cache over the same file. **Requirement 12.8**"""
    db_path = tmp_path / "cache.sqlite3"
    _init_cache(db_path)

    service = AutomationService(rules_provider=_rules, cache=CacheDb(db_path))
    service.evaluate_rule("r-1", {"cr_state": "APPROVED"}, trigger_type="manual")
    service.evaluate_rule("r-1", {"cr_state": "CANCELED"}, trigger_type="manual")

    # Simulated restart: read logs back through a fresh cache instance.
    reloaded = CacheDb(db_path)
    logs = reloaded.list_rule_logs()

    assert len(logs) == 2
    assert {log.rule_id for log in logs} == {"r-1"}
    assert {log.success for log in logs} == {True, False}


# --------------------------------------------------------------------------- #
# Dismissed-state persistence (12.5, 12.6)
# --------------------------------------------------------------------------- #


def test_dismissed_state_persists_across_reload(tmp_path: Path) -> None:
    """A dismissed notification reloads as dismissed after a restart.
    **Requirements 12.5, 12.6**"""
    db_path = tmp_path / "cache.sqlite3"
    _init_cache(db_path)

    service = NotificationService(event_publisher=None, cache=CacheDb(db_path))
    created = service.add("WARNING", "Heads up", "Check project")
    service.dismiss(created.id)

    reloaded = NotificationService(event_publisher=None, cache=CacheDb(db_path))
    reloaded.load_persisted()

    all_notifications = reloaded.get_all()
    assert len(all_notifications) == 1
    assert all_notifications[0].id == created.id
    assert all_notifications[0].dismissed is True


def test_mixed_dismissed_states_persist_independently(tmp_path: Path) -> None:
    """Only the dismissed notification reloads as dismissed; the other stays
    undismissed. **Requirement 12.5**"""
    db_path = tmp_path / "cache.sqlite3"
    _init_cache(db_path)

    service = NotificationService(event_publisher=None, cache=CacheDb(db_path))
    kept = service.add("INFO", "Kept", "Stays active")
    dismissed = service.add("INFO", "Gone", "Will be dismissed")
    service.dismiss(dismissed.id)

    reloaded = NotificationService(event_publisher=None, cache=CacheDb(db_path))
    reloaded.load_persisted()

    by_id = {n.id: n for n in reloaded.get_all()}
    assert by_id[kept.id].dismissed is False
    assert by_id[dismissed.id].dismissed is True
    # Undismissed view reflects the persisted state after reload.
    assert [n.id for n in reloaded.get_undismissed()] == [kept.id]


# --------------------------------------------------------------------------- #
# Write-failure handling (12.3, 12.7)
# --------------------------------------------------------------------------- #


def test_notification_create_write_failure_retains_prior_state(tmp_path: Path) -> None:
    """A failed notification create surfaces the error and leaves the prior
    persisted state unchanged with no partial update. **Requirement 12.7**"""
    db_path = tmp_path / "cache.sqlite3"
    inner = _init_cache(db_path)
    cache = _ToggleableCache(inner)

    service = NotificationService(event_publisher=None, cache=cache)
    surfaced: list[tuple[str, Exception]] = []
    service.write_failed.connect(lambda desc, exc: surfaced.append((desc, exc)))

    # First create persists successfully.
    first = service.add("INFO", "First", "Persisted ok")

    # Second create fails at the cache write.
    cache.fail_insert = True
    second = service.add("WARNING", "Second", "Write fails")

    # The error was surfaced.
    assert len(surfaced) == 1
    assert isinstance(surfaced[0][1], sqlite3.OperationalError)
    # In-memory result is retained even though persistence failed.
    assert second in service.get_all()
    # Prior persisted state is intact and not partially updated: only the first
    # notification was durably written.
    persisted = inner.list_notifications()
    assert [n.id for n in persisted] == [first.id]


def test_notification_dismiss_write_failure_retains_state(tmp_path: Path) -> None:
    """A failed dismiss surfaces the error and leaves both the persisted and
    in-memory dismissed state unchanged. **Requirement 12.7**"""
    db_path = tmp_path / "cache.sqlite3"
    inner = _init_cache(db_path)
    cache = _ToggleableCache(inner)

    service = NotificationService(event_publisher=None, cache=cache)
    surfaced: list[tuple[str, Exception]] = []
    service.write_failed.connect(lambda desc, exc: surfaced.append((desc, exc)))

    created = service.add("INFO", "Active", "Still active")

    cache.fail_dismiss = True
    service.dismiss(created.id)

    # The error was surfaced.
    assert len(surfaced) == 1
    assert isinstance(surfaced[0][1], sqlite3.OperationalError)
    # In-memory state is unchanged (still undismissed) so memory and cache align.
    assert service.get_all()[0].dismissed is False
    # Persisted state retains the prior (undismissed) value with no partial update.
    assert inner.list_notifications()[0].dismissed is False


def test_rule_log_write_failure_retains_result_and_surfaces_error(tmp_path: Path) -> None:
    """A failed rule-log write retains the in-memory result and surfaces the
    error rather than raising. **Requirement 12.3**"""
    db_path = tmp_path / "cache.sqlite3"
    inner = _init_cache(db_path)
    cache = _ToggleableCache(inner)
    cache.fail_append = True

    service = AutomationService(rules_provider=_rules, cache=cache)
    surfaced: list[tuple[object, Exception]] = []
    service.log_write_failed.connect(lambda result, exc: surfaced.append((result, exc)))

    result = service.evaluate_rule("r-1", {"cr_state": "APPROVED"})

    # Evaluation did not raise; the in-memory result is intact.
    assert result.passed is True
    # The failure was surfaced.
    assert len(surfaced) == 1
    assert isinstance(surfaced[0][1], sqlite3.OperationalError)
    # Nothing was partially written to the log table.
    assert inner.list_rule_logs() == []


# --------------------------------------------------------------------------- #
# Rebuild non-authoritativeness (12.8)
# --------------------------------------------------------------------------- #


def test_rebuild_recreates_empty_log_and_notification_tables(tmp_path: Path) -> None:
    """Rebuilding the cache recreates the log/notification schemas as empty,
    confirming these tables are not a source of truth. **Requirement 12.8**"""
    db_path = tmp_path / "cache.sqlite3"
    cache = _init_cache(db_path)

    # Populate both tables.
    cache.insert_notification(
        Notification(
            id="n-1",
            type="INFO",
            title="Title",
            message="Message",
            timestamp=datetime(2026, 6, 3, 9, 0, tzinfo=timezone.utc),
            project_path=None,
            dismissed=False,
        )
    )
    cache.append_rule_log(
        AutomationRuleLogRow(
            rule_id="r-1",
            rule_name="CR Approved",
            trigger_type="manual",
            success=True,
            timestamp=local_now(),
        )
    )
    assert cache.list_notifications()
    assert cache.list_rule_logs()

    # Rebuild from initialization (drops and recreates the cache file).
    cache.reset()

    # Schemas exist again and are queryable, but hold no rows: the rebuildable
    # cache never serves as the source of truth for this data.
    assert {"notifications", "automation_rule_logs"} <= _table_names(db_path)
    assert cache.list_notifications() == []
    assert cache.list_rule_logs() == []
    assert cache.health_check() is True
