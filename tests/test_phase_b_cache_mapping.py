from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path

from core.enums import CRState, DroneState, ProjectState
from core.models import DroneTicket, ProjectMetadata
from infrastructure.cache_db import cached_drone_rows_from_scan, cached_project_row_from_scan
from infrastructure.filesystem import ScannedProject


def _scanned_project(
    project_path: Path,
    *,
    metadata: ProjectMetadata | None = None,
    project_state: ProjectState = ProjectState.PROD_READY,
) -> ScannedProject:
    return ScannedProject(
        path=project_path,
        year="2026",
        project_state=project_state,
        metadata=metadata or ProjectMetadata(project_name="PAYMENT_MODULE_UPGRADE"),
        subproject_paths=[project_path / "APP_COMPONENT"],
    )


def test_cached_project_row_from_scan_derives_year_and_folder_state_from_scan(tmp_path: Path) -> None:
    project_path = tmp_path / "CR" / "2026" / ProjectState.CANCELED.value / "PAYMENT_MODULE_UPGRADE"
    scanned = _scanned_project(project_path, project_state=ProjectState.CANCELED)

    row = cached_project_row_from_scan(scanned)

    assert row.project_path == project_path
    assert row.year == "2026"
    assert row.project_state == ProjectState.CANCELED


def test_cached_project_row_from_scan_maps_project_metadata_fields(tmp_path: Path) -> None:
    start_datetime = datetime(2026, 6, 3, 10, 0, tzinfo=timezone.utc)
    end_datetime = datetime(2026, 6, 3, 11, 0, tzinfo=timezone.utc)
    pending_approval_at = datetime(2026, 5, 20, 9, 0, tzinfo=timezone.utc)
    updated_at = datetime(2026, 6, 3, 9, 30, tzinfo=timezone.utc)
    cr_link = "https://cr.example.local/change?CRNumber=CR202604209900114"
    metadata = ProjectMetadata(
        project_name="PAYMENT_MODULE_UPGRADE",
        start_datetime=start_datetime,
        end_datetime=end_datetime,
        cr_link=cr_link,
        cr_state=CRState.APPROVED,
        cr_pending_approval_at=pending_approval_at,
        updated_at=updated_at,
    )
    scanned = _scanned_project(tmp_path / "CR" / "2026" / "PROD_READY" / "PAYMENT_MODULE_UPGRADE", metadata=metadata)

    row = cached_project_row_from_scan(scanned)

    assert row.project_name == "PAYMENT_MODULE_UPGRADE"
    assert row.start_datetime == start_datetime
    assert row.end_datetime == end_datetime
    assert row.cr_link == cr_link
    assert row.cr_state == CRState.APPROVED
    assert row.cr_pending_approval_at == pending_approval_at
    assert row.updated_at == updated_at
    assert row.t10_status == "PASS"


def test_cached_project_row_from_scan_sets_scanned_at_timestamp(tmp_path: Path) -> None:
    scanned = _scanned_project(tmp_path / "CR" / "2026" / "PROD_READY" / "PAYMENT_MODULE_UPGRADE")

    row = cached_project_row_from_scan(scanned)

    assert row.scanned_at is not None
    assert row.scanned_at.tzinfo is not None


def test_cached_project_row_from_scan_extracts_cr_number_into_existing_display_field(tmp_path: Path) -> None:
    metadata = ProjectMetadata(cr_link="https://cr.example.local/change?CRNumber=CR202604209900114")
    scanned = _scanned_project(tmp_path / "CR" / "2026" / "PROD_READY" / "PAYMENT_MODULE_UPGRADE", metadata=metadata)

    row = cached_project_row_from_scan(scanned)

    assert row.cr_number == "CR202604209900114"


def test_cached_project_row_from_scan_sets_cr_number_to_none_when_extraction_fails(tmp_path: Path) -> None:
    metadata = ProjectMetadata(cr_link="https://cr.example.local/change?id=123")
    scanned = _scanned_project(tmp_path / "CR" / "2026" / "PROD_READY" / "PAYMENT_MODULE_UPGRADE", metadata=metadata)

    row = cached_project_row_from_scan(scanned)

    assert row.cr_number is None


