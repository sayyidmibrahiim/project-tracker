"""Phase E.1 — Notes persistence via notes.md file (PRD-correct).

Tests prove:
- notes_get reads from notes.md file, not from project_data.json
- notes_update writes to notes.md file and persists
- missing notes.md returns empty string
- update creates notes.md if absent
- unrelated mutations remain unavailable
"""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

from core.enums import CRState
from core.models import ProjectMetadata
from infrastructure.metadata_store import MetadataStore
from infrastructure.settings_store import SettingsStore


@pytest.fixture
def temp_project():
    """Temp project with notes.md file."""
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        year_dir = root / "2024"
        state_dir = year_dir / "UAT_PREPARE"
        proj_dir = state_dir / "test-project"
        proj_dir.mkdir(parents=True)

        metadata = ProjectMetadata(
            project_name="test-project",
            cr_link="https://cr.example.com/CR-999",
            cr_state=CRState.APPROVED,
        )
        store = MetadataStore()
        store.write(proj_dir, metadata)

        # Create notes.md with content
        (proj_dir / "notes.md").write_text("existing notes content")

        settings = SettingsStore(config_dir=root / "config")
        from dataclasses import replace

        updated = replace(settings.read(), root_folder=root)
        settings.write(updated)

        yield {
            "root": root,
            "project_path": proj_dir,
            "settings_store": settings,
        }


@pytest.fixture
def temp_project_no_notes():
    """Temp project WITHOUT notes.md file."""
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        year_dir = root / "2024"
        state_dir = year_dir / "UAT_PREPARE"
        proj_dir = state_dir / "test-project-no-notes"
        proj_dir.mkdir(parents=True)

        metadata = ProjectMetadata(project_name="test-project-no-notes")
        store = MetadataStore()
        store.write(proj_dir, metadata)

        settings = SettingsStore(config_dir=root / "config")
        from dataclasses import replace

        updated = replace(settings.read(), root_folder=root)
        settings.write(updated)

        yield {
            "root": root,
            "project_path": proj_dir,
            "settings_store": settings,
        }


@pytest.fixture
def js_api(temp_project):
    """JsApi from create_js_api with temp settings."""
    from project_tracker import app_web

    return app_web.create_js_api(settings_store=temp_project["settings_store"])


@pytest.fixture
def js_api_no_notes(temp_project_no_notes):
    """JsApi from create_js_api for project without notes.md."""
    from project_tracker import app_web

    return app_web.create_js_api(settings_store=temp_project_no_notes["settings_store"])


# ── notes_get reads from notes.md file ──────────────────────────────────


def test_notes_get_reads_from_notes_md_file(js_api, temp_project):
    """notes_get must read content from notes.md, not from project_data.json."""
    path = str(temp_project["project_path"])
    result = js_api.notes_get(path)
    assert result["ok"] is True
    assert result["data"] == "existing notes content"


def test_notes_get_returns_empty_when_no_notes_md(js_api_no_notes, temp_project_no_notes):
    """notes_get returns empty string when notes.md does not exist."""
    path = str(temp_project_no_notes["project_path"])
    result = js_api_no_notes.notes_get(path)
    assert result["ok"] is True
    assert result["data"] == ""


# ── notes_update writes to notes.md file ─────────────────────────────────


def test_notes_update_no_longer_service_unavailable(js_api, temp_project):
    """notes_update must not return SERVICE_UNAVAILABLE."""
    path = str(temp_project["project_path"])
    result = js_api.notes_update(path, "new notes")
    assert result["ok"] is True, f"Expected ok=True, got {result}"


def test_notes_update_persists_to_notes_md(js_api, temp_project):
    """notes_update writes content to notes.md file."""
    path = str(temp_project["project_path"])
    js_api.notes_update(path, "updated content")

    notes_file = temp_project["project_path"] / "notes.md"
    assert notes_file.read_text() == "updated content"


def test_notes_update_creates_notes_md_if_absent(js_api_no_notes, temp_project_no_notes):
    """notes_update creates notes.md if it does not exist."""
    path = str(temp_project_no_notes["project_path"])
    result = js_api_no_notes.notes_update(path, "brand new notes")
    assert result["ok"] is True

    notes_file = temp_project_no_notes["project_path"] / "notes.md"
    assert notes_file.exists()
    assert notes_file.read_text() == "brand new notes"


