from pathlib import Path

import pytest

from project_tracker.core.enums import CRState, ProjectState
from project_tracker.core.exceptions import InvalidTransitionError
from project_tracker.core.models import AppSettings, ProjectMetadata
from project_tracker.infrastructure.metadata_store import MetadataStore
from project_tracker.services.project_service import ProjectService


def create_project(tmp_path: Path, folder_state: ProjectState, cr_state: CRState) -> Path:
    project_path = tmp_path / "2026" / folder_state.value / "PROJECT_A"
    project_path.mkdir(parents=True)
    MetadataStore().save(
        project_path,
        ProjectMetadata(
            project_name="PROJECT_A",
            cr_state=cr_state,
        ),
    )
    return project_path


def test_reopen_project_from_postponed_moves_folder_to_uat_prepare_and_resets_cr_state(tmp_path: Path) -> None:
    project_path = create_project(tmp_path, ProjectState.POSTPONED, CRState.POSTPONED)
    service = ProjectService(MetadataStore())

    moved_path = service.reopen_project(project_path, AppSettings(display_name="Tester"))

    assert moved_path == tmp_path / "2026" / "UAT_PREPARE" / "PROJECT_A"
    assert not project_path.exists()
    saved_metadata = MetadataStore().load(moved_path)
    assert saved_metadata is not None
    assert saved_metadata.cr_state == CRState.PENDING_SUBMISSION
    assert saved_metadata.cr_state != CRState.REOPEN
    assert saved_metadata.cr_state_updated_at is not None
    assert saved_metadata.updated_at is not None
    assert saved_metadata.history[-1].action == "REOPEN"
    assert saved_metadata.history[-1].detail == "REOPEN: project moved from POSTPONED to UAT_PREPARE"


def test_reopen_project_from_canceled_moves_folder_to_uat_prepare_and_resets_cr_state(tmp_path: Path) -> None:
    project_path = create_project(tmp_path, ProjectState.CANCELED, CRState.CANCELED)
    service = ProjectService(MetadataStore())

    moved_path = service.reopen_project(project_path, AppSettings(display_name="Tester"))

    assert moved_path == tmp_path / "2026" / "UAT_PREPARE" / "PROJECT_A"
    assert not project_path.exists()
    saved_metadata = MetadataStore().load(moved_path)
    assert saved_metadata is not None
    assert saved_metadata.cr_state == CRState.PENDING_SUBMISSION
    assert saved_metadata.cr_state != CRState.REOPEN
    assert saved_metadata.history[-1].action == "REOPEN"
    assert saved_metadata.history[-1].detail == "REOPEN: project moved from CANCELED to UAT_PREPARE"


def test_reopen_project_from_uat_prepare_is_rejected(tmp_path: Path) -> None:
    project_path = create_project(tmp_path, ProjectState.UAT_PREPARE, CRState.PENDING_SUBMISSION)
    service = ProjectService(MetadataStore())

    with pytest.raises(InvalidTransitionError, match="REOPEN"):
        service.reopen_project(project_path, AppSettings(display_name="Tester"))
