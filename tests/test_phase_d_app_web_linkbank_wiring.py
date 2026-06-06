"""Phase D.12a: app_web Link Bank dependency wiring."""

from __future__ import annotations

from pathlib import Path


def test_create_js_api_wires_linkbank_get_with_temp_store(tmp_path: Path) -> None:
    """create_js_api() must wire LinkBankStore so linkbank_get() returns data."""
    from project_tracker import app_web
    from project_tracker.infrastructure.link_bank_store import LinkBank, LinkBankStore

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
    assert data["links"] == [
        {
            "name": "Runbook",
            "url": "https://example.test/runbook",
            "notes": "Deployment checklist",
            "category": "Ops",
        }
    ]
