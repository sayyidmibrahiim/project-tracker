from __future__ import annotations

import json
import uuid
from dataclasses import dataclass, field
from json import JSONDecodeError
from pathlib import Path
from typing import Any

from infrastructure.metadata_store import atomic_write_json
from infrastructure.settings_store import link_bank_path


@dataclass(slots=True)
class LinkBank:
    categories: list[str] = field(default_factory=list)
    links: list[dict[str, str]] = field(default_factory=list)
    #: Categories the user archived (Task 6). Missing on legacy files -> [].
    archived_categories: list[str] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> LinkBank:
        categories = data.get("categories", [])
        links = data.get("links", [])
        archived_categories = data.get("archived_categories", [])
        if not isinstance(categories, list):
            categories = []
        if not isinstance(links, list):
            links = []
        if not isinstance(archived_categories, list):
            archived_categories = []
        return cls(
            categories=[str(category) for category in categories if isinstance(category, str)],
            links=[_normalize_link(link) for link in links if isinstance(link, dict)],
            archived_categories=[str(category) for category in archived_categories if isinstance(category, str)],
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "categories": self.categories,
            "links": self.links,
            "archived_categories": self.archived_categories,
        }

    def search(self, query: str) -> list[dict[str, str]]:
        needle = query.casefold()
        return [
            link
            for link in self.links
            if needle in link.get("name", "").casefold()
            or needle in link.get("url", "").casefold()
            or needle in link.get("notes", "").casefold()
        ]


def _normalize_link(link: dict[Any, Any]) -> dict[str, str]:
    details = str(link.get("details", link.get("notes", "")))
    notes = str(link.get("notes", details))
    tags_value = link.get("tags", "")
    if isinstance(tags_value, list):
        tags = ",".join(str(tag).strip() for tag in tags_value if str(tag).strip())
    else:
        tags = str(tags_value)
    return {
        "id": str(link.get("id", "")) or uuid.uuid4().hex,
        "name": str(link.get("name", link.get("title", ""))),
        "url": str(link.get("url", "")),
        "notes": notes,
        "details": details,
        "tags": tags,
        "category": str(link.get("category", link.get("category_id", ""))),
        "archived": _normalize_bool(link.get("archived", False)),
        "pinned": _normalize_bool(link.get("pinned", False)),
        "favorite": _normalize_bool(link.get("favorite", False)),
        "created_at": str(link.get("created_at", "")),
        "updated_at": str(link.get("updated_at", "")),
    }


def _normalize_bool(value: object) -> str:
    """Normalize legacy JSON/CSV flag values to the storage contract."""
    if value is True or value == 1:
        return "true"
    if isinstance(value, str) and value.strip().casefold() in {"true", "1", "yes", "on"}:
        return "true"
    return "false"


class LinkBankStore:
    def __init__(self, path: Path | None = None) -> None:
        self.path = path or link_bank_path()
        self.warnings: list[str] = []

    def read(self) -> LinkBank:
        if not self.path.exists():
            return LinkBank()

        try:
            with self.path.open("r", encoding="utf-8") as file:
                data: object = json.load(file)
        except JSONDecodeError:
            self.warnings.append(f"Corrupt JSON: {self.path}")
            return LinkBank()

        if not isinstance(data, dict):
            self.warnings.append(f"Invalid schema: {self.path}")
            return LinkBank()
        return LinkBank.from_dict(data)

    def write(self, bank: LinkBank) -> None:
        atomic_write_json(self.path, bank.to_dict())
