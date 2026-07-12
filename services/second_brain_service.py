"""Second Brain cached filesystem index, search, metadata, and Personal CRUD."""

from __future__ import annotations

import base64
import json
import hashlib
import logging
import os
import re
import unicodedata
from collections.abc import Callable
from dataclasses import dataclass, replace
from datetime import date, datetime, timezone
from json import JSONDecodeError
from pathlib import Path, PurePosixPath

from core.enums import ProjectState, ProjectType
from core.models import ProjectMetadata, local_now

from infrastructure.cache_db import CacheDb, SecondBrainActivityRow
from infrastructure.filesystem import (
    ScannedProject,
    assert_within,
    create_directory,
    create_file,
    delete_target,
    discover_appcodes,
    discover_drone_paths,
    rename_file,
    scan_appcode_year,
)
from infrastructure.metadata_store import MetadataStore, atomic_write_json
from services.bootstrap_service import default_second_brain

#: Sidecar index file persisted under the Second Brain folder. Chosen over the
#: rebuildable Cache_Db so the pin/favorite metadata travels with the notes
#: folder and rebuilds trivially (design §13).
INDEX_FILENAME = ".project_tracker_index.json"
INDEX_VERSION = 2
MAX_SEARCHABLE_BYTES = 1024 * 1024
INTERNAL_DIRECTORY_NAMES = frozenset({".git", ".rte", "cicd"})
INTERNAL_FILE_NAMES = frozenset(
    {"project_data.json", "appcode.json", INDEX_FILENAME.casefold()}
)
MARKDOWN_EXTENSIONS = frozenset({".md"})
TEXT_EXTENSIONS = frozenset(
    {
        ".txt", ".py", ".sh", ".ps1", ".sql", ".json", ".csv", ".log",
        ".yml", ".yaml", ".xml", ".toml", ".ini", ".cfg", ".env", ".ts",
        ".js", ".html", ".css",
    }
)
IMAGE_EXTENSIONS = frozenset({".png", ".jpg", ".jpeg", ".gif", ".bmp"})
IMAGE_MIME_TYPES = {
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".gif": "image/gif",
    ".bmp": "image/bmp",
}
WIKI_LINK_PATTERN = re.compile(r"\[\[([^\]]+)\]\]")

logger = logging.getLogger(__name__)

#: Task 5: supported Second Brain recent-activity actions.
ACTIVITY_ACTIONS = frozenset(
    {"opened", "created", "edited", "renamed", "recycled", "opened_externally"}
)


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
    source: str = "personal"
    relative_path: str = ""
    tree_path: str = ""
    parent_path: str | None = None
    open_mode: str = "external"
    file_format: str = ""
    project_path: Path | None = None
    project_state: str | None = None
    appcode: str | None = None
    year: str | None = None
    project_name: str | None = None
    drone_name: str | None = None
    locked: bool = False
    tags: tuple[str, ...] = ()
    match_reason: str | None = None


