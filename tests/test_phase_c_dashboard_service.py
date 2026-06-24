from __future__ import annotations

import json
from pathlib import Path

import pytest

from core.enums import CRState, DroneState, ProjectState
from core.models import ProjectMetadata
from core.rules import extract_drone_ticket
from infrastructure.cache_db import CacheDb, CachedDroneTicketRow, CachedProjectRow
from infrastructure.metadata_store import MetadataStore
from services.dashboard_service import (
    DashboardData,
    DashboardDroneTicket,
    DashboardProject,
    DashboardRowDrone,
    DashboardService,
    DashboardSummary,
)


def _cache(tmp_path: Path) -> CacheDb:
    cache = CacheDb(tmp_path / "cache.sqlite3")
    cache.initialize()
    return cache


def _project_row(
    project_path: Path,
    *,
    year: str = "2026",
    project_state: ProjectState = ProjectState.UAT_PREPARE,
    project_name: str = "PAYMENT_MODULE_UPGRADE",
    cr_state: CRState = CRState.APPROVED,
    cr_number: str | None = "CR202604209900114",
    cr_link: str = "https://cr.example.local/change?CRNumber=CR202604209900114",
    drone_tickets_json: str = "[]",
    subprojects_json: str = "[]",
    t10_status: str = "UNKNOWN",
) -> CachedProjectRow:
    return CachedProjectRow(
        project_path=project_path,
        year=year,
        project_state=project_state,
        project_name=project_name,
        cr_link=cr_link,
        cr_number=cr_number,
        cr_state=cr_state,
        drone_tickets_json=drone_tickets_json,
        subprojects_json=subprojects_json,
        t10_status=t10_status,
    )


def test_list_projects_returns_cache_backed_dashboard_project_dtos(tmp_path: Path) -> None:
    cache = _cache(tmp_path)
    project_path = tmp_path / "CR" / "2026" / ProjectState.PROD_READY.value / "PAYMENT_MODULE_UPGRADE"
    cache.upsert_project(
        _project_row(
            project_path,
            project_state=ProjectState.PROD_READY,
            project_name="PAYMENT_MODULE_UPGRADE",
            cr_state=CRState.APPROVED,
            drone_tickets_json='[{"drone_link": "https://drone.example.local/tickets/D-SSIDBI-159"}]',
            t10_status="PASS",
        )
    )

    projects = DashboardService(cache).list_projects("2026")

    assert projects == [
        DashboardProject(
            project_path=project_path,
            year="2026",
            project_name="PAYMENT_MODULE_UPGRADE",
            project_state=ProjectState.PROD_READY,
            cr_number="CR202604209900114",
            cr_link="https://cr.example.local/change?CRNumber=CR202604209900114",
            cr_state=CRState.APPROVED,
            cr_pending_approval_at=None,
            start_datetime=None,
            end_datetime=None,
            t10_status="PASS",
            drone_ticket_count=1,
            updated_at=None,
            scanned_at=None,
            subprojects=(),
            drone_tickets=(
                DashboardRowDrone(
                    subfolder_name=None,
                    drone_ticket=extract_drone_ticket("https://drone.example.local/tickets/D-SSIDBI-159"),
                    drone_link="https://drone.example.local/tickets/D-SSIDBI-159",
                    drone_state="",
                    owner="",
                ),
            ),
        )
    ]


def test_list_projects_filters_by_year_using_cache_api(tmp_path: Path) -> None:
    cache = _cache(tmp_path)
    row_2026_path = tmp_path / "CR" / "2026" / ProjectState.UAT_PREPARE.value / "A"
    row_2027_path = tmp_path / "CR" / "2027" / ProjectState.UAT_PREPARE.value / "B"
    cache.upsert_project(_project_row(row_2026_path, year="2026", project_name="A"))
    cache.upsert_project(_project_row(row_2027_path, year="2027", project_name="B"))

    projects = DashboardService(cache).list_projects("2026")

    assert [project.project_path for project in projects] == [row_2026_path]


