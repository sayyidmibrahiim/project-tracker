"""Task 15.5 — Unit tests for the Outlook draft/send/contacts/download adapter.

Named ``test_project_*`` so it sorts after the ``test_phase_c_*`` import-isolation
tests: importing ``app_web`` (which imports ``webview``) must not pollute
``sys.modules`` before those tests assert ``webview`` is absent.

These tests exercise the wired ``JsApi`` (via ``create_js_api``) and its
``_OutlookServiceAdapter`` route through ``EmailService.render_email_template``
and the guarded ``outlook_client``, entirely against ``tmp_path`` and entirely
off-Windows (no COM, no worker, no native automation).

Covered behaviour (Req 8.5, 8.6, 8.7, 8.8):
- unresolved required placeholder aborts draft/send with ``ok=false``,
  ``OUTLOOK_DRAFT_FAILED`` / ``OUTLOOK_SEND_FAILED`` naming the placeholder in
  ``error.details.placeholder`` (Req 8.5)
- unmet Template_Category condition skips composition with a skipped
  Bridge_Response (``ok=true``, ``data.status == "skipped"`` + reason) (Req 8.6)
- ``outlook_get_contacts`` off-Windows returns the dev fallback contact and never
  executes COM, regardless of query (Req 8.7)
- ``outlook_download_emails`` off-Windows returns a dev-skipped Bridge_Response
  with no COM and no background worker started (Req 8.8)
"""

from __future__ import annotations

import sys
from dataclasses import replace
from pathlib import Path

import pytest

from project_tracker.core.enums import CRState
from project_tracker.core.models import (
    AppSettings,
    EmailCategorySettings,
    EmailSettings,
    ProjectMetadata,
)
from project_tracker.infrastructure import outlook_client
from project_tracker.infrastructure.metadata_store import MetadataStore
from project_tracker.infrastructure.settings_store import SettingsStore

# The download / contacts dev-skip and dev-fallback behaviour is the off-Windows
# guard; on Windows these would execute COM and are covered by the manual gate.
not_windows = pytest.mark.skipif(
    sys.platform == "win32",
    reason="off-Windows guard behaviour (dev fallback / dev_skipped) only",
)


# ── helpers / fixtures ────────────────────────────────────────────────────


def _email_settings(category_code: str, category: EmailCategorySettings) -> EmailSettings:
    """Build EmailSettings with ``category_code`` configured (others default)."""
    categories = EmailSettings.default().categories
    categories[category_code] = category
    return EmailSettings(categories=categories)


def _full_metadata(name: str = "CR-2026-001") -> ProjectMetadata:
    """Metadata that resolves the canonical required placeholders used here."""
    return ProjectMetadata(
        project_name=name,
        cr_link="https://crportal/CR-2026-001",
        cr_state=CRState.APPROVED,
    )


@pytest.fixture
def env(tmp_path):
    """Configured root + settings store + wired JsApi, all under tmp_path."""
    from project_tracker import app_web

    root = tmp_path / "root"
    root.mkdir()

    settings = SettingsStore(config_dir=tmp_path / "config")
    settings.write(replace(settings.read(), root_folder=root, display_name="Jane Doe"))

    js_api = app_web.create_js_api(db_path=tmp_path / "cache.db", settings_store=settings)

    return {"root": root, "settings": settings, "js_api": js_api}


def _make_project(
    env,
    *,
    metadata: ProjectMetadata,
    state: str = "UAT_PREPARE",
    name: str = "proj",
    year: str = "2026",
) -> Path:
    """Create a project folder under ``root/year/state/name`` and write metadata."""
    folder = env["root"] / year / state / name
    folder.mkdir(parents=True)
    MetadataStore().write(folder, metadata)
    return folder


def _configure_category(env, category_code: str, category: EmailCategorySettings) -> None:
    """Persist a configured Template_Category into the live settings store."""
    store: SettingsStore = env["settings"]
    store.write(replace(store.read(), email=_email_settings(category_code, category)))


# ── unresolved required placeholder abort (Req 8.5) ───────────────────────


def test_draft_unresolved_placeholder_aborts_naming_it(env):
    metadata = _full_metadata()
    metadata.cr_link = ""  # makes {CR_LINK} unresolvable
    folder = _make_project(env, metadata=metadata)
    _configure_category(
        env,
        "ACK_UAT",
        EmailCategorySettings(
            to="ops@example.com",
            subject_template="{PROJECT_NAME}",
            body_template="CR link: {CR_LINK}",
        ),
    )

    result = env["js_api"].outlook_draft_email("ACK_UAT", str(folder))

    assert result["ok"] is False
    assert result["error"]["code"] == "OUTLOOK_DRAFT_FAILED"
    assert result["error"]["details"]["placeholder"] == "{CR_LINK}"
    assert "{CR_LINK}" in result["error"]["message"]


