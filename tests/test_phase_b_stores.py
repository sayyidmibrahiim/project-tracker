from __future__ import annotations

import json
import types
from datetime import datetime, timezone
from pathlib import Path

from project_tracker.core.enums import CRState, ProjectState
from project_tracker.core.models import AppSettings, ProjectMetadata
from project_tracker.infrastructure import filesystem
from project_tracker.infrastructure.filesystem import ensure_year_structure, scan_year
from project_tracker.infrastructure.link_bank_store import LinkBank, LinkBankStore
from project_tracker.infrastructure.metadata_store import METADATA_FILE, MetadataStore
from project_tracker.infrastructure.settings_store import SETTINGS_FILE, SettingsStore


def test_metadata_store_missing_project_data_returns_default_with_folder_name(tmp_path: Path) -> None:
    project_path = tmp_path / "2026" / ProjectState.UAT_PREPARE.value / "PAYMENT_MODULE_UPGRADE"
    project_path.mkdir(parents=True)
    store = MetadataStore()

    metadata = store.read(project_path)

    assert metadata is not None
    assert metadata.project_name == "PAYMENT_MODULE_UPGRADE"
    assert store.warnings == [f"Missing project_data.json: {project_path}"]


def test_metadata_store_corrupt_json_returns_none_and_warning(tmp_path: Path) -> None:
    project_path = tmp_path / "2026" / ProjectState.UAT_PREPARE.value / "CORRUPT_PROJECT"
    project_path.mkdir(parents=True)
    metadata_path = project_path / METADATA_FILE
    metadata_path.write_text("{not json", encoding="utf-8")
    store = MetadataStore()

    metadata = store.read(project_path)

    assert metadata is None
    assert store.warnings == [f"Corrupt JSON: {metadata_path}"]


def test_metadata_store_write_does_not_persist_project_state(tmp_path: Path) -> None:
    project_path = tmp_path / "2026" / ProjectState.UAT_PREPARE.value / "NO_STATE_IN_JSON"
    metadata = ProjectMetadata(project_name="NO_STATE_IN_JSON", cr_state=CRState.APPROVED)
    store = MetadataStore()

    store.write(project_path, metadata)

    data = json.loads((project_path / METADATA_FILE).read_text(encoding="utf-8"))
    assert "project_state" not in data
    assert data["project_name"] == "NO_STATE_IN_JSON"
    assert data["cr_state"] == CRState.APPROVED.value


def test_metadata_store_write_uses_atomic_json_path_behavior(tmp_path: Path) -> None:
    project_path = tmp_path / "2026" / ProjectState.UAT_PREPARE.value / "ATOMIC_PROJECT"
    metadata = ProjectMetadata(project_name="ATOMIC_PROJECT")

    MetadataStore().write(project_path, metadata)

    assert (project_path / METADATA_FILE).exists()
    assert not (project_path / f"{METADATA_FILE}.tmp").exists()


def test_settings_store_corrupt_json_returns_default_and_warning(tmp_path: Path) -> None:
    settings_path = tmp_path / SETTINGS_FILE
    settings_path.write_text("{not json", encoding="utf-8")
    store = SettingsStore(config_dir=tmp_path)

    settings = store.read()

    assert isinstance(settings, AppSettings)
    assert settings.root_folder is None
    assert store.warnings == [f"Corrupt JSON: {settings_path}"]


def test_settings_store_write_read_round_trip(tmp_path: Path) -> None:
    root_folder = tmp_path / "CR"
    store = SettingsStore(config_dir=tmp_path)
    settings = AppSettings(root_folder=root_folder, display_name="Sayyid", t10_threshold_days=7)

    store.write(settings)
    loaded = store.read()

    assert loaded.root_folder == root_folder
    assert loaded.display_name == "Sayyid"
    assert loaded.t10_threshold_days == 7


def test_settings_store_config_path_behavior_is_platform_safe(tmp_path: Path) -> None:
    store = SettingsStore(config_dir=tmp_path)

    assert store.config_dir == tmp_path
    assert store.path == tmp_path / SETTINGS_FILE


