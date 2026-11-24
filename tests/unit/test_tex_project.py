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

    MainFileOperation().draft_model("main", True)
    assert (tmp_path / "main.tex").read_text(encoding="utf-8").strip() == expected


def test_restore_draft_is_idempotent(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    original = r"\documentclass[a4paper]{article}"
    (tmp_path / "main.tex").write_text(original + "\n", encoding="utf-8")

    mfo = MainFileOperation()
    mfo.draft_model("main", True)
    mfo.restore_draft()
    first = (tmp_path / "main.tex").read_text(encoding="utf-8")
    mfo.restore_draft()
    assert (tmp_path / "main.tex").read_text(encoding="utf-8") == first
    assert first.strip() == original


def test_draft_model_ignores_commented_line(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    original = "%\\documentclass{article}"
    (tmp_path / "main.tex").write_text(original + "\n", encoding="utf-8")

    MainFileOperation().draft_model("main", True)
    assert (tmp_path / "main.tex").read_text(encoding="utf-8").strip() == original


def test_draft_marker_recovers_after_crashed_run(tmp_path):
    """上次进程崩溃留下的标记，下一次非 draft 编译要摘除 draft 并清标记。"""
    aux = tmp_path / "Auxiliary"
    aux.mkdir()
    (tmp_path / "main.tex").write_text(
        "\\documentclass[draft]{article}\n", encoding="utf-8"
    )
    (aux / ".pytexmk-draft").write_text(
        str(tmp_path / "main.tex") + "\n", encoding="utf-8"
    )

    MainFileOperation().draft_model("main", False, aux)

    assert (tmp_path / "main.tex").read_text(encoding="utf-8").strip() == (
        "\\documentclass{article}"
    )
    assert not (aux / ".pytexmk-draft").exists()


def test_author_draft_is_kept_without_pytexmk_marker(tmp_path):
    """没有 PyTeXMK 标记时不能“自愈”掉作者自己写的 draft。"""
    (tmp_path / "main.tex").write_text(
        "\\documentclass[draft]{article}\n", encoding="utf-8"
    )
    MainFileOperation().draft_model("main", False, tmp_path / "Auxiliary")
    assert "draft" in (tmp_path / "main.tex").read_text(encoding="utf-8")


def test_documentclass_pattern_handles_named_groups():
    """冒烟：草稿模式依赖的分组名索引（3.5+ 语法）在当前解释器可用。"""
    match = re.search(r"(?P<opts>\[[^\]]*\])?\{(?P<class>[^\}]*)\}", "[a4paper]{article}")
    assert match is not None
    assert match["opts"] == "[a4paper]"
    assert match["class"] == "article"


def _run_with_fake_engine(tmp_path, monkeypatch, draft):
    """跑一遍 RUN：编译模型与编译主体都换成桩，返回编译期间读到的源文件。"""
    from pytexmk import compile_engine

    monkeypatch.chdir(tmp_path)
    (tmp_path / "main.tex").write_text(
        "\\documentclass{article}\n", encoding="utf-8"
    )

    class FakeModel:
        detector = None

        def __init__(self, *args, **kwargs):
            pass

    monkeypatch.setattr(compile_engine, "CompileLaTeX", FakeModel)

    seen: dict[str, str] = {}

    def fake_run_impl(*args, **kwargs):
        seen["content"] = (tmp_path / "main.tex").read_text(encoding="utf-8")
        return {}

    monkeypatch.setattr(compile_engine, "_run_impl", fake_run_impl)

    compile_engine.RUN(
        {},
        "main",
        "XeLaTeX",
        ["main.pdf"],
        ["main.log"],
        "./Build/",
        "./Auxiliary/",
        non_quiet=False,
        draft=draft,
        shell_escape=False,
    )
    return seen


def test_run_applies_draft_only_while_compiling(tmp_path, monkeypatch):
    """`-dr` 必须在编译期间真的带上 draft，结束（含异常）后必须摘干净。

    回归：调用点曾把 ``not draft`` 传给第二个布尔开关，以致 ``-dr``
    走「关闭草稿」分支，草稿模式静默失效。
    """
    seen = _run_with_fake_engine(tmp_path, monkeypatch, True)

    assert "draft" in seen["content"]
    assert (tmp_path / "main.tex").read_text(encoding="utf-8").strip() == (
        "\\documentclass{article}"
    )
    assert not (tmp_path / "Auxiliary" / ".pytexmk-draft").exists()


def test_run_without_draft_leaves_source_alone(tmp_path, monkeypatch):
    """不带 `-dr` 时不得改写源文件，也不得留下草稿标记。"""
    seen = _run_with_fake_engine(tmp_path, monkeypatch, False)

    assert seen["content"] == "\\documentclass{article}\n"
    assert (tmp_path / "main.tex").read_text(encoding="utf-8") == (
        "\\documentclass{article}\n"
    )
    assert not (tmp_path / "Auxiliary" / ".pytexmk-draft").exists()

