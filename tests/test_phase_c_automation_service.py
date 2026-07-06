"""Phase C.14 — AutomationService foundation tests (TDD: RED first)."""

import pytest

from services.automation_service import (
    AutomationRuleResult,
    AutomationService,
)


def _rules() -> list[dict[str, object]]:
    return [
        {
            "id": "r-1",
            "name": "CR Approved",
            "enabled": True,
            "conditions": [
                {"field": "cr_state", "operator": "equals", "value": "APPROVED"},
            ],
        },
        {
            "id": "r-2",
            "name": "Project Name Check",
            "enabled": True,
            "conditions": [
                {"field": "project_name", "operator": "contains", "value": "Alpha"},
            ],
        },
        {
            "id": "r-3",
            "name": "Has Drone",
            "enabled": True,
            "conditions": [
                {"field": "drone_count", "operator": "exists"},
            ],
        },
        {
            "id": "r-4",
            "name": "Disabled Rule",
            "enabled": False,
            "conditions": [
                {"field": "project_name", "operator": "equals", "value": "Beta"},
            ],
        },
        {
            "id": "r-5",
            "name": "Multi Condition",
            "enabled": True,
            "conditions": [
                {"field": "cr_state", "operator": "equals", "value": "APPROVED"},
                {"field": "project_state", "operator": "not_equals", "value": "IMPLEMENTED"},
            ],
        },
    ]


def test_list_rules_returns_provider_rules():
    service = AutomationService(rules_provider=_rules)
    rules = service.list_rules()
    assert len(rules) == 5
    assert rules[0]["id"] == "r-1"
    assert rules[3]["enabled"] is False


def test_evaluate_equals_success():
    service = AutomationService(rules_provider=_rules)
    result = service.evaluate_rule("r-1", {"cr_state": "APPROVED"})
    assert result.rule_id == "r-1"
    assert result.passed is True
    assert result.skipped is False
    assert len(result.matched_conditions) == 1


def test_evaluate_equals_failure():
    service = AutomationService(rules_provider=_rules)
    result = service.evaluate_rule("r-1", {"cr_state": "CANCELED"})
    assert result.passed is False


def test_evaluate_not_equals():
    service = AutomationService(rules_provider=_rules)
    result = service.evaluate_rule("r-5", {"cr_state": "APPROVED", "project_state": "UAT_PREPARE"})
    assert result.passed is True


def test_evaluate_contains():
    service = AutomationService(rules_provider=_rules)
    result = service.evaluate_rule("r-2", {"project_name": "Project Alpha Test"})
    assert result.passed is True


def test_evaluate_exists():
    service = AutomationService(rules_provider=_rules)
    has = service.evaluate_rule("r-3", {"drone_count": 3})
    missing = service.evaluate_rule("r-3", {})
    assert has.passed is True
    assert missing.passed is False


def test_disabled_rule_is_skipped():
    service = AutomationService(rules_provider=_rules)
    result = service.evaluate_rule("r-4", {"project_name": "Beta"})
    assert result.skipped is True
    assert result.passed is False


def test_missing_rule_raises_key_error():
    service = AutomationService(rules_provider=_rules)
    with pytest.raises(KeyError, match="Rule not found: nonexistent"):
        service.evaluate_rule("nonexistent", {})


def test_evaluate_all():
    service = AutomationService(rules_provider=_rules)
    results = service.evaluate_all({"cr_state": "APPROVED", "project_name": "Alpha", "drone_count": 1, "project_state": "UAT_PREPARE"})

    assert len(results) == 5
    passed = [r for r in results if r.passed]
    skipped = [r for r in results if r.skipped]
    assert len(passed) == 4  # r-1, r-2, r-3, r-5
    assert len(skipped) == 1  # r-4


