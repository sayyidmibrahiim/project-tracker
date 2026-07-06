from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

from core.enums import CRState, DroneState, EmailMode, Language, NonCrState, ProjectType, Theme

PROJECT_DATA_SCHEMA = "project_data_v1"


def local_now() -> datetime:
    return datetime.now().astimezone()


def datetime_to_json(value: datetime | None) -> str | None:
    if value is None:
        return None
    if value.tzinfo is None or value.tzinfo.utcoffset(value) is None:
        raise ValueError("Datetime must be timezone-aware")
    return value.isoformat()


def datetime_from_json(value: str | None) -> datetime | None:
    if not value:
        return None
    result = datetime.fromisoformat(value)
    if result.tzinfo is None or result.tzinfo.utcoffset(result) is None:
        raise ValueError("Datetime must be timezone-aware")
    return result


def _string_list(values: Any) -> list[str]:
    if not isinstance(values, list):
        return []
    return [str(value) for value in values]


def _conditions(values: Any) -> list[dict[str, Any]]:
    if not isinstance(values, list):
        return []
    return [dict(value) for value in values if isinstance(value, dict)]


@dataclass(slots=True)
class HistoryEntry:
    timestamp: datetime
    action: str
    detail: str
    user: str
    override: bool = False

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> HistoryEntry:
        timestamp = datetime_from_json(data.get("timestamp"))
        if timestamp is None:
            raise ValueError("History timestamp is required")
        return cls(
            timestamp=timestamp,
            action=str(data.get("action", "")),
            detail=str(data.get("detail", "")),
            user=str(data.get("user", "")),
            override=bool(data.get("override", False)),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "timestamp": datetime_to_json(self.timestamp),
            "action": self.action,
            "detail": self.detail,
            "user": self.user,
            "override": self.override,
        }


@dataclass(slots=True)
class EmailFlags:
    ack_sent: bool = False
    approval_sent: bool = False
    last_cr_link_when_sent: str | None = None

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> EmailFlags:
        return cls(
            ack_sent=bool(data.get("ack_sent", False)),
            approval_sent=bool(data.get("approval_sent", False)),
            last_cr_link_when_sent=data.get("last_cr_link_when_sent"),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "ack_sent": self.ack_sent,
            "approval_sent": self.approval_sent,
            "last_cr_link_when_sent": self.last_cr_link_when_sent,
        }


@dataclass(slots=True)
class DroneTicket:
    subfolder_name: str | None = None
    drone_link: str = ""
    drone_state: DroneState = DroneState.UAT
    drone_state_updated_at: datetime | None = None
    owner: str = ""
    previous_drone_state_before_canceled: DroneState | None = None

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> DroneTicket:
        subfolder_name = data.get("subfolder_name")
        previous_state = data.get("previous_drone_state_before_canceled")
        return cls(
            subfolder_name=str(subfolder_name) if subfolder_name else None,
            drone_link=str(data.get("drone_link", "")),
            drone_state=DroneState(data.get("drone_state", DroneState.UAT.value)),
            drone_state_updated_at=datetime_from_json(data.get("drone_state_updated_at")),
            owner=str(data.get("owner", "")),
            previous_drone_state_before_canceled=DroneState(previous_state) if previous_state else None,
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "subfolder_name": self.subfolder_name,
            "drone_link": self.drone_link,
            "drone_state": self.drone_state.value,
            "drone_state_updated_at": datetime_to_json(self.drone_state_updated_at),
            "owner": self.owner,
            "previous_drone_state_before_canceled": self.previous_drone_state_before_canceled.value if self.previous_drone_state_before_canceled else None,
        }


