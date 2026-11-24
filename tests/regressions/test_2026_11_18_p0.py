"""2026-11-18 审查 P0 项的回归测试。

覆盖 9 条 P0 中可被单元测试直接钉住的部分：
* 主文件名被 ``rstrip`` 吃字（``text.tex`` → 空串）；
* native 构建下 nomencl/makeidx 的触发与快照只查 CWD；
* ``.toc`` 变更在 auxdir 里检测不到；
* 索引命令里 Windows 反斜杠路径被 ``shlex`` 拆坏；
* 草稿模式整份回写覆盖编译期间的其它编辑；
* ``latexdiff --style=1`` 非法参数。
"""

import shlex
from pathlib import Path

import pytest

from pytexmk.compile import CompileLaTeX
from pytexmk.detection import _INDEX_REGISTRY, CompilationDetector, _quote_cmd_path
from pytexmk.latexdiff import LaTeXDiff_Aux
from pytexmk.tex_project import MainFileOperation


def _detector(tmp_path: Path, aux: Path) -> CompilationDetector:
    return CompilationDetector(
        "main", "PdfLaTeX", [], [], str(tmp_path), str(aux), False, None
    )


# --------------------------------------------------------------- P0-1 主文件名


@pytest.mark.parametrize("arg", ["text.tex", "text", "next.tex", "latex.tex"])
def test_main_file_name_is_not_eaten_by_rstrip(tmp_path, monkeypatch, arg):
    """``rstrip(".tex")`` 会按字符集裁剪；``text.tex`` 曾被裁成空串。"""
    monkeypatch.chdir(tmp_path)
    (tmp_path / "text.tex").write_text("\\documentclass{article}", encoding="utf-8")
    mfo = MainFileOperation()
    main_files = ["text", "next", "latex"]
    expected = Path(arg).stem if arg.endswith(".tex") else arg
    assert mfo.check_project_name(main_files, arg, ".tex") == expected


# ------------------------------------------------------- P0-2/3 nomencl + 快照


def test_nomencl_trigger_sees_auxiliary_dir(tmp_path):
    """native 构建把 .nlo 写在 Auxiliary，trigger 必须能看见它。"""
    aux = tmp_path / "Auxiliary"
    aux.mkdir()
    (aux / "main.nlo").write_text("\\nomenclatureentry", encoding="utf-8")
    rule = next(r for r in _INDEX_REGISTRY if r.name == "nomencl")
    assert rule.trigger("main", "", aux) is True


def test_index_snapshot_reads_auxiliary_dir(tmp_path):
    """快照必须从 auxdir 读 .nlo，否则 idx 维度永远判"需重跑"。"""
    aux = tmp_path / "Auxiliary"
    aux.mkdir()
    (aux / "main.aux").write_text("\\relax\n", encoding="utf-8")
    (aux / "main.nlo").write_text("\\nomenclatureentry{}{A}{}", encoding="utf-8")
    snap = _detector(tmp_path, aux)._index_aux_content_get()
    assert "main.nlo" in snap
    assert snap["main.nlo"] == "\\nomenclatureentry{}{A}{}"


# --------------------------------------------------------------- P0-4 .toc


def test_toc_change_detected_in_auxiliary_dir(tmp_path):
    aux = tmp_path / "Auxiliary"
    aux.mkdir()
    (aux / "main.toc").write_text("OLD", encoding="utf-8")
    det = _detector(tmp_path, aux)
    assert det.toc_changed_judgment("OLD") is False
    assert det.toc_changed_judgment("NEW") is True


# --------------------------------------------------------------- P0-7 shlex


def test_index_command_keeps_windows_backslashes():
    """``C:\\...\\nomencl.ist`` 加引号后再分词必须还原成一个参数。"""
    ist = r"C:\Program Files\texmf\nomencl.ist"
    command_text = f"makeindex -s {_quote_cmd_path(ist)} -o main.nls main.nlo"
    tokens = [
        CompileLaTeX._strip_wrapping_quotes(tok)
        for tok in shlex.split(command_text, posix=False)
    ]
    assert tokens == ["makeindex", "-s", ist, "-o", "main.nls", "main.nlo"]
    # 回归对照：未加引号的 Windows 路径会被 POSIX 分词吃掉反斜杠
    unquoted = r"makeindex -s C:\texmf\nomencl.ist -o main.nls main.nlo"
    assert r"C:\texmf\nomencl.ist" not in shlex.split(unquoted)


def test_quote_cmd_path_only_quotes_when_needed():
    assert _quote_cmd_path(r"C:\texmf\nomencl.ist") == r"C:\texmf\nomencl.ist"
    assert _quote_cmd_path("C:/Program Files/x.ist") == '"C:/Program Files/x.ist"'


# ------------------------------------------------------------ P0-9 草稿恢复


def test_draft_restore_keeps_concurrent_edits(tmp_path, monkeypatch):
    """恢复草稿时只能摘掉 draft，不能整份回写编译前的快照。"""
    monkeypatch.chdir(tmp_path)
    src = tmp_path / "main.tex"
    src.write_text("\\documentclass[a4paper]{article}\nOLD\n", encoding="utf-8")

    mfo = MainFileOperation()
    mfo.draft_model("main", True)
    assert "draft" in src.read_text(encoding="utf-8")

    # 模拟用户在编译期间又保存了新内容
    src.write_text(src.read_text(encoding="utf-8") + "NEW\n", encoding="utf-8")

    mfo.restore_draft()
    content = src.read_text(encoding="utf-8")
    assert "draft" not in content
    assert "\\documentclass[a4paper]{article}" in content
    assert "OLD" in content
    assert "NEW" in content, "编译期间的编辑被整份回写覆盖了"


# ------------------------------------------------------------ P0-6 --style


def test_latexdiff_command_has_no_illegal_style_flag(tmp_path, monkeypatch):
    class _MSP:
        def __init__(self) -> None:
            self.commands: list[list[str]] = []

        def run_command(self, command, *_args, **kwargs):
            self.commands.append(command)
            # 真实 latexdiff 会通过 stdout_path 产出差异稿；这里模拟写出，
            # 才能校验“产出为空即失败”的新契约。
            target = kwargs.get("stdout_path")
            if target:
                Path(target).write_text("% diff\n", encoding="utf-8")

    # 输出路径是相对 cwd 的 "diff.tex"：必须在临时目录里跑，否则会把
    # 差异稿写进仓库根目录（此前确实漏下过 diff.tex）。
    monkeypatch.chdir(tmp_path)
    lda = LaTeXDiff_Aux(str(tmp_path), [".pdf"], [".aux"], str(tmp_path))
    lda.MSP = _MSP()
    lda.compile_LaTeXDiff("old", "new", "diff", ".tex")
    command = lda.MSP.commands[0]
    assert command[:2] == ["latexdiff", "old.tex"]
    assert not any(token.startswith("--style") for token in command)
    assert (tmp_path / "diff.tex").read_text(encoding="utf-8") == "% diff\n"
