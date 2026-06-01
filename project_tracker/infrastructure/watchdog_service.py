from __future__ import annotations

from pathlib import Path
from typing import Callable


class SignalStub:
    def __init__(self) -> None:
        self._callbacks: list[Callable[[Path], None]] = []

    def connect(self, callback: Callable[[Path], None]) -> None:
        self._callbacks.append(callback)

    def emit(self, path: Path) -> None:
        for callback in self._callbacks:
            callback(path)


class WatchdogService:
    def __init__(self, root_path: Path, *, debounce_ms: int = 300) -> None:
        self.root_path = root_path
        self.debounce_ms = debounce_ms
        self.changed = SignalStub()
        self._pending_path: Path | None = None
        self._observer: object | None = None

    def start(self) -> None:
        try:
            from watchdog.observers import Observer
        except ImportError:
            self._observer = None
            return
        self._observer = Observer()

    def stop(self) -> None:
        observer = self._observer
        if observer is not None and hasattr(observer, "stop"):
            observer.stop()
        self._observer = None

    def record_event(self, path: Path) -> None:
        self._pending_path = path

    def flush(self) -> None:
        if self._pending_path is None:
            return
        path = self._pending_path
        self._pending_path = None
        self.changed.emit(path)