def test_ensure_year_structure_creates_all_prd_folder_states(tmp_path: Path) -> None:
    root_folder = tmp_path / "CR"

    ensure_year_structure(root_folder, 2026)

    for state in ProjectState:
        assert (root_folder / "2026" / state.value).is_dir()


def test_scan_year_derives_year_and_folder_state_from_path(tmp_path: Path) -> None:
    root_folder = tmp_path / "CR"
    project_path = root_folder / "2026" / ProjectState.PROD_READY.value / "PAYMENT_MODULE_UPGRADE"
    MetadataStore().write(
        project_path,
        ProjectMetadata(project_name="PAYMENT_MODULE_UPGRADE", cr_state=CRState.APPROVED),
    )

    projects = scan_year(root_folder / "2026")

    assert len(projects) == 1
    assert projects[0].year == "2026"
    assert projects[0].project_state == ProjectState.PROD_READY
    assert projects[0].path == project_path


def test_scan_year_excludes_organizational_folders_from_subprojects(tmp_path: Path) -> None:
    root_folder = tmp_path / "CR"
    project_path = root_folder / "2026" / ProjectState.UAT_PREPARE.value / "PAYMENT_MODULE_UPGRADE"
    MetadataStore().write(project_path, ProjectMetadata(project_name="PAYMENT_MODULE_UPGRADE"))
    (project_path / "docs").mkdir()
    (project_path / "scripts").mkdir()
    (project_path / "APP_COMPONENT").mkdir()

    projects = scan_year(root_folder / "2026")

    assert len(projects) == 1
    assert projects[0].subproject_paths == [project_path / "APP_COMPONENT"]


def test_send_to_recycle_bin_uses_send2trash_with_string_path(tmp_path: Path, monkeypatch) -> None:
    calls: list[str] = []
    fake_module = types.SimpleNamespace(send2trash=lambda value: calls.append(value))
    monkeypatch.setitem(__import__("sys").modules, "send2trash", fake_module)
    target = tmp_path / "PROJECT"

    filesystem.send_to_recycle_bin(target)

    assert calls == [str(target)]


def test_open_folder_logs_dev_message_on_linux(tmp_path: Path, capsys) -> None:
    target = tmp_path / "PROJECT"

    filesystem.open_folder(target)

    assert capsys.readouterr().out == f"[DEV] Would open folder: {target}\n"


def test_link_bank_store_missing_file_returns_default(tmp_path: Path) -> None:
    store = LinkBankStore(tmp_path / "link_bank.json")

    bank = store.read()

    assert bank == LinkBank()
    assert store.warnings == []


def test_link_bank_store_corrupt_json_returns_default_and_warning(tmp_path: Path) -> None:
    path = tmp_path / "link_bank.json"
    path.write_text("{not json", encoding="utf-8")
    store = LinkBankStore(path)

    bank = store.read()

    assert bank == LinkBank()
    assert store.warnings == [f"Corrupt JSON: {path}"]


def test_link_bank_store_write_read_round_trip_current_schema(tmp_path: Path) -> None:
    path = tmp_path / "link_bank.json"
    bank = LinkBank(
        categories=["CR & ITSM Tools"],
        links=[
            {
                "name": "CR Portal",
                "url": "https://example.local/",
                "notes": "Daily CR work portal.",
                "category": "CR & ITSM Tools",
            }
        ],
    )

    LinkBankStore(path).write(bank)
    loaded = LinkBankStore(path).read()

    assert loaded == bank


def test_metadata_store_write_preserves_timezone_aware_datetimes(tmp_path: Path) -> None:
    project_path = tmp_path / "2026" / ProjectState.UAT_PREPARE.value / "DATED_PROJECT"
    start_datetime = datetime(2026, 6, 3, 10, 0, tzinfo=timezone.utc)
    metadata = ProjectMetadata(project_name="DATED_PROJECT", start_datetime=start_datetime)

    MetadataStore().write(project_path, metadata)
    loaded = MetadataStore().read(project_path)

    assert loaded is not None
    assert loaded.start_datetime == start_datetime
