"""Minimal observer/signal utility used across services.

Replaces four local ``class Signal`` definitions with one importable from
``project_tracker.core.signal`` (Ponytail: DRY).
"""

from __future__ import annotations

from collections.abc import Callable


class Signal:
    """Minimal typed-observer: connect callbacks, emit to all connected."""

    def __init__(self) -> None:
        self._callbacks: list[Callable[..., None]] = []

    def connect(self, callback: Callable[..., None]) -> None:
        self._callbacks.append(callback)

    def emit(self, *args: object, **kwargs: object) -> None:
        for callback in list(self._callbacks):
            callback(*args, **kwargs)
