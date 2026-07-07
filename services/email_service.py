"""Email service — template rendering, condition evaluation, and email operations."""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, fields
from datetime import datetime
from typing import Any

from pathlib import Path

from core.models import AppSettings, DroneTicket, EmailCategorySettings, ProjectMetadata

_log = logging.getLogger(__name__)


@dataclass(slots=True)
class RenderedEmail:
    """Email with all placeholders substituted."""

    to: str
    cc: str
    subject: str
    body: str
    attachment_path: Path | None = None


# Token regex: {NAME} or {NESTED.0.FIELD} — uppercase letters, digits, dots.
_TOKEN_RE = re.compile(r"\{([A-Z][A-Z0-9_]*(?:\.[A-Z0-9_]+)*)\}")


class PlaceholderResolver:
    """Reflective placeholder resolver over ProjectMetadata / DroneTicket / AppSettings.

    Replaces the hard-coded ``_placeholder_values`` 11-token map with discovery
    via :func:`dataclasses.fields`. Supports::

        {PROJECT_NAME}          flat field on metadata / settings
        {DRONE.LINK}            nested -> metadata.drone_tickets[0].drone_link
        {DRONE.0.LINK}          indexed -> metadata.drone_tickets[0].drone_link
        {SETTINGS.DISPLAY_NAME} explicit settings prefix

    The 11 legacy ``REQUIRED_PLACEHOLDERS`` tokens are preserved as aliases so
    existing configured templates keep rendering unchanged. ``resolve`` returns
    ``(resolved_text, unresolved_tokens)``; :meth:`assert_required_resolved`
    raises :class:`UnresolvedPlaceholderError` for required tokens referenced
    but empty (Requirement 8.5 contract kept).
    """

    # Canonical required tokens (legacy aliases). Each maps to a dotted path or
    # a resolver callable. Required = subject to the Resolution-8.5 abort.
    LEGACY_ALIASES: dict[str, str] = {
        "{PROJECT_NAME}": "project_name",
        "{CR_NUMBER}": "@cr_number",
        "{CR_LINK}": "cr_link",
        "{CR_STATE}": "@cr_state_value",
        "{DRONE_TICKET}": "@drone.subfolder_name",
        "{DRONE_LINK}": "@drone.drone_link",
        "{DRONE_STATE}": "@drone.drone_state_value",
        "{START_DATETIME}": "@start_str",
        "{END_DATETIME}": "@end_str",
        "{IMPLEMENTATION_PLAN}": "implementation_plan",
        "{DISPLAY_NAME}": "@display_name",
    }
    # Non-required legacy aliases (never abort, just substitute).
    LEGACY_OPTIONAL: dict[str, str] = {
        "{SUBPROJECT_NAME}": "@empty",
        "{START}": "@start_str",
        "{END}": "@end_str",
        "{USER}": "@display_name",
        "{YEAR}": "@year",
    }
    # Token-part -> DroneTicket field name (token parts are uppercased field
    # names, but DroneTicket fields carry a ``drone_`` prefix for some attrs).
    DRONE_FIELD_ALIASES: dict[str, str] = {
        "LINK": "drone_link",
        "STATE": "drone_state",
        "STATE_UPDATED_AT": "drone_state_updated_at",
        "TICKET": "subfolder_name",
        "SUBFOLDER": "subfolder_name",
        "SUBFOLDER_NAME": "subfolder_name",
        "OWNER": "owner",
    }

    def __init__(
        self,
        metadata: ProjectMetadata,
        settings: AppSettings,
        extra_context: dict[str, object] | None = None,
    ) -> None:
        self._metadata = metadata
        self._settings = settings
        self._extra = dict(extra_context or {})
        self._email_service = EmailService()  # reuse _format_datetime / _extract_*

    # -- public API ---------------------------------------------------------

    def resolve(self, template_text: str) -> tuple[str, list[str]]:
        """Return ``(resolved_text, unresolved_tokens)`` for ``template_text``.

        Unresolved tokens are ``{...}`` whose path is unknown (not just empty);
        they are left in place in the text and reported in the list. An empty
        but known value substitutes to "".
        """
        text = template_text or ""
        unresolved: list[str] = []
        out_parts: list[str] = []
        last = 0
        for m in _TOKEN_RE.finditer(text):
            out_parts.append(text[last : m.start()])
            token = m.group(0)
            value, ok = self._lookup(token)
            if ok:
                out_parts.append(value)
            else:
                out_parts.append(token)  # leave marker, report unknown
                unresolved.append(token)
            last = m.end()
        out_parts.append(text[last:])
        return "".join(out_parts), unresolved

    def assert_required_resolved(self, templates: Any) -> None:
        """Raise :class:`UnresolvedPlaceholderError` if a required token is
        referenced but resolves empty (Requirement 8.5)."""
        combined = "".join(str(t or "") for t in templates)
        unresolved = [
            token
            for token in self.LEGACY_ALIASES
            if token in combined and not self._lookup(token)[0]
        ]
        if unresolved:
            raise UnresolvedPlaceholderError(unresolved)

    def available_tokens(self) -> list[tuple[str, str]]:
        """Return ``[(token, preview_value)]`` for the autocomplete UI."""
        tokens: list[tuple[str, str]] = []
        seen: set[str] = set()
        # Legacy aliases first (the canonical set users see).
        for token in list(self.LEGACY_ALIASES) + list(self.LEGACY_OPTIONAL):
            value, _ = self._lookup(token)
            tokens.append((token, value))
            seen.add(token)
        # Reflective discovery over ProjectMetadata scalar fields.
        for f in fields(ProjectMetadata):
            token = "{" + self._field_to_token(f.name) + "}"
            if token in seen:
                continue
            value = self._format_value(getattr(self._metadata, f.name, ""))
            tokens.append((token, value))
            seen.add(token)
        # Drone ticket fields (first ticket).
        drone = self._metadata.drone_tickets[0] if self._metadata.drone_tickets else None
        for f in fields(DroneTicket):
            token = "{DRONE." + self._field_to_token(f.name) + "}"
            if token in seen:
                continue
            value = self._format_value(getattr(drone, f.name, "")) if drone else ""
            tokens.append((token, value))
            seen.add(token)
        return tokens

    # -- internals ----------------------------------------------------------

    def _lookup(self, token: str) -> tuple[str, bool]:
        """Resolve a single token to ``(value, ok)``. ``ok=False`` = unknown path."""
        if token in self._extra:
            return self._format_value(self._extra[token]), True
        if token in self.LEGACY_ALIASES:
            return self._resolve_alias(self.LEGACY_ALIASES[token])
        if token in self.LEGACY_OPTIONAL:
            return self._resolve_alias(self.LEGACY_OPTIONAL[token])
        return self._resolve_dotted(token[1:-1])  # strip braces

    def _resolve_alias(self, spec: str) -> tuple[str, bool]:
        """Resolve an alias spec. ``@``-prefixed = synthetic, else dotted path."""
        if spec == "@empty":
            return "", True
        m = self._metadata
        s = self._settings
        if spec == "@cr_number":
            return self._email_service._extract_cr_number(m.project_name), True
        if spec == "@cr_state_value":
            return m.cr_state.value, True
        if spec == "@drone.subfolder_name":
            drone = m.drone_tickets[0] if m.drone_tickets else None
            return ((drone.subfolder_name or "") if drone else ""), True
        if spec == "@drone.drone_link":
            drone = m.drone_tickets[0] if m.drone_tickets else None
            return ((drone.drone_link or "") if drone else ""), True
        if spec == "@drone.drone_state_value":
            drone = m.drone_tickets[0] if m.drone_tickets else None
            return (drone.drone_state.value if drone else ""), True
        if spec == "@start_str":
            return self._email_service._format_datetime(m.start_datetime, s), True
        if spec == "@end_str":
            return self._email_service._format_datetime(m.end_datetime, s), True
        if spec == "@display_name":
            return s.display_name or "", True
        if spec == "@year":
            return self._email_service._extract_year(m.project_name), True
        # dotted path fallback
        return self._resolve_dotted(spec)

    def _resolve_dotted(self, dotted: str) -> tuple[str, bool]:
        """Resolve a dotted token like ``PROJECT.NAME`` or ``DRONE.0.LINK``.

        Returns ``(value, ok)`` where ``ok=False`` marks an unknown path (so the
        token is reported unresolved rather than silently dropped).
        """
        parts = dotted.split(".")
        root = parts[0]
        if root in ("SETTINGS", "APP"):
            value: object = self._settings
            for p in parts[1:]:
                value = _attr_or_empty(value, self._token_to_field(p))
            return self._format_value(value), True
        if root == "DRONE":
            idx = 0
            rest = parts[1:]
            if rest and rest[0].isdigit():
                idx = int(rest[0])
                rest = rest[1:]
            drones = self._metadata.drone_tickets
            if not rest:
                return "", True
            if idx >= len(drones):
                return "", False
            value: object = drones[idx]
            for p in rest:
                attr = self.DRONE_FIELD_ALIASES.get(p, self._token_to_field(p))
                value = _attr_or_empty(value, attr)
            return self._format_value(value), True
        # default root = metadata; normalize token to field name
        field_guess = self._token_to_field(root)
        if not hasattr(self._metadata, field_guess):
            return "", False
        value: object = getattr(self._metadata, field_guess)
        for p in parts[1:]:
            value = _attr_or_empty(value, self._token_to_field(p))
        return self._format_value(value), True

    @staticmethod
    def _field_to_token(name: str) -> str:
        return name.upper()

    @staticmethod
    def _token_to_field(token: str) -> str:
        return token.lower()

    def _format_value(self, value: object) -> str:
        if value is None:
            return ""
        if isinstance(value, datetime):
            return self._email_service._format_datetime(value, self._settings)
        if hasattr(value, "value"):  # StrEnum
            return str(value.value)
        return str(value)


