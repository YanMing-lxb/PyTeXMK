"""SyncTeX 处理回归测试：取样行、反向落点、缺失/陈旧产物、同目录归档。

这些用例都针对 2026-11 修订前真实踩到的问题：

* 前言 30 行 → 取样行落在 ``\\usepackage``，反向回到 ``\\begin{document}``，
  被判“行号偏差过大”的假失败；
* 取样行映射到 ``\\input`` 的子文件被误判为“定位到错误文件”；
* outdir 与 auxdir 相同 → 归档时先删目标再搬源，PDF/SyncTeX 直接消失。
"""

import os
import re
import types
from pathlib import Path

from pytexmk import synctex as synctex_mod
from pytexmk.cli import cli_compile
from pytexmk.file_ops import FileMoveRemoveManager

LONG_PREAMBLE_TEX = (
    "\\documentclass{article}\n"
    "\\usepackage{amsmath}\n"
    + "% filler preamble line\n" * 30
    + "\\begin{document}\n"
    "First body line.\n"
    "Second body line.\n"
    "\\end{document}\n"
)


def _make_project(tmp_path: Path, text: str = LONG_PREAMBLE_TEX) -> tuple[Path, Path]:
    """准备 main.tex + Build/main.pdf + Build/main.synctex.gz 的最小工程。"""
    tex = tmp_path / "main.tex"
    tex.write_text(text, encoding="utf-8")
    out = tmp_path / "Build"
    out.mkdir()
    pdf = out / "main.pdf"
    pdf.write_bytes(b"%PDF-1.4")
    (out / "main.synctex.gz").write_bytes(b"fake")
    return tex, pdf


def _mock_synctex(monkeypatch, reverse_output):
    """把 _run 换成脚本化的假实现；reverse_output(command) 返回 edit 的输出。"""
    calls: list[list[str]] = []

    def fake_run(command, _cwd):
        calls.append(command)
        if command[1] == "view":
            return 0, "SyncTeX result begin\nPage:1\nx:10.0\ny:20.0\nSyncTeX result end\n"
        return 0, reverse_output(command)

    monkeypatch.setattr(synctex_mod, "_run", fake_run)
    monkeypatch.setattr(synctex_mod.shutil, "which", lambda _name: "synctex")
    return calls


# ---------------------------------------------------------------- 取样行


def test_candidate_lines_skip_preamble():
    r"""取样行必须落在 \begin{document} 之后，而不是第 2 行的 \usepackage。"""
    lines = synctex_mod.candidate_lines(LONG_PREAMBLE_TEX)
    assert lines, "至少要有一个候选行"
    assert 2 not in lines
    assert lines[0] == 34  # “First body line.”
    assert all(line > 33 for line in lines)


def test_candidate_lines_prefers_visible_command():
    r"""正文首行是纯 \input 时，应继续往后找真正有盒子的行。"""
    text = (
        "\\documentclass{article}\n"
        "\\begin{document}\n"
        "\\input{sections/intro}\n"
        "\\section{Introduction}\n"
        "Some text.\n"
        "\\end{document}\n"
    )
    lines = synctex_mod.candidate_lines(text)
    assert lines[0] == 4  # \section{Introduction} 有可见内容


# ---------------------------------------------------------------- 双向校验


def test_check_tolerates_preamble_fallback_reverse(tmp_path, monkeypatch):
    r"""MiKTeX 对前言行会兜底反查到 \begin{document} 附近；正文取样后不该判失败。"""
    tex, pdf = _make_project(tmp_path)
    calls = _mock_synctex(
        monkeypatch, lambda _command: f"Input:{tex}\nLine:35\n"
    )

    report = synctex_mod.check(pdf, tex, root=tmp_path)

    assert report.ok, report.errors
    assert report.sample_line == 34
    assert report.reverse_line == 35
    assert len(calls) >= 2  # 正向 + 反向都跑过


def test_check_accepts_included_subfile(tmp_path, monkeypatch):
    """多文件论文：反向落在项目内的子文件是正常行为，不是“错误文件”。"""
    tex, pdf = _make_project(tmp_path)
    sub = tmp_path / "sections" / "intro.tex"
    sub.parent.mkdir()
    sub.write_text("Text in the sub file.\n", encoding="utf-8")
    _mock_synctex(monkeypatch, lambda _command: f"Input:{sub}\nLine:1\n")

    report = synctex_mod.check(pdf, tex, root=tmp_path)

    assert report.ok, report.errors
    assert report.warnings and "子文件" in report.warnings[0]


def test_check_rejects_file_outside_project(tmp_path, monkeypatch):
    tex, pdf = _make_project(tmp_path)
    outside = tmp_path.parent / "elsewhere.tex"
    _mock_synctex(monkeypatch, lambda _command: f"Input:{outside}\nLine:1\n")

    report = synctex_mod.check(pdf, tex, root=tmp_path)

    assert not report.ok
    assert any("项目外" in error for error in report.errors)


