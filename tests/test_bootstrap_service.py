from __future__ import annotations

from pathlib import Path

from services.bootstrap_service import rewrite_path


def test_rewrite_path_inside_root():
    old = Path("D:/WORK/CR")
    new = Path("C:/Users/user/Documents/Project Tracker")
    result = rewrite_path(Path("D:/WORK/CR/SSID/2026"), old, new)
    assert result == Path("C:/Users/user/Documents/Project Tracker/SSID/2026")


def test_rewrite_path_outside_root():
    old = Path("D:/WORK/CR")
    new = Path("C:/Users/user/Documents/Project Tracker")
    external = Path("D:/Other/Vault")
    result = rewrite_path(external, old, new)
    assert result == external


def test_rewrite_path_none():
    result = rewrite_path(None, Path("D:/WORK"), Path("C:/New"))
    assert result is None


def test_rewrite_path_is_old_root_itself():
    old = Path("D:/WORK/CR")
    new = Path("C:/Users/user/Documents/Project Tracker")
    result = rewrite_path(old, old, new)
    assert result == new
