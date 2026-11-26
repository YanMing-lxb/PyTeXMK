"""2026-11-23 第二轮：产物、验证与诊断契约的回归测试。

覆盖报告里尚未落地、且能在纯 Python 层复现的行为：

* 明文 ``.synctex`` 的归档/清理/缓存识别；
* 辅助文件自愈不能把注释里的花括号当成截断；
* 关闭 reproducible 后 ZIP 真的使用源文件时间戳；
* ``--explain`` 与编译共用命令行覆盖，且不产生副作用。
"""

import logging
import os
import re
import time
import zipfile
from pathlib import Path
from types import SimpleNamespace

import pytest

from pytexmk import aux_repair, submission
from pytexmk.cli import cli_compile, cli_config, cli_context
from pytexmk.cli.cli_state import WorkflowState


def _workflow_state(**overrides) -> WorkflowState:
    state = WorkflowState(args=SimpleNamespace(), logger=logging.getLogger("test"))
    state.project_name = "main"
    state.output_name = "main"
    state.outdir = "./Build/"
    state.auxdir = "./Auxiliary/"
    state.native_build = True
    state.synctex = True
    state.refresh_file_lists()
    for key, value in overrides.items():
        setattr(state, key, value)
    return state


# ---------------------------------------------------------------- SyncTeX sidecar


def test_plain_synctex_is_archived_like_gzip(tmp_path, monkeypatch):
    """`-synctex=-1` 产出明文 sidecar：必须和 PDF 一起归档，不能留在辅助目录。"""
    monkeypatch.chdir(tmp_path)
    aux = tmp_path / "Auxiliary"
    build = tmp_path / "Build"
    aux.mkdir()
    build.mkdir()
    (aux / "main.pdf").write_bytes(b"%PDF-1.4\n")
    (aux / "main.synctex").write_text("SyncTeX Version:1\n", encoding="utf-8")

    state = _workflow_state()
    result = cli_compile._archive_outputs(state)  # noqa: SLF001

    assert (build / "main.pdf").exists()
    assert (build / "main.synctex").exists()
    assert not (aux / "main.synctex").exists()
    assert result.moved >= 2


def test_plain_synctex_is_in_clean_patterns_and_output_list(tmp_path, monkeypatch):
    """`-ca` 与 `-C` 也必须同时认 `.synctex` 与 `.synctex.gz`。"""
    monkeypatch.chdir(tmp_path)
    (tmp_path / "main.synctex").write_text("plain", encoding="utf-8")
    state = _workflow_state()
    assert "main.synctex" in state.out_files
    assert "main.synctex.gz" in state.out_files
    assert any(re.fullmatch(pattern, "main.synctex") for pattern in state.aux_regex_files)

    targets = cli_compile._recursive_clean_targets(  # noqa: SLF001
        SimpleNamespace(clean_recursive_out=False), state
    )
    assert Path("main.synctex") in targets


# ---------------------------------------------------------------- 辅助文件自愈


def test_aux_repair_ignores_braces_inside_tex_comments(tmp_path):
    """合法 `.bbl` 的模板注释 `% ... { ...` 不应被判成截断文件删除。"""
    bbl = tmp_path / "main.bbl"
    bbl.write_text(
        "% template note: { is a brace\n"
        "\\begin{thebibliography}{1}\n"
        "\\bibitem{key} Author. Title.\n"
        "\\end{thebibliography}\n",
        encoding="utf-8",
    )
    assert aux_repair.find_truncated_aux_files([tmp_path], "main") == []

    truncated = tmp_path / "other.bbl"
    truncated.write_text(
        "\\begin{thebibliography}{1}\n\\@writefile{toc}{\\contentsline {section}",
        encoding="utf-8",
    )
    assert aux_repair.find_truncated_aux_files([tmp_path], "other") == [truncated]


def test_brace_balance_understands_comments_and_escapes():
    assert aux_repair._brace_balance("50\\% {ok}") == 0  # type: ignore[attr-defined]
    assert aux_repair._brace_balance("50% {unbalanced") == 0  # type: ignore[attr-defined]
    assert aux_repair._brace_balance("a\\\\% {unbalanced") == 0  # type: ignore[attr-defined]
    assert aux_repair._brace_balance("\\@writefile{toc}{\\contentsline {section}") == 1  # type: ignore[attr-defined]


# ---------------------------------------------------------------- ZIP 时间戳


def test_zip_timestamp_switch_actually_changes_entries(tmp_path):
    staging = tmp_path / "staging"
    staging.mkdir()
    source = staging / "a.tex"
    source.write_text("body\n", encoding="utf-8")
    stamp = time.mktime((2020, 5, 6, 12, 0, 0, 0, 0, -1))
    os.utime(source, (stamp, stamp))

    fixed_zip = tmp_path / "fixed.zip"
    live_zip = tmp_path / "live.zip"
    submission._write_zip(staging, ["a.tex"], fixed_zip, reproducible=True)
    submission._write_zip(staging, ["a.tex"], live_zip, reproducible=False)

    with zipfile.ZipFile(fixed_zip) as archive:
        assert archive.infolist()[0].date_time == (1980, 1, 1, 0, 0, 0)
    with zipfile.ZipFile(live_zip) as archive:
        assert archive.infolist()[0].date_time == (2020, 5, 6, 12, 0, 0)

    fixed_again = tmp_path / "fixed-again.zip"
    submission._write_zip(staging, ["a.tex"], fixed_again, reproducible=True)
    assert fixed_zip.read_bytes() == fixed_again.read_bytes()
    assert live_zip.read_bytes() != fixed_zip.read_bytes()


# ---------------------------------------------------------------- explain 计划


def test_explain_applies_cli_overrides_without_side_effects(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    build = tmp_path / "Build"
    build.mkdir()
    stale = build / "main.synctex.gz"
    stale.write_bytes(b"old")

    state = _workflow_state(preview_after_compile=True)
    state.interaction = "batchmode"  # 只来自 [build] interaction，命令行没有该开关
    args = SimpleNamespace(
        extra_args=["-pa=-8bit"],
        draft=False,
    )
    state.args = args
    cli_compile.apply_effective_build_plan(args, state)  # noqa: SLF001
    assert stale.exists()  # --explain 不应顺手删旧 sidecar

    assert state.native_build is True
    assert state.synctex is True
    assert state.interaction == "batchmode"
    assert state.extra_args == ["-pa=-8bit"]
    assert state.preview_after_compile is True

    cli_config.explain(state)
    out = capsys.readouterr().out
    assert "batchmode" in out
    assert "-pa=-8bit" in out
    assert str((Path(state.outdir) / "main.pdf").resolve()) in out


def test_explain_does_not_open_pdf_for_pv(tmp_path, monkeypatch):
    """`--explain -pv FILE` 是只读解释，不能先把用户的 PDF 拉起来。"""
    state = _workflow_state()
    state.pfo = SimpleNamespace(pdf_preview=lambda *_a: pytest.fail("不应预览"))
    state.args = SimpleNamespace(pdf_preview="main", document=None, explain=True)

    cli_context._apply_pdf_preview(state)  # noqa: SLF001
