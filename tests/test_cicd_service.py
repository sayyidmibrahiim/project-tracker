"""Piece D CICD service tests (consolidated — user rule: one file)."""

from __future__ import annotations

import subprocess
import time

import pytest

from app_web import create_js_api
from core.models import AppSettings
from infrastructure.settings_store import SettingsStore
import services.cicd_service as cicd
from web.js_api import JsApi


# ── parse_repo_name ────────────────────────────────────────────────────
@pytest.mark.parametrize(
    "url, expected",
    [
        ("https://bitbucket.sgp.dbs.com:8443/scm/dcifbinary/myapp.git", "myapp"),
        ("https://host/scm/team/anotherapp", "anotherapp"),
        ("https://host/scm/team/myapp.git/", "myapp"),
    ],
)
def test_parse_repo_name(url, expected):
    assert cicd.parse_repo_name(url) == expected


def test_parse_repo_name_empty_raises():
    with pytest.raises(ValueError):
        cicd.parse_repo_name("   ")


# ── parse_clone_url ─────────────────────────────────────────────────────
@pytest.mark.parametrize(
    "url, expected_repo",
    [
        ("https://bitbucket.sgp.dbs.com:8443/scm/dcifbinary/myapp.git", "myapp"),
        ("https://bitbucket.sgp.dbs.com:8443/projects/dcif/repos/anotherapp", "anotherapp"),
        ("https://host/team/final-repo.git", "final-repo"),
        ("https://host/scm/team/My%20App.git", "My App"),
    ],
)
def test_parse_clone_url_accepts_bitbucket_shapes(url, expected_repo):
    info = cicd.parse_clone_url(url)
    assert info.repo_name == expected_repo
    assert info.appcode_candidate == expected_repo


@pytest.mark.parametrize(
    "url",
    [
        "ssh://host/scm/team/repo.git",
        "https://user:secret@host/scm/team/repo.git",
        "https:///scm/team/repo.git",
        "https://host/scm/team/.git",
        "https://host/scm/team/CON.git",
    ],
)
def test_parse_clone_url_rejects_unsafe_urls(url):
    with pytest.raises(ValueError):
        cicd.parse_clone_url(url)


# ── CICD preview adapter ────────────────────────────────────────────────
def _api_with_root(tmp_path):
    store = SettingsStore(tmp_path / "config")
    store.write(AppSettings(root_folder=tmp_path / "root"))
    return create_js_api(db_path=tmp_path / "cache.sqlite", settings_store=store)


def test_cicd_preview_link_matches_existing_appcode_exact(tmp_path):
    api = _api_with_root(tmp_path)
    assert api.appcode_add("myapp")["ok"] is True
    resp = api.cicd_preview_link("https://host/scm/team/myapp.git")
    data = resp["data"]
    assert resp["ok"] is True
    assert data["repo_name"] == "myapp"
    assert data["matched_appcode"] == "myapp"
    assert data["appcode_exists"] is True
    assert data["needs_confirmation"] is False
    assert data["target_repo_path"].endswith("myapp\\CICD\\myapp") or data["target_repo_path"].endswith("myapp/CICD/myapp")


def test_cicd_preview_link_matches_existing_appcode_case_insensitive(tmp_path):
    api = _api_with_root(tmp_path)
    assert api.appcode_add("WGID")["ok"] is True
    resp = api.cicd_preview_link("https://host/scm/team/wgid.git")
    assert resp["data"]["matched_appcode"] == "WGID"
    assert resp["data"]["appcode_candidate"] == "wgid"


def test_cicd_preview_link_missing_appcode_requires_confirmation(tmp_path):
    api = _api_with_root(tmp_path)
    resp = api.cicd_preview_link("https://host/scm/team/newapp.git")
    data = resp["data"]
    assert data["matched_appcode"] == ""
    assert data["appcode_exists"] is False
    assert data["needs_confirmation"] is True
    assert data["target_repo_path"].endswith("newapp\\CICD\\newapp") or data["target_repo_path"].endswith("newapp/CICD/newapp")


def test_cicd_preview_link_warns_when_candidate_has_separators(tmp_path):
    api = _api_with_root(tmp_path)
    resp = api.cicd_preview_link("https://host/scm/team/wgid-cicd.git")
    assert any("separator" in warning.lower() for warning in resp["data"]["warnings"])


# ── clone from link adapter ─────────────────────────────────────────────
def test_cicd_clone_from_link_missing_appcode_requires_confirmation(tmp_path):
    api = _api_with_root(tmp_path)
    resp = api.cicd_clone_from_link("https://host/scm/team/newapp.git")
    assert resp["ok"] is False
    assert resp["error"]["code"] == "CICD_CLONE_FROM_LINK_FAILED"
    assert "Create appcode confirmation is required" in resp["error"]["message"]