def test_check_reports_missing_synctex(tmp_path, monkeypatch):
    """synctex.gz 缺失时直接给出“需要重新编译”，而不是让 synctex 报 No tag。"""
    tex, pdf = _make_project(tmp_path)
    (tmp_path / "Build" / "main.synctex.gz").unlink()
    calls = _mock_synctex(monkeypatch, lambda _command: f"Input:{tex}\nLine:1\n")

    report = synctex_mod.check(pdf, tex, root=tmp_path)

    assert not report.ok
    assert any("不存在" in error for error in report.errors)
    assert calls == []  # 连 synctex 都不用调


def test_check_warns_about_stale_synctex(tmp_path, monkeypatch):
    tex, pdf = _make_project(tmp_path)
    sync = tmp_path / "Build" / "main.synctex.gz"
    os.utime(sync, (pdf.stat().st_mtime - 30, pdf.stat().st_mtime - 30))
    _mock_synctex(monkeypatch, lambda _command: f"Input:{tex}\nLine:34\n")

    report = synctex_mod.check(pdf, tex, root=tmp_path)

    assert report.ok
    assert any("比 PDF 旧" in warning for warning in report.warnings)


def test_check_line_tolerance(tmp_path, monkeypatch):
    """偏差 5 行以内放行，超过则报错。"""
    tex, pdf = _make_project(tmp_path)
    _mock_synctex(monkeypatch, lambda _command: f"Input:{tex}\nLine:39\n")
    report = synctex_mod.check(pdf, tex, line=34, root=tmp_path)
    assert report.ok, report.errors

    _mock_synctex(monkeypatch, lambda _command: f"Input:{tex}\nLine:45\n")
    report = synctex_mod.check(pdf, tex, line=34, root=tmp_path)
    assert not report.ok
    assert any("偏差过大" in error for error in report.errors)


# ---------------------------------------------------------------- 归档 / 跳过编译


def test_move_specific_files_same_dir_keeps_files(tmp_path):
    """outdir == auxdir 时绝不能“先删目标再搬源”把产物删掉。"""
    (tmp_path / "main.pdf").write_bytes(b"%PDF-1.4")
    (tmp_path / "main.synctex.gz").write_bytes(b"fake")

    moved = FileMoveRemoveManager().move_specific_files(
        ["main.pdf", "main.synctex.gz"], str(tmp_path), str(tmp_path)
    )

    assert moved == 0
    assert (tmp_path / "main.pdf").read_bytes() == b"%PDF-1.4"
    assert (tmp_path / "main.synctex.gz").exists()


def test_same_directory_detection(tmp_path):
    twin = tmp_path / "sub"
    twin.mkdir()
    assert cli_compile._same_directory(tmp_path, str(tmp_path) + os.sep)
    assert not cli_compile._same_directory(tmp_path, twin)


def _write_valid_pdf(path: Path) -> None:
    from pypdf import PdfWriter

    writer = PdfWriter()
    writer.add_blank_page(width=100, height=100)
    with path.open("wb") as handle:
        writer.write(handle)


def test_outputs_present_requires_synctex(tmp_path):
    """只查 PDF 会让“被删掉 synctex”的工程永远跳过编译、永远跳不了转。"""
    state = types.SimpleNamespace(outdir=str(tmp_path), output_name="main")
    assert not cli_compile._outputs_present(state)

    _write_valid_pdf(tmp_path / "main.pdf")
    assert not cli_compile._outputs_present(state)

    (tmp_path / "main.synctex.gz").write_bytes(b"fake")
    assert cli_compile._outputs_present(state)

    (tmp_path / "main.synctex.gz").unlink()
    (tmp_path / "main.synctex").write_bytes(b"fake")
    assert cli_compile._outputs_present(state)


def test_aux_suffixes_do_not_glob_gz():
    """辅助后缀里不能再有裸 .gz，否则 -ca 会删掉用户自己的 *.gz 数据文件。"""
    from pytexmk.cli.cli_state import SUFFIXES_AUX, SUFFIXES_OUT

    assert ".gz" not in SUFFIXES_AUX
    assert ".synctex.gz" in SUFFIXES_OUT


def test_aux_regex_escapes_inner_dots():
    """后缀里的点必须整体转义，不能把用户文件 x.runXxml 当成 main.run.xml。"""
    import argparse
    import logging

    from pytexmk.cli.cli_state import WorkflowState

    state = WorkflowState(args=argparse.Namespace(), logger=logging.getLogger())
    state.output_name = "main"
    state.refresh_file_lists()
    patterns = [re.compile(pattern) for pattern in state.aux_regex_files]
    assert not any(pattern.match("x.runXxml") for pattern in patterns)
    assert any(pattern.match("main.run.xml") for pattern in patterns)
