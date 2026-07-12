"""Phase D.12a: app_web Link Bank dependency wiring."""

from __future__ import annotations

from pathlib import Path


def test_create_js_api_wires_linkbank_get_with_temp_store(tmp_path: Path) -> None:
    """create_js_api() must wire LinkBankStore so linkbank_get() returns data."""
    from project_tracker import app_web
    from infrastructure.link_bank_store import LinkBank, LinkBankStore

    link_bank_path = tmp_path / "link_bank.json"
    store = LinkBankStore(link_bank_path)
    store.write(
        LinkBank(
            categories=["Ops"],
            links=[
                {
                    "name": "Runbook",
                    "url": "https://example.test/runbook",
                    "notes": "Deployment checklist",
                    "category": "Ops",
                }
            ],
        )
    )

    api = app_web.create_js_api(
        db_path=tmp_path / "cache.db",
        linkbank_store=LinkBankStore(link_bank_path),
    )
    result = api.linkbank_get()

    assert result.get("ok") is True, f"linkbank_get must be wired, got {result}"
    assert result.get("error") is None
    data = result.get("data")
    assert isinstance(data, dict)
    assert data["categories"] == ["Ops"]
    assert len(data["links"]) == 1
    link = data["links"][0]
    assert link["name"] == "Runbook"
    assert link["url"] == "https://example.test/runbook"
    assert link["notes"] == "Deployment checklist"
    assert link["category"] == "Ops"
    assert link["archived"] == "false"
    assert link["id"]  # stable uuid generated on normalize


def test_create_js_api_wires_linkbank_restore_and_category_restore(tmp_path: Path) -> None:
    """Task 6: create_js_api wires the new restore_link/category_restore facades."""
    from project_tracker import app_web
    from infrastructure.link_bank_store import LinkBank, LinkBankStore

    link_bank_path = tmp_path / "link_bank.json"
    store = LinkBankStore(link_bank_path)
    store.write(LinkBank(categories=["Ops"], links=[]))

    api = app_web.create_js_api(
        db_path=tmp_path / "cache.db",
        linkbank_store=LinkBankStore(link_bank_path),
    )

    added = api.linkbank_add_link({"name": "Runbook", "url": "https://example.test/runbook", "category": "Ops"})
    assert added["ok"] is True
    link_id = added["data"]["id"]

    archived = api.linkbank_archive_link(link_id)
    assert archived["ok"] is True
    assert archived["data"]["archived"] == "true"

    restored = api.linkbank_restore_link(link_id)
    assert restored["ok"] is True
    assert restored["data"]["archived"] == "false"

    cat_archived_result = api.linkbank_category_archive("Ops")
    assert cat_archived_result["ok"] is True

    cat_restored_result = api.linkbank_category_restore("Ops")
    assert cat_restored_result["ok"] is True
    assert "Ops" in cat_restored_result["data"]["categories"]


def test_create_js_api_wires_linkbank_export_and_preview_merge(tmp_path: Path) -> None:
    """Task 6: create_js_api wires export_file/preview_import/merge_import facades."""
    import json

    from project_tracker import app_web
    from infrastructure.link_bank_store import LinkBankStore

    link_bank_path = tmp_path / "link_bank.json"
    api = app_web.create_js_api(
        db_path=tmp_path / "cache.db",
        linkbank_store=LinkBankStore(link_bank_path),
    )

    added = api.linkbank_add_link({"name": "Docs", "url": "https://docs.example.test", "category": "Ops"})
    assert added["ok"] is True

    exported = api.linkbank_export_file("csv")
    assert exported["ok"] is True
    assert exported["data"]["format"] == "csv"
    assert exported["data"]["suggested_name"] == "link-bank.csv"
    assert (
        "id,name,url,category,tags,description,pinned,favorite,archived,created_at,updated_at"
        in exported["data"]["content"]
    )

    content = json.dumps({"links": [{"name": "New", "url": "https://new.example.test"}]})
    preview = api.linkbank_import_preview("json", content)
    assert preview["ok"] is True
    assert preview["data"]["add"] == 1

    merged = api.linkbank_import_merge("json", content)
    assert merged["ok"] is True
    assert merged["data"]["added"] == 1

    final = api.linkbank_get()
    assert len(final["data"]["links"]) == 2