def test_cicd_clone_from_link_confirmed_creates_tree_and_starts_clone(tmp_path, monkeypatch):
    started = {}

    def fake_start_clone(self, clone_url, dest_dir):
        started["clone_url"] = clone_url
        started["dest_dir"] = str(dest_dir)
        return {"repo_name": "newapp", "path": str(dest_dir / "newapp"), "status": "cloning"}

    monkeypatch.setattr(cicd.CicdService, "start_clone", fake_start_clone)
    api = _api_with_root(tmp_path)
    resp = api.cicd_clone_from_link("https://host/scm/team/newapp.git", confirm_create=True)
    data = resp["data"]
    root = tmp_path / "root" / "newapp"
    assert resp["ok"] is True
    assert data["status"] == "cloning"
    assert data["repo_name"] == "newapp"
    assert data["appcode"] == "newapp"
    assert data["job_id"] == "newapp"
    assert data["repo_id"]
    assert started["dest_dir"].endswith("newapp\\CICD") or started["dest_dir"].endswith("newapp/CICD")
    assert (root / "CICD").is_dir()
    year_dirs = [p for p in root.iterdir() if p.name.isdigit()]
    assert year_dirs
    year = year_dirs[0]
    for state in ["UAT_PREPARE", "PROD_READY", "IMPLEMENTED", "POSTPONED", "CANCELED"]:
        assert (year / "CR" / state).is_dir()
    assert (year / "Non-CR").is_dir()
    assert (root / "appcode.json").is_file()


def test_cicd_clone_from_link_existing_appcode_keeps_config(tmp_path, monkeypatch):
    def fake_start_clone(self, clone_url, dest_dir):
        return {"repo_name": "myapp", "path": str(dest_dir / "myapp"), "status": "cloning"}

    monkeypatch.setattr(cicd.CicdService, "start_clone", fake_start_clone)
    api = _api_with_root(tmp_path)
    assert api.appcode_add("myapp")["ok"] is True
    before = api.appcode_get_config("myapp")["data"]
    resp = api.cicd_clone_from_link("https://host/scm/team/myapp.git")
    after = api.appcode_get_config("myapp")["data"]
    assert resp["ok"] is True
    assert after == before


def test_cicd_clone_from_link_existing_same_remote_returns_exists(tmp_path, monkeypatch):
    api = _api_with_root(tmp_path)
    assert api.appcode_add("myapp")["ok"] is True
    repo = tmp_path / "root" / "myapp" / "CICD" / "myapp"
    repo.mkdir(parents=True)
    monkeypatch.setattr(cicd.CicdService, "remote_url", lambda self, path: "https://host/scm/team/myapp.git")
    resp = api.cicd_clone_from_link("https://host/scm/team/myapp.git")
    assert resp["ok"] is True
    assert resp["data"]["status"] == "exists"
    assert resp["data"]["repo_name"] == "myapp"


def test_cicd_clone_from_link_existing_different_remote_blocks(tmp_path, monkeypatch):
    api = _api_with_root(tmp_path)
    assert api.appcode_add("myapp")["ok"] is True
    repo = tmp_path / "root" / "myapp" / "CICD" / "myapp"
    repo.mkdir(parents=True)
    monkeypatch.setattr(cicd.CicdService, "remote_url", lambda self, path: "https://host/scm/team/other.git")
    resp = api.cicd_clone_from_link("https://host/scm/team/myapp.git")
    assert resp["ok"] is False
    assert "different remote" in resp["error"]["message"]


# ── repo id / status / workspace ───────────────────────────────────────
def test_cicd_repo_status_rejects_repo_id_escape(tmp_path):
    api = _api_with_root(tmp_path)
    assert api.appcode_add("myapp")["ok"] is True
    bad_id = cicd.encode_repo_id("myapp", "../evil")
    resp = api.cicd_repo_status(bad_id)
    assert resp["ok"] is False
    assert "outside CICD folder" in resp["error"]["message"]


def test_parse_git_status_porcelain_branch_changes():
    text = "## cicd...origin/cicd [ahead 1, behind 2]\n M a.txt\nA  staged.txt\n?? new.txt\nUU conflict.txt\n D old.txt\n"
    result = cicd.parse_git_status(text)
    assert result["branch"] == "cicd"
    assert result["upstream"] == "origin/cicd"
    assert result["ahead"] == 1
    assert result["behind"] == 2
    assert result["dirty"] is True
    assert result["conflicted"] is True
    changes = {item["rel_path"]: item for item in result["changes"]}
    assert changes["a.txt"]["status"] == "modified"
    assert changes["staged.txt"]["status"] == "staged"
    assert changes["new.txt"]["status"] == "untracked"
    assert changes["conflict.txt"]["status"] == "conflict"
    assert changes["old.txt"]["status"] == "deleted"


