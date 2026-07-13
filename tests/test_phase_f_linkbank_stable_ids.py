"""Phase F.3 — Link Bank Stable IDs + CRUD tests."""

from __future__ import annotations

import csv
import io
import json
import tempfile
from pathlib import Path

import pytest

from infrastructure.link_bank_store import LinkBank, LinkBankStore, _normalize_link
from services.link_bank_service import LinkBankService


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

    @pytest.mark.parametrize("raw", [True, "true", "TRUE", 1, "1", "yes", "on"])
    def test_truthy_flags_normalize_to_true(self, raw):
        result = _normalize_link({"name": "Test", "url": "https://x.com", "pinned": raw})
        assert result["pinned"] == "true"

    @pytest.mark.parametrize("raw", [False, "false", "FALSE", 0, "0", "no", "off", "unexpected"])
    def test_other_flags_normalize_to_false(self, raw):
        result = _normalize_link({"name": "Test", "url": "https://x.com", "favorite": raw})
        assert result["favorite"] == "false"


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
    from app_web import create_js_api

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


# ── Task 6: LinkBank.archived_categories schema ────────────────────────


class TestArchivedCategoriesSchema:
    """LinkBank.archived_categories field + legacy-file normalization."""

    def test_default_archived_categories_empty(self):
        assert LinkBank().archived_categories == []

    def test_legacy_file_without_archived_categories_loads(self, tmp_path: Path):
        store = LinkBankStore(path=tmp_path / "links.json")
        raw = {"categories": ["dev"], "links": []}
        store.path.parent.mkdir(parents=True, exist_ok=True)
        store.path.write_text(json.dumps(raw), encoding="utf-8")
        loaded = store.read()
        assert loaded.archived_categories == []

    def test_roundtrip_preserves_archived_categories(self, tmp_path: Path):
        store = LinkBankStore(path=tmp_path / "links.json")
        bank = LinkBank(categories=["dev"], links=[], archived_categories=["legacy"])
        store.write(bank)
        loaded = store.read()
        assert loaded.archived_categories == ["legacy"]

    def test_from_dict_filters_non_string_archived_categories(self):
        bank = LinkBank.from_dict({"archived_categories": ["ok", 5, None, "also-ok"]})
        assert bank.archived_categories == ["ok", "also-ok"]

    def test_from_dict_treats_non_list_collections_as_empty(self):
        bank = LinkBank.from_dict(
            {"categories": "dev", "links": {"name": "not-a-list"}, "archived_categories": "old"}
        )
        assert bank.to_dict() == {"categories": [], "links": [], "archived_categories": []}


# ── Task 6: LinkBankService CRUD parity with the former adapter ───────


class TestLinkBankServiceCrudParity:
    """LinkBankService reproduces the existing adapter CRUD contract."""

    def _service(self, tmp_path: Path) -> LinkBankService:
        return LinkBankService(LinkBankStore(path=tmp_path / "links.json"))

    def test_add_link_success(self, tmp_path: Path):
        service = self._service(tmp_path)
        link = service.add_link({"name": "Svelte", "url": "https://svelte.dev", "category": "frontend"})
        assert link["name"] == "Svelte"
        assert len(link["id"]) == 32
        assert link["archived"] == "false"
        assert link["created_at"]
        assert link["updated_at"]

    def test_add_link_requires_name_and_url(self, tmp_path: Path):
        service = self._service(tmp_path)
        with pytest.raises(ValueError, match="required"):
            service.add_link({"name": "", "url": "https://x.com"})

    def test_add_link_requires_http_scheme(self, tmp_path: Path):
        service = self._service(tmp_path)
        with pytest.raises(ValueError, match="http"):
            service.add_link({"name": "FTP", "url": "ftp://files.example.com"})

    def test_add_link_requires_absolute_http_url(self, tmp_path: Path):
        service = self._service(tmp_path)
        with pytest.raises(ValueError, match="http"):
            service.add_link({"name": "Relative", "url": "https:relative"})

    def test_update_validates_name_and_url_before_writing(self, tmp_path: Path):
        service = self._service(tmp_path)
        link = service.add_link({"name": "Docs", "url": "https://docs.example.com"})
        before = service.get_linkbank()

        with pytest.raises(ValueError, match="http"):
            service.update_linkbank({"id": link["id"], "url": "javascript:alert(1)"})

        assert service.get_linkbank() == before

    def test_add_and_update_reuse_category_spelling_case_insensitively(self, tmp_path: Path):
        service = self._service(tmp_path)
        first = service.add_link({"name": "A", "url": "https://a.example.com", "category": "DevOps"})
        second = service.add_link({"name": "B", "url": "https://b.example.com", "category": "devops"})
        updated = service.update_linkbank({"id": first["id"], "category": "DEVOPS"})

        assert second["category"] == "DevOps"
        assert updated["category"] == "DevOps"
        assert service.get_linkbank()["categories"] == ["DevOps"]


