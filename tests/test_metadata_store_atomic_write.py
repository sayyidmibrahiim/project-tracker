"""Unit tests for atomic-write failure preservation in metadata_store.

Covers Requirements 2.4, 2.5, 2.10:
- temp-file-then-replace atomic write,
- failure before replace preserves the existing target unchanged + raises,
- project_state is never serialized into project_data.json.

All filesystem activity is confined to pytest's tmp_path (Temp_Root).
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from core.exceptions import AtomicWriteError
from core.models import ProjectMetadata
from infrastructure.metadata_store import (
    METADATA_FILE,
    MetadataStore,
    atomic_write_json,
)


def test_atomic_write_replaces_target_on_success(tmp_path: Path) -> None:
    target = tmp_path / "store.json"

    atomic_write_json(target, {"value": 1})

    assert json.loads(target.read_text(encoding="utf-8")) == {"value": 1}
    # The temp file is consumed by the replace step.
    assert not target.with_name(f"{target.name}.tmp").exists()


def test_atomic_write_failure_preserves_existing_target(tmp_path: Path) -> None:
    target = tmp_path / "store.json"
    atomic_write_json(target, {"value": "original"})

    # A set is not JSON-serializable, so json.dump fails before the replace.
    with pytest.raises(AtomicWriteError):
        atomic_write_json(target, {"value": {1, 2, 3}})

    # The original target is left unchanged.
    assert json.loads(target.read_text(encoding="utf-8")) == {"value": "original"}
    # No partial temp file is left behind.
    assert not target.with_name(f"{target.name}.tmp").exists()


def test_atomic_write_failure_does_not_create_missing_target(tmp_path: Path) -> None:
    target = tmp_path / "store.json"

    with pytest.raises(AtomicWriteError):
        atomic_write_json(target, {"value": {1, 2, 3}})

    # A failed write must not leave a target or temp file behind.
    assert not target.exists()
    assert not target.with_name(f"{target.name}.tmp").exists()


def test_metadata_store_write_never_serializes_project_state(tmp_path: Path) -> None:
    project_path = tmp_path / "2026" / "UAT_PREPARE" / "PROJECT_A"
    metadata = ProjectMetadata(project_name="PROJECT_A")

    MetadataStore().write(project_path, metadata)

    raw = json.loads((project_path / METADATA_FILE).read_text(encoding="utf-8"))
    assert "project_state" not in raw
