"""Link Bank business service: CRUD, archive/restore, browser open, import/export.

Wraps ``LinkBankStore`` (atomic JSON persistence) with the rules that used to
live inline in ``app_web._LinkBankAdapter``, plus the Task 6 additions:
category archive/restore parity, browser open through an injectable opener,
and a stateless preview -> confirm -> atomic-merge import flow for CSV/JSON.

``import_json``/``export_json`` remain a blunt, backward-compatible full-bank
replace/read (unchanged behavior). ``preview_import``/``merge_import`` are the
new deterministic-merge pathway (design doc 2026-07-12 §4.5/§15.3): parse,
validate, preview add/update/conflict/invalid counts, then a single atomic
write on confirm. Malformed input never reaches ``LinkBankStore.write``.
"""

from __future__ import annotations

import csv
import io
import json
import uuid
import webbrowser
from collections.abc import Callable
from typing import Any
from urllib.parse import urlparse

from core.models import local_now
from infrastructure.link_bank_store import LinkBank, LinkBankStore, _normalize_link

#: CSV column order (Task 6 rule 2 / design doc §15.3).
CSV_COLUMNS = [
    "id",
    "name",
    "url",
    "category",
    "tags",
    "description",
    "pinned",
    "favorite",
    "archived",
    "created_at",
    "updated_at",
]


def _now() -> str:
    return local_now().isoformat()


def _normalize_url(url: str) -> str:
    return url.strip().rstrip("/").casefold()


def _is_http_url(url: str) -> bool:
    return urlparse(url).scheme in {"http", "https"}