def _attr_or_empty(obj: object, attr: str) -> object:
    candidate = attr.lower()
    if hasattr(obj, candidate):
        return getattr(obj, candidate)
    if hasattr(obj, attr):
        return getattr(obj, attr)
    return ""


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
        resolver = PlaceholderResolver(metadata, settings)

        # 2. Required-placeholder resolution (Requirement 8.5).
        resolver.assert_required_resolved(templates.values())

        # 3. Substitute (Requirement 8.4).
        rendered = {key: resolver.resolve(text)[0] for key, text in templates.items()}

        return RenderedEmail(
            to=rendered["to"],
            cc=rendered["cc"],
            subject=rendered["subject"],
            body=rendered["body"],
            attachment_path=self._resolve_attachment_path(category, settings),
        )

    def _resolve_attachment_path(
        self,
        category: EmailCategorySettings,
        settings: AppSettings,
    ) -> Path | None:
        """Resolve the attachment file from template_folder + attachment_template_file.

        Returns None (with a warning log) when either piece is missing or the
        resolved path does not exist on disk — render must never fail on a
        missing attachment.
        """
        file_name = (category.attachment_template_file or "").strip()
        folder = settings.email.template_folder_path if settings and settings.email else None
        if not file_name or not folder:
            return None
        path = Path(folder) / file_name
        if not path.exists():
            _log.warning("Attachment template file not found, skipping: %s", path)
            return None
        return path

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
