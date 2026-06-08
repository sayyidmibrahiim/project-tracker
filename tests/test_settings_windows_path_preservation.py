"""Windows path preservation for settings paths.

Validates Requirement 2.7: a path value that originates from Windows-formatted
settings must be preserved in its original Windows form (drive letter +
backslash separators) and must NOT be normalized/converted to a POSIX form.

All store I/O is confined to ``tmp_path``.
"""

from __future__ import annotations

import json
from pathlib import Path

from project_tracker.core.models import AppSettings
from project_tracker.infrastructure import settings_store as settings_store_module
from project_tracker.infrastructure.settings_store import SETTINGS_FILE, SettingsStore

# A representative Windows path: drive letter + backslash separators.
WINDOWS_ROOT = r"C:\Users\foo\Projects"
WINDOWS_SECOND_BRAIN = r"D:\Notes\Second Brain"
WINDOWS_TEMPLATES = r"C:\Users\foo\AppData\Roaming\Templates"


def test_appsettings_round_trip_preserves_windows_path_verbatim() -> None:
    """AppSettings.to_dict/from_dict keep the exact Windows path string."""
    settings = AppSettings(root_folder=Path(WINDOWS_ROOT))

    serialized = settings.to_dict()

    # Stored verbatim: drive letter + backslashes, no POSIX conversion.
    assert serialized["root_folder"] == WINDOWS_ROOT
    assert "\\" in serialized["root_folder"]
    assert "/" not in serialized["root_folder"]

    restored = AppSettings.from_dict(serialized)
    assert str(restored.root_folder) == WINDOWS_ROOT


def test_settings_store_persists_windows_paths_verbatim(tmp_path: Path, monkeypatch) -> None:
    """SettingsStore writes and reads Windows paths back verbatim via tmp_path.

    ``second_brain_folder`` and ``file_template_folder`` exercise the store
    without triggering any filesystem creation. ``root_folder`` would normally
    trigger ``ensure_year_structure``; that side effect is neutralized so the
    test only writes ``settings.json`` inside ``tmp_path``.
    """
    monkeypatch.setattr(
        settings_store_module,
        "ensure_year_structure",
        lambda *args, **kwargs: None,
        raising=False,
    )
    # Patch the source attribute too, since write() imports it lazily.
    import project_tracker.infrastructure.filesystem as filesystem_module

    monkeypatch.setattr(
        filesystem_module,
        "ensure_year_structure",
        lambda *args, **kwargs: None,
    )

    store = SettingsStore(config_dir=tmp_path)
    settings = AppSettings(
        root_folder=Path(WINDOWS_ROOT),
        second_brain_folder=Path(WINDOWS_SECOND_BRAIN),
        file_template_folder=Path(WINDOWS_TEMPLATES),
    )

    store.write(settings)
    loaded = store.read()

    # Read back verbatim, drive letter and backslashes intact.
    assert str(loaded.root_folder) == WINDOWS_ROOT
    assert str(loaded.second_brain_folder) == WINDOWS_SECOND_BRAIN
    assert str(loaded.file_template_folder) == WINDOWS_TEMPLATES


def test_settings_json_on_disk_keeps_backslashes_and_drive_letter(tmp_path: Path, monkeypatch) -> None:
    """The persisted JSON must contain Windows separators, not POSIX ones."""
    import project_tracker.infrastructure.filesystem as filesystem_module

    monkeypatch.setattr(filesystem_module, "ensure_year_structure", lambda *args, **kwargs: None)

    store = SettingsStore(config_dir=tmp_path)
    store.write(
        AppSettings(
            root_folder=Path(WINDOWS_ROOT),
            second_brain_folder=Path(WINDOWS_SECOND_BRAIN),
        )
    )

    raw = json.loads((tmp_path / SETTINGS_FILE).read_text(encoding="utf-8"))

    assert raw["root_folder"] == WINDOWS_ROOT
    assert raw["second_brain_folder"] == WINDOWS_SECOND_BRAIN
    # No POSIX normalization: original backslashes preserved, no forward slashes.
    assert "\\" in raw["root_folder"]
    assert "/" not in raw["root_folder"]
    assert raw["root_folder"].startswith("C:\\")