class LinkBankService:
    """Business rules around ``LinkBankStore``."""

    def __init__(self, store: LinkBankStore, *, opener: Callable[[str], object] | None = None) -> None:
        self._store = store
        # ponytail: injected opener so tests never spawn a real browser window.
        self._opener = opener or webbrowser.open

    # ── existing CRUD protocol (kept backward compatible) ──────────────

    def get_linkbank(self) -> dict[str, Any]:
        return self._store.read().to_dict()

    def update_linkbank(self, data: dict[str, object]) -> dict[str, Any]:
        """Update a single link's fields by id."""
        link_id = str(data.get("id", ""))
        if not link_id:
            raise ValueError("Link id is required")
        bank = self._store.read()
        target = self._find_link(bank, link_id)
        if target is None:
            raise ValueError(f"Link not found: {link_id}")
        for key in ("name", "url", "notes", "details", "tags", "category", "archived", "pinned", "favorite"):
            if key in data:
                target[key] = str(data[key])
        if "details" in data and "notes" not in data:
            target["notes"] = str(data["details"])
        if "notes" in data and "details" not in data:
            target["details"] = str(data["notes"])
        old_category = target.get("category", "")
        if old_category and old_category not in bank.categories:
            bank.categories.append(old_category)
        target["updated_at"] = _now()
        self._store.write(bank)
        return dict(target)

    def add_link(self, data: dict[str, object]) -> dict[str, Any]:
        """Create a new link with a stable uuid id and persist it."""
        name = str(data.get("name", data.get("title", ""))).strip()
        url = str(data.get("url", "")).strip()
        if not name or not url:
            raise ValueError("Link name and url are required")
        if not _is_http_url(url):
            raise ValueError("Link url must use http or https")
        details = str(data.get("details", data.get("notes", "")))
        now = _now()
        bank = self._store.read()
        link = {
            "id": uuid.uuid4().hex,
            "name": name,
            "url": url,
            "notes": details,
            "details": details,
            "tags": str(data.get("tags", "")),
            "category": str(data.get("category", "")),
            "archived": "false",
            "pinned": str(data.get("pinned", "false")).lower(),
            "favorite": str(data.get("favorite", "false")).lower(),
            "created_at": now,
            "updated_at": now,
        }
        bank.links.append(link)
        category = link["category"]
        if category and category not in bank.categories:
            bank.categories.append(category)
        self._store.write(bank)
        return dict(link)

    def archive_link(self, link_id: str) -> dict[str, Any]:
        """Soft-archive a link by id."""
        return self._set_link_archived(link_id, True)

    def restore_link(self, link_id: str) -> dict[str, Any]:
        """Reverse ``archive_link`` for a single link."""
        return self._set_link_archived(link_id, False)

    def category_create(self, name: str) -> dict[str, Any]:
        category = str(name).strip()
        if not category:
            raise ValueError("Category name is required")
        bank = self._store.read()
        if category not in bank.categories:
            bank.categories.append(category)
        self._store.write(bank)
        return bank.to_dict()

    def category_rename(self, old_name: str, new_name: str) -> dict[str, Any]:
        old = str(old_name).strip()
        new = str(new_name).strip()
        if not old or not new:
            raise ValueError("Old and new category names are required")
        bank = self._store.read()
        bank.categories = [new if cat == old else cat for cat in bank.categories]
        bank.archived_categories = [new if cat == old else cat for cat in bank.archived_categories]
        now = _now()
        for link in bank.links:
            if link.get("category") == old:
                link["category"] = new
                link["updated_at"] = now
        if new not in bank.categories:
            bank.categories.append(new)
        self._store.write(bank)
        return bank.to_dict()

    def category_archive(self, name: str) -> dict[str, Any]:
        """Archive a category: move it to ``archived_categories`` and archive its links."""
        return self._set_category_archived(name, True)

    def category_restore(self, name: str) -> dict[str, Any]:
        """Reverse ``category_archive``: restore the category and its links."""
        return self._set_category_archived(name, False)

    def open_link(self, link_id: str) -> dict[str, Any]:
        """Open a link's URL through the injected opener (OS default browser)."""
        bank = self._store.read()
        target = self._find_link(bank, link_id)
        if target is None:
            raise ValueError(f"Link not found: {link_id}")
        self._opener(target["url"])
        return dict(target)

    def export_json(self) -> dict[str, Any]:
        return self._store.read().to_dict()

    def import_json(self, data: dict[str, object]) -> dict[str, Any]:
        """Full-bank replace (legacy, blunt overwrite - kept for backward compat)."""
        bank = LinkBank.from_dict(data)
        self._store.write(bank)
        return bank.to_dict()

    def export_file(self, fmt: str = "json") -> dict[str, Any]:
        """Export the complete link bank as JSON or CSV text (rules 1-2)."""
        fmt_normalized = str(fmt).strip().lower()
        bank = self._store.read()
        if fmt_normalized == "json":
            content = json.dumps(bank.to_dict(), indent=2)
        elif fmt_normalized == "csv":
            content = self._to_csv(bank)
        else:
            raise ValueError(f"Unsupported export format: {fmt}")
        return {"format": fmt_normalized, "content": content}

    # ── preview / merge import (stateless: same payload for both calls) ─

    def preview_import(self, payload: dict[str, object]) -> dict[str, Any]:
        """Parse + reconcile against current data; never writes (rule 3)."""
        rows = self._parse_rows(payload)
        bank = self._store.read()
        diff = self._reconcile(bank, rows)
        return self._diff_summary(diff)

    def merge_import(self, payload: dict[str, object]) -> dict[str, Any]:
        """Apply a confirmed import: single atomic write (rule 11)."""
        rows = self._parse_rows(payload)
        bank = self._store.read()
        diff = self._reconcile(bank, rows)
        now = _now()
        for row in diff["to_add"]:
            bank.links.append(self._row_to_link(row, now))
        for existing_id, row in diff["to_update"]:
            target = self._find_link(bank, existing_id)
            if target is not None:
                self._apply_row(target, row, now)
        for category in diff["new_categories"]:
            if category not in bank.categories:
                bank.categories.append(category)
        self._store.write(bank)
        return self._diff_summary(diff)

    # ── internals: archive/restore ──────────────────────────────────────

    def _set_link_archived(self, link_id: str, archived: bool) -> dict[str, Any]:
        link_id = str(link_id)
        if not link_id:
            raise ValueError("Link id is required")
        bank = self._store.read()
        target = self._find_link(bank, link_id)
        if target is None:
            raise ValueError(f"Link not found: {link_id}")
        target["archived"] = "true" if archived else "false"
        target["updated_at"] = _now()
        self._store.write(bank)
        return dict(target)

    def _set_category_archived(self, name: str, archived: bool) -> dict[str, Any]:
        category = str(name).strip()
        if not category:
            raise ValueError("Category name is required")
        bank = self._store.read()
        now = _now()
        for link in bank.links:
            if link.get("category") == category:
                link["archived"] = "true" if archived else "false"
                link["updated_at"] = now
        if archived:
            bank.categories = [cat for cat in bank.categories if cat != category]
            if category not in bank.archived_categories:
                bank.archived_categories.append(category)
        else:
            bank.archived_categories = [cat for cat in bank.archived_categories if cat != category]
            if category not in bank.categories:
                bank.categories.append(category)
        self._store.write(bank)
        return bank.to_dict()

    # ── internals: lookup + CSV ──────────────────────────────────────────

    @staticmethod
    def _find_link(bank: LinkBank, link_id: str) -> dict[str, str] | None:
        return next((link for link in bank.links if link.get("id") == link_id), None)

    @staticmethod
    def _to_csv(bank: LinkBank) -> str:
        buffer = io.StringIO()
        writer = csv.DictWriter(buffer, fieldnames=CSV_COLUMNS)
        writer.writeheader()
        for link in bank.links:
            writer.writerow(
                {
                    "id": link.get("id", ""),
                    "name": link.get("name", ""),
                    "url": link.get("url", ""),
                    "category": link.get("category", ""),
                    "tags": link.get("tags", ""),
                    "description": link.get("details", link.get("notes", "")),
                    "pinned": link.get("pinned", "false"),
                    "favorite": link.get("favorite", "false"),
                    "archived": link.get("archived", "false"),
                    "created_at": link.get("created_at", ""),
                    "updated_at": link.get("updated_at", ""),
                }
            )
        return buffer.getvalue()

    # ── internals: import parsing ────────────────────────────────────────

    def _parse_rows(self, payload: dict[str, object]) -> list[dict[str, str]]:
        if not isinstance(payload, dict):
            raise ValueError("Import payload must be an object with 'format' and 'content'")
        fmt = str(payload.get("format", "json")).strip().lower()
        content = payload.get("content", "")
        if not isinstance(content, str) or not content.strip():
            raise ValueError("Import content is required")
        if fmt == "csv":
            return self._parse_csv_rows(content)
        if fmt == "json":
            return self._parse_json_rows(content)
        raise ValueError(f"Unsupported import format: {fmt}")

    @staticmethod
    def _parse_csv_rows(content: str) -> list[dict[str, str]]:
        reader = csv.DictReader(io.StringIO(content))
        if reader.fieldnames is None:
            raise ValueError("CSV import has no header row")
        return [{key: ("" if value is None else str(value)) for key, value in raw.items()} for raw in reader]

    @staticmethod
    def _parse_json_rows(content: str) -> list[dict[str, str]]:
        try:
            data = json.loads(content)
        except json.JSONDecodeError as exc:
            raise ValueError(f"Malformed JSON import: {exc}") from exc
        if isinstance(data, dict):
            rows_data = data.get("links", [])
        elif isinstance(data, list):
            rows_data = data
        else:
            raise ValueError("JSON import must be an object with 'links' or a list of links")
        if not isinstance(rows_data, list):
            raise ValueError("JSON import 'links' must be a list")
        rows: list[dict[str, str]] = []
        for item in rows_data:
            if not isinstance(item, dict):
                raise ValueError("Each imported link must be an object")
            tags_value = item.get("tags", "")
            if isinstance(tags_value, list):
                tags = ",".join(str(tag).strip() for tag in tags_value if str(tag).strip())
            else:
                tags = str(tags_value)
            description = str(item.get("description", item.get("details", item.get("notes", ""))))
            rows.append(
                {
                    "id": str(item.get("id", "")),
                    "name": str(item.get("name", "")),
                    "url": str(item.get("url", "")),
                    "category": str(item.get("category", "")),
                    "tags": tags,
                    "description": description,
                    "pinned": str(item.get("pinned", "false")),
                    "favorite": str(item.get("favorite", "false")),
                    "archived": str(item.get("archived", "false")),
                    "created_at": str(item.get("created_at", "")),
                    "updated_at": str(item.get("updated_at", "")),
                }
            )
        return rows

    # ── internals: reconciliation (rules 4-8) ────────────────────────────

    def _reconcile(self, bank: LinkBank, rows: list[dict[str, str]]) -> dict[str, Any]:
        existing_by_id = {link["id"]: link for link in bank.links}
        existing_url_to_id = {_normalize_url(link.get("url", "")): link["id"] for link in bank.links}
        existing_categories_cf = {cat.casefold(): cat for cat in bank.categories}
        new_categories_cf: dict[str, str] = {}

        seen_ids: set[str] = set()
        seen_urls: set[str] = set()

        to_add: list[dict[str, str]] = []
        to_update: list[tuple[str, dict[str, str]]] = []
        conflicts: list[dict[str, object]] = []
        invalid: list[dict[str, object]] = []

        for raw_row in rows:
            row = dict(raw_row)
            name = str(row.get("name", "")).strip()
            url = str(row.get("url", "")).strip()
            row["name"] = name
            row["url"] = url

            if not name or not _is_http_url(url):
                invalid.append({"row": raw_row, "reason": "invalid name or url"})
                continue

            row_id = str(row.get("id", "")).strip()
            norm_url = _normalize_url(url)

            if row_id and row_id in seen_ids:
                conflicts.append({"row": raw_row, "reason": "duplicate id in import"})
                continue
            if norm_url in seen_urls:
                conflicts.append({"row": raw_row, "reason": "duplicate url in import"})
                continue

            row["category"] = self._resolve_category(
                str(row.get("category", "")), existing_categories_cf, new_categories_cf
            )

            if row_id and row_id in existing_by_id:
                owner_id = existing_url_to_id.get(norm_url)
                if owner_id is not None and owner_id != row_id:
                    conflicts.append({"row": raw_row, "reason": "url belongs to another id"})
                    continue
                to_update.append((row_id, row))
                seen_ids.add(row_id)
                seen_urls.add(norm_url)
            else:
                owner_id = existing_url_to_id.get(norm_url)
                if owner_id is not None:
                    conflicts.append({"row": raw_row, "reason": "url exists under another id"})
                    continue
                to_add.append(row)
                if row_id:
                    seen_ids.add(row_id)
                seen_urls.add(norm_url)

        return {
            "to_add": to_add,
            "to_update": to_update,
            "conflicts": conflicts,
            "invalid": invalid,
            "new_categories": list(new_categories_cf.values()),
        }

    @staticmethod
    def _resolve_category(
        category_raw: str, existing_cf: dict[str, str], new_cf: dict[str, str]
    ) -> str:
        """Case-insensitive category merge preserving canonical spelling (rule 8)."""
        category = category_raw.strip()
        if not category:
            return ""
        key = category.casefold()
        if key in existing_cf:
            return existing_cf[key]
        if key in new_cf:
            return new_cf[key]
        new_cf[key] = category
        return category

    @staticmethod
    def _diff_summary(diff: dict[str, Any]) -> dict[str, Any]:
        return {
            "added": len(diff["to_add"]),
            "updated": len(diff["to_update"]),
            "conflicts": len(diff["conflicts"]),
            "invalid": len(diff["invalid"]),
            "skipped": [*diff["conflicts"], *diff["invalid"]],
        }

    def _row_to_link(self, row: dict[str, str], now: str) -> dict[str, str]:
        link_id = str(row.get("id", "")).strip() or uuid.uuid4().hex
        description = row.get("description", "")
        return _normalize_link(
            {
                "id": link_id,
                "name": row.get("name", ""),
                "url": row.get("url", ""),
                "category": row.get("category", ""),
                "tags": row.get("tags", ""),
                "notes": description,
                "details": description,
                "pinned": row.get("pinned", "false"),
                "favorite": row.get("favorite", "false"),
                "archived": row.get("archived", "false"),
                "created_at": row.get("created_at") or now,
                "updated_at": now,
            }
        )

    @staticmethod
    def _apply_row(target: dict[str, str], row: dict[str, str], now: str) -> None:
        target["name"] = row.get("name") or target.get("name", "")
        target["url"] = row.get("url") or target.get("url", "")
        target["category"] = row.get("category", target.get("category", ""))
        target["tags"] = row.get("tags", target.get("tags", ""))
        description = row.get("description", "")
        if description:
            target["notes"] = description
            target["details"] = description
        for flag in ("pinned", "favorite", "archived"):
            value = row.get(flag, "")
            if value:
                target[flag] = str(value).strip().lower()
        target["updated_at"] = now
