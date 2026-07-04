import pytest

from infrastructure.filesystem import (
    _scaffold_drone,
    discover_drone_paths,
    discover_subproject_paths,
)


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


def test_dot_folders_are_never_drones(tmp_path):
    """RTE sidecar dirs (.rte) and other dot-folders must not be drone candidates."""
    project = tmp_path / "MyProject"
    project.mkdir()
    (project / ".rte").mkdir()
    (project / ".git").mkdir()
    (project / "real-drone").mkdir()
    assert discover_drone_paths(project) == [project / "real-drone"]
    assert discover_subproject_paths(project) == [project / "real-drone"]


def test_scaffold_drone_rejects_dot_names(tmp_path):
    project = tmp_path / "MyProject"
    project.mkdir()
    with pytest.raises(ValueError):
        _scaffold_drone(project, ".rte")
