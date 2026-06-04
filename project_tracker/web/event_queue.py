"""Thread-safe event queue for background-to-frontend event push.

PRD §19.3 — Background threads push events; frontend polls via drain.
Pure stdlib, no pywebview or service dependencies.
"""

from __future__ import annotations

import queue
from datetime import datetime, timezone
from typing import Any


_event_queue: queue.Queue[dict[str, Any]] = queue.Queue()


def push_event(
    event_type: str,
    payload: dict[str, object] | None = None,
) -> None:
    """Push an event onto the queue (thread-safe, non-blocking).

    Args:
        event_type: Event type string (e.g. "AUTO_IN_PROGRESS", "NOTIFICATION").
        payload: Optional event data. Defaults to empty dict.
    """
    event: dict[str, Any] = {
        "type": event_type,
        "payload": payload if payload is not None else {},
        "timestamp": datetime.now(tz=timezone.utc).astimezone().isoformat(),
    }
    _event_queue.put_nowait(event)


def drain_events(limit: int | None = None) -> list[dict[str, Any]]:
    """Drain events from the queue (FIFO).

    Args:
        limit: Maximum number of events to drain. None = drain all.

    Returns:
        List of event dicts removed from the queue.
    """
    events: list[dict[str, Any]] = []
    count = 0
    while limit is None or count < limit:
        try:
            events.append(_event_queue.get_nowait())
            count += 1
        except queue.Empty:
            break
    return events


def clear_events() -> None:
    """Remove all events from the queue. Intended for test isolation."""
    while not _event_queue.empty():
        try:
            _event_queue.get_nowait()
        except queue.Empty:
            break