# ── Task 6: link/category archive + restore ────────────────────────────


class TestLinkAndCategoryArchiveRestore:
    """restore_link / category_restore reverse archive and update timestamps."""

    def _service(self, tmp_path: Path) -> LinkBankService:
        return LinkBankService(LinkBankStore(path=tmp_path / "links.json"))

    def test_restore_link_reverses_archive(self, tmp_path: Path):
        service = self._service(tmp_path)
        link = service.add_link({"name": "Docs", "url": "https://docs.example.com"})
        archived = service.archive_link(link["id"])
        assert archived["archived"] == "true"
        restored = service.restore_link(link["id"])
        assert restored["archived"] == "false"
        assert restored["updated_at"]

    def test_restore_link_nonexistent_raises(self, tmp_path: Path):
        service = self._service(tmp_path)
        with pytest.raises(ValueError, match="not found"):
            service.restore_link("missing")

    def test_restore_link_reactivates_category_without_restoring_sibling_links(
        self, tmp_path: Path
    ):
        service = self._service(tmp_path)
        first = service.add_link({"name": "A", "url": "https://a.com", "category": "ops"})
        second = service.add_link({"name": "B", "url": "https://b.com", "category": "ops"})
        service.category_archive("ops")

        restored = service.restore_link(first["id"])
        bank = service.get_linkbank()

        assert restored["archived"] == "false"
        assert bank["categories"] == ["ops"]
        assert bank["archived_categories"] == []
        assert next(link for link in bank["links"] if link["id"] == second["id"])["archived"] == "true"

    def test_category_archive_then_restore_reactivates_links(self, tmp_path: Path):
        service = self._service(tmp_path)
        service.add_link({"name": "A", "url": "https://a.com", "category": "ops"})
        service.add_link({"name": "B", "url": "https://b.com", "category": "ops"})

        archived_bank = service.category_archive("ops")
        assert "ops" not in archived_bank["categories"]
        assert "ops" in archived_bank["archived_categories"]
        assert all(link["archived"] == "true" for link in archived_bank["links"] if link["category"] == "ops")

        restored_bank = service.category_restore("ops")
        assert "ops" in restored_bank["categories"]
        assert "ops" not in restored_bank["archived_categories"]
        assert all(link["archived"] == "false" for link in restored_bank["links"] if link["category"] == "ops")

    def test_category_crud_is_case_insensitive_and_preserves_canonical_spelling(self, tmp_path: Path):
        service = self._service(tmp_path)
        service.add_link({"name": "A", "url": "https://a.com", "category": "DevOps"})

        assert service.category_create("devops")["categories"] == ["DevOps"]
        archived = service.category_archive("DEVOPS")
        assert archived["archived_categories"] == ["DevOps"]
        assert archived["links"][0]["archived"] == "true"
        restored = service.category_restore("devops")
        assert restored["categories"] == ["DevOps"]
        assert restored["links"][0]["archived"] == "false"

    def test_category_rename_requires_existing_category(self, tmp_path: Path):
        service = self._service(tmp_path)
        with pytest.raises(ValueError, match="not found"):
            service.category_rename("missing", "new")

    @pytest.mark.parametrize("destination_archived", [False, True])
    def test_category_rename_rejects_existing_destination(
        self, tmp_path: Path, destination_archived: bool
    ):
        service = self._service(tmp_path)
        service.add_link({"name": "Source", "url": "https://source.example.com", "category": "source"})
        service.add_link({"name": "Target", "url": "https://target.example.com", "category": "target"})
        if destination_archived:
            service.category_archive("target")
        before = service.get_linkbank()

        with pytest.raises(ValueError, match="already exists"):
            service.category_rename("source", "TARGET")

        assert service.get_linkbank() == before


