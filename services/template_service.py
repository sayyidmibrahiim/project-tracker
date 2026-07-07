"""Template service — per-CR/per-project template storage, merge, list, reset.

Automation epic Slice 2. Built on top of the existing flat-template storage
(``ProjectMetadata.approval_templates`` / ``AppSettings.default_approval_templates``)
keyed by ``template_key`` (e.g. ``uat_approval``). One project == one CR in this
repo, so per-project ≈ per-CR; no separate CR dimension is introduced (YAGNI).

Public functions are pure helpers (no I/O): they read/write the metadata /
settings objects handed to them; persistence is the caller's job.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from core.models import AppSettings, ProjectMetadata

# Known approval-template kinds and their storage keys.
TEMPLATE_KINDS: dict[str, str] = {
    "uat": "uat_approval",
    "lv": "lv_approval",
}
TEMPLATE_FIELDS: tuple[str, ...] = ("to", "cc", "subject", "body", "mode", "attachments")
EMPTY_TEMPLATE: dict[str, Any] = {
    "to": "",
    "cc": "",
    "subject": "",
    "body": "",
    "mode": "draft",
    "attachments": "",
}


def template_key(kind: str) -> str | None:
    """Return the storage key for a kind, or None if unknown."""
    return TEMPLATE_KINDS.get(kind)


def normalize_template(raw: dict[str, Any] | None) -> dict[str, Any]:
    """Coerce a raw template dict to the canonical field set + mode validation."""
    clean = dict(EMPTY_TEMPLATE)
    if not isinstance(raw, dict):
        return clean
    for field in TEMPLATE_FIELDS:
        if field in raw:
            value = raw[field]
            clean[field] = "" if value is None else str(value)
    if clean["mode"] not in ("draft", "send"):
        clean["mode"] = "draft"
    return clean


def get_effective_template(
    metadata: ProjectMetadata,
    settings: AppSettings,
    kind: str,
) -> tuple[dict[str, Any], str]:
    """Return ``(effective_template, source)`` for a kind.

    source ∈ {"project", "default", "none"} — project overrides default.
    """
    key = template_key(kind)
    if key is None:
        return dict(EMPTY_TEMPLATE), "none"
    project_template = metadata.approval_templates.get(key)
    if isinstance(project_template, dict) and project_template:
        return normalize_template(project_template), "project"
    default = settings.default_approval_templates.get(key)
    if isinstance(default, dict) and default:
        return normalize_template(default), "default"
    return dict(EMPTY_TEMPLATE), "none"


def save_project_template(
    metadata: ProjectMetadata,
    kind: str,
    template: dict[str, Any],
) -> dict[str, Any]:
    """Write a per-project template; returns the normalized stored dict."""
    key = template_key(kind)
    if key is None:
        raise ValueError(f"Unknown template kind: {kind}")
    clean = normalize_template(template)
    metadata.approval_templates[key] = clean
    metadata.updated_at = datetime.now().astimezone()
    return clean


def save_default_template(
    settings: AppSettings,
    kind: str,
    template: dict[str, Any],
) -> dict[str, Any]:
    """Write a global default template; returns the normalized stored dict."""
    key = template_key(kind)
    if key is None:
        raise ValueError(f"Unknown template kind: {kind}")
    clean = normalize_template(template)
    settings.default_approval_templates[key] = clean
    return clean


def reset_project_template(
    metadata: ProjectMetadata,
    kind: str,
) -> bool:
    """Remove a per-project override so the default takes effect. Returns True if removed."""
    key = template_key(kind)
    if key is None or key not in metadata.approval_templates:
        return False
    del metadata.approval_templates[key]
    metadata.updated_at = datetime.now().astimezone()
    return True


def list_templates(settings: AppSettings) -> list[dict[str, Any]]:
    """Return template summary rows for the Automations template list."""
    rows: list[dict[str, Any]] = []
    for kind, key in TEMPLATE_KINDS.items():
        default = settings.default_approval_templates.get(key)
        rows.append(
            {
                "kind": kind,
                "key": key,
                "name": "UAT Approval" if kind == "uat" else "LV Approval",
                "type": "email",
                "has_default": isinstance(default, dict) and bool(default),
                "last_modified": "",
            }
        )
    return rows
