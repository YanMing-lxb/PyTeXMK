"""用例：check_project_name 路径约束——禁止绝对路径与 `..` 越界。"""
import pytest
from pytexmk.tex_project import MainFileOperation


def test_check_project_name_rejects_absolute_path(tmp_path):
    abs_path = str((tmp_path / "main.tex").resolve())  # Windows 上绝对路径
    with pytest.raises(SystemExit):
        MainFileOperation().check_project_name(["main"], abs_path, ".tex")


def test_check_project_name_rejects_parent_escape():
    with pytest.raises(SystemExit):
        MainFileOperation().check_project_name(["main"], "../escape/main.tex", ".tex")