import pytest

from infrastructure.filesystem import _scaffold_drone


def test_scaffold_drone_creates_uat_prd_notes(tmp_path):
    project = tmp_path / "MyProject"
    project.mkdir()
    drone = _scaffold_drone(project, "api-module")
    assert drone.is_dir()
    assert (drone / "UAT").is_dir()
    assert (drone / "PRD").is_dir()
    assert (drone / "notes.md").is_file()


def test_scaffold_drone_rejects_duplicate(tmp_path):
    project = tmp_path / "MyProject"
    project.mkdir()
    _scaffold_drone(project, "api")
    with pytest.raises(ValueError, match="already exists"):
        _scaffold_drone(project, "api")


def test_scaffold_drone_rejects_cr_docs_name(tmp_path):
    project = tmp_path / "MyProject"
    project.mkdir()
    with pytest.raises(ValueError):
        _scaffold_drone(project, "_cr-docs")