def test_cached_project_row_from_scan_falls_back_to_folder_name_for_blank_project_name(tmp_path: Path) -> None:
    project_path = tmp_path / "CR" / "2026" / "PROD_READY" / "PAYMENT_MODULE_UPGRADE"
    metadata = ProjectMetadata(project_name="")
    scanned = _scanned_project(project_path, metadata=metadata)

    row = cached_project_row_from_scan(scanned)

    assert row.project_name == "PAYMENT_MODULE_UPGRADE"


def test_cached_drone_rows_from_scan_maps_all_drone_tickets(tmp_path: Path) -> None:
    metadata = ProjectMetadata(
        drone_tickets=[
            DroneTicket(drone_link="https://drone.example.local/tickets/D-SSIDBI-159"),
            DroneTicket(drone_link="https://drone.example.local/tickets/D-SSIDBI-160"),
        ]
    )
    scanned = _scanned_project(tmp_path / "CR" / "2026" / "PROD_READY" / "PAYMENT_MODULE_UPGRADE", metadata=metadata)

    rows = cached_drone_rows_from_scan(scanned)

    assert [row.drone_ticket for row in rows] == ["D-SSIDBI-159", "D-SSIDBI-160"]


def test_cached_drone_rows_from_scan_maps_drone_metadata_fields(tmp_path: Path) -> None:
    updated_at = datetime(2026, 6, 3, 9, 30, tzinfo=timezone.utc)
    metadata = ProjectMetadata(
        drone_tickets=[
            DroneTicket(
                subfolder_name="APP_COMPONENT",
                drone_link="https://drone.example.local/tickets/D-SSIDBI-159",
                drone_state=DroneState.APPROVED,
                drone_state_updated_at=updated_at,
                owner="Alice",
            )
        ]
    )
    project_path = tmp_path / "CR" / "2026" / "PROD_READY" / "PAYMENT_MODULE_UPGRADE"
    scanned = _scanned_project(project_path, metadata=metadata)

    rows = cached_drone_rows_from_scan(scanned)

    assert len(rows) == 1
    assert rows[0].project_path == project_path
    assert rows[0].subfolder_name == "APP_COMPONENT"
    assert rows[0].drone_state == DroneState.APPROVED
    assert rows[0].owner == "Alice"
    assert rows[0].updated_at == updated_at


def test_cached_drone_rows_from_scan_extracts_drone_ticket_id_into_existing_display_field(tmp_path: Path) -> None:
    metadata = ProjectMetadata(drone_tickets=[DroneTicket(drone_link="https://drone.example.local/tickets/D-SSIDBI-159")])
    scanned = _scanned_project(tmp_path / "CR" / "2026" / "PROD_READY" / "PAYMENT_MODULE_UPGRADE", metadata=metadata)

    rows = cached_drone_rows_from_scan(scanned)

    assert rows[0].drone_ticket == "D-SSIDBI-159"
    assert rows[0].display == "D-SSIDBI-159"


def test_cached_drone_rows_from_scan_sets_drone_ticket_to_none_when_extraction_fails(tmp_path: Path) -> None:
    metadata = ProjectMetadata(drone_tickets=[DroneTicket(drone_link="https://drone.example.local/tickets/123")])
    scanned = _scanned_project(tmp_path / "CR" / "2026" / "PROD_READY" / "PAYMENT_MODULE_UPGRADE", metadata=metadata)

    rows = cached_drone_rows_from_scan(scanned)

    assert rows[0].drone_ticket is None
    assert rows[0].display is None


def test_cache_mapping_functions_do_not_mutate_metadata_or_ticket_objects(tmp_path: Path) -> None:
    ticket = DroneTicket(
        subfolder_name="APP_COMPONENT",
        drone_link="https://drone.example.local/tickets/D-SSIDBI-159",
        drone_state=DroneState.APPROVED,
        owner="Alice",
    )
    metadata = ProjectMetadata(
        project_name="PAYMENT_MODULE_UPGRADE",
        cr_link="https://cr.example.local/change?CRNumber=CR202604209900114",
        drone_tickets=[ticket],
    )
    before = deepcopy(metadata)
    scanned = _scanned_project(tmp_path / "CR" / "2026" / "PROD_READY" / "PAYMENT_MODULE_UPGRADE", metadata=metadata)

    cached_project_row_from_scan(scanned)
    cached_drone_rows_from_scan(scanned)

    assert metadata == before
    assert ticket == before.drone_tickets[0]
