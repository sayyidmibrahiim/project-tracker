"""Piece D CICD service tests (consolidated — user rule: one file)."""

from __future__ import annotations

import subprocess
import time

import pytest

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

    def clone(self, appcode, clone_url):
        return self._service.start_clone(clone_url, "/tmp/cicd")

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


def test_bridge_service_unavailable():
    api = JsApi(dashboard_service=None)
    resp = api.cicd_git_status()
    assert resp["ok"] is False and resp["error"]["code"] == "SERVICE_UNAVAILABLE"
