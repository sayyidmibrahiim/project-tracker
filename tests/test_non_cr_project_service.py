"""Tests for Non-CR project service: set_non_cr_state + path helpers."""
import pytest
from pathlib import Path

from core.enums import NonCrState, ProjectType
from core.models import ProjectMetadata, AppSettings
from infrastructure.metadata_store import MetadataStore
from services.project_service import ProjectService


def _make_non_cr_project(tmp_path):
    appcode = tmp_path / "MYAPP"
    project = appcode / "2026" / "Non-CR" / "MyTask"
    project.mkdir(parents=True)
    store = MetadataStore()
    meta = ProjectMetadata(
        project_name="MyTask",
        project_type=ProjectType.NON_CR,
        non_cr_state=NonCrState.PLANNING,
    )
    store.save(project, meta)
    return project


def test_set_non_cr_state_planning_to_in_progress(tmp_path):
    project = _make_non_cr_project(tmp_path)
    svc = ProjectService()
    svc.set_non_cr_state(project, NonCrState.IN_PROGRESS, AppSettings())
    meta = svc.metadata_store.load(project)
    assert meta.non_cr_state == NonCrState.IN_PROGRESS
    assert len(meta.history) == 1
    assert "PLANNING" in meta.history[0].detail
    assert "IN_PROGRESS" in meta.history[0].detail


def test_set_non_cr_state_invalid_transition_raises(tmp_path):
    project = _make_non_cr_project(tmp_path)
    svc = ProjectService()
    meta = svc.metadata_store.load(project)
    meta.non_cr_state = NonCrState.DONE
    svc.metadata_store.save(project, meta)
    with pytest.raises(Exception):
        svc.set_non_cr_state(project, NonCrState.PLANNING, AppSettings())


def test_set_non_cr_state_on_cr_project_raises(tmp_path):
    appcode = tmp_path / "MYAPP"
    project = appcode / "2026" / "CR" / "UAT_PREPARE" / "MyCR"
    project.mkdir(parents=True)
    store = MetadataStore()
    store.save(project, ProjectMetadata(project_name="MyCR", project_type=ProjectType.CR))
    svc = ProjectService()
    with pytest.raises(ValueError, match="CR project"):
        svc.set_non_cr_state(project, NonCrState.IN_PROGRESS, AppSettings())