@dataclass(slots=True)
class ProjectMetadata:
    project_name: str = ""
    start_datetime: datetime | None = None
    end_datetime: datetime | None = None
    cr_link: str = ""
    cr_state: CRState = CRState.PENDING_SUBMISSION
    cr_state_updated_at: datetime | None = None
    cr_pending_approval_at: datetime | None = None
    drone_tickets: list[DroneTicket] = field(default_factory=list)
    notes: str = ""
    implementation_plan: str = ""
    email_flags: EmailFlags = field(default_factory=EmailFlags)
    history: list[HistoryEntry] = field(default_factory=list)
    created_at: datetime | None = None
    updated_at: datetime | None = None
    h10_notified_at: datetime | None = None
    project_type: ProjectType = ProjectType.CR
    non_cr_state: NonCrState | None = None
    automation_enabled: bool | None = None
    approval_templates: dict[str, Any] = field(default_factory=dict)
    approval_auto_download: dict[str, bool] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ProjectMetadata:
        return cls(
            project_name=str(data.get("project_name", "")),
            start_datetime=datetime_from_json(data.get("start_datetime")),
            end_datetime=datetime_from_json(data.get("end_datetime")),
            cr_link=str(data.get("cr_link", "")),
            cr_state=CRState(data.get("cr_state", CRState.PENDING_SUBMISSION.value)),
            cr_state_updated_at=datetime_from_json(data.get("cr_state_updated_at")),
            cr_pending_approval_at=datetime_from_json(data.get("cr_pending_approval_at")),
            drone_tickets=[DroneTicket.from_dict(item) for item in data.get("drone_tickets", [])],
            implementation_plan=str(data.get("implementation_plan", "")),
            email_flags=EmailFlags.from_dict(data.get("email_flags", {})),
            history=[HistoryEntry.from_dict(item) for item in data.get("history", [])],
            created_at=datetime_from_json(data.get("created_at")),
            updated_at=datetime_from_json(data.get("updated_at")),
            h10_notified_at=datetime_from_json(data.get("h10_notified_at")),
            project_type=ProjectType(data.get("project_type", ProjectType.CR.value)),
            non_cr_state=NonCrState(data["non_cr_state"]) if data.get("non_cr_state") else None,
            automation_enabled=data["automation_enabled"] if isinstance(data.get("automation_enabled"), bool) else None,
            approval_templates=dict(data["approval_templates"]) if isinstance(data.get("approval_templates"), dict) else {},
            approval_auto_download={str(k): bool(v) for k, v in data["approval_auto_download"].items()} if isinstance(data.get("approval_auto_download"), dict) else {},
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "$schema": PROJECT_DATA_SCHEMA,
            "project_name": self.project_name,
            "start_datetime": datetime_to_json(self.start_datetime),
            "end_datetime": datetime_to_json(self.end_datetime),
            "cr_link": self.cr_link,
            "cr_state": self.cr_state.value,
            "cr_state_updated_at": datetime_to_json(self.cr_state_updated_at),
            "cr_pending_approval_at": datetime_to_json(self.cr_pending_approval_at),
            "drone_tickets": [ticket.to_dict() for ticket in self.drone_tickets],
            "implementation_plan": self.implementation_plan,
            "email_flags": self.email_flags.to_dict(),
            "history": [entry.to_dict() for entry in self.history],
            "created_at": datetime_to_json(self.created_at),
            "updated_at": datetime_to_json(self.updated_at),
            "h10_notified_at": datetime_to_json(self.h10_notified_at),
            "project_type": self.project_type.value,
            "non_cr_state": self.non_cr_state.value if self.non_cr_state else None,
            "automation_enabled": self.automation_enabled,
            "approval_templates": self.approval_templates,
            "approval_auto_download": self.approval_auto_download,
        }


@dataclass(slots=True)
class AppCodeConfig:
    display_name: str = ""
    cicd_location: str = "per_appcode"
    cicd_shared_path: Path | None = None
    created_at: datetime | None = None

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> AppCodeConfig:
        cicd_shared = data.get("cicd_shared_path", "")
        return cls(
            display_name=str(data.get("display_name", "")),
            cicd_location=str(data.get("cicd_location", "per_appcode")),
            cicd_shared_path=Path(cicd_shared) if cicd_shared else None,
            created_at=datetime_from_json(data.get("created_at")),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "display_name": self.display_name,
            "cicd_location": self.cicd_location,
            "cicd_shared_path": str(self.cicd_shared_path) if self.cicd_shared_path else "",
            "created_at": datetime_to_json(self.created_at),
        }