def test_run_git_uses_safe_subprocess_conventions(tmp_path, monkeypatch):
    captured = {}

    def fake_run(cmd, **kwargs):
        captured["cmd"] = cmd
        captured["kwargs"] = kwargs
        return subprocess.CompletedProcess(cmd, 0, stdout="ok", stderr="")

    monkeypatch.setattr(cicd.subprocess, "run", fake_run)
    cicd.run_git(tmp_path, ["status"], timeout=12)
    assert captured["cmd"][-1] == "status"
    assert captured["kwargs"]["shell"] is False
    assert captured["kwargs"]["timeout"] == 12
    assert captured["kwargs"]["env"]["GIT_TERMINAL_PROMPT"] == "0"
    assert "creationflags" in captured["kwargs"]


def test_cicd_workspace_returns_appcodes_and_repo_ids(tmp_path):
    api = _api_with_root(tmp_path)
    assert api.appcode_add("myapp")["ok"] is True
    (tmp_path / "root" / "myapp" / "CICD" / "repo1").mkdir(parents=True)
    resp = api.cicd_workspace()
    assert resp["ok"] is True
    assert resp["data"]["appcodes"][0]["name"] == "myapp"
    repo = resp["data"]["repos"][0]
    assert repo["name"] == "repo1"
    assert repo["repo_id"]


def test_cicd_repo_status_bridge(tmp_path, monkeypatch):
    api = _api_with_root(tmp_path)
    assert api.appcode_add("myapp")["ok"] is True
    (tmp_path / "root" / "myapp" / "CICD" / "repo1").mkdir(parents=True)

    def fake_run(cmd, **kwargs):
        return subprocess.CompletedProcess(cmd, 0, stdout="## cicd...origin/cicd [ahead 1]\n M pipe.yml\n", stderr="")

    monkeypatch.setattr(cicd.subprocess, "run", fake_run)
    resp = api.cicd_repo_status(cicd.encode_repo_id("myapp", "repo1"))
    assert resp["ok"] is True
    assert resp["data"]["branch"] == "cicd"
    assert resp["data"]["ahead"] == 1
    assert resp["data"]["changes"][0]["rel_path"] == "pipe.yml"


# ── parse_porcelain ────────────────────────────────────────────────────
def test_parse_porcelain_categories():
    text = " M src/main.py\n?? new.sh\nA  staged.txt\nMM both.py\n"
    result = cicd.parse_porcelain(text)
    assert result["src/main.py"] == "modified"
    assert result["new.sh"] == "untracked"
    assert result["staged.txt"] == "staged"
    assert result["both.py"] == "staged"  # index change wins


def test_parse_porcelain_rename_maps_new_path():
    assert cicd.parse_porcelain("R  old.py -> new.py\n") == {"new.py": "staged"}


# ── build_file_tree ────────────────────────────────────────────────────
def test_build_file_tree_nests_skips_git_attaches_status(tmp_path):
    (tmp_path / ".git").mkdir()
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "main.py").write_text("x", encoding="utf-8")
    (tmp_path / "README.md").write_text("y", encoding="utf-8")
    tree = cicd.build_file_tree(tmp_path, {"src/main.py": "modified"})
    names = [n["name"] for n in tree]
    assert ".git" not in names
    assert names[0] == "src"  # dirs before files
    src_node = next(n for n in tree if n["name"] == "src")
    assert src_node["type"] == "dir"
    child = src_node["children"][0]
    assert child["name"] == "main.py" and child["git_status"] == "modified"
    readme = next(n for n in tree if n["name"] == "README.md")
    assert readme["git_status"] == ""


# ── check_git (monkeypatched) ──────────────────────────────────────────
def test_check_git_absent(monkeypatch):
    monkeypatch.setattr(cicd.shutil, "which", lambda _: None)
    assert cicd.check_git() == {"installed": False, "version": None}


def test_check_git_present(monkeypatch):
    monkeypatch.setattr(cicd.shutil, "which", lambda _: "C:/git.exe")

    def fake_run(*a, **k):
        return subprocess.CompletedProcess(a, 0, stdout="git version 2.45.0\n", stderr="")

    monkeypatch.setattr(cicd.subprocess, "run", fake_run)
    status = cicd.check_git()
    assert status["installed"] is True
    assert "2.45.0" in status["version"]


