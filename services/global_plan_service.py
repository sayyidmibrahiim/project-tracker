from __future__ import annotations

import json
from json import JSONDecodeError
from pathlib import Path
from typing import Any

from infrastructure.metadata_store import atomic_write_json
from infrastructure.settings_store import app_config_dir

PLAN_FILE = "global_plan.json"
VALID_STATUSES = {"backlog", "ready", "doing", "review", "done"}


def _item(item_id: str, title: str, menu: str, branch_desc: str, status: str, goal: str, checks: list[str], notes: str = "") -> dict[str, Any]:
    return {
        "id": item_id,
        "title": title,
        "menu": menu,
        "branch_desc": branch_desc,
        "status": status,
        "goal": goal,
        "acceptance_checks": checks,
        "notes": notes,
        "blocked_reason": "",
        "updated_at": "2026-06-30",
    }


def default_plan() -> dict[str, Any]:
    return {
        "schema": 1,
        "loop_rule": [
            "Pick highest-priority ready item.",
            "Create branch {menu}/{branch_desc} from main.",
            "Run graphify before code lookup.",
            "Work one approved scope at a time.",
            "Move to review after app verification and doc sync.",
            "Move to done only after user approval.",
        ],
        "items": [
            _item("global-plan", "Build Global App Plan", "general", "global-plan", "doing", "Show roadmap, current work, next work, review, done, and production gaps inside the app.", ["Global Plan page opens from titlebar navigation.", "Plan data loads from local JSON.", "Cards drag/drop across status columns and persist.", "No existing fixed menu behavior changes."], "Global Plan is official menu 7."),
            _item("windows-runtime-verify", "Windows runtime verify", "general", "windows-verification", "backlog", "Verify Outlook COM, Teams, shell, dialogs, file operations, and startup on real Windows.", ["App starts from repo-root venv.", "No startup traceback.", "Manual Windows checklist passes."]),
            _item("package-windows", "Package Windows build", "general", "package-windows", "backlog", "Build and smoke packaged app on clean Windows install.", ["PyInstaller package builds.", "Clean machine launch works."]),
            _item("report-native-csv-export", "Report native CSV export", "report", "native-csv-export", "backlog", "Export real filtered report data via desktop save flow or documented fallback.", ["CSV uses real filtered rows.", "UTF-8 BOM included.", "Success/failure is visible."]),
            _item("report-add-missing-filters", "Report missing filters", "report", "add-missing-filters", "backlog", "Add Month and Drone State filters from real report data.", ["Month filter works.", "Drone State filter works."]),
            _item("report-summary-sections", "Report summary sections", "report", "summary-sections", "backlog", "Show CR State, Drone State, and Monthly Activity summaries without chart dependency.", ["Summaries match visible rows."]),
            _item("report-complete-table-columns", "Report table columns", "report", "complete-table-columns", "backlog", "Align report table with PRD fields where real data exists.", ["No, Project, CR, Drone, T-10, Last Updated visible."]),
            _item("second-brain-notes-tree", "Second Brain notes tree", "second-brain", "notes-tree", "backlog", "Complete grouped note tree from real filesystem items.", ["Pinned, Favorites, Notes groups work."]),
            _item("second-brain-search-sort-filter", "Second Brain search/sort/filter", "second-brain", "search-sort-filter", "backlog", "Wire note search, type filter, date filter, and sort controls.", ["Controls affect real filesystem notes."]),
            _item("second-brain-editor-preview", "Second Brain editor preview", "second-brain", "editor-preview", "backlog", "Improve simple editor preview/save flow without replacing RTE architecture.", ["Edit/save/preview use real files."]),
            _item("second-brain-link-bank-complete", "Link Bank completion", "second-brain", "link-bank-complete", "backlog", "Expose import/export/rename/restore controls backed by link_bank.json.", ["No dummy link data."]),
            _item("automations-scheduler-metrics", "Scheduler metrics and trigger", "automations", "scheduler-metrics", "backlog", "Use real scheduler entries and trigger matching projects instead of hardcoded metrics.", ["Trigger now targets selected entry.", "In-app notification fires for matching disposable project."]),
            _item("automations-downloaded-emails-dialog", "Downloaded emails dialog", "automations", "downloaded-emails-dialog", "backlog", "Show searchable/sortable downloaded email results when bridge returns records.", ["Real Outlook/download response displayed honestly."]),
            _item("automations-teams-crud-dialog", "Teams automation CRUD dialog", "automations", "teams-crud-dialog", "backlog", "Persist Teams automation definitions with preview/confirm/send gates.", ["No unconfirmed auto-send."]),
            _item("automations-rules-editor-logs", "Rules execute and logs", "automations", "rules-editor-logs", "backlog", "Expose execute rule separately from preview and show real execution logs.", ["Execution logs persist.", "Unsupported unsafe actions fail loudly."]),
            _item("settings-remove-theme-switch", "Remove theme switch", "settings", "remove-theme-switch", "backlog", "Match fixed-theme PRD by hiding theme switch while preserving stored value.", ["Theme selector no longer shown."]),
            _item("settings-validation-hot-reload", "Settings validation and notices", "settings", "validation-hot-reload", "backlog", "Validate obvious settings constraints and show restart-required notice.", ["Invalid values block save.", "Restart notice visible after save."]),
        ],
    }


