"""Unit tests for scheduler entry CRUD + JsApi surface (Tasks 19.2/19.3).

Covers Req 10.4/10.5/10.7-10.11 on Linux with a fake APScheduler (no real jobs
run) and a real ``SettingsStore`` pointed at ``tmp_path`` (faithful persistence,
never a real config dir):

* create/update/delete validation + persistence round-trip;
* enable/disable (pause/resume) status reconciliation;
* trigger filter match vs no-match recording + in-app delivery;
* preservation of the 60-second auto IN-PROGRESS interval job;
* JsApi ``scheduler_entry_*`` Bridge_Response shapes + ``requires_confirmation``.
"""

from __future__ import annotations

import pytest

from infrastructure.settings_store import SettingsStore
from services.scheduler_service import (
    SchedulerEntryError,
    SchedulerService,
)
from web.js_api import JsApi


class _FakeScheduler:
    """Records job-management calls; no real APScheduler threads."""

    running = False

    def __init__(self) -> None:
        self.jobs: dict[str, object] = {}
        self.removed: list[str] = []

    def add_job(self, func, *, id, replace_existing=True, **kwargs):  # noqa: A002
        self.jobs[id] = kwargs

    def remove_job(self, job_id):
        self.removed.append(job_id)
        self.jobs.pop(job_id, None)

    def pause_job(self, job_id):
        pass

    def resume_job(self, job_id):
        pass

    def start(self):
        self.running = True

    def shutdown(self, wait=False):
        self.running = False


def _service(tmp_path, *, projects=None, job=None, notification_service=None) -> SchedulerService:
    return SchedulerService(
        job=job,
        scheduler=_FakeScheduler(),
        settings_store=SettingsStore(config_dir=tmp_path),
        notification_service=notification_service,
        project_provider=(lambda: list(projects or [])),
    )


def _entries(tmp_path) -> list:
    return SettingsStore(config_dir=tmp_path).read().automation.scheduler.entries


# --- create / persistence (Req 10.4) -----------------------------------------

def test_create_entry_persists_and_lists(tmp_path) -> None:
    svc = _service(tmp_path)
    entry = svc.create_entry({"name": "Daily check", "schedule_type": "daily", "channels": ["in_app"]})
    assert entry.id
    assert [e.id for e in svc.list_entries()] == [entry.id]
    assert [e.id for e in _entries(tmp_path)] == [entry.id]  # durable round-trip


def test_create_entry_rejects_invalid_and_leaves_store_unchanged(tmp_path) -> None:
    svc = _service(tmp_path)
    with pytest.raises(SchedulerEntryError):
        svc.create_entry({"name": "", "schedule_type": "daily"})  # missing name
    with pytest.raises(SchedulerEntryError):
        svc.create_entry({"name": "x", "schedule_type": "bogus"})  # bad schedule_type
    with pytest.raises(SchedulerEntryError):
        svc.create_entry({"name": "x", "schedule_type": "daily", "channels": ["sms"]})  # bad channel
    assert _entries(tmp_path) == []


# --- update / delete (Req 10.4) ----------------------------------------------

def test_update_entry_persists_changes(tmp_path) -> None:
    svc = _service(tmp_path)
    entry = svc.create_entry({"name": "old", "schedule_type": "daily", "channels": ["in_app"]})
    updated = svc.update_entry(entry.id, {"name": "new"})
    assert updated.name == "new"
    assert _entries(tmp_path)[0].name == "new"


def test_update_and_delete_unknown_id_raise(tmp_path) -> None:
    svc = _service(tmp_path)
    with pytest.raises(SchedulerEntryError):
        svc.update_entry("missing", {"name": "x"})
    with pytest.raises(SchedulerEntryError):
        svc.delete_entry("missing")


def test_delete_entry_removes(tmp_path) -> None:
    svc = _service(tmp_path)
    entry = svc.create_entry({"name": "tmp", "schedule_type": "daily", "channels": ["in_app"]})
    svc.delete_entry(entry.id)
    assert _entries(tmp_path) == []


# --- enable/disable (Req 10.5) -----------------------------------------------

