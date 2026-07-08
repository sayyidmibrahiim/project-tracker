"""Piece D — CICD Bitbucket integration service.

Git CLI detection + background `git clone -b cicd` + repo/file browsing.
Stdlib only (subprocess/shutil) — office network blocks new deps.
Domain rule: never crash on missing git or non-git folders (DEFAULT AMAN).
"""

from __future__ import annotations

from dataclasses import dataclass
import shutil
import subprocess
import sys
import threading
from pathlib import Path
from urllib.parse import unquote, urlparse

from core.rules import validate_windows_folder_name

# First subprocess in the app: suppress the console window on Windows so git
# calls don't flash a black box. 0 elsewhere (flag is Windows-only).
_CREATE_NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0) if sys.platform == "win32" else 0
_CLONE_TIMEOUT_SECONDS = 600


@dataclass(frozen=True)
class CloneUrlInfo:
    clone_url: str
    repo_name: str
    appcode_candidate: str
    host: str


def _git() -> str:
    """Resolve the git executable, falling back to bare 'git'."""
    return shutil.which("git") or "git"


def check_git() -> dict[str, object]:
    """Return {installed, version}. Never raises."""
    exe = shutil.which("git")
    if exe is None:
        return {"installed": False, "version": None}
    try:
        proc = subprocess.run(
            [exe, "--version"],
            capture_output=True,
            text=True,
            timeout=15,
            creationflags=_CREATE_NO_WINDOW,
        )
        version = (proc.stdout or "").strip() or None
        return {"installed": proc.returncode == 0, "version": version}
    except Exception:
        return {"installed": False, "version": None}


def parse_repo_name(clone_url: str) -> str:
    """Extract a folder-safe repo name from a clone URL."""
    return parse_clone_url(clone_url).repo_name


def parse_clone_url(clone_url: str) -> CloneUrlInfo:
    """Parse a HTTP(S) Bitbucket clone URL into repo/appcode candidates."""
    url = str(clone_url or "").strip().rstrip("/")
    if not url:
        raise ValueError("Clone URL is required")
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"}:
        raise ValueError("Clone URL must use http or https")
    if parsed.username or parsed.password:
        raise ValueError("Clone URL must not include username or password")
    if not parsed.netloc:
        raise ValueError("Clone URL host is required")
    parts = [unquote(part) for part in parsed.path.split("/") if part]
    if len(parts) >= 4 and parts[-4].casefold() == "projects" and parts[-2].casefold() == "repos":
        name = parts[-1]
    else:
        name = parts[-1] if parts else ""
    if name.casefold().endswith(".git"):
        name = name[:-4]
    name = name.strip()
    if not name:
        raise ValueError("Could not parse a repository name from the URL")
    try:
        validate_windows_folder_name(name)
    except Exception as exc:
        raise ValueError(str(exc)) from exc
    return CloneUrlInfo(clone_url=url, repo_name=name, appcode_candidate=name, host=parsed.netloc)


def _classify(code: str) -> str:
    """Map a git-porcelain XY status code to a display category."""
    if code == "??":
        return "untracked"
    index, worktree = code[0], code[1]
    if index not in " ?":
        return "staged"
    if worktree != " ":
        return "modified"
    return "clean"


def parse_porcelain(text: str) -> dict[str, str]:
    """Parse `git status --porcelain` output → {relpath: category}.

    Clean entries are omitted. Rename lines ('R  a -> b') map the new path.
    """
    result: dict[str, str] = {}
    for line in (text or "").splitlines():
        if len(line) < 4:
            continue
        code, rest = line[:2], line[3:]
        category = _classify(code)
        if category == "clean":
            continue
        path = rest.split(" -> ", 1)[-1].strip().strip('"')
        if path:
            result[path] = category
    return result


def build_file_tree(repo_path: Path, status_map: dict[str, str]) -> list[dict]:
    """Recursive file tree with per-file git status. '.git' skipped, dirs first."""
    repo_path = Path(repo_path)

    def walk(directory: Path) -> list[dict]:
        nodes: list[dict] = []
        try:
            children = sorted(directory.iterdir(), key=lambda p: (p.is_file(), p.name.lower()))
        except OSError:
            return nodes
        for child in children:
            if child.name == ".git":
                continue
            rel = child.relative_to(repo_path).as_posix()
            if child.is_dir():
                nodes.append(
                    {"name": child.name, "path": str(child), "type": "dir",
                     "git_status": "", "children": walk(child)}
                )
            else:
                nodes.append(
                    {"name": child.name, "path": str(child), "type": "file",
                     "git_status": status_map.get(rel, ""), "children": []}
                )
        return nodes

    return walk(repo_path)