def test_list_drone_tickets_returns_cache_backed_drone_dtos(tmp_path: Path) -> None:
    cache = _cache(tmp_path)
    project_path = tmp_path / "CR" / "2026" / ProjectState.PROD_READY.value / "PAYMENT_MODULE_UPGRADE"
    cache.replace_drone_tickets_for_project(
        project_path,
        [
            CachedDroneTicketRow(
                project_path=project_path,
                subfolder_name="APP_COMPONENT",
                drone_ticket="D-SSIDBI-159",
                drone_state=DroneState.APPROVED,
                owner="Alice",
                display="D-SSIDBI-159",
            )
        ],
    )

    tickets = DashboardService(cache).list_drone_tickets(project_path)

    assert tickets == [
        DashboardDroneTicket(
            project_path=project_path,
            subfolder_name="APP_COMPONENT",
            drone_ticket="D-SSIDBI-159",
            drone_state=DroneState.APPROVED,
            owner="Alice",
            display="D-SSIDBI-159",
            updated_at=None,
        )
    ]


def test_get_summary_counts_project_states_cr_states_t10_and_drone_ticket_totals(tmp_path: Path) -> None:
    cache = _cache(tmp_path)
    cache.upsert_project(
        _project_row(
            tmp_path / "CR" / "2026" / ProjectState.UAT_PREPARE.value / "A",
            project_state=ProjectState.UAT_PREPARE,
            cr_state=CRState.APPROVED,
            drone_tickets_json="[{}, {}]",
            t10_status="PASS",
        )
    )
    cache.upsert_project(
        _project_row(
            tmp_path / "CR" / "2026" / ProjectState.PROD_READY.value / "B",
            project_state=ProjectState.PROD_READY,
            cr_state=CRState.PENDING_SUBMISSION,
            drone_tickets_json="[{}]",
            t10_status="FAIL",
        )
    )
    cache.upsert_project(
        _project_row(
            tmp_path / "CR" / "2026" / ProjectState.PROD_READY.value / "C",
            project_state=ProjectState.PROD_READY,
            cr_state=CRState.APPROVED,
            drone_tickets_json="[]",
            t10_status="UNKNOWN",
        )
    )

    summary = DashboardService(cache).get_summary("2026")

    assert summary == DashboardSummary(
        total_projects=3,
        by_project_state={ProjectState.UAT_PREPARE: 1, ProjectState.PROD_READY: 2},
        by_cr_state={CRState.APPROVED: 2, CRState.PENDING_SUBMISSION: 1},
        by_t10_status={"PASS": 1, "FAIL": 1, "UNKNOWN": 1},
        total_drone_tickets=3,
    )


def test_get_dashboard_returns_projects_and_summary_from_same_cache_snapshot(tmp_path: Path) -> None:
    cache = _cache(tmp_path)
    first_path = tmp_path / "CR" / "2026" / ProjectState.UAT_PREPARE.value / "A"
    second_path = tmp_path / "CR" / "2026" / ProjectState.PROD_READY.value / "B"
    cache.upsert_project(_project_row(first_path, project_name="A"))
    cache.upsert_project(_project_row(second_path, project_state=ProjectState.PROD_READY, project_name="B"))

    dashboard = DashboardService(cache).get_dashboard("2026")

    assert isinstance(dashboard, DashboardData)
    assert [project.project_path for project in dashboard.projects] == [first_path, second_path]
    assert dashboard.summary.total_projects == len(dashboard.projects)


def test_empty_cache_returns_empty_dashboard_and_zero_summary(tmp_path: Path) -> None:
    dashboard = DashboardService(_cache(tmp_path)).get_dashboard("2026")

    assert dashboard == DashboardData(
        projects=(),
        summary=DashboardSummary(
            total_projects=0,
            by_project_state={},
            by_cr_state={},
            by_t10_status={},
            total_drone_tickets=0,
        ),
    )