def test_piece_c_model_fields_round_trip():
    from core.models import AppSettings, ProjectMetadata

    meta = ProjectMetadata.from_dict(
        {
            "automation_enabled": True,
            "approval_templates": {"uat_approval": {"to": "a@b", "subject": "UAT {CR_NUMBER}"}},
        }
    )
    assert meta.automation_enabled is True
    assert meta.approval_templates["uat_approval"]["to"] == "a@b"
    out = meta.to_dict()
    assert out["automation_enabled"] is True
    assert out["approval_templates"]["uat_approval"]["subject"] == "UAT {CR_NUMBER}"
    assert ProjectMetadata.from_dict({}).automation_enabled is None
    assert ProjectMetadata.from_dict({}).approval_templates == {}
    assert ProjectMetadata.from_dict({}).approval_auto_download == {}
    assert ProjectMetadata.from_dict({"automation_enabled": False}).automation_enabled is False
    meta_dl = ProjectMetadata.from_dict({"approval_auto_download": {"uat": False}})
    assert meta_dl.approval_auto_download == {"uat": False}
    assert meta_dl.to_dict()["approval_auto_download"] == {"uat": False}

    settings = AppSettings.from_dict(
        {
            "default_approval_templates": {"lv_approval": {"subject": "LV {CR_NUMBER}"}},
            "approval_polling_interval_minutes": 7,
            "approval_polling_max_hours": 2,
        }
    )
    assert settings.approval_polling_interval_minutes == 7
    assert settings.approval_polling_max_hours == 2
    assert settings.default_approval_templates["lv_approval"]["subject"] == "LV {CR_NUMBER}"
    out = settings.to_dict()
    assert out["approval_polling_interval_minutes"] == 7
    assert out["approval_polling_max_hours"] == 2
    defaults = AppSettings.from_dict({})
    assert defaults.approval_polling_interval_minutes == 5
    assert defaults.approval_polling_max_hours == 3
    assert defaults.default_approval_templates == {}
    assert defaults.automation_default_enabled is False
    enabled = AppSettings.from_dict({"automation_default_enabled": True})
    assert enabled.automation_default_enabled is True
    assert enabled.to_dict()["automation_default_enabled"] is True


def _piece_c_service(tmp_path, monkeypatch=None):
    from infrastructure.cache_db import CacheDb
    from infrastructure.metadata_store import MetadataStore
    from services.approval_polling_service import ApprovalPollingService
    from services.email_service import EmailService

    class _FakeSettingsStore:
        def __init__(self):
            from core.models import AppSettings

            self.settings = AppSettings.from_dict(
                {
                    "default_approval_templates": {
                        "uat_approval": {"to": "boss@corp", "cc": "", "subject": "Request UAT Approval {CR_NUMBER}", "body": "Please approve {PROJECT_NAME}", "mode": "draft"},
                        "lv_approval": {"to": "boss@corp", "cc": "", "subject": "Request LV {CR_NUMBER}", "body": "LV for {PROJECT_NAME}", "mode": "draft"},
                    }
                }
            )

        def read(self):
            return self.settings

        def write(self, settings):
            self.settings = settings

    cache = CacheDb(tmp_path / "cache.db")
    cache.initialize()
    return ApprovalPollingService(
        settings_store=_FakeSettingsStore(),
        metadata_store=MetadataStore(),
        email_service=EmailService(),
        cache=cache,
    )


def _piece_c_project(tmp_path, *, drone_state="PENDING APPROVAL", cr_state="PENDING SUBMISSION", signoff=b"x", lv=b"", automation_enabled=True, extra=None):
    import json

    project = tmp_path / "CR-2026-001"
    docs = project / "_cr-docs"
    docs.mkdir(parents=True)
    if signoff is not None:
        (docs / "uat-signoff.docx").write_bytes(signoff)
    if lv is not None:
        (docs / "prod-lv.docx").write_bytes(lv)
    data = {
        "project_name": "CR-2026-001",
        "project_type": "CR",
        "cr_link": "https://itsm.corp/change?CRNumber=CR2026001",
        "cr_state": cr_state,
        "drone_tickets": [{"drone_link": "", "drone_state": drone_state}],
    }
    if automation_enabled is not None:
        data["automation_enabled"] = automation_enabled
    if extra:
        data.update(extra)
    (project / "project_data.json").write_text(json.dumps(data), encoding="utf-8")
    return project


def test_piece_c_conditions_gate_uat_and_lv(tmp_path):
    service = _piece_c_service(tmp_path)

    eligible = _piece_c_project(tmp_path / "a")
    status = service.get_status(eligible)
    assert status["automation_enabled"] is True
    assert status["uat"]["eligible"] is True
    assert status["lv"]["eligible"] is False  # empty prod-lv + not approved

    empty_signoff = _piece_c_project(tmp_path / "b", signoff=b"")
    assert service.get_status(empty_signoff)["uat"]["eligible"] is False

    lv_ready = _piece_c_project(tmp_path / "c", cr_state="APPROVED", lv=b"x")
    assert service.get_status(lv_ready)["lv"]["eligible"] is True

    drone_approved_lv = _piece_c_project(tmp_path / "d", drone_state="APPROVED", lv=b"x")
    assert service.get_status(drone_approved_lv)["lv"]["eligible"] is True


