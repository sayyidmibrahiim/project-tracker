"""Second Brain service foundation."""

from collections.abc import Callable
from dataclasses import dataclass, replace
from datetime import datetime
from pathlib import Path


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
    """Provider-backed Second Brain read/search service."""

    def __init__(
        self,
        items_provider: Callable[[], list[SecondBrainItem]] | None = None,
    ) -> None:
        self._items_provider = items_provider or list
        self._items_by_id: dict[str, SecondBrainItem] | None = None

    def list_items(self) -> list[SecondBrainItem]:
        """Return Second Brain items."""
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

    def pin_item(self, item_id: str) -> SecondBrainItem:
        """Mark item pinned in memory."""
        return self._update_item_flag(item_id, pinned=True)

    def favorite_item(self, item_id: str) -> SecondBrainItem:
        """Mark item favorite in memory."""
        return self._update_item_flag(item_id, favorite=True)

    def _items(self) -> list[SecondBrainItem]:
        if self._items_by_id is None:
            self._items_by_id = {item.id: item for item in self._items_provider()}
        return list(self._items_by_id.values())

    def _items_by_id_map(self) -> dict[str, SecondBrainItem]:
        self._items()
        assert self._items_by_id is not None
        return self._items_by_id

    def _update_item_flag(self, item_id: str, **changes: bool) -> SecondBrainItem:
        items = self._items_by_id_map()
        item = items.get(item_id)
        if item is None:
            raise KeyError(f"Second Brain item not found: {item_id}")
        updated = replace(item, **changes)
        items[item_id] = updated
        return updated