def test_dashboard_summary_mappings_are_runtime_immutable(tmp_path: Path) -> None:
    cache = _cache(tmp_path)
    cache.upsert_project(
        _project_row(
            tmp_path / "CR" / "2026" / ProjectState.UAT_PREPARE.value / "A",
            project_state=ProjectState.UAT_PREPARE,
            cr_state=CRState.APPROVED,
            drone_tickets_json="[]",
            t10_status="PASS",
        )
    )

    summary = DashboardService(cache).get_summary("2026")

    with pytest.raises(TypeError):
        summary.by_project_state[ProjectState.UAT_PREPARE] = 99
    with pytest.raises(TypeError):
        summary.by_cr_state[CRState.APPROVED] = 99
    with pytest.raises(TypeError):
        summary.by_t10_status["PASS"] = 99


def test_dashboard_data_projects_are_runtime_immutable(tmp_path: Path) -> None:
    cache = _cache(tmp_path)
    cache.upsert_project(_project_row(tmp_path / "CR" / "2026" / ProjectState.UAT_PREPARE.value / "A"))

    dashboard = DashboardService(cache).get_dashboard("2026")

    assert isinstance(dashboard.projects, tuple)
    with pytest.raises(AttributeError):
        dashboard.projects.append(dashboard.projects[0])


def test_invalid_drone_tickets_json_counts_as_zero(tmp_path: Path) -> None:
    cache = _cache(tmp_path)
    project_path = tmp_path / "CR" / "2026" / ProjectState.UAT_PREPARE.value / "BROKEN_JSON"
    cache.upsert_project(_project_row(project_path, drone_tickets_json="{not json"))

    dashboard = DashboardService(cache).get_dashboard("2026")

    assert dashboard.projects[0].drone_ticket_count == 0
    assert dashboard.summary.total_drone_tickets == 0


def test_dashboard_project_includes_subprojects_from_cache(tmp_path: Path) -> None:
    cache = _cache(tmp_path)
    project_path = tmp_path / "CR" / "2026" / ProjectState.UAT_PREPARE.value / "WITH_SUBS"
    cache.upsert_project(_project_row(project_path, subprojects_json='["alpha", "beta"]'))

    dashboard = DashboardService(cache).get_dashboard("2026")

    assert dashboard.projects[0].subprojects == ("alpha", "beta")


def test_invalid_subprojects_json_returns_empty_tuple(tmp_path: Path) -> None:
    cache = _cache(tmp_path)
    project_path = tmp_path / "CR" / "2026" / ProjectState.UAT_PREPARE.value / "BROKEN_SUBS"
    cache.upsert_project(_project_row(project_path, subprojects_json="{not json"))

    dashboard = DashboardService(cache).get_dashboard("2026")

    assert dashboard.projects[0].subprojects == ()


def test_dashboard_service_does_not_mutate_project_data_json_or_project_folders(tmp_path: Path) -> None:
    cache = _cache(tmp_path)
    root_folder = tmp_path / "CR"
    project_path = root_folder / "2026" / ProjectState.PROD_READY.value / "PAYMENT_MODULE_UPGRADE"
    MetadataStore().write(project_path, ProjectMetadata(project_name="PAYMENT_MODULE_UPGRADE"))
    (project_path / "APP_COMPONENT").mkdir()
    cache.upsert_project(_project_row(project_path, project_state=ProjectState.PROD_READY))
    metadata_path = project_path / "project_data.json"
    before_json = json.loads(metadata_path.read_text(encoding="utf-8"))
    before_children = sorted(path.relative_to(root_folder / "2026") for path in (root_folder / "2026").rglob("*"))

    service = DashboardService(cache)
    service.list_projects("2026")
    service.list_drone_tickets(project_path)
    service.get_summary("2026")
    service.get_dashboard("2026")

    after_json = json.loads(metadata_path.read_text(encoding="utf-8"))
    after_children = sorted(path.relative_to(root_folder / "2026") for path in (root_folder / "2026").rglob("*"))
    assert after_json == before_json
    assert after_children == before_children
