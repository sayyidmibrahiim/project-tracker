from __future__ import annotations

import json
import os
import sys
from json import JSONDecodeError
from pathlib import Path
from typing import Any

from project_tracker.core.models import AppSettings
from project_tracker.infrastructure.metadata_store import atomic_write_json

APP_NAME = "ProjectTrackerDBS"
SETTINGS_FILE = "settings.json"
LINK_BANK_FILE = "link_bank.json"


def app_config_dir() -> Path:
    if sys.platform == "win32":
        appdata = os.environ.get("APPDATA")
        if appdata:
            return Path(appdata) / APP_NAME
    return Path.home() / APP_NAME


def link_bank_path(config_dir: Path | None = None) -> Path:
    return (config_dir or app_config_dir()) / LINK_BANK_FILE


class SettingsStore:
    def __init__(self, config_dir: Path | None = None) -> None:
        self.config_dir = config_dir or app_config_dir()
        self.path = self.config_dir / SETTINGS_FILE
        self.warnings: list[str] = []

    def read(self) -> AppSettings:
        if not self.path.exists():
            return AppSettings()

        try:
            with self.path.open("r", encoding="utf-8") as file:
                data: dict[str, Any] = json.load(file)
        except JSONDecodeError:
            self.warnings.append(f"Corrupt JSON: {self.path}")
            return AppSettings()

        return AppSettings.from_dict(data)

    def write(self, settings: AppSettings) -> None:
        atomic_write_json(self.path, settings.to_dict())
        if settings.root_folder is not None:
            from datetime import datetime

            from project_tracker.infrastructure.filesystem import ensure_year_structure

            ensure_year_structure(settings.root_folder, datetime.now().year)

    def ensure_exists(self) -> AppSettings:
        settings = self.read()
        if not self.path.exists():
            self.write(settings)
        return settings

    load = read
    save = write
