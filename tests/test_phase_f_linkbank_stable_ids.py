"""Phase F.3 — Link Bank Stable IDs + CRUD tests."""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

import pytest

from project_tracker.infrastructure.link_bank_store import LinkBank, LinkBankStore, _normalize_link


# ── Unit: _normalize_link ──────────────────────────────────────────────


class TestNormalizeLinkIds:
    """Legacy links without id get a stable uuid; links with id preserve it."""

    def test_legacy_link_gets_id(self):
        link = {"name": "Google", "url": "https://google.com", "notes": "", "category": "search"}
        result = _normalize_link(link)
        assert "id" in result
        assert len(result["id"]) == 32  # uuid4().hex = 32 hex chars

    def test_existing_id_preserved(self):
        link = {"id": "abc123", "name": "Test", "url": "https://x.com"}
        result = _normalize_link(link)
        assert result["id"] == "abc123"

    def test_empty_string_id_gets_new_id(self):
        link = {"id": "", "name": "Test", "url": "https://x.com"}
        result = _normalize_link(link)
        assert result["id"] != ""
        assert len(result["id"]) == 32

    def test_archived_defaults_to_false(self):
        link = {"name": "Test", "url": "https://x.com"}
        result = _normalize_link(link)
        assert result["archived"] == "false"

    def test_archived_preserved_when_present(self):
        link = {"name": "Test", "url": "https://x.com", "archived": "true"}
        result = _normalize_link(link)
        assert result["archived"] == "true"


# ── Unit: LinkBankStore round-trip ─────────────────────────────────────


class TestLinkBankStoreRoundTrip:
    """Write -> read preserves ids."""

    def _tmp_store(self, tmp_path: Path) -> LinkBankStore:
        return LinkBankStore(path=tmp_path / "links.json")

    def test_roundtrip_preserves_ids(self, tmp_path: Path):
        store = self._tmp_store(tmp_path)
        bank = LinkBank(
            categories=["dev"],
            links=[{"id": "deadbeef", "name": "GH", "url": "https://github.com", "notes": "", "category": "dev", "archived": "false"}],
        )
        store.write(bank)
        loaded = store.read()
        assert loaded.links[0]["id"] == "deadbeef"

    def test_legacy_links_get_ids_on_read(self, tmp_path: Path):
        store = self._tmp_store(tmp_path)
        # Write raw JSON without id field
        raw = {"categories": ["misc"], "links": [{"name": "Old", "url": "https://old.com", "notes": "", "category": "misc"}]}
        store.path.parent.mkdir(parents=True, exist_ok=True)
        store.path.write_text(json.dumps(raw), encoding="utf-8")
        loaded = store.read()
        assert loaded.links[0]["id"]
        assert len(loaded.links[0]["id"]) == 32

    def test_ids_persisted_after_write(self, tmp_path: Path):
        store = self._tmp_store(tmp_path)
        raw = {"categories": [], "links": [{"name": "A", "url": "https://a.com"}]}
        store.path.parent.mkdir(parents=True, exist_ok=True)
        store.path.write_text(json.dumps(raw), encoding="utf-8")
        bank = store.read()
        generated_id = bank.links[0]["id"]
        # Write back
        store.write(bank)
        # Re-read
        bank2 = store.read()
        assert bank2.links[0]["id"] == generated_id


# ── Integration: _LinkBankAdapter via create_js_api ────────────────────


@pytest.fixture
def js_api(tmp_path: Path):
    """Create a JsApi with temp LinkBankStore.

    Seeds a legacy link (no id/archived) then persists once so generated
    ids are stable across subsequent reads — mirrors the real first-write
    that stabilizes ids for legacy data.
    """
    store = LinkBankStore(path=tmp_path / "linkbank.json")
    raw = {
        "categories": ["dev"],
        "links": [
            {"name": "GitHub", "url": "https://github.com", "notes": "Code hosting", "category": "dev"},
        ],
    }
    store.path.parent.mkdir(parents=True, exist_ok=True)
    store.path.write_text(json.dumps(raw), encoding="utf-8")
    # Persist generated ids so they are stable for get -> mutate flows.
    store.write(store.read())
    # Lazy import: app_web imports webview; module-level import here would
    # pollute sys.modules and break phase_c "import_does_not_require_pywebview" tests.
    from project_tracker.app_web import create_js_api

    return create_js_api(linkbank_store=store)


class TestAddLink:
    """linkbank_add_link CRUD."""

    def test_add_link_success(self, js_api):
        result = js_api.linkbank_add_link({"name": "Svelte", "url": "https://svelte.dev", "category": "frontend", "notes": "UI framework"})
        assert result["ok"] is True
        link = result["data"]
        assert link["name"] == "Svelte"
        assert link["url"] == "https://svelte.dev"
        assert link["id"]
        assert len(link["id"]) == 32
        assert link["archived"] == "false"

    def test_add_link_empty_name_fails(self, js_api):
        result = js_api.linkbank_add_link({"name": "", "url": "https://x.com"})
        assert result["ok"] is False
        assert "required" in result["error"]["message"].lower()

    def test_add_link_empty_url_fails(self, js_api):
        result = js_api.linkbank_add_link({"name": "Test", "url": ""})
        assert result["ok"] is False
        assert "required" in result["error"]["message"].lower()

    def test_add_link_invalid_scheme_fails(self, js_api):
        result = js_api.linkbank_add_link({"name": "FTP", "url": "ftp://files.example.com"})
        assert result["ok"] is False
        assert "http" in result["error"]["message"].lower()

    def test_add_link_new_category_added(self, js_api):
        js_api.linkbank_add_link({"name": "Tailwind", "url": "https://tailwindcss.com", "category": "css"})
        bank_result = js_api.linkbank_get()
        assert "css" in bank_result["data"]["categories"]


class TestArchiveLink:
    """linkbank_archive_link CRUD."""

    def test_archive_link_success(self, js_api):
        # Get link bank to find the seeded link's id
        bank = js_api.linkbank_get()
        link_id = bank["data"]["links"][0]["id"]
        result = js_api.linkbank_archive_link(link_id)
        assert result["ok"] is True
        assert result["data"]["archived"] == "true"
        assert result["data"]["id"] == link_id

    def test_archive_link_nonexistent_fails(self, js_api):
        result = js_api.linkbank_archive_link("nonexistent_id_999")
        assert result["ok"] is False
        assert "not found" in result["error"]["message"].lower()


class TestUpdateLinkbank:
    """linkbank_update CRUD (single link update by id)."""

    def test_update_link_success(self, js_api):
        bank = js_api.linkbank_get()
        link_id = bank["data"]["links"][0]["id"]
        result = js_api.linkbank_update({"id": link_id, "name": "GitHub Enterprise", "notes": "Updated notes"})
        assert result["ok"] is True
        assert result["data"]["name"] == "GitHub Enterprise"
        assert result["data"]["notes"] == "Updated notes"
        # url unchanged
        assert result["data"]["url"] == "https://github.com"

    def test_update_link_no_id_fails(self, js_api):
        result = js_api.linkbank_update({"name": "No ID"})
        assert result["ok"] is False
        assert "id" in result["error"]["message"].lower()

    def test_update_link_nonexistent_id_fails(self, js_api):
        result = js_api.linkbank_update({"id": "does_not_exist", "name": "X"})
        assert result["ok"] is False
        assert "not found" in result["error"]["message"].lower()
