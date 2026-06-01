from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from project_tracker.core.models import ProjectMetadata

ORGANIZATIONAL_FOLDERS = frozenset({
    "doc", "docs", "document", "documents",
    "bak", "backup", "before", "after",
    "script", "scripts", "cicd",
    "log", "logs", "temp", "tmp", "archive",
})


@dataclass(slots=True)
class ScanWarning:
    project_path: Path
    message: str


def is_organizational_folder(path: Path) -> bool:
    return path.name.casefold() in ORGANIZATIONAL_FOLDERS


def discover_subproject_folders(project_path: Path) -> list[Path]:
    if not project_path.exists():
        return []
    return sorted(
        path for path in project_path.iterdir()
        if path.is_dir() and not is_organizational_folder(path)
    )


def validate_drone_subfolders(project_path: Path, metadata: ProjectMetadata) -> list[ScanWarning]:
    warnings: list[ScanWarning] = []
    for ticket in metadata.drone_tickets:
        if not ticket.subfolder_name:
            continue
        if not (project_path / ticket.subfolder_name).is_dir():
            warnings.append(
                ScanWarning(
                    project_path=project_path,
                    message=f"Drone subfolder not found: {ticket.subfolder_name}",
                )
            )
    return warnings
