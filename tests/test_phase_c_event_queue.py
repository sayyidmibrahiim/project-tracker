"""Phase C.3a — Event queue foundation tests (TDD: RED first)."""

import threading
from datetime import datetime, timezone

import pytest

from web.event_queue import (
    clear_events,
    drain_events,
    push_event,
)


@pytest.fixture(autouse=True)
def _isolate_queue():
    """Clear event queue before and after each test."""
    clear_events()
    yield
    clear_events()


class TestPushAndDrain:
    """push_event() then drain_events() returns the event."""

    def test_push_then_drain_returns_event(self):
        push_event("TEST_EVENT", {"key": "value"})
        events = drain_events()
        assert len(events) == 1
        event = events[0]
        assert event["type"] == "TEST_EVENT"
        assert event["payload"] == {"key": "value"}
        assert "timestamp" in event


class TestFIFOOrder:
    """Drain returns events in FIFO order."""

    def test_fifo_order(self):
        push_event("FIRST")
        push_event("SECOND")
        push_event("THIRD")
        events = drain_events()
        types = [e["type"] for e in events]
        assert types == ["FIRST", "SECOND", "THIRD"]


class TestDrainEmpties:
    """Drain removes returned events from queue."""

    def test_drain_empties_queue(self):
        push_event("A")
        push_event("B")
        first = drain_events()
        assert len(first) == 2
        second = drain_events()
        assert second == []


class TestEmptyDrain:
    """Empty drain returns []."""

    def test_empty_drain_returns_empty_list(self):
        result = drain_events()
        assert result == []


class TestDrainLimit:
    """limit drains at most N and leaves remaining events."""

    def test_limit_drains_n(self):
        push_event("A")
        push_event("B")
        push_event("C")
        push_event("D")
        batch = drain_events(limit=2)
        assert len(batch) == 2
        assert batch[0]["type"] == "A"
        assert batch[1]["type"] == "B"
        remaining = drain_events()
        assert len(remaining) == 2
        assert remaining[0]["type"] == "C"
        assert remaining[1]["type"] == "D"

    def test_limit_none_drains_all(self):
        push_event("X")
        push_event("Y")
        events = drain_events(limit=None)
        assert len(events) == 2

    def test_limit_larger_than_queue(self):
        push_event("ONLY")
        events = drain_events(limit=100)
        assert len(events) == 1


class TestPayloadDefault:
    """Payload defaults to {} when omitted."""

    def test_payload_default_empty_dict(self):
        push_event("NO_PAYLOAD")
        events = drain_events()
        assert events[0]["payload"] == {}


class TestTimestamp:
    """Event has timezone-aware ISO timestamp."""

    def test_timestamp_is_timezone_aware_iso(self):
        push_event("TIMED")
        events = drain_events()
        ts_str = events[0]["timestamp"]
        # Must parse as ISO 8601
        parsed = datetime.fromisoformat(ts_str)
        # Must be timezone-aware
        assert parsed.tzinfo is not None

    def test_timestamp_is_recent(self):
        before = datetime.now(tz=timezone.utc)
        push_event("TIMED")
        after = datetime.now(tz=timezone.utc)
        events = drain_events()
        parsed = datetime.fromisoformat(events[0]["timestamp"])
        assert before <= parsed <= after


class TestThreadSafety:
    """Concurrent push from multiple threads drains all events without loss."""

    def test_concurrent_push(self):
        n_threads = 10
        events_per_thread = 50
        total = n_threads * events_per_thread

        def push_batch(thread_id: int):
            for i in range(events_per_thread):
                push_event(f"T{thread_id}", {"i": i})

        threads = [
            threading.Thread(target=push_batch, args=(t,))
            for t in range(n_threads)
        ]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        events = drain_events()
        assert len(events) == total


class TestClearEvents:
    """clear_events() removes all queued events."""

    def test_clear_removes_all(self):
        push_event("WILL_BE_CLEARED")
        push_event("ALSO_CLEARED")
        clear_events()
        assert drain_events() == []
