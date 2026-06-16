"""Cache-backed report filtering and CSV export service."""

from __future__ import annotations

import csv
from collections.abc import Iterable
from typing import Protocol
from datetime import datetime
from enum import Enum
from io import StringIO
from pathlib import Path

CSV_COLUMNS = (
    "year",
    "project_name",
    "project_state",
    "cr_number",
    "cr_state",
    "start_datetime",
    "end_datetime",
    "t10_status",
    "drone_ticket_count",
    "project_path",
)


class DashboardServiceProtocol(Protocol):
    """Dashboard service surface used by ReportService."""

    def list_projects(self, year: str | None = None) -> list[object]:
        """Return dashboard project DTOs."""


class ReportService:
    """Read-only report service over DashboardService project DTOs."""

    def __init__(self, dashboard_service: DashboardServiceProtocol) -> None:
        self._dashboard_service = dashboard_service

    def filter_projects(
        self,
        year: str | None = None,
        project_state: object | None = None,
        cr_state: object | None = None,
        search: str | None = None,
    ) -> list[object]:
        """Filter DashboardService project DTOs without mutating them."""
        projects = self._dashboard_service.list_projects(year)
        return [
            project
            for project in projects
            if self._matches_year(project, year)
            and self._matches_value(project, "project_state", project_state)
            and self._matches_value(project, "cr_state", cr_state)
            and self._matches_search(project, search)
        ]

    def export_csv(self, projects: Iterable[object]) -> str:
        """Export project DTOs as CSV text without writing files."""
        output = StringIO()
        writer = csv.DictWriter(output, fieldnames=CSV_COLUMNS)
        writer.writeheader()
        for project in projects:
            writer.writerow({column: _csv_value(getattr(project, column)) for column in CSV_COLUMNS})
        return output.getvalue()

    @staticmethod
    def _matches_year(project: object, year: str | None) -> bool:
        if year is None:
            return True
        return getattr(project, "year") == year

    @staticmethod
    def _matches_value(project: object, field_name: str, expected: object | None) -> bool:
        if expected is None:
            return True
        return getattr(project, field_name) == expected

    @staticmethod
    def _matches_search(project: object, search: str | None) -> bool:
        if not search:
            return True
        needle = search.casefold()
        haystacks = (
            getattr(project, "project_name"),
            getattr(project, "cr_number") or "",
            str(getattr(project, "project_path")),
        )
        return any(needle in haystack.casefold() for haystack in haystacks)


def _csv_value(value: object) -> object:
    """Return CSV-safe primitive value."""
    if value is None:
        return ""
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, Path):
        return value.as_posix()
    return value
