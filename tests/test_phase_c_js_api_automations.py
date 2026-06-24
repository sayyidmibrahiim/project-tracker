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