def test_set_enabled_toggles_status(tmp_path) -> None:
    svc = _service(tmp_path)
    entry = svc.create_entry({"name": "e", "schedule_type": "daily", "channels": ["in_app"]})
    disabled = svc.set_enabled(entry.id, False)
    assert disabled.enabled is False and disabled.status == "paused"
    enabled = svc.set_enabled(entry.id, True)
    assert enabled.enabled is True and enabled.status == "active"


# --- trigger filter match/no-match (Req 10.9/10.10/10.11) --------------------

class _RecordingNotifications:
    def __init__(self) -> None:
        self.added: list[tuple] = []

    def add(self, *args, **kwargs):
        self.added.append((args, kwargs))


def test_trigger_matches_and_delivers_in_app(tmp_path) -> None:
    notes = _RecordingNotifications()
    svc = _service(
        tmp_path,
        projects=[{"name": "Alpha", "state": "UAT_PREPARE"}],
        notification_service=notes,
    )
    entry = svc.create_entry(
        {"name": "m", "schedule_type": "daily", "channels": ["in_app"], "project_filter": "Alpha"}
    )
    record = svc.trigger_entry(entry.id)
    assert record["matched"] is True
    assert record["matched_projects"] == ["Alpha"]
    assert len(notes.added) == 1


def test_trigger_no_match_records_and_skips_delivery(tmp_path) -> None:
    notes = _RecordingNotifications()
    svc = _service(
        tmp_path,
        projects=[{"name": "Alpha", "state": "UAT_PREPARE"}],
        notification_service=notes,
    )
    entry = svc.create_entry(
        {"name": "m", "schedule_type": "daily", "channels": ["in_app"], "project_filter": "Zzz"}
    )
    record = svc.trigger_entry(entry.id)
    assert record["matched"] is False
    assert record["reason"] == "no_project_matched"
    assert notes.added == []


# --- 60s auto IN-PROGRESS job preserved (Req 10.x) ---------------------------

def test_interval_job_preserved_across_entry_crud(tmp_path) -> None:
    fake = _FakeScheduler()
    svc = SchedulerService(
        job=lambda: None,
        scheduler=fake,
        settings_store=SettingsStore(config_dir=tmp_path),
        project_provider=lambda: [],
    )
    svc.start()
    assert "scheduler_service_interval_job" in fake.jobs
    entry = svc.create_entry({"name": "e", "schedule_type": "daily", "channels": ["in_app"]})
    svc.delete_entry(entry.id)
    # The interval job is never removed by entry CRUD.
    assert "scheduler_service_interval_job" in fake.jobs
    assert "scheduler_service_interval_job" not in fake.removed


# --- JsApi scheduler_entry_* surface (Req 10.7/10.8) -------------------------

def test_jsapi_entry_crud_and_confirmation_flag(tmp_path) -> None:
    svc = _service(tmp_path)
    api = JsApi(None, scheduler_service=svc)

    created = api.scheduler_entry_create(
        {"name": "teams alarm", "schedule_type": "daily", "channels": ["teams"]}
    )
    assert created["ok"] is True
    assert created["data"]["requires_confirmation"] is True  # teams channel
    entry_id = created["data"]["id"]

    listed = api.scheduler_entry_list()
    assert listed["ok"] is True and len(listed["data"]) == 1

    toggled = api.scheduler_entry_toggle(entry_id, False)
    assert toggled["ok"] is True and toggled["data"]["enabled"] is False

    in_app = api.scheduler_entry_create(
        {"name": "inapp", "schedule_type": "daily", "channels": ["in_app"]}
    )
    assert in_app["data"]["requires_confirmation"] is False

    deleted = api.scheduler_entry_delete(entry_id)
    assert deleted["ok"] is True and deleted["data"]["deleted"] == entry_id


def test_jsapi_entry_create_invalid_returns_ok_false(tmp_path) -> None:
    api = JsApi(None, scheduler_service=_service(tmp_path))
    resp = api.scheduler_entry_create({"name": "", "schedule_type": "daily"})
    assert resp["ok"] is False
    assert resp["error"]["code"] == "SCHEDULER_ENTRY_CREATE_FAILED"


def test_jsapi_entry_methods_without_service_are_unavailable() -> None:
    api = JsApi(None)
    resp = api.scheduler_entry_list()
    assert resp["ok"] is False
    assert resp["error"]["code"] == "SERVICE_UNAVAILABLE"
