from datetime import datetime, timezone

import pytest

from project_tracker.core.models import AppSettings, DroneTicket, ProjectMetadata, datetime_from_json, datetime_to_json


def test_project_metadata_does_not_serialize_project_state() -> None:
    serialized = ProjectMetadata(project_name="PAYMENT_MODULE_UPGRADE").to_dict()

    assert "project_state" not in serialized


def test_project_metadata_does_not_serialize_notes() -> None:
    metadata = ProjectMetadata(project_name="PAYMENT_MODULE_UPGRADE")

    serialized = metadata.to_dict()

    assert "notes" not in serialized


def test_project_metadata_ignores_legacy_notes_input() -> None:
    metadata = ProjectMetadata.from_dict({"project_name": "PAYMENT_MODULE_UPGRADE", "notes": "legacy"})

    serialized = metadata.to_dict()

    assert "notes" not in serialized


def test_drone_ticket_owner_defaults_to_empty_string() -> None:
    ticket = DroneTicket()

    assert ticket.owner == ""
    assert ticket.to_dict()["owner"] == ""


def test_drone_ticket_serializes_owner() -> None:
    ticket = DroneTicket(owner="Alice")

    assert ticket.to_dict()["owner"] == "Alice"


def test_datetime_to_json_rejects_naive_datetime() -> None:
    with pytest.raises(ValueError, match="timezone-aware"):
        datetime_to_json(datetime(2026, 1, 15, 20, 40, 0))


def test_datetime_from_json_rejects_naive_iso_datetime() -> None:
    with pytest.raises(ValueError, match="timezone-aware"):
        datetime_from_json("2026-01-15T20:40:00")


def test_timezone_aware_datetime_round_trips() -> None:
    original = datetime(2026, 1, 15, 20, 40, 0, tzinfo=timezone.utc)

    serialized = datetime_to_json(original)
    parsed = datetime_from_json(serialized)

    assert parsed == original


def test_metadata_h10_notified_at_roundtrip() -> None:
    md = ProjectMetadata(project_name="X")
    assert md.h10_notified_at is None
    data = md.to_dict()
    assert "h10_notified_at" in data
    restored = ProjectMetadata.from_dict(data)
    assert restored.h10_notified_at is None


def test_settings_h10_reminder_days_default_and_roundtrip() -> None:
    s = AppSettings()
    assert s.h10_reminder_days == 10
    data = s.to_dict()
    assert data["h10_reminder_days"] == 10
    restored = AppSettings.from_dict({**data, "h10_reminder_days": 7})
    assert restored.h10_reminder_days == 7
