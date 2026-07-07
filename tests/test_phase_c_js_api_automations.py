"""Phase C.15 — JsApi automations facade tests (TDD: RED first)."""

from dataclasses import dataclass

from web.js_api import JsApi


@dataclass(frozen=True)
class FakeAutomationResult:
    rule_id: str
    rule_name: str
    passed: bool
    skipped: bool
    matched_conditions: list[dict[str, object]]


class FakeAutomationService:
    def __init__(self) -> None:
        self.calls: list[tuple[str, tuple[object, ...]]] = []
        self.rules = [
            {"id": "r-1", "name": "CR Approved", "enabled": True, "conditions": []},
        ]
        self.result = FakeAutomationResult(
            rule_id="r-1",
            rule_name="CR Approved",
            passed=True,
            skipped=False,
            matched_conditions=[{}],
        )

    def list_rules(self) -> list[dict[str, object]]:
        self.calls.append(("list_rules", ()))
        return self.rules

    def evaluate_rule(self, rule_id: str, context: dict[str, object]) -> object:
        self.calls.append(("evaluate_rule", (rule_id, context)))
        return self.result

    def evaluate_all(self, context: dict[str, object]) -> list[object]:
        self.calls.append(("evaluate_all", (context,)))
        return [self.result]


class ExplodingAutomationService(FakeAutomationService):
    def list_rules(self) -> list[dict[str, object]]:
        raise RuntimeError("automation unavailable")


def _expected_result() -> dict[str, object]:
    return {
        "rule_id": "r-1",
        "rule_name": "CR Approved",
        "passed": True,
        "skipped": False,
        "matched_conditions": [{}],
    }


def test_automation_list_rules_delegates_and_converts():
    service = FakeAutomationService()
    api = JsApi(dashboard_service=None, automation_service=service)

    response = api.automation_list_rules()

    assert response == {"ok": True, "data": service.rules, "error": None}
    assert service.calls == [("list_rules", ())]


def test_automation_evaluate_rule_delegates():
    service = FakeAutomationService()
    api = JsApi(dashboard_service=None, automation_service=service)
    ctx = {"cr_state": "APPROVED"}

    response = api.automation_evaluate_rule("r-1", ctx)

    assert response == {"ok": True, "data": _expected_result(), "error": None}
    assert service.calls == [("evaluate_rule", ("r-1", ctx))]


def test_automation_evaluate_all_delegates():
    service = FakeAutomationService()
    api = JsApi(dashboard_service=None, automation_service=service)
    ctx = {"cr_state": "APPROVED"}

    response = api.automation_evaluate_all(ctx)

    assert response == {"ok": True, "data": [_expected_result()], "error": None}
    assert service.calls == [("evaluate_all", (ctx,))]


def test_missing_automation_service_returns_service_unavailable():
    api = JsApi(dashboard_service=None)

    response = api.automation_list_rules()

    assert response == {
        "ok": False,
        "data": None,
        "error": {
            "code": "SERVICE_UNAVAILABLE",
            "message": "automation_service is not configured",
            "details": None,
        },
    }


def test_automation_exception_returns_fail():
    api = JsApi(dashboard_service=None, automation_service=ExplodingAutomationService())

    response = api.automation_list_rules()

    assert response == {
        "ok": False,
        "data": None,
        "error": {
            "code": "AUTOMATION_LIST_RULES_FAILED",
            "message": "automation unavailable",
            "details": None,
        },
    }


def test_approval_bridge_methods_delegate_and_guard():
    from web.js_api import JsApi

    class _FakeApproval:
        def __init__(self):
            self.calls = []

        def get_status(self, project_path):
            self.calls.append(("status", str(project_path)))
            return {"automation_enabled": True, "automation_locked": False, "uat": {"eligible": False, "reasons": [], "job": None, "auto_download": True}, "lv": {"eligible": False, "reasons": [], "job": None, "auto_download": True}, "outlook_available": False}

        def set_enabled(self, project_path, enabled):
            return {"ok": True, "data": {"automation_enabled": bool(enabled)}, "error": None}

        def set_auto_download(self, project_path, kind, enabled):
            return {"ok": True, "data": {"kind": kind, "auto_download": bool(enabled)}, "error": None}

        def set_auto_update_cr_state(self, project_path, enabled):
            return {"ok": True, "data": {"auto_update_cr_state": bool(enabled)}, "error": None}

        def send_request(self, project_path, kind, mode=None):
            return {"ok": True, "data": {"status": "polling", "kind": kind, "mode": mode}, "error": None}

        def stop(self, project_path, kind):
            return {"ok": True, "data": {"status": "stopped"}, "error": None}

        def force_check(self, project_path, kind):
            return {"ok": True, "data": {"status": "polling", "kind": kind}, "error": None}

        def get_template(self, project_path, kind):
            return {"ok": True, "data": {"source": "default", "template": {}}, "error": None}

        def update_template(self, project_path, kind, template):
            return {"ok": True, "data": {"source": "project", "template": template}, "error": None}

        def preview_template(self, project_path, kind, template):
            return {"ok": True, "data": {"subject": "S"}, "error": None}

    fake = _FakeApproval()
    api = JsApi(dashboard_service=None, approval_service=fake)

    assert api.get_approval_status("C:/p")["ok"] is True
    assert api.approval_set_enabled("C:/p", True)["data"]["automation_enabled"] is True
    assert api.approval_set_auto_download("C:/p", "uat", False)["data"]["auto_download"] is False
    assert api.approval_set_auto_update_cr_state("C:/p", True)["data"]["auto_update_cr_state"] is True
    assert api.send_uat_approval_request("C:/p", "send")["data"]["mode"] == "send"
    assert api.approval_force_check("C:/p", "uat")["data"]["status"] == "polling"
    assert api.send_uat_approval_request("C:/p")["data"]["kind"] == "uat"
    assert api.send_lv_approval_request("C:/p")["data"]["kind"] == "lv"
    assert api.stop_approval_polling("C:/p", "uat")["data"]["status"] == "stopped"
    assert api.get_approval_template("C:/p", "uat")["ok"] is True
    assert api.update_approval_template("C:/p", "uat", {"to": "x"})["ok"] is True
    assert api.preview_approval_template("C:/p", "uat", None)["ok"] is True

    bare = JsApi(dashboard_service=None)
    assert bare.get_approval_status("C:/p")["ok"] is False
    assert bare.get_approval_status("C:/p")["error"]["code"] == "SERVICE_UNAVAILABLE"