def test_piece_c_send_validates_template_and_records_job(tmp_path, monkeypatch):
    import services.approval_polling_service as aps

    service = _piece_c_service(tmp_path)
    project = _piece_c_project(tmp_path / "a")

    sent: list[tuple] = []
    monkeypatch.setattr(aps.outlook_client, "IS_WINDOWS", True)
    monkeypatch.setattr(
        aps.outlook_client,
        "create_draft_email",
        lambda to, cc, subject, body, attachment_path=None: (sent.append((to, subject)) or {"ok": True, "data": {"status": "drafted"}, "error": None}),
    )
    monkeypatch.setattr(aps.ApprovalPollingService, "_start_worker", lambda self, job: None)

    result = service.send_request(project, "uat")
    assert result["ok"] is True
    assert sent and "CR2026001" in sent[0][1]

    job = service._cache.latest_approval_job(str(project), "uat")
    assert job is not None and job["status"] == "polling"

    status = service.get_status(project)
    assert status["uat"]["job"]["status"] == "polling"

    stopped = service.stop(project, "uat")
    assert stopped["ok"] is True
    assert service._cache.latest_approval_job(str(project), "uat")["status"] == "stopped"


def test_piece_c_send_rejects_subject_without_cr_placeholder(tmp_path):
    service = _piece_c_service(tmp_path)
    project = _piece_c_project(tmp_path / "a")
    service.update_template(project, "uat", {"to": "x@y", "cc": "", "subject": "no placeholder", "body": "b", "mode": "draft"})
    result = service.send_request(project, "uat")
    assert result["ok"] is False
    assert result["error"]["code"] == "APPROVAL_TEMPLATE_INVALID"


def test_piece_c_template_get_update_preview(tmp_path):
    service = _piece_c_service(tmp_path)
    project = _piece_c_project(tmp_path / "a")

    got = service.get_template(project, "uat")
    assert got["ok"] is True and got["data"]["source"] == "default"

    service.update_template(project, "uat", {"to": "me@corp", "cc": "", "subject": "UAT {CR_NUMBER}", "body": "hi {PROJECT_NAME}", "mode": "send"})
    got = service.get_template(project, "uat")
    assert got["data"]["source"] == "project" and got["data"]["template"]["to"] == "me@corp"


def test_piece_c_status_inherits_global_default(tmp_path):
    service = _piece_c_service(tmp_path)

    inheriting = _piece_c_project(tmp_path / "a", automation_enabled=None)
    assert service.get_status(inheriting)["automation_enabled"] is False
    service._settings_store.settings.automation_default_enabled = True
    assert service.get_status(inheriting)["automation_enabled"] is True

    explicit_off = _piece_c_project(tmp_path / "b", automation_enabled=False)
    assert service.get_status(explicit_off)["automation_enabled"] is False  # explicit override wins


def test_piece_c_status_locked_for_terminal_cr_state(tmp_path):
    service = _piece_c_service(tmp_path)

    active = _piece_c_project(tmp_path / "a")
    status = service.get_status(active)
    assert status["automation_locked"] is False
    assert status["automation_enabled"] is True

    for i, state in enumerate(("FINISHED", "POSTPONED", "CANCELED")):
        locked = _piece_c_project(tmp_path / f"t{i}", cr_state=state)
        status = service.get_status(locked)
        assert status["automation_locked"] is True
        assert status["automation_enabled"] is False  # forced off despite explicit True


def test_piece_c_auto_download_flag(tmp_path):
    service = _piece_c_service(tmp_path)
    project = _piece_c_project(tmp_path / "a")

    status = service.get_status(project)
    assert status["uat"]["auto_download"] is True
    assert status["lv"]["auto_download"] is True

    result = service.set_auto_download(project, "uat", False)
    assert result["ok"] is True and result["data"]["auto_download"] is False
    assert service.get_status(project)["uat"]["auto_download"] is False
    assert service.get_status(project)["lv"]["auto_download"] is True

    invalid = service.set_auto_download(project, "nope", True)
    assert invalid["ok"] is False and invalid["error"]["code"] == "APPROVAL_KIND_INVALID"


def test_piece_c_send_without_auto_download_skips_polling(tmp_path, monkeypatch):
    import services.approval_polling_service as aps

    service = _piece_c_service(tmp_path)
    project = _piece_c_project(tmp_path / "a", extra={"approval_auto_download": {"uat": False}})

    started: list = []
    monkeypatch.setattr(aps.outlook_client, "IS_WINDOWS", True)
    monkeypatch.setattr(
        aps.outlook_client,
        "create_draft_email",
        lambda to, cc, subject, body, attachment_path=None: {"ok": True, "data": {"status": "drafted"}, "error": None},
    )
    monkeypatch.setattr(aps.ApprovalPollingService, "_start_worker", lambda self, job: started.append(job))

    result = service.send_request(project, "uat")
    assert result["ok"] is True and result["data"]["status"] == "sent"
    assert started == []
    assert service._cache.latest_approval_job(str(project), "uat") is None

    from infrastructure.metadata_store import MetadataStore

    metadata = MetadataStore().read(project)
    assert any(entry.action == "APPROVAL_REQUEST_SENT" for entry in metadata.history)

    preview = service.preview_template(project, "uat", None)
    assert preview["ok"] is True
    assert "CR-2026-001" in preview["data"]["body"] or "2026-001" in preview["data"]["subject"]
