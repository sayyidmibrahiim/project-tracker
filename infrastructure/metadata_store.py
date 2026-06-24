from __future__ import annotations

import json
from json import JSONDecodeError
from pathlib import Path
from typing import Any

from core.exceptions import AtomicWriteError
from core.models import PROJECT_DATA_SCHEMA, ProjectMetadata

METADATA_FILE = "project_data.json"


def atomic_write_json(path: Path, data: dict[str, Any]) -> None:
    """Write JSON atomically: serialize to a temp file in the same directory,
    then atomically replace the target.

    If the write fails before the replace step completes, the existing target
    file is left unchanged, the partial temp file is removed, and an
    AtomicWriteError is raised to indicate the write did not complete.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = path.with_name(f"{path.name}.tmp")
    try:
        with temp_path.open("w", encoding="utf-8") as file:
            json.dump(data, file, ensure_ascii=False, indent=2)
            file.write("\n")
        temp_path.replace(path)
    except Exception as exc:
        # The write did not reach the atomic replace, so the existing target
        # file is preserved unchanged. Clean up the partial temp file and
        # surface an explicit error indicating the write did not complete.
        try:
            temp_path.unlink()
        except OSError:
            pass
        raise AtomicWriteError(
            f"Atomic write to {path} did not complete; target left unchanged"
        ) from exc


class MetadataStore:
    def __init__(self) -> None:
        self.warnings: list[str] = []

    def read(self, project_path: Path) -> ProjectMetadata | None:
        metadata_path = project_path / METADATA_FILE
        if not metadata_path.exists():
            self.warnings.append(f"Missing project_data.json: {project_path}")
            return ProjectMetadata(project_name=project_path.name)

        try:
            with metadata_path.open("r", encoding="utf-8") as file:
                data = json.load(file)
        except JSONDecodeError:
            self.warnings.append(f"Corrupt JSON: {metadata_path}")
            return None

        if not isinstance(data, dict):
            self.warnings.append(f"Corrupt JSON: {metadata_path}")
            return None

        schema = data.get("$schema", PROJECT_DATA_SCHEMA)
        if schema != PROJECT_DATA_SCHEMA:
            self.warnings.append(f"Unknown schema {schema}: {metadata_path}")
            return None

        metadata = ProjectMetadata.from_dict(data)
        if not metadata.project_name:
            metadata.project_name = project_path.name
        return metadata

    def write(self, project_path: Path, metadata: ProjectMetadata) -> None:
        data = metadata.to_dict()
        data.pop("project_state", None)
        atomic_write_json(project_path / METADATA_FILE, data)

    load = read
    save = write
