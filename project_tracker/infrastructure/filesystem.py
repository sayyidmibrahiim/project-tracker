from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from project_tracker.core.enums import ProjectState
from project_tracker.core.models import ProjectMetadata
from project_tracker.core.rules import is_organizational_folder
from project_tracker.infrastructure.metadata_store import MetadataStore


@dataclass(frozen=True, slots=True)
class ScannedProject:
    path: Path
    year: str
    project_state: ProjectState
    metadata: ProjectMetadata
    subproject_paths: list[Path]


STATE_FOLDER_NAMES = tuple(state.value for state in ProjectState)


def ensure_year_structure(root_folder: Path, year: int) -> None:
    """Create root_folder / year / state subfolders if they don't exist."""
    year_path = root_folder / str(year)
    for state_name in STATE_FOLDER_NAMES:
        (year_path / state_name).mkdir(parents=True, exist_ok=True)


def state_folders_for_year(year_path: Path) -> list[Path]:
    folders = [year_path / state_name for state_name in STATE_FOLDER_NAMES]
    for folder in folders:
        folder.mkdir(parents=True, exist_ok=True)
    return folders


def scan_year(year_path: Path, metadata_store: MetadataStore | None = None) -> list[ScannedProject]:
    store = metadata_store or MetadataStore()
    projects: list[ScannedProject] = []
    if not year_path.exists():
        return projects

    for state in ProjectState:
        state_path = year_path / state.value
        if not state_path.is_dir():
            continue
        for project_path in sorted(child for child in state_path.iterdir() if child.is_dir()):
            metadata = store.read(project_path)
            if metadata is None:
                continue
            projects.append(
                ScannedProject(
                    path=project_path,
                    year=year_path.name,
                    project_state=state,
                    metadata=metadata,
                    subproject_paths=discover_subproject_paths(project_path),
                )
            )
    return projects


def discover_subproject_paths(project_path: Path) -> list[Path]:
    return sorted(
        child
        for child in project_path.iterdir()
        if child.is_dir() and not is_organizational_folder(child)
    )