@dataclass(slots=True)
class AutomationCondition:
    type: str = ""
    operator: str = "equals"
    value: str = ""

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> AutomationCondition:
        return cls(
            type=str(data.get("type", "")),
            operator=str(data.get("operator", "equals")),
            value=str(data.get("value", "")),
        )

    def to_dict(self) -> dict[str, Any]:
        return {"type": self.type, "operator": self.operator, "value": self.value}


@dataclass(slots=True)
class AutomationRule:
    name: str = ""
    description: str = ""
    warning_only: bool = False
    conditions: list[AutomationCondition] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> AutomationRule:
        return cls(
            name=str(data.get("name", "")),
            description=str(data.get("description", "")),
            warning_only=bool(data.get("warning_only", False)),
            conditions=[AutomationCondition.from_dict(item) for item in data.get("conditions", [])],
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "warning_only": self.warning_only,
            "conditions": [condition.to_dict() for condition in self.conditions],
        }


@dataclass(slots=True)
class EmailCategorySettings:
    to: str = ""
    cc: str = ""
    subject_template: str = ""
    body_template: str = ""
    attachment_template_file: str = ""
    mode_override: EmailMode | None = None
    conditions: list[dict[str, Any]] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> EmailCategorySettings:
        mode_override = data.get("mode_override")
        return cls(
            to=str(data.get("to", "")),
            cc=str(data.get("cc", "")),
            subject_template=str(data.get("subject_template", "")),
            body_template=str(data.get("body_template", "")),
            attachment_template_file=str(data.get("attachment_template_file", "")),
            mode_override=EmailMode(mode_override) if mode_override else None,
            conditions=_conditions(data.get("conditions", [])),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "to": self.to,
            "cc": self.cc,
            "subject_template": self.subject_template,
            "body_template": self.body_template,
            "attachment_template_file": self.attachment_template_file,
            "mode_override": self.mode_override.value if self.mode_override else None,
            "conditions": self.conditions,
        }


@dataclass(slots=True)
class EmailSettings:
    global_mode: EmailMode = EmailMode.DRAFT
    template_folder_path: Path | None = None
    download_poll_interval_seconds: int = 10
    download_timeout_hours: int = 3
    categories: dict[str, EmailCategorySettings] = field(default_factory=dict)

    @classmethod
    def default(cls) -> EmailSettings:
        return cls(
            categories={
                "ACK_UAT": EmailCategorySettings(),
                "ACK_SOP": EmailCategorySettings(),
                "APRVL_CR": EmailCategorySettings(),
                "APRVL_SOP": EmailCategorySettings(),
            }
        )

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> EmailSettings:
        categories = data.get("categories", {})
        default_categories = cls.default().categories
        parsed_categories = {
            name: EmailCategorySettings.from_dict(categories.get(name, {}))
            for name in default_categories
        }
        template_folder_path = data.get("template_folder_path", "")
        return cls(
            global_mode=EmailMode(data.get("global_mode", EmailMode.DRAFT.value)),
            template_folder_path=Path(template_folder_path) if template_folder_path else None,
            download_poll_interval_seconds=int(data.get("download_poll_interval_seconds", 10)),
            download_timeout_hours=int(data.get("download_timeout_hours", 3)),
            categories=parsed_categories,
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "global_mode": self.global_mode.value,
            "template_folder_path": str(self.template_folder_path) if self.template_folder_path else "",
            "download_poll_interval_seconds": self.download_poll_interval_seconds,
            "download_timeout_hours": self.download_timeout_hours,
            "categories": {name: settings.to_dict() for name, settings in self.categories.items()},
        }


@dataclass(slots=True)
class TeamsAutomation:
    name: str = ""
    target_email: str = ""
    target_group: str = ""
    mentions: list[str] = field(default_factory=list)
    message_template: str = ""
    attachment_paths: list[Path] = field(default_factory=list)
    conditions: list[dict[str, Any]] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> TeamsAutomation:
        return cls(
            name=str(data.get("name", "")),
            target_email=str(data.get("target_email", "")),
            target_group=str(data.get("target_group", "")),
            mentions=_string_list(data.get("mentions", [])),
            message_template=str(data.get("message_template", "")),
            attachment_paths=[Path(value) for value in _string_list(data.get("attachment_paths", []))],
            conditions=_conditions(data.get("conditions", [])),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "target_email": self.target_email,
            "target_group": self.target_group,
            "mentions": self.mentions,
            "message_template": self.message_template,
            "attachment_paths": [str(path) for path in self.attachment_paths],
            "conditions": self.conditions,
        }


