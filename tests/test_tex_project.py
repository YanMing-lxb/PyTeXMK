"""用例：check_project_name 路径约束——禁止绝对路径与 `..` 越界。"""
import re

import pytest

from pytexmk.tex_project import MainFileOperation


def test_check_project_name_rejects_absolute_path(tmp_path):
    abs_path = str((tmp_path / "main.tex").resolve())  # Windows 上绝对路径
    with pytest.raises(SystemExit):
        MainFileOperation().check_project_name(["main"], abs_path, ".tex")


def test_check_project_name_rejects_parent_escape():
    with pytest.raises(SystemExit):
        MainFileOperation().check_project_name(["main"], "../escape/main.tex", ".tex")


@pytest.mark.parametrize(
    ("original", "expected"),
    [
        # 无选项 -> 追加 / 已有 draft 不重复添加
        (r"\documentclass{article}", r"\documentclass[draft]{article}"),
        (r"\documentclass[draft]{article}", r"\documentclass[draft]{article}"),
        # 其它选项顺序必须保持（旧实现用 set 拼接，顺序随机）
        (r"\documentclass[a4paper,12pt]{article}", r"\documentclass[a4paper,12pt,draft]{article}"),
        (r"\documentclass[draft,11pt]{ctexart}", r"\documentclass[draft,11pt]{ctexart}"),
        # 含等号的键值选项不能被打散
        (
            r"\documentclass[xcolor=dvipsnames,pdf]{beamer}",
            r"\documentclass[xcolor=dvipsnames,pdf,draft]{beamer}",
        ),
    ],
)
def test_draft_model_enable(monkeypatch, tmp_path, original, expected):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "main.tex").write_text(original + "\n", encoding="utf-8")

    MainFileOperation().draft_model("main", True, True)
    assert (tmp_path / "main.tex").read_text(encoding="utf-8").strip() == expected


def test_draft_model_disable_is_idempotent(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    original = r"\documentclass[a4paper,draft]{article}"
    (tmp_path / "main.tex").write_text(original + "\n", encoding="utf-8")

    mfo = MainFileOperation()
    mfo.draft_model("main", True, False)
    first = (tmp_path / "main.tex").read_text(encoding="utf-8")
    mfo.draft_model("main", True, False)
    assert (tmp_path / "main.tex").read_text(encoding="utf-8") == first
    assert first.strip() == r"\documentclass[a4paper]{article}"


def test_draft_model_ignores_commented_line(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    original = "%\\documentclass{article}"
    (tmp_path / "main.tex").write_text(original + "\n", encoding="utf-8")

    MainFileOperation().draft_model("main", True, True)
    assert (tmp_path / "main.tex").read_text(encoding="utf-8").strip() == original


def test_documentclass_pattern_handles_named_groups():
    """冒烟：草稿模式依赖的分组名索引（3.5+ 语法）在当前解释器可用。"""
    match = re.search(r"(?P<opts>\[[^\]]*\])?\{(?P<class>[^\}]*)\}", "[a4paper]{article}")
    assert match is not None
    assert match["opts"] == "[a4paper]"
    assert match["class"] == "article"
