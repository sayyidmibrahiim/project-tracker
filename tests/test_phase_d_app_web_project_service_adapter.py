"""Phase D-pre.2: ProjectService adapter for app_web JsApi factory.

TDD RED: these tests fail because create_js_api() leaves project_service
None, causing JsApi.project_list() to return SERVICE_UNAVAILABLE.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pytest


# ── Fixture: create_js_api ────────────────────────────────────────────────

@pytest.fixture
def js_api_with_project():
    """Return JsApi from app_web.create_js_api()."""
    from project_tracker import app_web

    return app_web.create_js_api()


# ── RED 1: factory wires project_service ──────────────────────────────────

def test_create_js_api_has_project_service_attr():
    """create_js_api() must set _project_service on JsApi (not None)."""
    from project_tracker import app_web

    api = app_web.create_js_api()
    assert api._project_service is not None, (
        "JsApi._project_service must not be None after create_js_api()"
    )


# ── RED 2: project_list returns ok ────────────────────────────────────────

def test_project_list_returns_ok_with_cache(js_api_with_project):
    """api.project_list() returns ok when dashboard cache has data."""
    result = js_api_with_project.project_list()
    assert isinstance(result, dict)
    assert result.get("ok") is True, (
        f"project_list() must return ok=True, got {result}"
    )


# ── RED 3: project_list delegates to dashboard service ────────────────────

def test_project_list_delegates_to_dashboard_service():
    """project_list(year) delegates to DashboardService.list_projects(year)."""
    from project_tracker import app_web
    from services.dashboard_service import DashboardProject

    # Inject dashboard service with known data
    fake_project = DashboardProject(
        project_path=Path("/tmp/root/2024/UAT_PREPARE/my-project"),
        year="2024",
        project_name="my-project",
        project_state=None,  # type: ignore[arg-type]
        cr_number="CR123",
        cr_link="http://cr.example.com/CR123",
        cr_state=None,  # type: ignore[arg-type]
        cr_pending_approval_at=None,
        start_datetime=None,
        end_datetime=None,
        t10_status="pending",
        drone_ticket_count=0,
        updated_at=None,
        scanned_at=None,
    )

    @dataclass
    class FakeDashboardService:
        _projects: list[DashboardProject]

        def list_projects(self, year: str | None = None) -> list[DashboardProject]:
            if year is None or year == "2024":
                return self._projects
            return []

        def get_summary(self, year: str | None = None) -> object:
            return {"state_counts": {}}

        def get_dashboard(self, year: str | None = None) -> object:
            return {"projects": self.list_projects(year), "summary": self.get_summary(year)}

    fake_dashboard = FakeDashboardService(_projects=[fake_project])
    api = app_web.create_js_api(_dashboard_service=fake_dashboard)

    result = api.project_list(year="2024")
    assert result.get("ok") is True, f"project_list failed: {result}"
    assert result.get("data") is not None
    data = result["data"]
    assert isinstance(data, list), f"expected list, got {type(data)}"
    assert len(data) == 1
    first = data[0]
    assert first.get("project_name") == "my-project" or first.get("name") == "my-project"
    assert first.get("year") == "2024"


# ── RED 4: unsupported mutation returns controlled error ──────────────────

def test_unsupported_project_create_returns_fail(js_api_with_project):
    """api.project_create() returns fail with SERVICE_UNAVAILABLE or similar."""
    result = js_api_with_project.project_create({"name": "test"})
    assert isinstance(result, dict)
    assert result.get("ok") is False
    assert result.get("error") is not None


def test_unsupported_project_update_returns_fail(js_api_with_project):
    """api.project_update() returns fail with controlled error."""
    result = js_api_with_project.project_update("/some/path", {"name": "x"})
    assert isinstance(result, dict)
    assert result.get("ok") is False
    assert result.get("error") is not None


# ── RED 5: import safety ──────────────────────────────────────────────────

def test_app_web_import_is_linux_safe():
    """app_web.py must import without crash on Linux."""
    from project_tracker import app_web  # noqa: F401


# ── RED 6: adapter lists projects even with no data ────────────────────────

def test_project_list_returns_empty_ok(js_api_with_project):
    """project_list with no data returns ok with empty list, not crash."""
    result = js_api_with_project.project_list(year="9999")
    assert isinstance(result, dict)
    assert result.get("ok") is True, f"project_list(NonexistentYear) must return ok=True: {result}"
    assert isinstance(result.get("data"), list), f"data must be list: {result}"
