from __future__ import annotations

import json
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from types import MappingProxyType
from typing import Any

from core.enums import CRState, DroneState, NonCrState, ProjectState, ProjectType
from core.rules import extract_drone_ticket
from infrastructure.cache_db import CacheDb, CachedDroneTicketRow, CachedProjectRow


@dataclass(frozen=True, slots=True)
class DashboardRowDrone:
    """A drone ticket as shown inline on a Dashboard row (PRD §11.15)."""

    subfolder_name: str | None
    drone_ticket: str
    drone_link: str
    drone_state: str
    owner: str


@dataclass(frozen=True, slots=True)
class DashboardProject:
    project_path: Path
    year: str
    project_name: str
    project_state: ProjectState | None
    cr_number: str | None
    cr_link: str
    cr_state: CRState
    cr_pending_approval_at: datetime | None
    start_datetime: datetime | None
    end_datetime: datetime | None
    t10_status: str
    drone_ticket_count: int
    created_at: datetime | None
    updated_at: datetime | None
    scanned_at: datetime | None
    appcode: str = ""
    project_type: ProjectType = ProjectType.CR
    non_cr_state: NonCrState | None = None
    drones: tuple[str, ...] = ()
    drone_tickets: tuple[DashboardRowDrone, ...] = ()


@dataclass(frozen=True, slots=True)
class DashboardDroneTicket:
    project_path: Path
    subfolder_name: str | None
    drone_ticket: str | None
    drone_state: DroneState
    owner: str
    display: str | None
    updated_at: datetime | None


@dataclass(frozen=True, slots=True)
class DashboardSummary:
    total_projects: int
    by_project_state: Mapping[ProjectState, int]
    by_cr_state: Mapping[CRState, int]
    by_project_type: Mapping[ProjectType, int]
    by_t10_status: Mapping[str, int]
    total_drone_tickets: int


@dataclass(frozen=True, slots=True)
class DashboardData:
    projects: tuple[DashboardProject, ...]
    summary: DashboardSummary


class DashboardService:
    def __init__(self, cache: CacheDb) -> None:
        self.cache = cache

    def list_projects(self, year: str | None = None, appcode: str | None = None) -> list[DashboardProject]:
        return [_dashboard_project_from_cache_row(row) for row in self.cache.list_projects(year, appcode)]

    def list_drone_tickets(self, project_path: Path) -> list[DashboardDroneTicket]:
        return [_dashboard_drone_from_cache_row(row) for row in self.cache.list_drone_tickets(project_path)]

    def get_summary(self, year: str | None = None, appcode: str | None = None) -> DashboardSummary:
        return _summary_from_projects(self.list_projects(year, appcode))

    def get_dashboard(self, year: str | None = None, appcode: str | None = None) -> DashboardData:
        projects = self.list_projects(year, appcode)
        return DashboardData(projects=tuple(projects), summary=_summary_from_projects(projects))


def _dashboard_project_from_cache_row(row: CachedProjectRow) -> DashboardProject:
    return DashboardProject(
        project_path=row.project_path,
        year=row.year,
        project_name=row.project_name,
        project_state=row.project_state,
        cr_number=row.cr_number,
        cr_link=row.cr_link,
        cr_state=row.cr_state,
        cr_pending_approval_at=row.cr_pending_approval_at,
        start_datetime=row.start_datetime,
        end_datetime=row.end_datetime,
        t10_status=row.t10_status,
        drone_ticket_count=_drone_ticket_count(row.drone_tickets_json),
        created_at=row.created_at,
        updated_at=row.updated_at,
        scanned_at=row.scanned_at,
        drones=_drones_from_json(row.drone_paths_json),
        appcode=row.appcode,
        project_type=row.project_type,
        non_cr_state=row.non_cr_state,
        drone_tickets=_dashboard_drones_from_json(row.drone_tickets_json),
    )


def _drones_from_json(drone_paths_json: str) -> tuple[str, ...]:
    try:
        parsed: Any = json.loads(drone_paths_json)
    except json.JSONDecodeError:
        return ()
    if not isinstance(parsed, list):
        return ()
    return tuple(str(item) for item in parsed if isinstance(item, str) and item.strip())


def _dashboard_drones_from_json(drone_tickets_json: str) -> tuple[DashboardRowDrone, ...]:
    """Parse the cached drone_tickets JSON into frontend-safe row drones.

    Robust to malformed JSON and missing keys (mirrors ``_drone_ticket_count``):
    a bad payload yields an empty tuple rather than raising.
    """
    try:
        parsed: Any = json.loads(drone_tickets_json)
    except json.JSONDecodeError:
        return ()
    if not isinstance(parsed, list):
        return ()
    drones: list[DashboardRowDrone] = []
    for item in parsed:
        if not isinstance(item, dict):
            continue
        drone_link = str(item.get("drone_link", "") or "")
        subfolder = item.get("subfolder_name")
        drones.append(
            DashboardRowDrone(
                subfolder_name=str(subfolder) if subfolder else None,
                drone_ticket=extract_drone_ticket(drone_link),
                drone_link=drone_link,
                drone_state=str(item.get("drone_state", "") or ""),
                owner=str(item.get("owner", "") or ""),
            )
        )
    return tuple(drones)


def _dashboard_drone_from_cache_row(row: CachedDroneTicketRow) -> DashboardDroneTicket:
    return DashboardDroneTicket(
        project_path=row.project_path,
        subfolder_name=row.subfolder_name,
        drone_ticket=row.drone_ticket,
        drone_state=row.drone_state,
        owner=row.owner,
        display=row.display,
        updated_at=row.updated_at,
    )


def _drone_ticket_count(drone_tickets_json: str) -> int:
    try:
        parsed: Any = json.loads(drone_tickets_json)
    except json.JSONDecodeError:
        return 0
    if not isinstance(parsed, list):
        return 0
    return len(parsed)


def _summary_from_projects(projects: list[DashboardProject]) -> DashboardSummary:
    by_project_state: dict[ProjectState, int] = {}
    by_cr_state: dict[CRState, int] = {}
    by_project_type: dict[ProjectType, int] = {}
    by_t10_status: dict[str, int] = {}
    total_drone_tickets = 0

    for project in projects:
        if project.project_state is not None:
            by_project_state[project.project_state] = by_project_state.get(project.project_state, 0) + 1
        by_cr_state[project.cr_state] = by_cr_state.get(project.cr_state, 0) + 1
        by_project_type[project.project_type] = by_project_type.get(project.project_type, 0) + 1
        by_t10_status[project.t10_status] = by_t10_status.get(project.t10_status, 0) + 1
        total_drone_tickets += project.drone_ticket_count

    return DashboardSummary(
        total_projects=len(projects),
        by_project_state=MappingProxyType(dict(by_project_state)),
        by_cr_state=MappingProxyType(dict(by_cr_state)),
        by_project_type=MappingProxyType(dict(by_project_type)),
        by_t10_status=MappingProxyType(dict(by_t10_status)),
        total_drone_tickets=total_drone_tickets,
    )