@dataclass(slots=True)
class TeamsSettings:
    countdown_seconds: int = 3
    teams_auto_send: bool = False
    webhook_url: str = ""
    automations: list[TeamsAutomation] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> TeamsSettings:
        return cls(
            countdown_seconds=int(data.get("countdown_seconds", 3)),
            teams_auto_send=bool(data.get("teams_auto_send", False)),
            webhook_url=str(data.get("webhook_url", "")),
            automations=[TeamsAutomation.from_dict(item) for item in data.get("automations", [])],
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "countdown_seconds": self.countdown_seconds,
            "teams_auto_send": self.teams_auto_send,
            "webhook_url": self.webhook_url,
            "automations": [automation.to_dict() for automation in self.automations],
        }


@dataclass(slots=True)
class SchedulerEntry:
    """A single user-configured scheduler entry persisted under
    ``settings.automation.scheduler.entries``."""

    id: str = ""
    name: str = ""
    notes: str = ""
    schedule_type: str = "one_time"  # one_time|daily|weekly|monthly|cron
    schedule_config: dict[str, Any] = field(default_factory=dict)
    project_filter: str | None = None
    state_filter: str | None = None
    channels: list[str] = field(default_factory=list)  # in_app|outlook_email|teams
    channel_configs: dict[str, Any] = field(default_factory=dict)
    enabled: bool = True
    status: str = "active"  # active|paused|completed

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> SchedulerEntry:
        project_filter = data.get("project_filter")
        state_filter = data.get("state_filter")
        schedule_config = data.get("schedule_config", {})
        channel_configs = data.get("channel_configs", {})
        return cls(
            id=str(data.get("id", "")),
            name=str(data.get("name", "")),
            notes=str(data.get("notes", "")),
            schedule_type=str(data.get("schedule_type", "one_time")),
            schedule_config=dict(schedule_config) if isinstance(schedule_config, dict) else {},
            project_filter=str(project_filter) if project_filter else None,
            state_filter=str(state_filter) if state_filter else None,
            channels=_string_list(data.get("channels", [])),
            channel_configs=dict(channel_configs) if isinstance(channel_configs, dict) else {},
            enabled=bool(data.get("enabled", True)),
            status=str(data.get("status", "active")),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "notes": self.notes,
            "schedule_type": self.schedule_type,
            "schedule_config": self.schedule_config,
            "project_filter": self.project_filter,
            "state_filter": self.state_filter,
            "channels": self.channels,
            "channel_configs": self.channel_configs,
            "enabled": self.enabled,
            "status": self.status,
        }


@dataclass(slots=True)
class SchedulerSettings:
    entries: list[SchedulerEntry] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> SchedulerSettings:
        entries = data.get("entries", [])
        return cls(
            entries=[
                SchedulerEntry.from_dict(item) for item in entries if isinstance(item, dict)
            ]
        )

    def to_dict(self) -> dict[str, Any]:
        return {"entries": [entry.to_dict() for entry in self.entries]}


@dataclass(slots=True)
class AutomationSettings:
    """Automation settings persisted under ``settings.automation``.

    ``scheduler`` is modelled here (Task 19); ``rules_engine`` is preserved as a
    raw round-tripped mapping so the Rules Engine slice (Task 21) can model it
    without losing any persisted data in the interim.
    """

    scheduler: SchedulerSettings = field(default_factory=SchedulerSettings)
    rules_engine: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> AutomationSettings:
        scheduler = data.get("scheduler", {})
        rules_engine = data.get("rules_engine", {})
        return cls(
            scheduler=SchedulerSettings.from_dict(scheduler if isinstance(scheduler, dict) else {}),
            rules_engine=dict(rules_engine) if isinstance(rules_engine, dict) else {},
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "scheduler": self.scheduler.to_dict(),
            "rules_engine": self.rules_engine,
        }


