from __future__ import annotations

import json
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from types import MappingProxyType
from typing import Any

from project_tracker.core.enums import CRState, DroneState, ProjectState
from project_tracker.infrastructure.cache_db import CacheDb, CachedDroneTicketRow, CachedProjectRow


@dataclass(frozen=True, slots=True)
class DashboardProject:
    project_path: Path
    year: str
    project_name: str
    project_state: ProjectState
    cr_number: str | None
    cr_link: str
    cr_state: CRState
    cr_pending_approval_at: datetime | None
    start_datetime: datetime | None
    end_datetime: datetime | None
    t10_status: str
    drone_ticket_count: int
    updated_at: datetime | None
    scanned_at: datetime | None


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
    by_t10_status: Mapping[str, int]
    total_drone_tickets: int


@dataclass(frozen=True, slots=True)
class DashboardData:
    projects: tuple[DashboardProject, ...]
    summary: DashboardSummary


class DashboardService:
    def __init__(self, cache: CacheDb) -> None:
        self.cache = cache

    def list_projects(self, year: str | None = None) -> list[DashboardProject]:
        return [_dashboard_project_from_cache_row(row) for row in self.cache.list_projects(year)]

    def list_drone_tickets(self, project_path: Path) -> list[DashboardDroneTicket]:
        return [_dashboard_drone_from_cache_row(row) for row in self.cache.list_drone_tickets(project_path)]

    def get_summary(self, year: str | None = None) -> DashboardSummary:
        return _summary_from_projects(self.list_projects(year))

    def get_dashboard(self, year: str | None = None) -> DashboardData:
        projects = self.list_projects(year)
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
        updated_at=row.updated_at,
        scanned_at=row.scanned_at,
    )


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
    by_t10_status: dict[str, int] = {}
    total_drone_tickets = 0

    for project in projects:
        by_project_state[project.project_state] = by_project_state.get(project.project_state, 0) + 1
        by_cr_state[project.cr_state] = by_cr_state.get(project.cr_state, 0) + 1
        by_t10_status[project.t10_status] = by_t10_status.get(project.t10_status, 0) + 1
        total_drone_tickets += project.drone_ticket_count

    return DashboardSummary(
        total_projects=len(projects),
        by_project_state=MappingProxyType(dict(by_project_state)),
        by_cr_state=MappingProxyType(dict(by_cr_state)),
        by_t10_status=MappingProxyType(dict(by_t10_status)),
        total_drone_tickets=total_drone_tickets,
    )
