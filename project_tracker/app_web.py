"""pywebview application bootstrap for the HTML/Tailwind frontend."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import webview


class AppAPI:
    """JavaScript bridge exposed as ``pywebview.api``."""

    def get_projects(self) -> list[dict[str, Any]]:
        """Return mock project data for the first HTML shell."""
        return [
            {
                "id": "cr-2026-001",
                "name": "Core Banking Refresh",
                "year": 2026,
                "state": "UAT_PREPARE",
                "owner": "DBS Operations",
            },
            {
                "id": "cr-2026-014",
                "name": "ATM Monitoring Drone",
                "year": 2026,
                "state": "PROD_READY",
                "owner": "Automation Squad",
            },
        ]

    def get_settings(self) -> dict[str, Any]:
        """Return mock settings data for bridge smoke testing."""
        return {
            "display_name": "Sayyid Ibrahim",
            "theme": "catppuccin-mocha",
            "root_folder": None,
        }


def run() -> None:
    """Create webview window and start pywebview on main thread."""
    frontend_path = Path(__file__).resolve().parent.parent / "frontend" / "index.html"
    webview.create_window(
        "Project Tracker DBS",
        frontend_path.as_uri(),
        js_api=AppAPI(),
        width=1200,
        height=760,
        min_size=(960, 640),
    )
    webview.start()


if __name__ == "__main__":
    run()
