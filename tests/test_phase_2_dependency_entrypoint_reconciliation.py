from __future__ import annotations

import ast
import re
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

APPROVED_RUNTIME_DEPS = {
    "apscheduler",
    "pyautogui",
    "pyinstaller",
    "pyperclip",
    "python-dateutil",
    "pywebview",
    "pywin32",
    "send2trash",
    "watchdog",
}

LEGACY_RUNTIME_DEPS = {"pyqt6"}


def _normalize_dependency_name(requirement: str) -> str:
    requirement = requirement.strip()
    requirement = requirement.split(";", 1)[0].strip()
    match = re.match(r"([A-Za-z0-9_.-]+)", requirement)
    assert match is not None, f"Could not parse dependency name from {requirement!r}"
    return match.group(1).replace("_", "-").lower()


def _requirements_dependencies() -> set[str]:
    lines = (ROOT / "requirements.txt").read_text(encoding="utf-8").splitlines()
    return {
        _normalize_dependency_name(line)
        for line in lines
        if line.strip() and not line.lstrip().startswith("#")
    }


def _pyproject() -> dict:
    return tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))


def _pyproject_dependencies() -> set[str]:
    dependencies = _pyproject()["project"]["dependencies"]
    return {_normalize_dependency_name(dep) for dep in dependencies}


def test_pyproject_declares_approved_runtime_dependencies() -> None:
    assert APPROVED_RUNTIME_DEPS <= _pyproject_dependencies()


def test_pyproject_runtime_dependencies_match_requirements_baseline() -> None:
    requirements_deps = _requirements_dependencies()
    pyproject_deps = _pyproject_dependencies()

    assert APPROVED_RUNTIME_DEPS <= requirements_deps
    assert APPROVED_RUNTIME_DEPS <= pyproject_deps
    assert pyproject_deps == requirements_deps


def test_pyproject_does_not_declare_legacy_pyqt6_runtime() -> None:
    assert _pyproject_dependencies().isdisjoint(LEGACY_RUNTIME_DEPS)


def test_pyproject_has_pep517_build_system() -> None:
    data = _pyproject()

    assert data["build-system"]["requires"] == ["setuptools>=68"]
    assert data["build-system"]["build-backend"] == "setuptools.build_meta"


def test_project_tracker_main_calls_app_web_run() -> None:
    source = (ROOT / "main.py").read_text(encoding="utf-8")
    tree = ast.parse(source)

    imports_run = any(
        isinstance(node, ast.ImportFrom)
        and node.module == "app_web"
        and any(alias.name == "run" for alias in node.names)
        for node in tree.body
    )
    raises_system_exit_run = any(
        isinstance(node, ast.If)
        and any(
            isinstance(child, ast.Raise)
            and isinstance(child.exc, ast.Call)
            and isinstance(child.exc.func, ast.Name)
            and child.exc.func.id == "SystemExit"
            and child.exc.args
            and isinstance(child.exc.args[0], ast.Call)
            and isinstance(child.exc.args[0].func, ast.Name)
            and child.exc.args[0].func.id == "run"
            for child in node.body
        )
        for node in tree.body
    )

    assert imports_run
    assert raises_system_exit_run


def test_pyinstaller_spec_uses_project_tracker_main_entry_script() -> None:
    spec_text = (ROOT / "project_tracker_dbs.spec").read_text(encoding="utf-8")

    assert 'ENTRY_SCRIPT = str(REPO_ROOT / "main.py")' in spec_text
    assert "ENTRY_SCRIPT" in spec_text
    assert "Analysis(" in spec_text