def test_send_unresolved_placeholder_aborts_naming_it(env):
    metadata = _full_metadata()
    metadata.cr_link = ""
    folder = _make_project(env, metadata=metadata)
    _configure_category(
        env,
        "APRVL_CR",
        EmailCategorySettings(
            to="ops@example.com",
            subject_template="{PROJECT_NAME}",
            body_template="CR link: {CR_LINK}",
        ),
    )

    result = env["js_api"].outlook_send_email("APRVL_CR", str(folder))

    assert result["ok"] is False
    assert result["error"]["code"] == "OUTLOOK_SEND_FAILED"
    assert result["error"]["details"]["placeholder"] == "{CR_LINK}"
    assert "{CR_LINK}" in result["error"]["message"]


# ── unmet Template_Category condition skip (Req 8.6) ──────────────────────


def test_draft_unmet_condition_skips_with_reason(env):
    metadata = _full_metadata()
    metadata.cr_state = CRState.PENDING_APPROVAL  # condition below requires APPROVED
    folder = _make_project(env, metadata=metadata)
    _configure_category(
        env,
        "ACK_UAT",
        EmailCategorySettings(
            to="ops@example.com",
            subject_template="{PROJECT_NAME}",
            body_template="ok",
            conditions=[{"field": "cr_state", "operator": "equals", "value": "APPROVED"}],
        ),
    )

    result = env["js_api"].outlook_draft_email("ACK_UAT", str(folder))

    assert result["ok"] is True
    assert result["data"]["status"] == "skipped"
    assert "cr_state" in result["data"]["reason"]
    assert "APPROVED" in result["data"]["reason"]


def test_send_unmet_condition_skips_with_reason(env):
    metadata = _full_metadata()
    metadata.cr_state = CRState.PENDING_APPROVAL
    folder = _make_project(env, metadata=metadata)
    _configure_category(
        env,
        "APRVL_SOP",
        EmailCategorySettings(
            to="ops@example.com",
            subject_template="{PROJECT_NAME}",
            body_template="ok",
            conditions=[{"field": "cr_state", "operator": "equals", "value": "APPROVED"}],
        ),
    )

    result = env["js_api"].outlook_send_email("APRVL_SOP", str(folder))

    assert result["ok"] is True
    assert result["data"]["status"] == "skipped"
    assert "cr_state" in result["data"]["reason"]


# ── dev fallback contact off-Windows (Req 8.7) ────────────────────────────


@not_windows
def test_get_contacts_off_windows_returns_dev_fallback(env, monkeypatch):
    # Guard against any accidental COM execution: pythoncom must never be touched.
    def _boom():  # pragma: no cover - asserts the COM path is not reached
        raise AssertionError("COM thread must not run off-Windows")

    monkeypatch.setattr(outlook_client, "_run_on_com_thread", _boom)

    result = env["js_api"].outlook_get_contacts()

    assert result["ok"] is True
    assert result["data"]["contacts"] == [
        {"name": "Dev User", "email": "dev@example.local"}
    ]


@not_windows
def test_get_contacts_off_windows_ignores_query_filter(env):
    # Off-Windows the dev fallback is returned unfiltered even with a query that
    # would not match the fallback contact's name/email (Req 8.7).
    result = env["js_api"].outlook_get_contacts("no-such-name")

    assert result["ok"] is True
    assert result["data"]["contacts"] == [
        {"name": "Dev User", "email": "dev@example.local"}
    ]


# ── dev-skipped download off-Windows (Req 8.8) ────────────────────────────


@not_windows
def test_download_emails_off_windows_is_dev_skipped(env, monkeypatch):
    folder = _make_project(env, metadata=_full_metadata())

    # No background worker may be started off-Windows: fail if start_job is hit.
    from project_tracker.services.download_email_service import DownloadEmailService

    def _boom(*_args, **_kwargs):  # pragma: no cover - asserts worker not started
        raise AssertionError("download worker must not start off-Windows")

    monkeypatch.setattr(DownloadEmailService, "start_job", _boom)

    result = env["js_api"].outlook_download_emails(str(folder))

    assert result["ok"] is True
    assert result["data"]["status"] == "dev_skipped"
    assert str(folder) in result["data"]["message"]