def test_notes_update_round_trip(js_api, temp_project):
    """notes_update followed by notes_get returns same content."""
    path = str(temp_project["project_path"])
    js_api.notes_update(path, "round trip test")
    result = js_api.notes_get(path)
    assert result["ok"] is True
    assert result["data"] == "round trip test"


def test_notes_update_failure_preserves_existing_notes_file(
    js_api, temp_project, monkeypatch
):
    """Failed notes update leaves existing notes.md unchanged and removes temp file."""
    project_path = temp_project["project_path"]
    notes_file = project_path / "notes.md"
    notes_file.write_text("original notes", encoding="utf-8")
    original_write_text = Path.write_text

    def fail_temp_notes_write(self: Path, data: str, *args, **kwargs):
        if self.name == ".notes.md.tmp":
            raise OSError("simulated temp write failure")
        return original_write_text(self, data, *args, **kwargs)

    monkeypatch.setattr(Path, "write_text", fail_temp_notes_write)

    result = js_api.notes_update(str(project_path), "new notes")

    assert result["ok"] is False
    assert notes_file.read_text(encoding="utf-8") == "original notes"
    assert not (project_path / ".notes.md.tmp").exists()


# ── unrelated mutations remain unavailable ────────────────────────────────


def test_folder_move_still_deferred(js_api):
    """Folder moves remain SERVICE_UNAVAILABLE."""
    result = js_api.folder_move_to_prod_ready("/tmp/x")
    assert result["ok"] is False


def test_file_open_dev_skipped_off_windows(js_api):
    """File open is wired: dev-skipped (ok=true) off-Windows, no os.startfile (Req 6.5)."""
    result = js_api.file_open("/tmp/x")
    assert result["ok"] is True


# ── RTE format capabilities ────────────────────────────────────────────────


def test_rte_markdown_capability_and_save(js_api, temp_project):
    notes_path = temp_project["project_path"] / "notes.md"

    loaded = js_api.get_rte_file(str(notes_path))
    assert loaded["ok"] is True
    assert loaded["data"]["format"] == "markdown"
    assert loaded["data"]["capability"] == "editable"
    assert loaded["data"]["saveStrategy"] == "markdown"

    saved = js_api.save_rte_file(str(notes_path), "# Updated")
    assert saved["ok"] is True
    assert notes_path.read_text(encoding="utf-8") == "# Updated"


def test_rte_text_capability_and_plain_text_save(js_api, temp_project):
    text_path = temp_project["project_path"] / "plain.txt"
    text_path.write_text("plain", encoding="utf-8")

    loaded = js_api.get_rte_file(str(text_path))
    assert loaded["ok"] is True
    assert loaded["data"]["format"] == "text"
    assert loaded["data"]["capability"] == "editable"
    assert loaded["data"]["saveStrategy"] == "plain_text"
    assert loaded["data"]["supportedEditorFeatures"] == ["plain_text"]

    saved = js_api.save_rte_file(str(text_path), "new plain")
    assert saved["ok"] is True
    assert text_path.read_text(encoding="utf-8") == "new plain"


def test_rte_docx_is_read_only_until_source_sync_adapter_exists(js_api, temp_project):
    docx_path = temp_project["project_path"] / "_cr-docs" / "uat-signoff.docx"

    loaded = js_api.get_rte_file(str(docx_path))
    assert loaded["ok"] is True
    assert loaded["data"]["format"] == "docx"
    assert loaded["data"]["capability"] == "read_only"
    assert loaded["data"]["editable"] is False
    assert loaded["data"]["saveStrategy"] == "none"

    saved = js_api.save_rte_file(str(docx_path), "<p>must not save</p>")
    assert saved["ok"] is False
    assert saved["error"]["code"] == "RTE_SAVE_FAILED"


def test_rte_msg_is_unsupported_and_never_saved(js_api, temp_project):
    msg_path = temp_project["project_path"] / "_cr-docs" / "mail.msg"
    msg_path.parent.mkdir(parents=True, exist_ok=True)
    msg_path.write_bytes(b"not text")

    loaded = js_api.get_rte_file(str(msg_path))
    assert loaded["ok"] is True
    assert loaded["data"]["format"] == "msg"
    assert loaded["data"]["capability"] == "unsupported"
    assert loaded["data"]["content"] == ""

    saved = js_api.save_rte_file(str(msg_path), "nope")
    assert saved["ok"] is False
    assert saved["error"]["code"] == "RTE_SAVE_FAILED"
