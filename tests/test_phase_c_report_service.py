"""Phase C.6 — ReportService tests (TDD: RED first)."""

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from project_tracker.core.enums import CRState, ProjectState
from project_tracker.services.report_service import ReportService


@dataclass(frozen=True)
class FakeProject:
    year: str
    project_name: str
    project_state: ProjectState
    cr_number: str | None
    cr_state: CRState
    start_datetime: datetime | None
    end_datetime: datetime | None
    t10_status: str
    drone_ticket_count: int
    project_path: Path


class FakeDashboardService:
    def __init__(self, projects: list[FakeProject]) -> None:
        self.projects = projects
        self.calls: list[str | None] = []

    def list_projects(self, year: str | None = None) -> list[FakeProject]:
        self.calls.append(year)
        return list(self.projects)


def _project(
    name: str,
    *,
    year: str = "2026",
    project_state: ProjectState = ProjectState.UAT_PREPARE,
    cr_number: str | None = "CR-1",
    cr_state: CRState = CRState.APPROVED,
    path: str | None = None,
) -> FakeProject:
    return FakeProject(
        year=year,
        project_name=name,
        project_state=project_state,
        cr_number=cr_number,
        cr_state=cr_state,
        start_datetime=datetime(2026, 1, 2, 3, 4, 5, tzinfo=timezone.utc),
        end_datetime=None,
        t10_status="READY",
        drone_ticket_count=2,
        project_path=Path(path or f"/tmp/{year}/{name}"),
    )


def test_filter_projects_filters_by_year():
    dashboard = FakeDashboardService([_project("A", year="2026"), _project("B", year="2025")])
    service = ReportService(dashboard)

    result = service.filter_projects(year="2026")

    assert [project.project_name for project in result] == ["A"]
    assert dashboard.calls == ["2026"]


def test_filter_projects_filters_by_project_state():
    service = ReportService(FakeDashboardService([
        _project("A", project_state=ProjectState.UAT_PREPARE),
        _project("B", project_state=ProjectState.PROD_READY),
    ]))

    result = service.filter_projects(project_state=ProjectState.PROD_READY)

    assert [project.project_name for project in result] == ["B"]


def test_filter_projects_filters_by_cr_state():
    service = ReportService(FakeDashboardService([
        _project("A", cr_state=CRState.APPROVED),
        _project("B", cr_state=CRState.FINISHED),
    ]))

    result = service.filter_projects(cr_state=CRState.FINISHED)

    assert [project.project_name for project in result] == ["B"]


def test_filter_projects_searches_name_cr_number_and_path_case_insensitive():
    service = ReportService(FakeDashboardService([
        _project("Alpha", cr_number="CR-123", path="/tmp/Projects/Alpha"),
        _project("Beta", cr_number="CR-999", path="/tmp/Projects/SpecialPath"),
    ]))

    assert [p.project_name for p in service.filter_projects(search="alpha")] == ["Alpha"]
    assert [p.project_name for p in service.filter_projects(search="cr-999")] == ["Beta"]
    assert [p.project_name for p in service.filter_projects(search="specialpath")] == ["Beta"]


def test_filter_projects_combines_filters():
    service = ReportService(FakeDashboardService([
        _project("A", year="2026", project_state=ProjectState.PROD_READY, cr_state=CRState.APPROVED),
        _project("B", year="2026", project_state=ProjectState.PROD_READY, cr_state=CRState.FINISHED),
        _project("C", year="2025", project_state=ProjectState.PROD_READY, cr_state=CRState.FINISHED),
    ]))

    result = service.filter_projects(
        year="2026",
        project_state=ProjectState.PROD_READY,
        cr_state=CRState.FINISHED,
        search="b",
    )

    assert [project.project_name for project in result] == ["B"]


def test_export_csv_writes_header_and_frontend_safe_rows():
    service = ReportService(FakeDashboardService([]))
    project = _project("A")

    csv_text = service.export_csv([project])

    assert csv_text.splitlines() == [
        "year,project_name,project_state,cr_number,cr_state,start_datetime,end_datetime,t10_status,drone_ticket_count,project_path",
        "2026,A,UAT_PREPARE,CR-1,APPROVED,2026-01-02T03:04:05+00:00,,READY,2,/tmp/2026/A",
    ]


def test_export_csv_escapes_commas_and_quotes():
    service = ReportService(FakeDashboardService([]))
    project = _project('A, "Quoted"', cr_number='CR,"1"')

    csv_text = service.export_csv([project])

    assert '"A, ""Quoted"""' in csv_text
    assert '"CR,""1"""' in csv_text


def test_export_csv_empty_result_exports_header_only():
    service = ReportService(FakeDashboardService([]))

    csv_text = service.export_csv([])

    assert csv_text == "year,project_name,project_state,cr_number,cr_state,start_datetime,end_datetime,t10_status,drone_ticket_count,project_path\r\n"


def test_filter_projects_does_not_mutate_dashboard_data():
    projects = [_project("A")]
    original = list(projects)
    service = ReportService(FakeDashboardService(projects))

    service.filter_projects(search="a")
    service.export_csv(projects)

    assert projects == original