# ── Fix Round 1, Finding 2: reserved rail keywords rejected ─────────────


class TestReservedCategoryNames:
    """category_create/category_rename must reject rail keywords (all/pinned/
    favorites/archived) case-insensitively so a category can never collide
    with the rail's literal filter dispatch."""

    def _service(self, tmp_path: Path) -> LinkBankService:
        return LinkBankService(LinkBankStore(path=tmp_path / "links.json"))

    @pytest.mark.parametrize("reserved", ["all", "ALL", "Pinned", "FAVORITES", "Archived"])
    def test_category_create_rejects_reserved_names(self, tmp_path: Path, reserved: str):
        service = self._service(tmp_path)
        with pytest.raises(ValueError, match="reserved"):
            service.category_create(reserved)

    @pytest.mark.parametrize("reserved", ["all", "ALL", "Pinned", "FAVORITES", "Archived"])
    def test_category_rename_rejects_reserved_new_names(self, tmp_path: Path, reserved: str):
        service = self._service(tmp_path)
        service.add_link({"name": "A", "url": "https://a.example.com", "category": "ops"})
        with pytest.raises(ValueError, match="reserved"):
            service.category_rename("ops", reserved)


# ── Task 6: case-insensitive category merge on import ──────────────────


class TestCategoryCaseInsensitiveMerge:
    """Rule 8: import category names merge case-insensitively, preserving spelling."""

    def _service(self, tmp_path: Path) -> LinkBankService:
        return LinkBankService(LinkBankStore(path=tmp_path / "links.json"))

    def test_merge_import_preserves_existing_category_spelling(self, tmp_path: Path):
        service = self._service(tmp_path)
        service.add_link({"name": "Existing", "url": "https://existing.example.com", "category": "DevOps"})
        content = json.dumps(
            {"links": [{"name": "New", "url": "https://new.example.com", "category": "devops"}]}
        )
        result = service.merge_import("json", content)
        assert result["added"] == 1
        bank = service.get_linkbank()
        assert bank["categories"].count("DevOps") == 1
        assert "devops" not in bank["categories"]
        new_link = next(link for link in bank["links"] if link["url"] == "https://new.example.com")
        assert new_link["category"] == "DevOps"


# ── Task 6: JSON/CSV export ─────────────────────────────────────────────


