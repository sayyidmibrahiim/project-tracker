"""Second Brain service: read/search plus durable pin/favorite and note CRUD."""

from __future__ import annotations

import json
import os
from collections.abc import Callable
from dataclasses import dataclass, replace
from datetime import datetime
from json import JSONDecodeError
from pathlib import Path

from project_tracker.infrastructure.filesystem import (
    assert_within,
    create_directory,
    create_file,
    delete_target,
)
from project_tracker.infrastructure.metadata_store import atomic_write_json

#: Sidecar index file persisted under the Second Brain folder. Chosen over the
#: rebuildable Cache_Db so the pin/favorite metadata travels with the notes
#: folder and rebuilds trivially (design §13).
INDEX_FILENAME = ".project_tracker_index.json"
INDEX_VERSION = 1


@dataclass(frozen=True)
class SecondBrainItem:
    """Second Brain item DTO."""

    id: str
    title: str
    path: Path
    item_type: str
    updated_at: datetime | None = None
    pinned: bool = False
    favorite: bool = False
    excerpt: str = ""


class SecondBrainService:
    """Provider-backed Second Brain read/search service with durable metadata.

    Pin/favorite flags persist to an atomic sidecar
    ``{second_brain_folder}/.project_tracker_index.json`` and are restored on
    startup. Note ``create``/``write``/``delete`` operations route through the
    shared filesystem helpers so a failure leaves the folder contents unchanged
    and deletes go to the Recycle Bin via ``send2trash`` only.
    """

    def __init__(
        self,
        items_provider: Callable[[], list[SecondBrainItem]] | None = None,
        folder_provider: Callable[[], Path | None] | None = None,
    ) -> None:
        self._items_provider = items_provider or list
        self._folder_provider = folder_provider
        self._items_by_id: dict[str, SecondBrainItem] | None = None
        self._persisted: dict[str, dict[str, bool]] = {}
        self._persisted_loaded = False

    # ── reads ────────────────────────────────────────────────────────
    def list_items(self) -> list[SecondBrainItem]:
        """Return Second Brain items with persisted pin/favorite applied."""
        return list(self._items())

    def search(self, query: str) -> list[SecondBrainItem]:
        """Search items by title, path, or excerpt."""
        normalized = query.strip().casefold()
        items = self._items()
        if not normalized:
            return list(items)
        return [
            item
            for item in items
            if normalized in item.title.casefold()
            or normalized in str(item.path).casefold()
            or normalized in item.excerpt.casefold()
        ]

    def get_item(self, item_id: str) -> SecondBrainItem | None:
        """Return matching item or None."""
        return self._items_by_id_map().get(item_id)

    # ── durable pin/favorite ──────────────────────────────────────────
    def pin_item(self, item_id: str) -> SecondBrainItem:
        """Toggle the pinned flag and persist it durably."""
        return self._toggle_flag(item_id, "pinned")

    def favorite_item(self, item_id: str) -> SecondBrainItem:
        """Toggle the favorite flag and persist it durably."""
        return self._toggle_flag(item_id, "favorite")

    # ── note CRUD ─────────────────────────────────────────────────────
    def create_note(self, parent: Path, filename: str, content: str = "") -> Path:
        """Create a new note ``parent/filename`` within the Second Brain folder.

        The name is validated and the target must resolve within the folder; an
        existing target is rejected without overwrite (Req 13.4/13.5). On any
        failure no write occurs so the folder contents are left unchanged
        (Req 13.8). The search index is invalidated so the next list/search
        reflects the new note (Req 13.9).
        """
        folder = self._require_folder()
        target = create_file(folder, parent / filename, content=content)
        self._invalidate()
        return target

    def create_folder(self, parent: Path, name: str) -> Path:
        """Create a subfolder ``parent/name`` within the Second Brain folder.

        Mirrors ``create_note`` discipline: the name is validated, the target
        must resolve within the root, and an existing target is rejected (no
        silent reuse) so the UI can surface "already exists" honestly.
        """
        folder = self._require_folder()
        target = (parent / name).resolve()
        assert_within(folder, target)
        if target.exists():
            raise FileExistsError(f"Second Brain folder already exists: {target}")
        result = create_directory(folder, target)
        self._invalidate()
        return result

    #: Text-like extensions the in-app editor can open and edit (Req 13.1).
    TEXT_LIKE_EXTENSIONS: frozenset[str] = frozenset(
        {".md", ".txt", ".py", ".sql", ".json", ".csv", ".log", ".ini", ".yaml", ".yml", ".ts", ".js", ".html", ".css"}
    )

    def create_file(self, parent: Path, filename: str, content: str = "") -> Path:
        """Create a generic text-like file ``parent/filename`` in the Second Brain.

        Same guards as ``create_note`` plus an extension allowlist: only
        text-like files may be created here (binary/unknown types must be added
        by the user via the OS file system). An existing target is rejected
        without overwrite.
        """
        folder = self._require_folder()
        suffix = Path(filename).suffix.casefold()
        if suffix not in self.TEXT_LIKE_EXTENSIONS:
            raise ValueError(
                f"Unsupported file type '{suffix}'. Only text-like files "
                f"({', '.join(sorted(self.TEXT_LIKE_EXTENSIONS))}) can be created here."
            )
        target = create_file(folder, parent / filename, content=content)
        self._invalidate()
        return target

    def write_note(self, filepath: Path, content: str) -> Path:
        """Persist ``content`` to ``filepath`` via a temp-file-then-replace write.

        The original file content is retained unchanged if the write does not
        complete (Req 13.6/13.8). The search index is invalidated so the next
        list/search reflects the edited content (Req 13.9).
        """
        folder = self._require_folder()
        assert_within(folder, filepath)
        self._atomic_write_text(filepath, content)
        self._invalidate()
        return filepath

    def delete_note(self, filepath: Path) -> None:
        """Send ``filepath`` to the Recycle Bin via ``send2trash`` only.

        The target must resolve within the Second Brain folder. On failure the
        folder contents are left unchanged (Req 13.7/13.8). The search index is
        invalidated so the next list/search reflects the removal (Req 13.9).
        """
        folder = self._require_folder()
        delete_target(filepath, base=folder)
        self._invalidate()

    # ── internals ─────────────────────────────────────────────────────
    def _items(self) -> list[SecondBrainItem]:
        if self._items_by_id is None:
            self._load_persisted()
            built: dict[str, SecondBrainItem] = {}
            for item in self._items_provider():
                flags = self._persisted.get(item.id)
                if flags is not None:
                    item = replace(
                        item,
                        pinned=flags["pinned"],
                        favorite=flags["favorite"],
                    )
                built[item.id] = item
            self._items_by_id = built
        return list(self._items_by_id.values())

    def _items_by_id_map(self) -> dict[str, SecondBrainItem]:
        self._items()
        assert self._items_by_id is not None
        return self._items_by_id

    def _invalidate(self) -> None:
        """Drop the cached index so the next read re-reads from the provider."""
        self._items_by_id = None

    def _toggle_flag(self, item_id: str, flag: str) -> SecondBrainItem:
        items = self._items_by_id_map()
        item = items.get(item_id)
        if item is None:
            raise KeyError(f"Second Brain item not found: {item_id}")

        new_value = not getattr(item, flag)
        prior_persisted = {key: dict(value) for key, value in self._persisted.items()}
        entry = {"pinned": item.pinned, "favorite": item.favorite}
        entry.update(self._persisted.get(item_id, {}))
        entry[flag] = new_value
        self._persisted[item_id] = entry
        try:
            self._persist()
        except Exception:
            # Persistence failed: leave previously persisted metadata unchanged
            # and surface the failure to the caller (Req 13.2).
            self._persisted = prior_persisted
            raise

        updated = replace(item, **{flag: new_value})
        items[item_id] = updated
        return updated

    def _folder(self) -> Path | None:
        if self._folder_provider is None:
            return None
        return self._folder_provider()

    def _require_folder(self) -> Path:
        folder = self._folder()
        if folder is None:
            raise RuntimeError("Second Brain folder is not configured")
        return folder

    def _sidecar_path(self, folder: Path) -> Path:
        return folder / INDEX_FILENAME

    def _load_persisted(self) -> None:
        if self._persisted_loaded:
            return
        self._persisted_loaded = True
        folder = self._folder()
        if folder is None:
            return
        path = self._sidecar_path(folder)
        if not path.is_file():
            return
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, JSONDecodeError):
            return
        if not isinstance(raw, dict):
            return
        items = raw.get("items")
        if not isinstance(items, dict):
            return
        restored: dict[str, dict[str, bool]] = {}
        for item_id, flags in items.items():
            if isinstance(flags, dict):
                restored[str(item_id)] = {
                    "pinned": bool(flags.get("pinned", False)),
                    "favorite": bool(flags.get("favorite", False)),
                }
        self._persisted = restored

    def _persist(self) -> None:
        folder = self._folder()
        if folder is None:
            # No durable store configured yet (pin/favorite stays in memory).
            return
        data = {"version": INDEX_VERSION, "items": self._persisted}
        atomic_write_json(self._sidecar_path(folder), data)

    @staticmethod
    def _atomic_write_text(target: Path, content: str) -> None:
        """Write ``content`` to ``target`` via a sibling temp file then replace.

        The temp file is removed if anything fails before the replace, so the
        destination retains its prior content on failure (Req 13.6).
        """
        target.parent.mkdir(parents=True, exist_ok=True)
        temp_path = target.with_name(f"{target.name}.{os.getpid()}.tmp")
        try:
            with open(temp_path, "w", encoding="utf-8") as handle:
                handle.write(content)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temp_path, target)
        except BaseException:
            try:
                temp_path.unlink()
            except FileNotFoundError:
                pass
            raise
