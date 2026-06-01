"""Email service — template rendering and email operations."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from project_tracker.core.enums import CRState, DroneState
from project_tracker.core.models import AppSettings, EmailCategorySettings, ProjectMetadata


@dataclass(slots=True)
class RenderedEmail:
    """Email with all placeholders substituted."""

    to: str
    cc: str
    subject: str
    body: str
    attachment_path: Path | None = None


class EmailService:
    """Service for email template rendering and sending."""

    def __init__(self) -> None:
        self._settings = AppSettings()

    def set_settings(self, settings: AppSettings) -> None:
        """Set application settings for rendering."""
        self._settings = settings

    def render_email_template(
        self,
        metadata: ProjectMetadata,
        category: EmailCategorySettings,
        settings: AppSettings,
    ) -> RenderedEmail:
        """Render email template with all placeholders substituted.

        Args:
            metadata: Project metadata containing values for substitution.
            category: Email category with to/cc/subject/body templates.
            settings: App settings for user name and datetime formatting.

        Returns:
            RenderedEmail with all placeholders replaced.
        """
        to = self._render_template(category.to, metadata, settings)
        cc = self._render_template(category.cc, metadata, settings)
        subject = self._render_template(category.subject_template, metadata, settings)
        body = self._render_template(category.body_template, metadata, settings)

        return RenderedEmail(
            to=to,
            cc=cc,
            subject=subject,
            body=body,
            attachment_path=None,
        )

    def _render_template(
        self,
        template: str,
        metadata: ProjectMetadata,
        settings: AppSettings,
    ) -> str:
        """Render a single template string with placeholders substituted."""
        result = template

        # Project name
        result = result.replace("{PROJECT_NAME}", metadata.project_name or "")

        # Subproject name (empty if no subproject selected)
        result = result.replace("{SUBPROJECT_NAME}", "")

        # CR number (extract from project name if possible)
        cr_number = self._extract_cr_number(metadata.project_name)
        result = result.replace("{CR_NUMBER}", cr_number)

        # CR link
        result = result.replace("{CR_LINK}", metadata.cr_link or "")

        # Drone ticket info (use first drone ticket if exists)
        if metadata.drone_tickets:
            drone = metadata.drone_tickets[0]
            result = result.replace("{DRONE_TICKET}", drone.subfolder_name or "")
            result = result.replace("{DRONE_LINK}", drone.drone_link or "")
        else:
            result = result.replace("{DRONE_TICKET}", "")
            result = result.replace("{DRONE_LINK}", "")

        # Datetime placeholders
        start_str = self._format_datetime(metadata.start_datetime, settings)
        end_str = self._format_datetime(metadata.end_datetime, settings)
        result = result.replace("{START}", start_str)
        result = result.replace("{END}", end_str)

        # CR state
        result = result.replace("{CR_STATE}", metadata.cr_state.value)

        # Drone state (use first drone ticket if exists)
        if metadata.drone_tickets:
            result = result.replace("{DRONE_STATE}", metadata.drone_tickets[0].drone_state.value)
        else:
            result = result.replace("{DRONE_STATE}", "")

        # Year (extract from project name if possible)
        year = self._extract_year(metadata.project_name)
        result = result.replace("{YEAR}", year)

        # User (display name)
        result = result.replace("{USER}", settings.display_name or "")

        # Implementation plan
        result = result.replace("{IMPLEMENTATION_PLAN}", metadata.implementation_plan or "")

        return result

    def _format_datetime(self, dt: datetime | None, settings: AppSettings) -> str:
        """Format datetime using settings format or default."""
        if dt is None:
            return ""
        fmt = settings.datetime_format or "ddd, dd MMM yyyy HH:mm"
        # Convert common Qt-style format to Python strftime
        # This is a simple mapping; full Qt format support would need more logic
        python_fmt = fmt
        python_fmt = python_fmt.replace("ddd", "%a")
        python_fmt = python_fmt.replace("dd", "%d")
        python_fmt = python_fmt.replace("MMM", "%b")
        python_fmt = python_fmt.replace("yyyy", "%Y")
        python_fmt = python_fmt.replace("HH", "%H")
        python_fmt = python_fmt.replace("mm", "%M")
        return dt.strftime(python_fmt)

    def _extract_cr_number(self, project_name: str) -> str:
        """Extract CR number from project name like 'CR-2026-001'."""
        if not project_name:
            return ""
        parts = project_name.split("-")
        if len(parts) >= 3:
            return "-".join(parts[1:])  # Return "2026-001"
        return project_name

    def _extract_year(self, project_name: str) -> str:
        """Extract year from project name like 'CR-2026-001'."""
        if not project_name:
            return ""
        parts = project_name.split("-")
        if len(parts) >= 2:
            return parts[1]  # Return "2026"
        return ""