class GlobalPlanService:
    def __init__(self, config_dir: Path | None = None) -> None:
        self.path = (config_dir or app_config_dir()) / PLAN_FILE
        self.warnings: list[str] = []

    def get_plan(self) -> dict[str, Any]:
        if not self.path.exists():
            plan = default_plan()
            atomic_write_json(self.path, plan)
            return plan
        try:
            with self.path.open("r", encoding="utf-8") as file:
                data = json.load(file)
        except JSONDecodeError:
            self.warnings.append(f"Corrupt JSON: {self.path}")
            return default_plan()
        if not isinstance(data, dict):
            self.warnings.append(f"Invalid global plan: {self.path}")
            return default_plan()
        data.setdefault("schema", 1)
        data.setdefault("loop_rule", default_plan()["loop_rule"])
        existing = self._normalize_items(data.get("items") if isinstance(data.get("items"), list) else [])
        seen = {item["id"] for item in existing}
        for item in default_plan()["items"]:
            if item["id"] not in seen:
                existing.append(item)
        data["items"] = existing
        return data

    def save_plan(self, data: dict[str, Any]) -> dict[str, Any]:
        plan = {
            "schema": 1,
            "loop_rule": data.get("loop_rule") if isinstance(data.get("loop_rule"), list) else default_plan()["loop_rule"],
            "items": self._normalize_items(data.get("items") if isinstance(data.get("items"), list) else []),
        }
        atomic_write_json(self.path, plan)
        return plan

    def _normalize_items(self, items: list[Any]) -> list[dict[str, Any]]:
        normalized: list[dict[str, Any]] = []
        for raw in items:
            if not isinstance(raw, dict):
                continue
            item = {
                "id": str(raw.get("id") or raw.get("title") or "item").strip(),
                "title": str(raw.get("title") or "Untitled").strip(),
                "menu": str(raw.get("menu") or "general").strip(),
                "branch_desc": str(raw.get("branch_desc") or "work").strip(),
                "status": str(raw.get("status") or "backlog").strip(),
                "goal": str(raw.get("goal") or "").strip(),
                "acceptance_checks": [str(v) for v in raw.get("acceptance_checks", []) if str(v).strip()] if isinstance(raw.get("acceptance_checks"), list) else [],
                "notes": str(raw.get("notes") or "").strip(),
                "blocked_reason": str(raw.get("blocked_reason") or "").strip(),
                "updated_at": str(raw.get("updated_at") or "").strip(),
            }
            if item["status"] not in VALID_STATUSES:
                item["status"] = "backlog"
            normalized.append(item)
        return normalized
