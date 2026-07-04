"""RTE document pipeline service (D-0012, _docs/flow-tiptap.md).

For formats Tiptap cannot save natively (.docx), the source of truth is a
Tiptap-JSON sidecar (`<dir>/.rte/<stem>.source.json`); the real .docx is a
derived export produced in the background by infrastructure/docx_writer.

Layout per document:
    <dir>/.rte/<stem>.source.json     source of truth (revision, hash, content)
    <dir>/.rte/assets/<id>.<ext>      pasted/inserted image assets (shared per dir)

Rules implemented here (flow-tiptap §8-11, 17-18, 21):
- autosave saves JSON only; exports run through a single-worker coordinator
  with latest-revision-wins; identical content hashes are skipped
- stale base_revision is rejected (RTE_REVISION_STALE at the bridge)
- image bytes are validated by magic number, capped, content-addressed
- asset reads are locked to the assets dir (no path traversal)
- a locked .docx (open in Word) marks export_pending and never destroys
  the previous file; export retries on next open/save
"""

from __future__ import annotations

import base64
import copy
import hashlib
import json
import re
import threading
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from io import BytesIO
from pathlib import Path
from typing import Any, Callable

from core.enums import ProjectState
from infrastructure.docx_writer import (
    DEFAULT_DOCUMENT_SETTINGS,
    DocxTargetLockedError,
    export_source_to_docx,
)

SCHEMA_VERSION = 1
MAX_ASSET_BYTES = 15 * 1024 * 1024
ASSET_NAME_RE = re.compile(r"^[0-9a-f]{16}\.(png|jpe?g|gif|webp)$")

_MAGIC: list[tuple[bytes, str, str]] = [
    (b"\x89PNG\r\n\x1a\n", "png", "image/png"),
    (b"\xff\xd8\xff", "jpg", "image/jpeg"),
    (b"GIF87a", "gif", "image/gif"),
    (b"GIF89a", "gif", "image/gif"),
]

_DOCX_EDITOR_FEATURES = [
    "bold", "italic", "strike", "heading", "list", "task_list",
    "link", "code", "image", "table",
]


class StaleRevisionError(ValueError):
    """base_revision does not match the stored revision."""


class SchemaUnsupportedError(ValueError):
    """source.json was written by a newer app version."""


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _canonical_hash(content: dict) -> str:
    return hashlib.sha256(
        json.dumps(content, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()


def _sniff_image(data: bytes) -> tuple[str, str] | None:
    for magic, ext, mime in _MAGIC:
        if data.startswith(magic):
            return ext, mime
    # WEBP: RIFF....WEBP
    if data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return "webp", "image/webp"
    return None


def _project_state_for(path: Path) -> ProjectState | None:
    """Mirror of app_web._folder_state_for_path (service layer cannot import app_web)."""
    state_values = {state.value for state in ProjectState}
    for part in Path(path).parts:
        if part in state_values:
            return ProjectState(part)
    return None


def _atomic_write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f".{path.name}.tmp")
    try:
        tmp.write_text(text, encoding="utf-8")
        tmp.replace(path)
    except Exception:
        tmp.unlink(missing_ok=True)
        raise


def _atomic_write_bytes(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f".{path.name}.tmp")
    try:
        tmp.write_bytes(data)
        tmp.replace(path)
    except Exception:
        tmp.unlink(missing_ok=True)
        raise


def _docx_to_html(path: Path) -> str:
    import mammoth

    with BytesIO(path.read_bytes()) as source:
        result = mammoth.convert_to_html(source)
    return str(result.value or "")


def _push_event(event_type: str, payload: dict[str, object]) -> None:
    try:
        from web.event_queue import push_event

        push_event(event_type, payload)
    except Exception:
        pass  # events are best-effort; export state also lives in source.json


class ExportCoordinator:
    """Single-worker, latest-revision-wins export queue (flow-tiptap §10-11)."""

    def __init__(self, run_export: Callable[[Path], None]) -> None:
        self._run_export = run_export
        self._executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="docx-export")
        self._lock = threading.Lock()
        self._active: dict[str, int] = {}
        self._pending: dict[str, int] = {}
        self._idle = threading.Event()
        self._idle.set()
        self._shutdown = False

    def request(self, docx_path: Path, revision: int) -> str:
        key = str(docx_path)
        with self._lock:
            if self._shutdown:
                return "skipped"
            if key in self._active:
                # A job is running: remember only the newest revision.
                if revision > self._pending.get(key, -1):
                    self._pending[key] = revision
                return "queued"
            self._active[key] = revision
            self._idle.clear()
        self._executor.submit(self._job, docx_path)
        return "running"

    def is_running(self, docx_path: Path) -> bool:
        with self._lock:
            return str(docx_path) in self._active

    def _job(self, docx_path: Path) -> None:
        key = str(docx_path)
        try:
            self._run_export(docx_path)
        finally:
            resubmit: int | None = None
            with self._lock:
                self._active.pop(key, None)
                if not self._shutdown and key in self._pending:
                    resubmit = self._pending.pop(key)
                if not self._active:
                    self._idle.set()
            if resubmit is not None:
                self.request(docx_path, resubmit)

    def wait_idle(self, timeout_s: float) -> bool:
        return self._idle.wait(timeout=timeout_s)

    def shutdown(self, timeout_s: float) -> None:
        self.wait_idle(timeout_s)
        with self._lock:
            self._shutdown = True
            self._pending.clear()
        self._executor.shutdown(wait=False, cancel_futures=True)