class SecondBrainService:
    """Cached Personal + Project index with a provider seam for focused tests.

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
        root_provider: Callable[[], Path | None] | None = None,
        metadata_store: MetadataStore | None = None,
        folder_setter: Callable[[Path], None] | None = None,
        cache: CacheDb | None = None,
    ) -> None:
        self._items_provider = items_provider
        self._folder_provider = folder_provider
        self._root_provider = root_provider
        self._metadata_store = metadata_store or MetadataStore()
        self._folder_setter = folder_setter
        self._cache = cache
        self._items_by_id: dict[str, SecondBrainItem] | None = None
        self._full_text_by_id: dict[str, str] | None = None
        self._warnings: list[str] = []
        self._personal_root: Path | None = None
        self._project_root: Path | None = None
        self._personal_status = "unset"
        self._persisted: dict[str, dict[str, object]] = {}
        self._persisted_loaded = False
        self._context_initialized = False
        self._folder_snapshot: Path | None = None
        self._root_snapshot: Path | None = None

    # ── reads ────────────────────────────────────────────────────────
    def list_items(self) -> list[SecondBrainItem]:
        """Return Second Brain items with persisted pin/favorite applied."""
        return list(self._items())

    def search(
        self,
        query: str,
        date_filter: str = "",
        sort: str = "newest",
        type_filter: str = "all",
        source_filter: str = "all",
    ) -> list[SecondBrainItem]:
        """Filter and search the complete cached index, then sort results."""
        normalized = query.strip().casefold()
        filtered = [
            item
            for item in self._items()
            if self._matches_source(item, source_filter)
            and self._matches_type(item, type_filter)
            and self._matches_date(item, date_filter)
        ]
        matched: list[SecondBrainItem] = []
        for item in filtered:
            reason = self._match_reason(item, normalized) if normalized else None
            if normalized and reason is None:
                continue
            matched.append(replace(item, match_reason=reason))
        return self._sort_items(matched, sort)

    def get_item(self, item_id: str) -> SecondBrainItem | None:
        """Return matching item or None."""
        return self._items_by_id_map().get(item_id)

    def workspace(self) -> dict[str, object]:
        """Return the complete cached Personal + Project workspace index."""
        items = self._items()
        return {
            "items": list(items),
            "warnings": list(self._warnings),
            "personal_root": self._personal_root,
            "project_root": self._project_root,
            "personal_status": self._personal_status,
        }

    # ── durable pin/favorite ──────────────────────────────────────────
    def pin_item(self, item_id: str) -> SecondBrainItem:
        """Toggle the pinned flag and persist it durably."""
        return self._toggle_flag(item_id, "pinned")

    def favorite_item(self, item_id: str) -> SecondBrainItem:
        """Toggle the favorite flag and persist it durably."""
        return self._toggle_flag(item_id, "favorite")

    def set_tags(self, item_id: str, tags: list[str]) -> SecondBrainItem:
        """Replace one item's normalized tags and persist them atomically."""
        items = self._items_by_id_map()
        item = items.get(item_id)
        if item is None:
            raise KeyError(f"Second Brain item not found: {item_id}")
        normalized = self._normalize_tags(tags)
        prior_persisted = {key: dict(value) for key, value in self._persisted.items()}
        entry = {
            "pinned": item.pinned,
            "favorite": item.favorite,
            "tags": list(item.tags),
        }
        entry.update(self._persisted.get(item_id, {}))
        entry["tags"] = list(normalized)
        self._persisted[item_id] = entry
        try:
            self._persist()
        except Exception:
            self._persisted = prior_persisted
            raise
        updated = replace(item, tags=normalized)
        items[item_id] = updated
        return updated

    def related(self, item_id: str, limit: int = 20) -> list[dict[str, object]]:
        """Rank wiki, tag, Drone, and project relationships deterministically."""
        items = self._items_by_id_map()
        current = items.get(item_id)
        if current is None:
            raise KeyError(f"Second Brain item not found: {item_id}")
        if limit <= 0:
            return []

        current_wiki_targets = self._wiki_targets(current)
        current_tags = {tag.casefold() for tag in current.tags}
        ranked: list[dict[str, object]] = []
        scores = {"wiki_link": 4, "shared_tag": 3, "same_drone": 2, "same_project": 1}
        for candidate in items.values():
            if candidate.id == current.id or candidate.item_type == "folder":
                continue
            reason: str | None = None
            if self._wiki_matches(current_wiki_targets, candidate) or self._wiki_matches(
                self._wiki_targets(candidate), current
            ):
                reason = "wiki_link"
            elif current_tags.intersection(tag.casefold() for tag in candidate.tags):
                reason = "shared_tag"
            elif (
                current.project_path is not None
                and current.project_path == candidate.project_path
                and current.drone_name
                and current.drone_name == candidate.drone_name
            ):
                reason = "same_drone"
            elif current.project_path is not None and current.project_path == candidate.project_path:
                reason = "same_project"
            if reason is not None:
                ranked.append({"item": candidate, "reason": reason, "score": scores[reason]})
        ranked.sort(
            key=lambda row: (
                -int(row["score"]),
                str(row["item"].title).casefold(),
                str(row["item"].path).casefold(),
            )
        )
        return ranked[:limit]

    def invalidate(self) -> None:
        """Public cache invalidation for mutations and manual refresh."""
        self._invalidate()

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
        self._record_created(target)
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
        self._record_created(result)
        return result

    #: Text-like extensions the in-app editor can open and edit (Req 13.1).
    TEXT_LIKE_EXTENSIONS: frozenset[str] = MARKDOWN_EXTENSIONS | TEXT_EXTENSIONS

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
        self._record_created(target)
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

    # ── guarded personal item ops ────────────────────────────────────────
    def rename_item(self, filepath: Path, new_name: str) -> SecondBrainItem:
        """Rename a Personal item (file or folder) in place.

        Only ``source == "personal"`` items may be renamed; a Project item
        rejects with a clear error (Project docs are never mutated here).
        Windows filename validation, path-traversal, and duplicate-target
        guards route through the existing ``rename_file`` helper. When the
        renamed item is a folder, every descendant already in the index has
        its persisted pin/favorite/tags entry remapped from the old relative
        path to the new one so metadata survives the move.

        The physical rename is the source of truth: once ``rename_file``
        succeeds, this method always reports success. A sidecar (pin/
        favorite/tags) persist failure afterward is best-effort — it is
        logged, the in-memory remap is kept so this process keeps serving
        correct flags, and the cache is unconditionally invalidated so the
        next read reflects the renamed path either way.
        """
        folder = self._require_folder()
        item = self._find_by_path(filepath)
        if item is None:
            raise KeyError(f"Second Brain item not found: {filepath}")
        if item.source != "personal":
            raise ValueError("Only Personal items can be renamed")

        source = item.path
        destination = source.with_name(new_name)
        old_relative = item.relative_path
        new_relative = self._sibling_relative(old_relative, new_name)

        remap = {item.id: self._stable_id(f"personal/{new_relative}")}
        if item.item_type == "folder":
            prefix = f"{old_relative}/"
            for other in self._items_by_id_map().values():
                if other.source == "personal" and other.relative_path.startswith(prefix):
                    suffix = other.relative_path[len(old_relative):]
                    remap[other.id] = self._stable_id(f"personal/{new_relative}{suffix}")

        rename_file(folder, source, destination)
        try:
            self._remap_persisted(remap)
        finally:
            self._invalidate()

        renamed = self._find_by_path(destination)
        if renamed is None:
            raise RuntimeError(f"Renamed item vanished from index: {destination}")
        self.record_activity(renamed.id, "renamed")
        return renamed

    def recycle_item(self, filepath: Path) -> None:
        """Send a Personal item to the Recycle Bin via ``send2trash`` (Personal-only).

        A Project item rejects with a clear error. Persisted pin/favorite/
        tags entries for the removed item — and, for a folder, every indexed
        descendant — are dropped so the sidecar never accumulates metadata
        for paths that no longer exist.

        The physical recycle is the source of truth: once ``delete_target``
        succeeds, this method always reports success. A sidecar persist
        failure afterward (dropping the stale entries) is best-effort — it
        is logged and the cache is unconditionally invalidated so the next
        read no longer shows the recycled item either way.
        """
        folder = self._require_folder()
        item = self._find_by_path(filepath)
        if item is None:
            raise KeyError(f"Second Brain item not found: {filepath}")
        if item.source != "personal":
            raise ValueError("Only Personal items can be recycled")

        stale_ids = {item.id}
        if item.item_type == "folder":
            prefix = f"{item.relative_path}/"
            stale_ids.update(
                other.id
                for other in self._items_by_id_map().values()
                if other.source == "personal" and other.relative_path.startswith(prefix)
            )

        delete_target(item.path, base=folder)
        self.record_activity(item.id, "recycled")
        try:
            self._drop_persisted(stale_ids)
        finally:
            self._invalidate()

    def read_image(self, filepath: Path) -> dict[str, object]:
        """Return a base64 data URI preview for an indexed image item only.

        Guards against reading arbitrary files off disk: ``filepath`` must
        match a currently indexed item whose ``open_mode`` is ``"image"``.
        """
        item = self._find_by_path(filepath)
        if item is None or item.open_mode != "image":
            raise ValueError(f"Not an indexed image item: {filepath}")
        data = item.path.read_bytes()
        encoded = base64.b64encode(data).decode("ascii")
        mime = IMAGE_MIME_TYPES.get(item.path.suffix.casefold(), "application/octet-stream")
        return {"data_uri": f"data:{mime};base64,{encoded}", "name": item.path.name}

    def mark_saved(self, filepath: Path) -> None:
        """Invalidate and eagerly rebuild the index after a shared RTE autosave.

        The RTE save path writes directly to disk via the notes/rte services
        (outside ``SecondBrainService``), so the cached index and full-content
        search would otherwise keep serving the pre-save excerpt until the
        next unrelated read. Rebuilding immediately means the very next
        search already reflects the edit. ``filepath`` identifies the saved
        item for callers/logging symmetry with the other guarded ops; a full
        rebuild is the only granularity the cache supports today.
        """
        self._invalidate()
        self._items()
        item = self._find_by_path(filepath)
        if item is not None:
            self.record_activity(item.id, "edited")

    def use_default_folder(self) -> Path:
        """Create ``<root>/Second Brain`` (if needed) and persist it as active.

        The folder is created on disk before the Settings update fires, so a
        setter failure never leaves Settings pointing at a folder that does
        not exist yet.
        """
        root = self._root()
        if root is None:
            raise RuntimeError("Root folder is not configured")
        target = default_second_brain(root)
        target.mkdir(parents=True, exist_ok=True)
        if self._folder_setter is not None:
            self._folder_setter(target)
        return target

    def refresh(self) -> dict[str, object]:
        """Force a full reindex and return the fresh workspace (manual refresh)."""
        self._invalidate()
        return self.workspace()

    # ── recent activity (Task 5) ────────────────────────────────────────
    def record_activity(self, item_id: str, action: str) -> SecondBrainActivityRow | None:
        """Best-effort capped recent-activity ledger entry.

        No-op (returns ``None``) when no cache is wired, when ``item_id``
        no longer resolves in the index, or when persisting fails — a
        ledger write must never break the mutation that already succeeded.
        Dedupe/cap/ordering live in ``CacheDb.append_second_brain_activity``.
        """
        if action not in ACTIVITY_ACTIONS:
            raise ValueError(f"Unsupported Second Brain activity action: {action}")
        if self._cache is None:
            return None
        item = self.get_item(item_id)
        if item is None:
            return None
        row = SecondBrainActivityRow(
            item_id=item.id,
            path=item.path,
            title=item.title,
            source=item.source,
            action=action,
            timestamp=local_now(),
        )
        try:
            return self._cache.append_second_brain_activity(row)
        except Exception:
            # ponytail: activity is a convenience ledger, not source of truth;
            # swallow write failures rather than fail the caller's mutation.
            return None

    def list_activity(self, item_id: str = "") -> list[SecondBrainActivityRow]:
        """Return recent activity, optionally filtered to one item."""
        if self._cache is None:
            return []
        return self._cache.list_second_brain_activity(item_id=item_id)

    def _record_created(self, target: Path) -> None:
        created = self._find_by_path(target)
        if created is not None:
            self.record_activity(created.id, "created")

    # ── internals ─────────────────────────────────────────────────────
    def _items(self) -> list[SecondBrainItem]:
        self._sync_context()
        if self._items_by_id is None:
            self._load_persisted()
            indexed_items, full_text = self._build_index()
            built: dict[str, SecondBrainItem] = {}
            for item in indexed_items:
                flags = self._persisted.get(item.id)
                if flags is not None:
                    item = replace(
                        item,
                        pinned=bool(flags.get("pinned", False)),
                        favorite=bool(flags.get("favorite", False)),
                        tags=self._normalize_tags(flags.get("tags", [])),
                    )
                built[item.id] = item
            self._items_by_id = built
            self._full_text_by_id = full_text
        return list(self._items_by_id.values())

    def _sync_context(self) -> None:
        folder = self._folder()
        root = self._root()
        if not self._context_initialized:
            self._context_initialized = True
            self._folder_snapshot = folder
            self._root_snapshot = root
            return
        folder_changed = folder != self._folder_snapshot
        root_changed = root != self._root_snapshot
        if not folder_changed and not root_changed:
            return
        self._folder_snapshot = folder
        self._root_snapshot = root
        self._invalidate()
        if folder_changed:
            self._persisted = {}
            self._persisted_loaded = False

    def _items_by_id_map(self) -> dict[str, SecondBrainItem]:
        self._items()
        assert self._items_by_id is not None
        return self._items_by_id

    def _invalidate(self) -> None:
        """Drop every derived index cache so the next read rebuilds together."""
        self._items_by_id = None
        self._full_text_by_id = None
        self._warnings = []

    def _build_index(self) -> tuple[list[SecondBrainItem], dict[str, str]]:
        self._warnings = []
        self._personal_root = self._folder_snapshot
        self._project_root = self._root_snapshot
        self._personal_status = self._personal_folder_status(self._personal_root)

        if self._items_provider is not None:
            items = list(self._items_provider())
            return items, {item.id: item.excerpt for item in items}

        items: list[SecondBrainItem] = []
        full_text: dict[str, str] = {}
        if self._personal_status == "ready" and self._personal_root is not None:
            self._scan_personal(self._personal_root, items, full_text)
        self._scan_projects(self._project_root, self._personal_root, items, full_text)
        items.sort(key=lambda item: (item.source, item.tree_path.casefold(), str(item.path).casefold()))
        return items, full_text

    def _personal_folder_status(self, folder: Path | None) -> str:
        if folder is None:
            return "unset"
        if not folder.is_absolute():
            return "invalid"
        try:
            if not folder.exists():
                return "missing"
            if not folder.is_dir():
                return "invalid"
            with os.scandir(folder):
                pass
        except OSError as exc:
            self._warn(folder, exc, "Personal Notes folder is unreadable")
            return "unreadable"
        return "ready"

    def _scan_personal(
        self,
        root: Path,
        items: list[SecondBrainItem],
        full_text: dict[str, str],
    ) -> None:
        def on_error(exc: OSError) -> None:
            self._warn(Path(exc.filename) if exc.filename else root, exc, "Could not scan Personal Notes")

        for current_raw, directory_names, file_names in os.walk(root, topdown=True, onerror=on_error):
            current = Path(current_raw)
            directory_names[:] = sorted(
                name for name in directory_names if not self._excluded_directory(name)
            )
            if current != root:
                relative = current.relative_to(root).as_posix()
                item = self._folder_item(current, relative)
                self._append_index_item(items, full_text, item, "")
            for name in sorted(file_names):
                if self._excluded_file(name):
                    continue
                path = current / name
                relative = path.relative_to(root).as_posix()
                item, content = self._file_item(
                    path,
                    source="personal",
                    relative_path=relative,
                    tree_path=relative,
                    stable_key=f"personal/{relative}",
                )
                self._append_index_item(items, full_text, item, content)

    def _scan_projects(
        self,
        root: Path | None,
        personal_root: Path | None,
        items: list[SecondBrainItem],
        full_text: dict[str, str],
    ) -> None:
        if root is None:
            return
        try:
            if not root.is_dir():
                return
            appcodes = self._discover_appcodes(root)
        except OSError as exc:
            self._warn(root, exc, "Could not discover project appcodes")
            return

        for appcode_path, appcode_name in appcodes:
            if self._excluded_directory(appcode_name):
                continue
            try:
                years = sorted(
                    child.name
                    for child in appcode_path.iterdir()
                    if child.is_dir() and len(child.name) == 4 and child.name.isdigit()
                )
            except OSError as exc:
                self._warn(appcode_path, exc, "Could not scan appcode years")
                continue
            for year in years:
                projects = self._scan_year_projects(appcode_path, appcode_name, year)
                for project in projects:
                    if self._excluded_directory(project.path.name):
                        continue
                    self._scan_project(project, personal_root, items, full_text)

    def _discover_appcodes(self, root: Path) -> list[tuple[Path, str]]:
        """Use canonical discovery, then recover year folders hidden by bad config."""
        try:
            discovered = discover_appcodes(root)
        except (OSError, ValueError, TypeError, AttributeError) as exc:
            self._warn(root, exc, "Canonical appcode discovery was incomplete")
            discovered = []
        by_path = {entry.path.resolve(): (entry.path, entry.name) for entry in discovered}
        for child in sorted(root.iterdir()):
            if not child.is_dir() or self._excluded_directory(child.name):
                continue
            try:
                has_year = any(
                    grandchild.is_dir()
                    and len(grandchild.name) == 4
                    and grandchild.name.isdigit()
                    for grandchild in child.iterdir()
                )
            except OSError as exc:
                self._warn(child, exc, "Could not inspect appcode")
                continue
            resolved = child.resolve()
            if has_year and resolved not in by_path:
                if (child / "appcode.json").exists():
                    self._warnings.append(f"Could not read appcode metadata: {child / 'appcode.json'}")
                by_path[resolved] = (child, child.name)
        return sorted(by_path.values(), key=lambda entry: entry[1].casefold())

    def _scan_year_projects(
        self, appcode_path: Path, appcode_name: str, year: str
    ) -> list[ScannedProject]:
        """Run canonical scan, then recover skipped projects one at a time."""
        warning_start = len(self._metadata_store.warnings)
        try:
            projects = scan_appcode_year(appcode_path, year, self._metadata_store)
        except (OSError, ValueError, TypeError, AttributeError, KeyError) as exc:
            self._warn(appcode_path / year, exc, "Could not complete project year scan")
            projects = []
        self._warnings.extend(self._metadata_store.warnings[warning_start:])

        by_path = {project.path.resolve(): project for project in projects}
        for path, project_type, state in self._project_candidates(appcode_path, year):
            resolved = path.resolve()
            if resolved in by_path:
                continue
            recovered = self._load_project_candidate(
                path,
                appcode_name=appcode_name,
                year=year,
                project_type=project_type,
                state=state,
            )
            by_path[resolved] = recovered
        return sorted(by_path.values(), key=lambda project: str(project.path).casefold())

    def _project_candidates(
        self, appcode_path: Path, year: str
    ) -> list[tuple[Path, ProjectType, ProjectState | None]]:
        year_path = appcode_path / year
        candidates: list[tuple[Path, ProjectType, ProjectState | None]] = []
        seen: set[Path] = set()
        cr_roots = [year_path / "CR"] if (year_path / "CR").is_dir() else []
        cr_roots.append(year_path)
        for cr_root in cr_roots:
            for state in ProjectState:
                state_path = cr_root / state.value
                if not state_path.is_dir():
                    continue
                try:
                    children = sorted(path for path in state_path.iterdir() if path.is_dir())
                except OSError as exc:
                    self._warn(state_path, exc, "Could not inspect project state folder")
                    continue
                for path in children:
                    resolved = path.resolve()
                    if resolved not in seen:
                        seen.add(resolved)
                        candidates.append((path, ProjectType.CR, state))

        non_cr_root = year_path / "Non-CR"
        if non_cr_root.is_dir():
            try:
                non_cr_children = sorted(path for path in non_cr_root.iterdir() if path.is_dir())
            except OSError as exc:
                self._warn(non_cr_root, exc, "Could not inspect Non-CR folder")
                non_cr_children = []
            for path in non_cr_children:
                candidates.append((path, ProjectType.NON_CR, None))
        return candidates

    def _load_project_candidate(
        self,
        path: Path,
        *,
        appcode_name: str,
        year: str,
        project_type: ProjectType,
        state: ProjectState | None,
    ) -> ScannedProject:
        warning_start = len(self._metadata_store.warnings)
        try:
            metadata = self._metadata_store.read(path)
        except (OSError, ValueError, TypeError, AttributeError, KeyError) as exc:
            self._warn(path / "project_data.json", exc, "Could not read project metadata")
            metadata = None
        self._warnings.extend(self._metadata_store.warnings[warning_start:])
        if metadata is None:
            metadata = ProjectMetadata(project_name=path.name)
        metadata.project_type = project_type
        drone_paths: list[Path] = []
        if project_type == ProjectType.CR:
            try:
                drone_paths = discover_drone_paths(path)
            except OSError as exc:
                self._warn(path, exc, "Could not discover Drone folders")
        return ScannedProject(
            path=path,
            year=year,
            appcode=appcode_name,
            project_type=project_type,
            project_state=state,
            metadata=metadata,
            drone_paths=drone_paths,
        )

    def _scan_project(
        self,
        project: ScannedProject,
        personal_root: Path | None,
        items: list[SecondBrainItem],
        full_text: dict[str, str],
    ) -> None:
        project_root = project.path.resolve()
        personal_resolved = personal_root.resolve() if personal_root is not None else None
        if personal_resolved == project_root:
            return

        def on_error(exc: OSError) -> None:
            self._warn(Path(exc.filename) if exc.filename else project.path, exc, "Could not scan project files")

        drone_roots = [(path.resolve(), path.name) for path in project.drone_paths]
        for current_raw, directory_names, file_names in os.walk(project.path, topdown=True, onerror=on_error):
            current = Path(current_raw)
            kept_directories: list[str] = []
            for name in sorted(directory_names):
                if self._excluded_directory(name):
                    continue
                candidate = (current / name).resolve()
                if personal_resolved is not None and (
                    candidate == personal_resolved or candidate.is_relative_to(personal_resolved)
                ):
                    continue
                kept_directories.append(name)
            directory_names[:] = kept_directories

            for name in sorted(file_names):
                if self._excluded_file(name):
                    continue
                path = current / name
                relative = path.relative_to(project.path).as_posix()
                branch = "CR" if project.project_type == ProjectType.CR else "Non-CR"
                prefix_parts = [project.appcode, project.year, branch]
                if project.project_type == ProjectType.CR and project.project_state is not None:
                    prefix_parts.append(project.project_state.value)
                prefix_parts.append(project.path.name)
                tree_path = "/".join([*prefix_parts, relative])
                drone_name = self._drone_name(path, drone_roots)
                stable_key = "/".join(
                    [
                        "project",
                        project.appcode,
                        project.year,
                        project.project_type.value,
                        project.path.name,
                        relative,
                    ]
                )
                item, content = self._file_item(
                    path,
                    source="project",
                    relative_path=relative,
                    tree_path=tree_path,
                    stable_key=stable_key,
                    project=project,
                    drone_name=drone_name,
                )
                self._append_index_item(items, full_text, item, content)

    def _folder_item(self, path: Path, relative: str) -> SecondBrainItem:
        try:
            updated_at = datetime.fromtimestamp(path.stat().st_mtime).astimezone()
        except OSError as exc:
            self._warn(path, exc, "Could not read folder metadata")
            updated_at = None
        return SecondBrainItem(
            id=self._stable_id(f"personal/{relative}"),
            title=path.name,
            path=path,
            item_type="folder",
            updated_at=updated_at,
            source="personal",
            relative_path=relative,
            tree_path=relative,
            parent_path=self._parent_path(relative),
            open_mode="external",
        )

    def _append_index_item(
        self,
        items: list[SecondBrainItem],
        full_text: dict[str, str],
        item: SecondBrainItem,
        content: str,
    ) -> None:
        if item.id in full_text:
            original_id = item.id
            item = replace(item, id=self._stable_id(f"{original_id}/{item.path.as_posix()}"))
            self._warnings.append(
                f"Duplicate Second Brain identity {original_id}; disambiguated: {item.path}"
            )
        items.append(item)
        full_text[item.id] = content

    def _file_item(
        self,
        path: Path,
        *,
        source: str,
        relative_path: str,
        tree_path: str,
        stable_key: str,
        project: ScannedProject | None = None,
        drone_name: str | None = None,
    ) -> tuple[SecondBrainItem, str]:
        suffix = path.suffix.casefold()
        open_mode = self._open_mode(suffix)
        try:
            stat = path.stat()
            updated_at = datetime.fromtimestamp(stat.st_mtime).astimezone()
            size = stat.st_size
        except OSError as exc:
            self._warn(path, exc, "Could not read file metadata")
            updated_at = None
            size = None

        content = ""
        if open_mode in {"markdown", "text"} and size is not None and size <= MAX_SEARCHABLE_BYTES:
            try:
                content = path.read_text(encoding="utf-8", errors="replace")
            except OSError as exc:
                self._warn(path, exc, "Could not read searchable file")

        state = project.project_state.value if project is not None and project.project_state is not None else None
        return (
            SecondBrainItem(
                id=self._stable_id(stable_key),
                title=path.stem,
                path=path,
                item_type="note" if open_mode in {"markdown", "text"} else "file",
                updated_at=updated_at,
                excerpt=content[:200],
                source=source,
                relative_path=relative_path,
                tree_path=tree_path,
                parent_path=self._parent_path(tree_path),
                open_mode=open_mode,
                file_format=suffix.removeprefix("."),
                project_path=project.path if project is not None else None,
                project_state=state,
                appcode=project.appcode if project is not None else None,
                year=project.year if project is not None else None,
                project_name=project.metadata.project_name if project is not None else None,
                drone_name=drone_name,
                locked=state == ProjectState.IMPLEMENTED.value,
            ),
            content,
        )

    @staticmethod
    def _open_mode(suffix: str) -> str:
        if suffix in MARKDOWN_EXTENSIONS:
            return "markdown"
        if suffix in TEXT_EXTENSIONS:
            return "text"
        if suffix == ".docx":
            return "docx"
        if suffix in IMAGE_EXTENSIONS:
            return "image"
        return "external"

    @staticmethod
    def _stable_id(key: str) -> str:
        return hashlib.sha1(key.encode("utf-8")).hexdigest()[:16]

    @staticmethod
    def _parent_path(tree_path: str) -> str | None:
        parent = PurePosixPath(tree_path).parent.as_posix()
        return None if parent == "." else parent

    @staticmethod
    def _excluded_directory(name: str) -> bool:
        return name.startswith(".") or name.casefold() in INTERNAL_DIRECTORY_NAMES

    @staticmethod
    def _excluded_file(name: str) -> bool:
        return name.startswith(".") or name.casefold() in INTERNAL_FILE_NAMES

    @staticmethod
    def _drone_name(path: Path, drone_roots: list[tuple[Path, str]]) -> str | None:
        resolved = path.resolve()
        for drone_root, name in drone_roots:
            if resolved.is_relative_to(drone_root):
                return name
        return None

    def _root(self) -> Path | None:
        if self._root_provider is None:
            return None
        return self._root_provider()

    def _warn(self, path: Path, exc: BaseException, prefix: str) -> None:
        self._warnings.append(f"{prefix}: {path} ({exc})")

    def _match_reason(self, item: SecondBrainItem, query: str) -> str | None:
        if query in item.title.casefold():
            return "title"
        path_fields = " ".join(
            (item.path.name, str(item.path), item.relative_path, item.tree_path)
        ).casefold()
        if query in path_fields:
            return "path"
        if query in (self._full_text_by_id or {}).get(item.id, "").casefold():
            return "content"
        if any(query in tag.casefold() for tag in item.tags):
            return "tag"
        context = " ".join(
            value
            for value in (
                item.appcode,
                item.year,
                item.project_name,
                item.drone_name,
                item.project_state,
            )
            if value
        ).casefold()
        return "context" if query in context else None

    @staticmethod
    def _matches_source(item: SecondBrainItem, source_filter: str) -> bool:
        source = source_filter.strip().casefold()
        return source in {"", "all"} or item.source.casefold() == source

    @staticmethod
    def _matches_type(item: SecondBrainItem, type_filter: str) -> bool:
        requested = type_filter.strip().casefold().removeprefix(".")
        if requested in {"", "all"}:
            return True
        return requested in {
            item.item_type.casefold(),
            item.open_mode.casefold(),
            item.file_format.casefold(),
        }

    @staticmethod
    def _matches_date(item: SecondBrainItem, date_filter: str) -> bool:
        requested = date_filter.strip().casefold()
        if requested in {"", "all"}:
            return True
        if item.updated_at is None:
            return False
        if requested == "today":
            target = datetime.now().astimezone().date()
        else:
            try:
                target = date.fromisoformat(requested)
            except ValueError as exc:
                raise ValueError("Second Brain date filter must be YYYY-MM-DD, today, or empty") from exc
        updated = item.updated_at
        updated_date = updated.astimezone().date() if updated.tzinfo is not None else updated.date()
        return updated_date == target

    def _sort_items(self, items: list[SecondBrainItem], sort: str) -> list[SecondBrainItem]:
        requested = sort.strip().casefold() or "newest"
        if requested == "newest":
            return sorted(
                items,
                key=lambda item: (
                    self._timestamp(item) is None,
                    -(self._timestamp(item) or 0.0),
                    item.title.casefold(),
                    str(item.path).casefold(),
                ),
            )
        if requested == "oldest":
            return sorted(
                items,
                key=lambda item: (
                    self._timestamp(item) is None,
                    self._timestamp(item) or 0.0,
                    item.title.casefold(),
                    str(item.path).casefold(),
                ),
            )
        if requested == "az":
            return sorted(items, key=lambda item: (item.title.casefold(), str(item.path).casefold()))
        if requested == "type":
            return sorted(
                items,
                key=lambda item: (
                    (item.file_format or item.item_type).casefold(),
                    item.title.casefold(),
                    str(item.path).casefold(),
                ),
            )
        raise ValueError(f"Unsupported Second Brain sort: {sort}")

    @staticmethod
    def _timestamp(item: SecondBrainItem) -> float | None:
        updated = item.updated_at
        if updated is None:
            return None
        if updated.tzinfo is None:
            updated = updated.replace(tzinfo=timezone.utc)
        return updated.timestamp()

    def _wiki_targets(self, item: SecondBrainItem) -> set[str]:
        content = (self._full_text_by_id or {}).get(item.id, "")
        return {
            target.strip().replace("\\", "/").casefold()
            for target in WIKI_LINK_PATTERN.findall(content)
            if target.strip()
        }

    @staticmethod
    def _wiki_matches(targets: set[str], candidate: SecondBrainItem) -> bool:
        if not targets:
            return False
        names = {
            candidate.title.casefold(),
            candidate.path.name.casefold(),
            candidate.relative_path.replace("\\", "/").casefold(),
            candidate.tree_path.replace("\\", "/").casefold(),
        }
        return bool(targets.intersection(names))

    @staticmethod
    def _normalize_tags(raw_tags: object) -> tuple[str, ...]:
        if not isinstance(raw_tags, list | tuple):
            return ()
        normalized: list[str] = []
        seen: set[str] = set()
        for raw in raw_tags:
            if not isinstance(raw, str):
                continue
            tag = unicodedata.normalize("NFC", raw.strip())
            key = tag.casefold()
            if tag and key not in seen:
                seen.add(key)
                normalized.append(tag)
        return tuple(normalized)

    def _toggle_flag(self, item_id: str, flag: str) -> SecondBrainItem:
        items = self._items_by_id_map()
        item = items.get(item_id)
        if item is None:
            raise KeyError(f"Second Brain item not found: {item_id}")

        new_value = not getattr(item, flag)
        prior_persisted = {key: dict(value) for key, value in self._persisted.items()}
        entry = {"pinned": item.pinned, "favorite": item.favorite, "tags": list(item.tags)}
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

    def _find_by_path(self, filepath: Path) -> SecondBrainItem | None:
        """Locate a currently indexed item by filesystem path (resolve-based)."""
        resolved = Path(filepath).resolve()
        for candidate in self._items_by_id_map().values():
            if candidate.path.resolve() == resolved:
                return candidate
        return None

    @staticmethod
    def _sibling_relative(old_relative: str, new_name: str) -> str:
        parent = PurePosixPath(old_relative).parent
        return new_name if str(parent) == "." else (parent / new_name).as_posix()

    def _remap_persisted(self, remap: dict[str, str]) -> None:
        """Move persisted flags from old ids to new ids (rename support).

        Called only after the physical rename already succeeded, so a sidecar
        write failure here must not be raised back to the caller (that would
        misreport the whole rename as failed). The remap is kept in-memory
        regardless — this process keeps serving the correct flags under the
        new id — and the disk write is best-effort: a failure is logged and
        the next successful persist writes the remap through.
        """
        moves = {old: new for old, new in remap.items() if old in self._persisted}
        if not moves:
            return
        updated = dict(self._persisted)
        for old_id, new_id in moves.items():
            updated[new_id] = updated.pop(old_id)
        self._persisted = updated
        try:
            self._persist()
        except Exception as exc:
            logger.warning("Second Brain sidecar persist failed after rename: %s", exc)

    def _drop_persisted(self, item_ids: set[str]) -> None:
        """Remove persisted flags for ids that no longer resolve (recycle support).

        Called only after the physical recycle already succeeded, so a
        sidecar write failure here must not be raised back to the caller
        (the item is already gone from disk regardless). The drop is kept
        in-memory and the disk write is best-effort: a failure is logged and
        the next successful persist writes the drop through.
        """
        if not any(item_id in self._persisted for item_id in item_ids):
            return
        self._persisted = {
            key: value for key, value in self._persisted.items() if key not in item_ids
        }
        try:
            self._persist()
        except Exception as exc:
            logger.warning("Second Brain sidecar persist failed after recycle: %s", exc)

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
        restored: dict[str, dict[str, object]] = {}
        for item_id, flags in items.items():
            if isinstance(flags, dict):
                restored[str(item_id)] = {
                    "pinned": bool(flags.get("pinned", False)),
                    "favorite": bool(flags.get("favorite", False)),
                    "tags": list(self._normalize_tags(flags.get("tags", []))),
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
