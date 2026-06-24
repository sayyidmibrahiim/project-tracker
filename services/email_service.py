"""Email service — template rendering, condition evaluation, and email operations."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any

from pathlib import Path

from core.models import AppSettings, EmailCategorySettings, ProjectMetadata


@dataclass(slots=True)
class RenderedEmail:
    """Email with all placeholders substituted."""

    to: str
    cc: str
    subject: str
    body: str
    attachment_path: Path | None = None


class UnresolvedPlaceholderError(Exception):
    """Raised when a required placeholder cannot be resolved from project metadata.

    Per Requirement 8.5, composition is aborted and the unresolved placeholder(s)
    are named so the caller can surface ``ok=false`` identifying the placeholder.
    """

    def __init__(self, placeholders: list[str]) -> None:
        self.placeholders = list(placeholders)
        self.placeholder = self.placeholders[0] if self.placeholders else ""
        joined = ", ".join(self.placeholders)
        super().__init__(f"Unresolved required placeholder(s): {joined}")


class TemplateConditionsNotMetError(Exception):
    """Raised when a Template_Category's conditions are not satisfied.

    Per Requirement 8.6, composition is skipped and the reason is reported so the
    caller can return a skipped Bridge_Response.
    """

    def __init__(self, reason: str) -> None:
        self.reason = reason
        super().__init__(reason)


# Canonical Template_Category placeholders (Requirement 8.4). Each maps to a
# project-metadata-derived value; when a template references one of these and the
# resolved value is empty, the placeholder is treated as unresolved (Requirement 8.5).
REQUIRED_PLACEHOLDERS: tuple[str, ...] = (
    "{PROJECT_NAME}",
    "{CR_NUMBER}",
    "{CR_LINK}",
    "{CR_STATE}",
    "{DRONE_TICKET}",
    "{DRONE_LINK}",
    "{DRONE_STATE}",
    "{START_DATETIME}",
    "{END_DATETIME}",
    "{IMPLEMENTATION_PLAN}",
    "{DISPLAY_NAME}",
)


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

        The render follows the Requirement 8 contract:

        1. Evaluate the Template_Category conditions first; if they are not met,
           raise :class:`TemplateConditionsNotMetError` so composition is skipped
           (Requirement 8.6).
        2. Resolve every required placeholder (Requirement 8.4); if a required
           placeholder referenced by any template cannot be resolved from project
           metadata, raise :class:`UnresolvedPlaceholderError` naming it
           (Requirement 8.5).
        3. Substitute placeholders and return the rendered email.

        Args:
            metadata: Project metadata containing values for substitution.
            category: Email category with to/cc/subject/body templates.
            settings: App settings for user name and datetime formatting.

        Returns:
            RenderedEmail with all placeholders replaced.

        Raises:
            TemplateConditionsNotMetError: If the category conditions are unmet.
            UnresolvedPlaceholderError: If a required placeholder cannot resolve.
        """
        # 1. Conditions gate (Requirement 8.6).
        self._evaluate_conditions(metadata, category)

        templates = {
            "to": category.to,
            "cc": category.cc,
            "subject": category.subject_template,
            "body": category.body_template,
        }
        values = self._placeholder_values(metadata, settings)

        # 2. Required-placeholder resolution (Requirement 8.5).
        self._assert_placeholders_resolved(templates.values(), values)

        # 3. Substitute (Requirement 8.4).
        rendered = {key: self._substitute(text, values) for key, text in templates.items()}

        return RenderedEmail(
            to=rendered["to"],
            cc=rendered["cc"],
            subject=rendered["subject"],
            body=rendered["body"],
            attachment_path=None,
        )

    def _placeholder_values(
        self,
        metadata: ProjectMetadata,
        settings: AppSettings,
    ) -> dict[str, str]:
        """Resolve every placeholder token to its string value."""
        drone = metadata.drone_tickets[0] if metadata.drone_tickets else None
        start_str = self._format_datetime(metadata.start_datetime, settings)
        end_str = self._format_datetime(metadata.end_datetime, settings)
        display_name = settings.display_name or ""

        return {
            # Canonical Requirement 8.4 placeholders.
            "{PROJECT_NAME}": metadata.project_name or "",
            "{CR_NUMBER}": self._extract_cr_number(metadata.project_name),
            "{CR_LINK}": metadata.cr_link or "",
            "{CR_STATE}": metadata.cr_state.value,
            "{DRONE_TICKET}": (drone.subfolder_name or "") if drone else "",
            "{DRONE_LINK}": (drone.drone_link or "") if drone else "",
            "{DRONE_STATE}": drone.drone_state.value if drone else "",
            "{START_DATETIME}": start_str,
            "{END_DATETIME}": end_str,
            "{IMPLEMENTATION_PLAN}": metadata.implementation_plan or "",
            "{DISPLAY_NAME}": display_name,
            # Legacy aliases retained for backward compatibility with existing
            # configured templates; not part of the required-resolution check.
            "{SUBPROJECT_NAME}": "",
            "{START}": start_str,
            "{END}": end_str,
            "{USER}": display_name,
            "{YEAR}": self._extract_year(metadata.project_name),
        }

    def _assert_placeholders_resolved(
        self,
        templates: Any,
        values: dict[str, str],
    ) -> None:
        """Abort when a required placeholder used in a template resolves empty."""
        combined = "".join(str(text or "") for text in templates)
        unresolved = [
            placeholder
            for placeholder in REQUIRED_PLACEHOLDERS
            if placeholder in combined and not values.get(placeholder, "")
        ]
        if unresolved:
            raise UnresolvedPlaceholderError(unresolved)

    def _substitute(self, template: str, values: dict[str, str]) -> str:
        """Replace every placeholder token in a single template string."""
        result = template or ""
        for placeholder, value in values.items():
            result = result.replace(placeholder, value)
        return result

    def _evaluate_conditions(
        self,
        metadata: ProjectMetadata,
        category: EmailCategorySettings,
    ) -> None:
        """Evaluate Template_Category conditions; raise when any is unmet.

        Conditions reuse the ``{field, operator, value}`` shape used by the
        automation rules engine. All conditions must pass (logical AND).
        """
        if not category.conditions:
            return

        context = self._condition_context(metadata)
        for condition in category.conditions:
            if not isinstance(condition, dict):
                continue
            if not self._condition_passes(condition, context):
                field = str(condition.get("field", ""))
                operator = str(condition.get("operator", ""))
                value = condition.get("value", "")
                raise TemplateConditionsNotMetError(
                    f"Condition not met: {field} {operator} {value}".strip()
                )

    def _condition_context(self, metadata: ProjectMetadata) -> dict[str, str]:
        """Build the evaluation context from project metadata."""
        return {
            "project_name": metadata.project_name or "",
            "cr_number": self._extract_cr_number(metadata.project_name),
            "cr_link": metadata.cr_link or "",
            "cr_state": metadata.cr_state.value,
            "drone_count": str(len(metadata.drone_tickets)),
            "implementation_plan": metadata.implementation_plan or "",
        }

    @staticmethod
    def _condition_passes(condition: dict[str, Any], context: dict[str, str]) -> bool:
        """Evaluate a single condition against the context."""
        field = str(condition.get("field", ""))
        operator = str(condition.get("operator", "equals"))

        if operator == "exists":
            return field in context and context[field] != ""

        if field not in context:
            return False

        actual = context[field]
        expected = condition.get("value")

        if operator == "equals":
            return actual == str(expected)
        if operator == "not_equals":
            return actual != str(expected)
        if operator == "contains":
            return str(expected).casefold() in actual.casefold()

        # Unknown operator: treat as not satisfied rather than raising, so a
        # misconfigured condition skips composition instead of crashing.
        return False

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