# ── clone job lifecycle (monkeypatched subprocess) ─────────────────────
def test_start_clone_rejects_existing_dest(tmp_path, monkeypatch):
    monkeypatch.setattr(cicd, "check_git", lambda: {"installed": True, "version": "x"})
    (tmp_path / "myapp").mkdir()
    service = cicd.CicdService()
    with pytest.raises(ValueError):
        service.start_clone("https://host/scm/t/myapp.git", tmp_path)


def test_clone_success_sets_done(tmp_path, monkeypatch):
    monkeypatch.setattr(cicd, "check_git", lambda: {"installed": True, "version": "x"})

    def fake_run(cmd, *a, **k):
        return subprocess.CompletedProcess(cmd, 0, stdout="", stderr="")

    monkeypatch.setattr(cicd.subprocess, "run", fake_run)
    service = cicd.CicdService()
    started = service.start_clone("https://host/scm/t/myapp.git", tmp_path)
    assert started["repo_name"] == "myapp"
    # daemon thread is trivial with a fake run; poll until it settles.
    for _ in range(50):
        if service.clone_status("myapp")["status"] != "cloning":
            break
        time.sleep(0.01)
    assert service.clone_status("myapp")["status"] == "done"


def test_clone_failure_sets_error(tmp_path, monkeypatch):
    monkeypatch.setattr(cicd, "check_git", lambda: {"installed": True, "version": "x"})

    def fake_run(cmd, *a, **k):
        return subprocess.CompletedProcess(cmd, 128, stdout="", stderr="fatal: auth failed")

    monkeypatch.setattr(cicd.subprocess, "run", fake_run)
    service = cicd.CicdService()
    service.start_clone("https://host/scm/t/myapp.git", tmp_path)
    for _ in range(50):
        if service.clone_status("myapp")["status"] != "cloning":
            break
        time.sleep(0.01)
    result = service.clone_status("myapp")
    assert result["status"] == "error" and "auth failed" in result["error"]


# ── bridge envelope (fake service) ─────────────────────────────────────
class FakeCicdService:
    def __init__(self):
        self.calls = []

    def git_status(self):
        self.calls.append("git_status")
        return {"installed": True, "version": "git version 2.45.0"}

    def start_clone(self, clone_url, dest_dir):
        self.calls.append(("start_clone", clone_url))
        return {"repo_name": "myapp", "path": str(dest_dir), "status": "cloning"}

    def clone_status(self, repo_name):
        return {"status": "done", "error": ""}

    def list_repos(self, cicd_dir):
        return [{"name": "myapp", "path": str(cicd_dir), "status": {"modified": 1, "untracked": 0, "staged": 0, "clean": False}}]

    def list_files(self, repo_path):
        return [{"name": "README.md", "path": str(repo_path), "type": "file", "git_status": "", "children": []}]


class _CicdAdapterStub:
    """Mimics _CicdServiceAdapter surface for the bridge test."""

    def __init__(self, service):
        self._service = service

    def git_status(self):
        return self._service.git_status()

    def preview_link(self, clone_url):
        return {"repo_name": "myapp", "appcode_candidate": "myapp"}

    def clone(self, appcode, clone_url):
        return self._service.start_clone(clone_url, "/tmp/cicd")

    def clone_from_link(self, clone_url, appcode_override="", confirm_create=False):
        return {"job_id": "myapp", "repo_id": "abc", "repo_name": "myapp", "appcode": "myapp", "status": "cloning"}

    def clone_status(self, repo_name):
        return self._service.clone_status(repo_name)

    def list_repos(self, appcode):
        return self._service.list_repos("/tmp/cicd")

    def list_files(self, repo_path):
        return self._service.list_files(repo_path)


def test_bridge_git_status_ok():
    api = JsApi(dashboard_service=None, cicd_service=_CicdAdapterStub(FakeCicdService()))
    resp = api.cicd_git_status()
    assert resp["ok"] is True and resp["data"]["installed"] is True


def test_bridge_preview_link_ok():
    api = JsApi(dashboard_service=None, cicd_service=_CicdAdapterStub(FakeCicdService()))
    resp = api.cicd_preview_link("https://host/scm/team/myapp.git")
    assert resp["ok"] is True and resp["data"]["repo_name"] == "myapp"


def test_bridge_clone_from_link_ok():
    api = JsApi(dashboard_service=None, cicd_service=_CicdAdapterStub(FakeCicdService()))
    resp = api.cicd_clone_from_link("https://host/scm/team/myapp.git")
    assert resp["ok"] is True and resp["data"]["status"] == "cloning"


def test_bridge_service_unavailable():
    api = JsApi(dashboard_service=None)
    resp = api.cicd_git_status()
    assert resp["ok"] is False and resp["error"]["code"] == "SERVICE_UNAVAILABLE"
