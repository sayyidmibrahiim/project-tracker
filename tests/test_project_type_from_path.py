from pathlib import Path

from core.enums import ProjectType
from infrastructure.filesystem import project_type_from_path


def test_cr_project_path_returns_cr():
    path = Path("D:/WORK/MYAPP/2026/CR/UAT_PREPARE/MyProject")
    assert project_type_from_path(path) == ProjectType.CR


def test_non_cr_project_path_returns_non_cr():
    path = Path("D:/WORK/MYAPP/2026/Non-CR/MyTask")
    assert project_type_from_path(path) == ProjectType.NON_CR


def test_cr_in_implemented_state():
    path = Path("D:/WORK/MYAPP/2026/CR/IMPLEMENTED/DoneProject")
    assert project_type_from_path(path) == ProjectType.CR
