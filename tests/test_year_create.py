"""year_create bridge — create {root}/{year}/ + the five Folder_State folders (PRD §11.7)."""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path

from core.enums import ProjectState
from infrastructure.settings_store import SettingsStore


def _api_with_root(tmp_path: Path):
    from project_tracker import app_web

    root = tmp_path / "root"
    root.mkdir()
    settings = SettingsStore(config_dir=tmp_path / "config")
    settings.write(replace(settings.read(), root_folder=root))
    return app_web.create_js_api(settings_store=settings), root


def _api_no_root(tmp_path: Path):
    from project_tracker import app_web

    settings = SettingsStore(config_dir=tmp_path / "config")
    return app_web.create_js_api(settings_store=settings)


def test_year_create_makes_year_and_state_folders(tmp_path: Path) -> None:
    api, root = _api_with_root(tmp_path)
    result = api.year_create("2027")
    assert result["ok"] is True
    year_dir = root / "2027"
    assert year_dir.is_dir()
    for state in ProjectState:
        assert (year_dir / state.value).is_dir()
    assert "2027" in api.year_list()["data"]


def test_year_create_existing_folder_fails(tmp_path: Path) -> None:
    api, root = _api_with_root(tmp_path)
    (root / "2028").mkdir()
    result = api.year_create("2028")
    assert result["ok"] is False
    assert result["error"]["code"] == "YEAR_CREATE_FAILED"
    assert "already exists" in result["error"]["message"].lower()


def test_year_create_non_numeric_fails(tmp_path: Path) -> None:
    api, _ = _api_with_root(tmp_path)
    result = api.year_create("twenty")
    assert result["ok"] is False
    assert "numeric" in result["error"]["message"].lower()


def test_year_create_without_root_fails(tmp_path: Path) -> None:
    api = _api_no_root(tmp_path)
    result = api.year_create("2027")
    assert result["ok"] is False
    assert "root folder" in result["error"]["message"].lower()
