"""Unit tests for EmailService template rendering, required-placeholder abort,
and Template_Category condition evaluation (Requirements 8.4, 8.5, 8.6)."""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

from core.enums import CRState, DroneState
from core.models import (
    AppSettings,
    DroneTicket,
    EmailCategorySettings,
    ProjectMetadata,
)
from services.email_service import (
    REQUIRED_PLACEHOLDERS,
    EmailService,
    TemplateConditionsNotMetError,
    UnresolvedPlaceholderError,
)

ALL_CATEGORIES = ["ACK_UAT", "ACK_SOP", "APRVL_CR", "APRVL_SOP"]


def _full_metadata() -> ProjectMetadata:
    """Metadata that can resolve every required placeholder."""
    return ProjectMetadata(
        project_name="CR-2026-001",
        start_datetime=datetime(2026, 1, 10, 9, 0, tzinfo=timezone.utc),
        end_datetime=datetime(2026, 1, 11, 17, 0, tzinfo=timezone.utc),
        cr_link="https://crportal/CR-2026-001",
        cr_state=CRState.APPROVED,
        drone_tickets=[
            DroneTicket(
                subfolder_name="DRONE-1",
                drone_link="https://drone/1",
                drone_state=DroneState.APPROVED,
            )
        ],
        implementation_plan="Deploy during the maintenance window.",
    )


def _settings() -> AppSettings:
    return AppSettings(display_name="Jane Doe")


def _all_placeholders_template() -> str:
    return " ".join(REQUIRED_PLACEHOLDERS)


def test_resolves_all_required_placeholders_for_every_category():
    service = EmailService()
    metadata = _full_metadata()
    settings = _settings()
    template = _all_placeholders_template()

    for _category in ALL_CATEGORIES:
        category = EmailCategorySettings(
            to="ops@example.com",
            subject_template=template,
            body_template=template,
        )
        rendered = service.render_email_template(metadata, category, settings)

        # No required placeholder token should remain in the rendered output.
        for placeholder in REQUIRED_PLACEHOLDERS:
            assert placeholder not in rendered.subject
            assert placeholder not in rendered.body


def test_resolves_new_canonical_placeholders():
    """{START_DATETIME}, {END_DATETIME}, {DISPLAY_NAME} must resolve (Req 8.4)."""
    service = EmailService()
    metadata = _full_metadata()
    settings = _settings()
    category = EmailCategorySettings(
        to="ops@example.com",
        subject_template="{DISPLAY_NAME}",
        body_template="Start {START_DATETIME} End {END_DATETIME}",
    )

    rendered = service.render_email_template(metadata, category, settings)

    assert rendered.subject == "Jane Doe"
    assert "{START_DATETIME}" not in rendered.body
    assert "{END_DATETIME}" not in rendered.body
    assert "Start" in rendered.body and "End" in rendered.body


def test_abort_on_unresolved_required_placeholder_names_it():
    """A required placeholder that cannot resolve aborts and is named (Req 8.5)."""
    service = EmailService()
    metadata = _full_metadata()
    metadata.cr_link = ""  # make {CR_LINK} unresolvable
    settings = _settings()
    category = EmailCategorySettings(
        to="ops@example.com",
        subject_template="CR link: {CR_LINK}",
        body_template="body",
    )

    with pytest.raises(UnresolvedPlaceholderError) as exc:
        service.render_email_template(metadata, category, settings)

    assert "{CR_LINK}" in exc.value.placeholders
    assert "{CR_LINK}" in str(exc.value)


def test_unreferenced_empty_placeholder_does_not_abort():
    """Empty values are only unresolved when actually referenced by a template."""
    service = EmailService()
    metadata = _full_metadata()
    metadata.implementation_plan = ""  # empty but not referenced below
    settings = _settings()
    category = EmailCategorySettings(
        to="ops@example.com",
        subject_template="{PROJECT_NAME}",
        body_template="No optional fields referenced.",
    )

    rendered = service.render_email_template(metadata, category, settings)
    assert rendered.subject == "CR-2026-001"


def test_conditions_met_renders():
    """When conditions are satisfied, composition proceeds (Req 8.6)."""
    service = EmailService()
    metadata = _full_metadata()
    settings = _settings()
    category = EmailCategorySettings(
        to="ops@example.com",
        subject_template="{PROJECT_NAME}",
        body_template="ok",
        conditions=[{"field": "cr_state", "operator": "equals", "value": "APPROVED"}],
    )

    rendered = service.render_email_template(metadata, category, settings)
    assert rendered.subject == "CR-2026-001"


def test_conditions_unmet_skips_with_reason():
    """When conditions are not met, composition is skipped with a reason (Req 8.6)."""
    service = EmailService()
    metadata = _full_metadata()
    metadata.cr_state = CRState.PENDING_APPROVAL
    settings = _settings()
    category = EmailCategorySettings(
        to="ops@example.com",
        subject_template="{PROJECT_NAME}",
        body_template="ok",
        conditions=[{"field": "cr_state", "operator": "equals", "value": "APPROVED"}],
    )

    with pytest.raises(TemplateConditionsNotMetError) as exc:
        service.render_email_template(metadata, category, settings)

    assert "cr_state" in exc.value.reason
    assert "APPROVED" in exc.value.reason


def test_conditions_evaluated_before_placeholder_resolution():
    """Unmet conditions skip before an unresolved placeholder would abort (Req 8.6)."""
    service = EmailService()
    metadata = _full_metadata()
    metadata.cr_state = CRState.PENDING_APPROVAL
    metadata.cr_link = ""  # would otherwise trigger UnresolvedPlaceholderError
    settings = _settings()
    category = EmailCategorySettings(
        to="ops@example.com",
        subject_template="{CR_LINK}",
        body_template="ok",
        conditions=[{"field": "cr_state", "operator": "equals", "value": "APPROVED"}],
    )

    # Conditions are checked first, so we get a skip rather than an abort.
    with pytest.raises(TemplateConditionsNotMetError):
        service.render_email_template(metadata, category, settings)


def test_exists_operator_on_drone_count():
    service = EmailService()
    metadata = _full_metadata()
    settings = _settings()
    category = EmailCategorySettings(
        to="ops@example.com",
        subject_template="{PROJECT_NAME}",
        body_template="ok",
        conditions=[{"field": "drone_count", "operator": "exists"}],
    )

    rendered = service.render_email_template(metadata, category, settings)
    assert rendered.subject == "CR-2026-001"
