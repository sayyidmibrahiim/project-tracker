"""Unit tests for the reflective PlaceholderResolver (Automation epic Slice 2).

Covers: legacy alias compatibility, nested/indexed tokens, required-token abort,
attachment path resolution, and the autocomplete token preview.
"""

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
    EmailService,
    PlaceholderResolver,
    UnresolvedPlaceholderError,
)


def _full_metadata() -> ProjectMetadata:
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


def test_legacy_required_aliases_resolve():
    r = PlaceholderResolver(_full_metadata(), _settings())
    text, unresolved = r.resolve("{PROJECT_NAME} {CR_NUMBER} {CR_LINK} {DISPLAY_NAME}")
    assert unresolved == []
    assert "CR-2026-001" in text
    assert "2026-001" in text  # CR_NUMBER
    assert "https://crportal/CR-2026-001" in text
    assert "Jane Doe" in text


def test_nested_drone_token_resolves_first_ticket():
    r = PlaceholderResolver(_full_metadata(), _settings())
    text, unresolved = r.resolve("{DRONE.LINK} {DRONE.STATE}")
    assert unresolved == []
    assert "https://drone/1" in text
    assert "APPROVED" in text


def test_indexed_drone_token():
    r = PlaceholderResolver(_full_metadata(), _settings())
    text, unresolved = r.resolve("{DRONE.0.LINK}")
    assert unresolved == []
    assert text == "https://drone/1"


def test_unresolved_token_left_in_place_and_reported():
    r = PlaceholderResolver(_full_metadata(), _settings())
    text, unresolved = r.resolve("Hello {DOES_NOT_EXIST}!")
    assert "{DOES_NOT_EXIST}" in text
    assert "{DOES_NOT_EXIST}" in unresolved


def test_assert_required_resolved_aborts_on_empty_required():
    metadata = _full_metadata()
    metadata.cr_link = ""  # {CR_LINK} is required
    r = PlaceholderResolver(metadata, _settings())
    with pytest.raises(UnresolvedPlaceholderError) as exc:
        r.assert_required_resolved(["CR link: {CR_LINK}"])
    assert "{CR_LINK}" in exc.value.placeholders


def test_assert_required_resolved_passes_when_optional_empty():
    """Optional legacy alias empty must NOT abort."""
    metadata = _full_metadata()
    r = PlaceholderResolver(metadata, _settings())
    # {SUBPROJECT_NAME} is optional; empty is fine.
    r.assert_required_resolved(["Sub: {SUBPROJECT_NAME}"])  # no raise


def test_available_tokens_returns_legacy_plus_reflective():
    r = PlaceholderResolver(_full_metadata(), _settings())
    tokens = dict(r.available_tokens())
    # Legacy canonical tokens present with real preview values.
    assert tokens["{PROJECT_NAME}"] == "CR-2026-001"
    assert tokens["{DISPLAY_NAME}"] == "Jane Doe"
    # Reflective drone token present.
    assert "{DRONE.DRONE_LINK}" in tokens
    assert tokens["{DRONE.DRONE_LINK}"] == "https://drone/1"


def test_render_email_template_still_works_via_resolver():
    """Existing render path now delegates to PlaceholderResolver."""
    service = EmailService()
    metadata = _full_metadata()
    settings = _settings()
    category = EmailCategorySettings(
        to="ops@example.com",
        subject_template="{PROJECT_NAME} approved",
        body_template="CR {CR_NUMBER} drone {DRONE.LINK}",
    )
    rendered = service.render_email_template(metadata, category, settings)
    assert rendered.subject == "CR-2026-001 approved"
    assert "2026-001" in rendered.body
    assert "https://drone/1" in rendered.body


def test_attachment_path_resolved_when_file_exists(tmp_path):
    folder = tmp_path / "templates"
    folder.mkdir()
    (folder / "plan.xlsx").write_bytes(b"x")
    settings = _settings()
    settings.email.template_folder_path = folder
    category = EmailCategorySettings(
        to="ops@example.com",
        subject_template="{PROJECT_NAME}",
        body_template="ok",
        attachment_template_file="plan.xlsx",
    )
    rendered = EmailService().render_email_template(_full_metadata(), category, settings)
    assert rendered.attachment_path is not None
    assert rendered.attachment_path.name == "plan.xlsx"


def test_attachment_path_none_when_missing_or_unset(tmp_path):
    settings = _settings()
    # template_folder_path set but file missing
    settings.email.template_folder_path = tmp_path
    category = EmailCategorySettings(
        to="ops@example.com",
        subject_template="{PROJECT_NAME}",
        body_template="ok",
        attachment_template_file="nope.xlsx",
    )
    rendered = EmailService().render_email_template(_full_metadata(), category, settings)
    assert rendered.attachment_path is None  # missing file -> None, no raise
    # attachment_template_file unset -> None
    category2 = EmailCategorySettings(
        to="ops@example.com",
        subject_template="{PROJECT_NAME}",
        body_template="ok",
    )
    rendered2 = EmailService().render_email_template(_full_metadata(), category2, settings)
    assert rendered2.attachment_path is None