@dataclass(slots=True)
class AppSettings:
    root_folder: Path | None = None
    display_name: str = ""
    language: Language = Language.ENGLISH
    datetime_format: str = "ddd, dd MMM yyyy HH:mm"
    t10_threshold_days: int = 10
    h10_reminder_days: int = 10
    auto_refresh_interval: str = "off"
    theme: Theme = Theme.DARK
    startup_behavior: str = "current_year_dashboard"
    second_brain_folder: Path | None = None
    file_template_folder: Path | None = None
    automation_rules: list[AutomationRule] = field(default_factory=list)
    email: EmailSettings = field(default_factory=EmailSettings.default)
    teams: TeamsSettings = field(default_factory=TeamsSettings)
    automation: AutomationSettings = field(default_factory=AutomationSettings)
    default_approval_templates: dict[str, Any] = field(default_factory=dict)
    approval_polling_interval_minutes: int = 5
    approval_polling_max_hours: int = 3
    automation_default_enabled: bool = False

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> AppSettings:
        root_folder = data.get("root_folder", "")
        second_brain_folder = data.get("second_brain_folder", "")
        file_template_folder = data.get("file_template_folder", "")
        return cls(
            root_folder=Path(root_folder) if root_folder else None,
            display_name=str(data.get("display_name", "")),
            language=Language(data.get("language", Language.ENGLISH.value)),
            datetime_format=str(data.get("datetime_format", "ddd, dd MMM yyyy HH:mm")),
            t10_threshold_days=int(data.get("t10_threshold_days", 10)),
            h10_reminder_days=int(data.get("h10_reminder_days", 10)),
            auto_refresh_interval=str(data.get("auto_refresh_interval", "off")),
            theme=Theme(data.get("theme", Theme.DARK.value)),
            startup_behavior=str(data.get("startup_behavior", "current_year_dashboard")),
            second_brain_folder=Path(second_brain_folder) if second_brain_folder else None,
            file_template_folder=Path(file_template_folder) if file_template_folder else None,
            automation_rules=[AutomationRule.from_dict(item) for item in data.get("automation_rules", [])],
            email=EmailSettings.from_dict(data.get("email", {})),
            teams=TeamsSettings.from_dict(data.get("teams", {})),
            automation=AutomationSettings.from_dict(data.get("automation", {})),
            default_approval_templates=dict(data["default_approval_templates"]) if isinstance(data.get("default_approval_templates"), dict) else {},
            approval_polling_interval_minutes=int(data.get("approval_polling_interval_minutes", 5)),
            approval_polling_max_hours=int(data.get("approval_polling_max_hours", 3)),
            automation_default_enabled=bool(data.get("automation_default_enabled", False)),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "root_folder": str(self.root_folder) if self.root_folder else "",
            "display_name": self.display_name,
            "language": self.language.value,
            "datetime_format": self.datetime_format,
            "t10_threshold_days": self.t10_threshold_days,
            "h10_reminder_days": self.h10_reminder_days,
            "auto_refresh_interval": self.auto_refresh_interval,
            "theme": self.theme.value,
            "startup_behavior": self.startup_behavior,
            "second_brain_folder": str(self.second_brain_folder) if self.second_brain_folder else "",
            "file_template_folder": str(self.file_template_folder) if self.file_template_folder else "",
            "automation_rules": [rule.to_dict() for rule in self.automation_rules],
            "email": self.email.to_dict(),
            "teams": self.teams.to_dict(),
            "automation": self.automation.to_dict(),
            "default_approval_templates": self.default_approval_templates,
            "approval_polling_interval_minutes": self.approval_polling_interval_minutes,
            "approval_polling_max_hours": self.approval_polling_max_hours,
            "automation_default_enabled": self.automation_default_enabled,
        }

@dataclass(slots=True)
class Notification:
    id: str
    type: str
    title: str
    message: str
    timestamp: datetime
    project_path: Path | None = None
    dismissed: bool = False


@dataclass(slots=True)
class DownloadEmailJob:
    """Download Email automation job state."""
    job_id: str
    cr_number: str
    project_name: str
    project_path: Path
    start_time: datetime
    status: str  # active, completed, timeout, stopped
    matching_rule: str | None = None
    dismissed: bool = False
