"""Phase C.5e — JsApi scanner facade tests (TDD: RED first)."""

from dataclasses import dataclass
from pathlib import Path

from project_tracker.web.js_api import JsApi


@dataclass(frozen=True)
class FakeScanResult:
    year: str
    project_count: int
    warnings: list[str]


class FakeScannerService:
    def __init__(self) -> None:
        self.called_with: Path | None = None

    def rebuild_year(self, year_path: Path) -> FakeScanResult:
        self.called_with = year_path
        return FakeScanResult(year="2026", project_count=2, warnings=["warn"])


class ExplodingScannerService:
    def rebuild_year(self, year_path: Path) -> FakeScanResult:
        raise RuntimeError("scan unavailable")


def test_scanner_rebuild_year_converts_path_and_returns_result_dict():
    service = FakeScannerService()
    api = JsApi(dashboard_service=None, scanner_service=service)

    response = api.scanner_rebuild_year("/tmp/projects/2026")

    assert response == {
        "ok": True,
        "data": {"year": "2026", "project_count": 2, "warnings": ["warn"]},
        "error": None,
    }
    assert service.called_with == Path("/tmp/projects/2026")


def test_scanner_rebuild_year_exception_returns_fail():
    api = JsApi(dashboard_service=None, scanner_service=ExplodingScannerService())

    response = api.scanner_rebuild_year("/tmp/projects/2026")

    assert response == {
        "ok": False,
        "data": None,
        "error": {
            "code": "SCANNER_REBUILD_YEAR_FAILED",
            "message": "scan unavailable",
            "details": None,
        },
    }