class RteDocumentService:
    def __init__(self, exporter: Callable[[dict, Path, Path], None] = export_source_to_docx) -> None:
        self._exporter = exporter
        self._locks: dict[str, threading.Lock] = {}
        self._locks_guard = threading.Lock()
        self._known_docs: set[str] = set()
        self.coordinator = ExportCoordinator(self._run_export)

    # ── Layout ──

    def sidecar_dir(self, document_path: Path) -> Path:
        return Path(document_path).parent / ".rte"

    def source_path(self, docx_path: Path) -> Path:
        docx_path = Path(docx_path)
        return self.sidecar_dir(docx_path) / f"{docx_path.stem}.source.json"

    def assets_dir(self, document_path: Path) -> Path:
        return self.sidecar_dir(document_path) / "assets"

    def _doc_lock(self, docx_path: Path) -> threading.Lock:
        key = str(docx_path)
        with self._locks_guard:
            return self._locks.setdefault(key, threading.Lock())

    # ── Source store ──

    def _load_source(self, docx_path: Path) -> dict | None:
        path = self.source_path(docx_path)
        if not path.is_file():
            return None
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return None
        if not isinstance(data, dict):
            return None
        version = data.get("schema_version", 1)
        if isinstance(version, int) and version > SCHEMA_VERSION:
            raise SchemaUnsupportedError(
                f"source.json schema {version} is newer than supported {SCHEMA_VERSION}"
            )
        return data

    def _store_source(self, docx_path: Path, source: dict) -> None:
        _atomic_write_text(
            self.source_path(docx_path),
            json.dumps(source, ensure_ascii=False, indent=1),
        )

    def _new_source(self, docx_path: Path) -> dict:
        return {
            "schema_version": SCHEMA_VERSION,
            "document_id": Path(docx_path).stem,
            "revision": 0,
            "content_hash": "",
            "saved_at": _utc_now_iso(),
            "document_settings": dict(DEFAULT_DOCUMENT_SETTINGS),
            "export": {
                "last_exported_revision": 0,
                "last_exported_hash": "",
                "export_pending": False,
                "docx_mtime_ns": 0,
                "docx_size": 0,
                "last_error": None,
            },
            "content": {"type": "doc", "content": []},
        }

    # ── Hydration (asset:// <-> data URI) ──

    def _walk_images(self, node: Any, fn: Callable[[dict], None]) -> None:
        if isinstance(node, dict):
            if node.get("type") == "image":
                fn(node)
            for child in node.get("content") or []:
                self._walk_images(child, fn)
        elif isinstance(node, list):
            for child in node:
                self._walk_images(child, fn)

    def _hydrate(self, docx_path: Path, content: dict) -> dict:
        content = copy.deepcopy(content)
        assets = self.assets_dir(docx_path)

        def fill(node: dict) -> None:
            attrs = node.setdefault("attrs", {})
            src = attrs.get("src") or ""
            if isinstance(src, str) and src.startswith("asset://"):
                name = src.removeprefix("asset://")
                if ASSET_NAME_RE.match(name) and (assets / name).is_file():
                    data = (assets / name).read_bytes()
                    sniff = _sniff_image(data)
                    mime = sniff[1] if sniff else "image/png"
                    attrs["src"] = f"data:{mime};base64,{base64.b64encode(data).decode('ascii')}"
                else:
                    attrs["src"] = ""
                    attrs["alt"] = attrs.get("alt") or "missing image"

        self._walk_images(content, fill)
        return content

    def _dehydrate(self, docx_path: Path, content: dict) -> dict:
        """Normalize image nodes to asset:// refs; sweep loose base64 into assets."""
        content = copy.deepcopy(content)
        assets = self.assets_dir(docx_path)

        def strip(node: dict) -> None:
            attrs = node.setdefault("attrs", {})
            asset_id = attrs.get("assetId")
            src = attrs.get("src") or ""
            if asset_id and isinstance(asset_id, str):
                existing = sorted(assets.glob(f"{asset_id}.*")) if assets.is_dir() else []
                ext = existing[0].suffix.lstrip(".") if existing else "png"
                attrs["src"] = f"asset://{asset_id}.{ext}"
                return
            if isinstance(src, str) and src.startswith("data:image/"):
                try:
                    b64 = src.split(",", 1)[1]
                    saved = self.save_image(docx_path, b64)
                    attrs["assetId"] = saved["asset_id"]
                    attrs["src"] = saved["src"]
                except (ValueError, IndexError):
                    pass  # unparseable data URI stays inline (bounded by editor)

        self._walk_images(content, strip)
        return content

    # ── Bridge surface ──

    def open_document(self, docx_path: Path) -> dict:
        docx_path = Path(docx_path)
        self._known_docs.add(str(docx_path))
        state = _project_state_for(docx_path)
        read_only = state == ProjectState.IMPLEMENTED
        capability = {
            "format": "docx",
            "editable": not read_only,
            "capability": "read_only" if read_only else "editable",
            "saveStrategy": "none" if read_only else "docx_pipeline",
            "supportedEditorFeatures": [] if read_only else list(_DOCX_EDITOR_FEATURES),
            "message": (
                "Proyek IMPLEMENTED terkunci — dokumen hanya-baca." if read_only else ""
            ),
        }

        with self._doc_lock(docx_path):
            source = self._load_source(docx_path)

            if source is not None and self._docx_is_stale(docx_path, source):
                # User edited the .docx directly in Word: re-import it.
                source_path = self.source_path(docx_path)
                backup = source_path.with_suffix(".json.bak")
                try:
                    backup.write_text(
                        json.dumps(source, ensure_ascii=False), encoding="utf-8"
                    )
                    source_path.unlink(missing_ok=True)
                except OSError:
                    pass
                source = None

            if source is not None:
                if not read_only and source["export"].get("export_pending"):
                    self.coordinator.request(docx_path, int(source.get("revision", 0)))
                return {
                    **capability,
                    "content": self._hydrate(docx_path, source.get("content") or {}),
                    "content_html": None,
                    "needs_migration": False,
                    "revision": int(source.get("revision", 0)),
                    "content_hash": source.get("content_hash", ""),
                    "export": self._export_state(docx_path, source),
                }

            # No usable source.json yet.
            if docx_path.is_file() and docx_path.stat().st_size > 0:
                try:
                    html = _docx_to_html(docx_path)
                except Exception:
                    html = ""
                if html.strip():
                    return {
                        **capability,
                        "content": None,
                        "content_html": html,
                        "needs_migration": True,
                        "revision": 0,
                        "content_hash": "",
                        "export": self._export_state(docx_path, None),
                    }

            fresh = self._new_source(docx_path)
            return {
                **capability,
                "content": fresh["content"],
                "content_html": None,
                "needs_migration": False,
                "revision": 0,
                "content_hash": "",
                "export": self._export_state(docx_path, None),
            }

    def save_document(self, docx_path: Path, payload: dict) -> dict:
        docx_path = Path(docx_path)
        self._known_docs.add(str(docx_path))
        if _project_state_for(docx_path) == ProjectState.IMPLEMENTED:
            raise ValueError("Proyek IMPLEMENTED terkunci — dokumen tidak dapat disimpan.")
        content = payload.get("content")
        if not isinstance(content, dict) or content.get("type") != "doc":
            raise ValueError("Invalid document content")
        base_revision = int(payload.get("base_revision", 0))
        reason = str(payload.get("reason") or "autosave")

        with self._doc_lock(docx_path):
            source = self._load_source(docx_path) or self._new_source(docx_path)
            stored_revision = int(source.get("revision", 0))
            if base_revision != stored_revision:
                raise StaleRevisionError(
                    f"Revision {base_revision} is stale (stored {stored_revision})"
                )

            dehydrated = self._dehydrate(docx_path, content)
            new_hash = _canonical_hash(dehydrated)
            if new_hash == source.get("content_hash") and reason == "autosave":
                return {
                    "revision": stored_revision,
                    "content_hash": new_hash,
                    "skipped": True,
                    "export_scheduled": False,
                }

            if new_hash != source.get("content_hash"):
                source["revision"] = stored_revision + 1
                source["content"] = dehydrated
                source["content_hash"] = new_hash
                source["saved_at"] = _utc_now_iso()
                self._store_source(docx_path, source)

            export_scheduled = False
            if reason in ("manual", "switch", "migration"):
                needs_export = source["export"].get("last_exported_hash") != new_hash
                if needs_export:
                    self.coordinator.request(docx_path, int(source["revision"]))
                    export_scheduled = True
            return {
                "revision": int(source["revision"]),
                "content_hash": new_hash,
                "skipped": False,
                "export_scheduled": export_scheduled,
            }

    def save_image(self, document_path: Path, data_b64: str) -> dict:
        document_path = Path(document_path)
        if not data_b64 or not isinstance(data_b64, str):
            raise ValueError("Empty image payload")
        try:
            data = base64.b64decode(data_b64, validate=True)
        except Exception as exc:
            raise ValueError("Invalid base64 image payload") from exc
        if len(data) > MAX_ASSET_BYTES:
            raise ValueError("Image exceeds the 15 MB limit")
        sniff = _sniff_image(data)
        if sniff is None:
            raise ValueError("Unsupported image format (png/jpeg/gif/webp only)")
        ext, mime = sniff
        asset_id = hashlib.sha256(data).hexdigest()[:16]
        file_name = f"{asset_id}.{ext}"
        target = self.assets_dir(document_path) / file_name
        if not target.is_file():
            _atomic_write_bytes(target, data)
        return {
            "asset_id": asset_id,
            "file_name": file_name,
            "src": f"asset://{file_name}",
            "rel_src": f".rte/assets/{file_name}",
            "data_uri": f"data:{mime};base64,{base64.b64encode(data).decode('ascii')}",
        }

    def read_asset(self, document_path: Path, src: str) -> dict:
        if not isinstance(src, str) or not src:
            raise ValueError("Empty asset reference")
        name = src.removeprefix("asset://").removeprefix(".rte/assets/")
        name = name.replace("\\", "/").rsplit("/", 1)[-1]
        if not ASSET_NAME_RE.match(name):
            raise ValueError("Invalid asset name")
        path = self.assets_dir(Path(document_path)) / name
        if not path.is_file():
            raise ValueError("Asset not found")
        data = path.read_bytes()
        sniff = _sniff_image(data)
        mime = sniff[1] if sniff else "application/octet-stream"
        return {"data_uri": f"data:{mime};base64,{base64.b64encode(data).decode('ascii')}"}

    def request_export(self, docx_path: Path) -> dict:
        docx_path = Path(docx_path)
        source = self._load_source(docx_path)
        if source is None:
            raise ValueError("No document source to export")
        if source["export"].get("last_exported_hash") == source.get("content_hash"):
            return self.export_status(docx_path)
        self.coordinator.request(docx_path, int(source.get("revision", 0)))
        return self.export_status(docx_path)

    def export_status(self, docx_path: Path) -> dict:
        docx_path = Path(docx_path)
        source = self._load_source(docx_path)
        return self._export_state(docx_path, source)

    def _export_state(self, docx_path: Path, source: dict | None) -> dict:
        export = (source or {}).get("export") or {}
        if self.coordinator.is_running(docx_path):
            state = "running"
        elif export.get("last_error") == "locked":
            state = "pending_retry"
        elif export.get("last_error"):
            state = "error"
        else:
            state = "idle"
        return {
            "state": state,
            "revision": int((source or {}).get("revision", 0)),
            "last_exported_revision": int(export.get("last_exported_revision", 0)),
            "export_pending": bool(export.get("export_pending", False)),
            "last_error": export.get("last_error"),
        }

    def flush_all(self, timeout_s: float = 10.0) -> None:
        for key in list(self._known_docs):
            docx_path = Path(key)
            try:
                source = self._load_source(docx_path)
            except SchemaUnsupportedError:
                continue
            if source is None:
                continue
            if source["export"].get("last_exported_hash") != source.get("content_hash"):
                self.coordinator.request(docx_path, int(source.get("revision", 0)))
        self.coordinator.shutdown(timeout_s)

    # ── Export worker ──

    def _docx_is_stale(self, docx_path: Path, source: dict) -> bool:
        """True when the .docx was modified outside the app after our last export."""
        if not docx_path.is_file():
            return False
        export = source.get("export") or {}
        recorded_mtime = int(export.get("docx_mtime_ns") or 0)
        if recorded_mtime == 0:
            # Never exported by us. Only treat as external content when the
            # file is non-empty AND we have no content of our own yet.
            return docx_path.stat().st_size > 0 and not (source.get("content") or {}).get("content")
        stat = docx_path.stat()
        drift_ns = abs(stat.st_mtime_ns - recorded_mtime)
        return drift_ns > 2_000_000_000 and stat.st_mtime_ns > recorded_mtime

    def _run_export(self, docx_path: Path) -> None:
        with self._doc_lock(docx_path):
            source = self._load_source(docx_path)
            if source is None:
                return
        payload = {"path": str(docx_path), "revision": int(source.get("revision", 0))}
        try:
            self._exporter(source, self.assets_dir(docx_path), docx_path)
        except DocxTargetLockedError:
            with self._doc_lock(docx_path):
                source = self._load_source(docx_path)
                if source is not None:
                    source["export"]["export_pending"] = True
                    source["export"]["last_error"] = "locked"
                    self._store_source(docx_path, source)
            _push_event("RTE_EXPORT_LOCKED", payload)
        except Exception as exc:  # export failure must never lose source content
            with self._doc_lock(docx_path):
                source = self._load_source(docx_path)
                if source is not None:
                    source["export"]["export_pending"] = True
                    source["export"]["last_error"] = str(exc)[:300]
                    self._store_source(docx_path, source)
            _push_event("RTE_EXPORT_FAILED", {**payload, "error": str(exc)[:300]})
        else:
            with self._doc_lock(docx_path):
                source = self._load_source(docx_path)
                if source is not None:
                    stat = docx_path.stat()
                    source["export"].update(
                        {
                            "last_exported_revision": int(source.get("revision", 0)),
                            "last_exported_hash": source.get("content_hash", ""),
                            "export_pending": False,
                            "docx_mtime_ns": stat.st_mtime_ns,
                            "docx_size": stat.st_size,
                            "last_error": None,
                        }
                    )
                    self._store_source(docx_path, source)
            _push_event("RTE_EXPORT_DONE", payload)


_service: RteDocumentService | None = None
_service_guard = threading.Lock()


def get_rte_document_service() -> RteDocumentService:
    global _service
    with _service_guard:
        if _service is None:
            _service = RteDocumentService()
        return _service


def shutdown_rte_document_service(timeout_s: float = 10.0) -> None:
    global _service
    with _service_guard:
        service = _service
        _service = None
    if service is not None:
        service.flush_all(timeout_s)