def _run_porcelain(repo_path: Path) -> str:
    """Run `git status --porcelain` in repo_path. '' if it fails (not a git repo)."""
    try:
        proc = subprocess.run(
            [_git(), "-C", str(repo_path), "status", "--porcelain"],
            capture_output=True,
            text=True,
            timeout=30,
            creationflags=_CREATE_NO_WINDOW,
        )
        if proc.returncode != 0:
            return ""
        return proc.stdout or ""
    except Exception:
        return ""


def _repo_summary(repo_path: Path) -> dict[str, object]:
    """Per-repo status summary {modified, untracked, staged, clean}."""
    status_map = parse_porcelain(_run_porcelain(repo_path))
    counts = {"modified": 0, "untracked": 0, "staged": 0}
    for category in status_map.values():
        counts[category] = counts.get(category, 0) + 1
    counts["clean"] = not status_map
    return counts


class CicdService:
    """Git detection + background clone (poll-able) + repo/file browsing.

    ponytail: clone jobs live in a process-lifetime dict keyed by repo_name
    (few repos per session). Upgrade to persisted/queued jobs only if the user
    ever clones dozens concurrently.
    """

    def __init__(self) -> None:
        self._jobs: dict[str, dict[str, object]] = {}
        self._lock = threading.Lock()

    # ── detection ──────────────────────────────────────────────────────
    def git_status(self) -> dict[str, object]:
        return check_git()

    # ── clone ──────────────────────────────────────────────────────────
    def _set_job(self, repo_name: str, status: str, error: str) -> None:
        with self._lock:
            self._jobs[repo_name] = {"status": status, "error": error}

    def clone_status(self, repo_name: str) -> dict[str, object]:
        with self._lock:
            job = self._jobs.get(str(repo_name))
        if job is None:
            return {"status": "unknown", "error": ""}
        return dict(job)

    def start_clone(self, clone_url: str, dest_dir: Path) -> dict[str, object]:
        """Validate, then clone the 'cicd' branch on a daemon thread.

        Returns immediately with {repo_name, path, status:'cloning'}.
        Poll clone_status(repo_name) until 'done' or 'error'.
        """
        if not check_git()["installed"]:
            raise ValueError("Git CLI is not installed")
        repo_name = parse_repo_name(clone_url)
        dest = Path(dest_dir) / repo_name
        if dest.exists():
            raise ValueError(f"Repository already cloned: {repo_name}")
        with self._lock:
            if self._jobs.get(repo_name, {}).get("status") == "cloning":
                raise ValueError(f"Clone already in progress: {repo_name}")
        Path(dest_dir).mkdir(parents=True, exist_ok=True)
        self._set_job(repo_name, "cloning", "")
        url = str(clone_url).strip()
        thread = threading.Thread(
            target=self._do_clone, args=(url, dest, repo_name), daemon=True
        )
        thread.start()
        return {"repo_name": repo_name, "path": str(dest), "status": "cloning"}

    def _do_clone(self, url: str, dest: Path, repo_name: str) -> None:
        try:
            proc = subprocess.run(
                [_git(), "clone", "-b", "cicd", "--single-branch", url, str(dest)],
                capture_output=True,
                text=True,
                timeout=_CLONE_TIMEOUT_SECONDS,
                creationflags=_CREATE_NO_WINDOW,
            )
            if proc.returncode == 0:
                self._set_job(repo_name, "done", "")
            else:
                message = (proc.stderr or proc.stdout or "git clone failed").strip()
                self._set_job(repo_name, "error", message)
        except subprocess.TimeoutExpired:
            self._set_job(repo_name, "error", "Clone timed out. Check VPN/connection.")
        except Exception as exc:  # noqa: BLE001 — surface any git failure to UI
            self._set_job(repo_name, "error", str(exc))

    # ── browse ─────────────────────────────────────────────────────────
    def list_repos(self, cicd_dir: Path) -> list[dict]:
        directory = Path(cicd_dir)
        if not directory.is_dir():
            return []
        repos: list[dict] = []
        for child in sorted(directory.iterdir(), key=lambda p: p.name.lower()):
            if not child.is_dir():
                continue
            repos.append(
                {"name": child.name, "path": str(child), "status": _repo_summary(child)}
            )
        return repos

    def list_files(self, repo_path: Path) -> list[dict]:
        path = Path(repo_path)
        if not path.is_dir():
            return []
        status_map = parse_porcelain(_run_porcelain(path))
        return build_file_tree(path, status_map)