class TestExportFormats:
    """Rules 1-2: JSON/CSV complete export."""

    def _service(self, tmp_path: Path) -> LinkBankService:
        return LinkBankService(LinkBankStore(path=tmp_path / "links.json"))

    def test_export_json_is_complete_and_keeps_archived_state(self, tmp_path: Path):
        service = self._service(tmp_path)
        service.add_link({"name": "A", "url": "https://a.com", "category": "x", "tags": "t1,t2"})
        service.category_archive("x")

        exported = service.export_file("json")
        assert exported["format"] == "json"
        assert exported["suggested_name"] == "link-bank.json"
        data = json.loads(exported["content"])
        assert data["archived_categories"] == ["x"]
        assert data["links"][0]["archived"] == "true"

    def test_exported_json_merge_preserves_updated_at_for_new_link(self, tmp_path: Path):
        source = self._service(tmp_path / "source")
        source.add_link({"name": "A", "url": "https://a.example.com"})
        exported = source.export_file("json")
        exported_updated_at = json.loads(exported["content"])["links"][0]["updated_at"]
        destination = self._service(tmp_path / "destination")

        destination.merge_import("json", exported["content"])

        assert destination.get_linkbank()["links"][0]["updated_at"] == exported_updated_at

    def test_legacy_full_bank_replace_is_not_exposed_by_service(self, tmp_path: Path):
        service = LinkBankService(LinkBankStore(path=tmp_path / "links.json"))

        assert not hasattr(service, "import_json")

    def test_export_csv_has_expected_columns(self, tmp_path: Path):
        service = self._service(tmp_path)
        service.add_link(
            {"name": "A", "url": "https://a.com", "category": "x", "tags": "t1,t2", "details": "desc"}
        )

        exported = service.export_file("csv")
        assert exported["format"] == "csv"
        assert exported["suggested_name"] == "link-bank.csv"
        reader = csv.DictReader(io.StringIO(exported["content"]))
        assert reader.fieldnames == [
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
        row = next(reader)
        assert row["name"] == "A"
        assert row["description"] == "desc"
        assert row["tags"] == "t1,t2"


# ── Task 6: preview / merge import ──────────────────────────────────────


class TestPreviewMergeImport:
    """Rules 3-7, 10-11: preview/merge add, update, conflict, invalid, duplicate, no-write."""

    def _service(self, tmp_path: Path) -> LinkBankService:
        return LinkBankService(LinkBankStore(path=tmp_path / "links.json"))

    def test_preview_reports_counts_without_writing(self, tmp_path: Path):
        service = self._service(tmp_path)
        existing = service.add_link({"name": "Existing", "url": "https://existing.example.com"})
        content = json.dumps(
                {
                    "links": [
                        {"id": existing["id"], "name": "Existing Updated", "url": "https://existing.example.com"},
                        {"name": "Brand New", "url": "https://brand-new.example.com"},
                        {"name": "", "url": "not-a-url"},
                    ]
                }
            )

        preview = service.preview_import("json", content)

        assert preview["update"] == 1
        assert preview["add"] == 1
        assert preview["invalid"] == 1
        assert preview["conflict"] == 0
        assert len(preview["skipped"]) == 1
        bank = service.get_linkbank()
        assert len(bank["links"]) == 1
        assert bank["links"][0]["name"] == "Existing"

    def test_matching_id_updates_unless_url_owned_by_another_id(self, tmp_path: Path):
        service = self._service(tmp_path)
        a = service.add_link({"name": "A", "url": "https://a.example.com"})
        service.add_link({"name": "B", "url": "https://b.example.com"})
        content = json.dumps(
                {"links": [{"id": a["id"], "name": "A2", "url": "https://b.example.com"}]}
            )

        preview = service.preview_import("json", content)

        assert preview["conflict"] == 1
        assert preview["update"] == 0

    def test_new_id_unique_url_adds(self, tmp_path: Path):
        service = self._service(tmp_path)
        content = json.dumps(
                {"links": [{"id": "brand-new-id", "name": "New", "url": "https://new.example.com"}]}
            )

        preview = service.preview_import("json", content)

        assert preview["add"] == 1

    def test_same_url_another_id_conflicts(self, tmp_path: Path):
        service = self._service(tmp_path)
        service.add_link({"name": "A", "url": "https://dup.example.com"})
        content = json.dumps({"links": [{"id": "other-id", "name": "Dup", "url": "https://dup.example.com"}]})

        preview = service.preview_import("json", content)

        assert preview["conflict"] == 1
        assert preview["add"] == 0

    def test_duplicate_ids_within_import_conflict(self, tmp_path: Path):
        service = self._service(tmp_path)
        content = json.dumps(
                {
                    "links": [
                        {"id": "dup-id", "name": "First", "url": "https://first.example.com"},
                        {"id": "dup-id", "name": "Second", "url": "https://second.example.com"},
                    ]
                }
            )

        preview = service.preview_import("json", content)

        assert preview["add"] == 1
        assert preview["conflict"] == 1

    def test_duplicate_urls_within_import_conflict(self, tmp_path: Path):
        service = self._service(tmp_path)
        content = json.dumps(
                {
                    "links": [
                        {"name": "First", "url": "https://same.example.com"},
                        {"name": "Second", "url": "https://same.example.com"},
                    ]
                }
            )

        preview = service.preview_import("json", content)

        assert preview["add"] == 1
        assert preview["conflict"] == 1

    def test_malformed_json_performs_no_write(self, tmp_path: Path):
        service = self._service(tmp_path)
        service.add_link({"name": "A", "url": "https://a.example.com"})
        content = "{not valid json"

        with pytest.raises(ValueError):
            service.preview_import("json", content)
        with pytest.raises(ValueError):
            service.merge_import("json", content)

        bank = service.get_linkbank()
        assert len(bank["links"]) == 1

    def test_confirmed_merge_writes_once_atomically(self, tmp_path: Path, monkeypatch):
        service = self._service(tmp_path)
        service.add_link({"name": "A", "url": "https://a.example.com"})
        write_calls = []
        original_write = LinkBankStore.write

        def spy_write(self, bank):
            write_calls.append(bank)
            return original_write(self, bank)

        monkeypatch.setattr(LinkBankStore, "write", spy_write)
        content = json.dumps({"links": [{"name": "New", "url": "https://new.example.com"}]})

        result = service.merge_import("json", content)

        assert result["added"] == 1
        assert len(write_calls) == 1

    def test_csv_import_preview_and_merge(self, tmp_path: Path):
        service = self._service(tmp_path)
        csv_content = (
            "id,name,url,category,tags,description,pinned,favorite,archived,created_at,updated_at\n"
            ",CSV Link,https://csv.example.com,ops,tag1,CSV desc,false,false,false,,\n"
        )
        preview = service.preview_import("csv", csv_content)
        assert preview["add"] == 1

        result = service.merge_import("csv", csv_content)
        assert result["added"] == 1

        bank = service.get_linkbank()
        link = next(link for link in bank["links"] if link["url"] == "https://csv.example.com")
        assert link["name"] == "CSV Link"
        assert link["category"] == "ops"
        assert link["notes"] == "CSV desc"

    def test_url_normalization_preserves_case_sensitive_path(self, tmp_path: Path):
        service = self._service(tmp_path)
        service.add_link({"name": "Upper", "url": "https://Example.COM/Case/"})
        content = json.dumps(
            {
                "links": [
                    {"name": "Same", "url": "https://example.com/Case#fragment"},
                    {"name": "Different", "url": "https://example.com/case"},
                ]
            }
        )

        preview = service.preview_import("json", content)

        assert preview["conflict"] == 1
        assert preview["add"] == 1

    def test_json_merge_restores_archived_categories(self, tmp_path: Path):
        service = self._service(tmp_path)
        content = json.dumps(
            {
                "categories": ["Active"],
                "archived_categories": ["Legacy"],
                "links": [
                    {
                        "id": "legacy-link",
                        "name": "Legacy docs",
                        "url": "https://legacy.example.com",
                        "category": "legacy",
                        "archived": True,
                    }
                ],
            }
        )

        result = service.merge_import("json", content)
        bank = service.get_linkbank()

        assert result == {"added": 1, "updated": 0, "conflicts": 0, "invalid": 0}
        assert bank["archived_categories"] == ["Legacy"]
        assert "Legacy" not in bank["categories"]
        assert bank["links"][0]["category"] == "Legacy"
        assert bank["links"][0]["archived"] == "true"


# ── Fix Round 2, Finding A: conflicting rows must not leak categories ───


class TestMergeImportConflictCategoryLeak:
    """A row discarded as a conflict must not register its novel category."""

    def _service(self, tmp_path: Path) -> LinkBankService:
        return LinkBankService(LinkBankStore(path=tmp_path / "links.json"))

    def test_url_belongs_to_another_id_conflict_does_not_leak_category(self, tmp_path: Path):
        service = self._service(tmp_path)
        a = service.add_link({"name": "A", "url": "https://a.example.com"})
        service.add_link({"name": "B", "url": "https://b.example.com"})
        content = json.dumps(
            {"links": [{"id": a["id"], "name": "A2", "url": "https://b.example.com", "category": "NovelCat"}]}
        )

        result = service.merge_import("json", content)

        assert result["conflicts"] == 1
        bank = service.get_linkbank()
        assert "NovelCat" not in bank["categories"]
        assert "NovelCat" not in bank["archived_categories"]

    def test_url_exists_under_another_id_conflict_does_not_leak_category(self, tmp_path: Path):
        service = self._service(tmp_path)
        service.add_link({"name": "A", "url": "https://dup.example.com"})
        content = json.dumps(
            {"links": [{"id": "other-id", "name": "Dup", "url": "https://dup.example.com", "category": "NovelCat"}]}
        )

        result = service.merge_import("json", content)

        assert result["conflicts"] == 1
        bank = service.get_linkbank()
        assert "NovelCat" not in bank["categories"]
        assert "NovelCat" not in bank["archived_categories"]


# ── Fix Round 2, Finding B: merge-update must not wipe category/tags ─────


class TestApplyRowPreservesOptionalTextFields:
    """Absent optional text fields preserve values; explicit blanks clear them."""

    def _service(self, tmp_path: Path) -> LinkBankService:
        return LinkBankService(LinkBankStore(path=tmp_path / "links.json"))

    def test_merge_update_without_category_or_tags_preserves_existing(self, tmp_path: Path):
        service = self._service(tmp_path)
        link = service.add_link(
            {
                "name": "Old Name",
                "url": "https://example.com",
                "category": "ops",
                "tags": "a,b",
                "details": "old description",
                "pinned": "true",
                "favorite": "true",
            }
        )
        content = json.dumps(
            {"links": [{"id": link["id"], "name": "New Name", "url": "https://example.com"}]}
        )

        result = service.merge_import("json", content)

        assert result["updated"] == 1
        bank = service.get_linkbank()
        updated = next(item for item in bank["links"] if item["id"] == link["id"])
        assert updated["name"] == "New Name"
        assert updated["category"] == "ops"
        assert updated["tags"] == "a,b"
        assert updated["notes"] == "old description"
        assert updated["details"] == "old description"
        assert updated["pinned"] == "true"
        assert updated["favorite"] == "true"

    @pytest.mark.parametrize("format_name", ["json", "csv"])
    def test_merge_update_explicit_blanks_clear_optional_text_fields(
        self, tmp_path: Path, format_name: str
    ):
        service = self._service(tmp_path)
        link = service.add_link(
            {
                "name": "Old Name",
                "url": "https://example.com",
                "category": "ops",
                "tags": "a,b",
                "details": "old description",
            }
        )
        if format_name == "json":
            content = json.dumps(
                {
                    "links": [
                        {
                            "id": link["id"],
                            "name": "New Name",
                            "url": "https://example.com",
                            "category": "",
                            "tags": "",
                            "description": "",
                        }
                    ]
                }
            )
        else:
            content = (
                "id,name,url,category,tags,description\n"
                f'{link["id"]},New Name,https://example.com,,,\n'
            )

        result = service.merge_import(format_name, content)

        assert result["updated"] == 1
        updated = next(
            item for item in service.get_linkbank()["links"] if item["id"] == link["id"]
        )
        assert updated["category"] == ""
        assert updated["tags"] == ""
        assert updated["notes"] == ""
        assert updated["details"] == ""

    def test_csv_merge_update_without_optional_columns_preserves_existing(self, tmp_path: Path):
        service = self._service(tmp_path)
        link = service.add_link(
            {
                "name": "Old Name",
                "url": "https://example.com",
                "category": "ops",
                "tags": "a,b",
                "details": "old description",
            }
        )
        content = "id,name,url\n" f'{link["id"]},New Name,https://example.com\n'

        service.merge_import("csv", content)

        updated = next(
            item for item in service.get_linkbank()["links"] if item["id"] == link["id"]
        )
        assert updated["category"] == "ops"
        assert updated["tags"] == "a,b"
        assert updated["notes"] == "old description"
        assert updated["details"] == "old description"

    @pytest.mark.parametrize("format_name", ["json", "csv"])
    def test_merge_update_explicit_blank_flags_normalize_to_false(
        self, tmp_path: Path, format_name: str
    ):
        service = self._service(tmp_path)
        link = service.add_link(
            {
                "name": "Old Name",
                "url": "https://example.com",
                "pinned": "true",
                "favorite": "true",
                "archived": "true",
            }
        )
        if format_name == "json":
            content = json.dumps(
                {
                    "links": [
                        {
                            "id": link["id"],
                            "name": "New Name",
                            "url": "https://example.com",
                            "pinned": "",
                            "favorite": "",
                            "archived": "",
                        }
                    ]
                }
            )
        else:
            content = (
                "id,name,url,pinned,favorite,archived\n"
                f'{link["id"]},New Name,https://example.com,,,\n'
            )

        service.merge_import(format_name, content)

        updated = next(
            item for item in service.get_linkbank()["links"] if item["id"] == link["id"]
        )
        assert updated["pinned"] == "false"
        assert updated["favorite"] == "false"
        assert updated["archived"] == "false"


class TestMergeImportArchivedCategoryInvariant:
    """A stable-ID update cannot reactivate a link inside an archived category."""

    def test_update_omitting_archived_category_keeps_link_archived(self, tmp_path: Path):
        service = LinkBankService(LinkBankStore(path=tmp_path / "links.json"))
        link = service.add_link(
            {"name": "Old Name", "url": "https://example.com", "category": "ops"}
        )
        service.category_archive("ops")
        content = json.dumps(
            {
                "links": [
                    {
                        "id": link["id"],
                        "name": "New Name",
                        "url": "https://example.com",
                        "archived": False,
                    }
                ]
            }
        )

        service.merge_import("json", content)

        updated = next(
            item for item in service.get_linkbank()["links"] if item["id"] == link["id"]
        )
        assert updated["category"] == "ops"
        assert updated["archived"] == "true"


# ── Fix Round 2, Finding C: update_linkbank archived-category parity ────


class TestUpdateLinkbankArchivedCategoryParity:
    """Editing a link into an archived category must archive it, like add_link does."""

    def _service(self, tmp_path: Path) -> LinkBankService:
        return LinkBankService(LinkBankStore(path=tmp_path / "links.json"))

    def test_editing_link_into_archived_category_archives_link(self, tmp_path: Path):
        service = self._service(tmp_path)
        service.add_link({"name": "Ops Link", "url": "https://ops.example.com", "category": "ops"})
        service.category_archive("ops")
        link = service.add_link({"name": "Active Link", "url": "https://active.example.com", "category": "misc"})

        updated = service.update_linkbank({"id": link["id"], "category": "ops"})

        assert updated["archived"] == "true"


# ── Task 6: OS browser open via injected opener ─────────────────────────


class TestOpenLinkOpener:
    """OS browser open occurs only through the service with an injected opener."""

    def test_open_link_calls_injected_opener(self, tmp_path: Path):
        store = LinkBankStore(path=tmp_path / "links.json")
        opened: list[str] = []
        service = LinkBankService(store, opener=opened.append)
        link = service.add_link({"name": "Docs", "url": "https://docs.example.com"})

        result = service.open_link(link["id"])

        assert opened == ["https://docs.example.com"]
        assert result["id"] == link["id"]

    def test_open_link_nonexistent_raises(self, tmp_path: Path):
        store = LinkBankStore(path=tmp_path / "links.json")
        service = LinkBankService(store, opener=lambda url: None)
        with pytest.raises(ValueError, match="not found"):
            service.open_link("missing")

    def test_open_link_rejects_invalid_stored_url(self, tmp_path: Path):
        store = LinkBankStore(path=tmp_path / "links.json")
        store.write(LinkBank(links=[{"id": "bad", "name": "Bad", "url": "file:///tmp/secret"}]))
        opened: list[str] = []
        service = LinkBankService(store, opener=opened.append)

        with pytest.raises(ValueError, match="http"):
            service.open_link("bad")

        assert opened == []


# ── Fix Round 2: reserved categories blocked at every creation path ─────


class TestReservedCategoriesAllCreationPaths:
    """Reviewer follow-up on b3a80f84: category_create/category_rename already
    guard reserved rail keywords, but add_link/update_linkbank (via
    _canonical_category(create=True)) and merge_import (via new_categories
    appended unchecked) were sibling entry points that could still create a
    reserved-named category. Creation is blocked everywhere; resolving an
    EXISTING reserved-named category (legacy data) still works."""

    def _service(self, tmp_path: Path) -> LinkBankService:
        return LinkBankService(LinkBankStore(path=tmp_path / "links.json"))

    def test_add_link_rejects_new_reserved_category(self, tmp_path: Path):
        service = self._service(tmp_path)
        with pytest.raises(ValueError, match="reserved"):
            service.add_link({"name": "A", "url": "https://a.example.com", "category": "Archived"})
        bank = service.get_linkbank()
        assert bank["links"] == []
        assert "Archived" not in bank["categories"]

    def test_update_linkbank_rejects_new_reserved_category(self, tmp_path: Path):
        service = self._service(tmp_path)
        link = service.add_link({"name": "A", "url": "https://a.example.com", "category": "ops"})
        with pytest.raises(ValueError, match="reserved"):
            service.update_linkbank({"id": link["id"], "category": "all"})
        bank = service.get_linkbank()
        assert bank["links"][0]["category"] == "ops"
        assert "all" not in bank["categories"]

    def test_merge_import_row_with_reserved_category_is_skipped_not_created(self, tmp_path: Path):
        service = self._service(tmp_path)
        content = json.dumps(
            {
                "links": [
                    {"name": "Bad", "url": "https://bad.example.com", "category": "all"},
                    {"name": "Good", "url": "https://good.example.com", "category": "ops"},
                ]
            }
        )

        preview = service.preview_import("json", content)
        assert preview["add"] == 1
        assert preview["invalid"] == 1

        result = service.merge_import("json", content)
        assert result["added"] == 1
        assert result["invalid"] == 1
        bank = service.get_linkbank()
        assert "all" not in bank["categories"]
        assert "all" not in bank["archived_categories"]
        assert len(bank["links"]) == 1
        assert bank["links"][0]["name"] == "Good"

    def test_merge_import_top_level_reserved_category_list_not_created(self, tmp_path: Path):
        service = self._service(tmp_path)
        content = json.dumps(
            {
                "links": [{"name": "Good", "url": "https://good.example.com", "category": "ops"}],
                "categories": ["Favorites"],
            }
        )

        result = service.merge_import("json", content)

        assert result["added"] == 1
        bank = service.get_linkbank()
        assert "Favorites" not in bank["categories"]

    def test_legacy_bank_with_existing_reserved_named_category_still_resolves(self, tmp_path: Path):
        store = LinkBankStore(path=tmp_path / "links.json")
        store.write(
            LinkBank(
                links=[
                    {
                        "id": "legacy1",
                        "name": "Legacy",
                        "url": "https://legacy.example.com",
                        "category": "Archived",
                    }
                ],
                categories=["Archived"],
            )
        )
        service = LinkBankService(store)

        bank = service.get_linkbank()
        assert bank["categories"] == ["Archived"]

        added = service.add_link({"name": "New", "url": "https://new.example.com", "category": "archived"})
        assert added["category"] == "Archived"
        bank = service.get_linkbank()
        assert bank["categories"].count("Archived") == 1
