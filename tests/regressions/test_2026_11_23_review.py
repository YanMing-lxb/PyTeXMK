"""2026-11-23 功能审查轮的回归测试（P0/P1 高优先级项）。

每一项都对应报告里的一个可复现缺陷，测试名直接写明“旧行为为什么错”。
"""

import re
from pathlib import Path
from types import SimpleNamespace

import pytest

from pytexmk.build_state import BuildState
from pytexmk.cli import cli_compile
from pytexmk.cli.cli_state import SUFFIXES_AUX
from pytexmk.compile_engine import _persist_build_state, _tool_input_files
from pytexmk.diagnostics import LogSummary, report_summary
from pytexmk.file_ops import FileMoveRemoveManager
from pytexmk.latexdiff import LaTeXDiff_Aux
from pytexmk.pdf_tools import PdfFileOperation, inspect_pdf
from pytexmk.preflight import check_project

# ---------------------------------------------------------------- P0：清理范围


def _aux_patterns() -> list[str]:
    return [rf".*{re.escape(suffix)}$" for suffix in SUFFIXES_AUX] + [r".*\.synctex\.gz$"]


def _clean_state(tmp: Path, *, out_files: list[str] | None = None):
    return SimpleNamespace(
        aux_regex_files=_aux_patterns(),
        output_name="main",
        outdir="Build",
        auxdir="Auxiliary",
        aux_files=["main.aux", "main.log", "main.bbl", "main.xdv", "main.xdy"],
        out_files=out_files or ["main.pdf", "main.synctex.gz"],
        mro=FileMoveRemoveManager(),
        runtime_dict={},
    )


def test_recursive_clean_patterns_are_end_anchored(tmp_path, monkeypatch):
    """旧正则 `.*\\.aux` 会把 `chapter.aux.notes.tex` 当辅助产物删除。"""
    monkeypatch.chdir(tmp_path)
    (tmp_path / "main.aux").write_text("aux", encoding="utf-8")
    (tmp_path / "chapter.aux.notes.tex").write_text("源文件", encoding="utf-8")
    state = _clean_state(tmp_path)
    args = SimpleNamespace(Clean_any=False)
    targets = cli_compile._recursive_clean_targets(args, state)
    names = {path.name for path in targets}
    assert "main.aux" in names
    assert "chapter.aux.notes.tex" not in names


def test_recursive_clean_removes_bbl_xdv_and_xdy(tmp_path, monkeypatch):
    """`.bbl/.xdv/.xdy` 一律按后缀清理，不再按 jobname 判定“作者文件”。"""
    monkeypatch.chdir(tmp_path)
    for name in ("main.bbl", "main-cn.bbl", "main.xdv", "author.xdy", "main.xdy"):
        (tmp_path / name).write_text(name, encoding="utf-8")
    state = _clean_state(tmp_path)
    args = SimpleNamespace(Clean_any=False)

    targets = cli_compile._recursive_clean_targets(args, state)
    assert {p.name for p in targets} == {
        "main.bbl", "main-cn.bbl", "main.xdv", "author.xdy", "main.xdy",
    }


def test_clean_c_only_cleans_auxdir(tmp_path, monkeypatch):
    """`-c` 只处理辅助目录；根目录同名副本留给 `-C`。"""
    monkeypatch.chdir(tmp_path)
    (tmp_path / "Auxiliary").mkdir()
    (tmp_path / "Auxiliary" / "main.aux").write_text("aux", encoding="utf-8")
    (tmp_path / "main.aux").write_text("root", encoding="utf-8")
    (tmp_path / "Build").mkdir()
    (tmp_path / "Build" / "main.pdf").write_bytes(b"%PDF-1.4\n")
    state = _clean_state(tmp_path)
    args = SimpleNamespace(clean=True, Clean=False)

    removed, failed = cli_compile._clean(args, state)
    assert [p.as_posix() for p in removed] == ["Auxiliary/main.aux"]
    assert (tmp_path / "main.aux").exists()
    assert (tmp_path / "Build" / "main.pdf").exists()
    assert not failed


def test_clean_C_cleans_root_and_outputs(tmp_path, monkeypatch):
    """`-C` 清理辅助目录 + 根目录，并删除 `Build/` 的 PDF/SyncTeX。"""
    monkeypatch.chdir(tmp_path)
    (tmp_path / "Auxiliary").mkdir()
    (tmp_path / "Auxiliary" / "main.aux").write_text("aux", encoding="utf-8")
    (tmp_path / "main.log").write_text("log", encoding="utf-8")
    (tmp_path / "Build").mkdir()
    (tmp_path / "Build" / "main.pdf").write_bytes(b"%PDF-1.4\n")
    state = _clean_state(tmp_path)
    args = SimpleNamespace(clean=False, Clean=True)

    removed, _failed = cli_compile._clean(args, state)
    names = {p.name for p in removed}
    assert {"main.aux", "main.log", "main.pdf"} <= names
    assert not (tmp_path / "main.log").exists()
    assert not (tmp_path / "Build" / "main.pdf").exists()


def test_clean_ca_without_main_removes_aux_only(tmp_path, monkeypatch):
    """`-ca` 不要求唯一主文件，只删辅助文件，保留输出。"""
    monkeypatch.chdir(tmp_path)
    (tmp_path / "Build").mkdir()
    (tmp_path / "Build" / "main.pdf").write_bytes(b"%PDF-1.4\n")
    (tmp_path / "main.bbl").write_text("bbl", encoding="utf-8")
    (tmp_path / "main.xdv").write_text("xdv", encoding="utf-8")
    state = _clean_state(tmp_path)
    state.output_name = ""
    args = SimpleNamespace(Clean_any=False)

    targets = cli_compile._recursive_clean_targets(args, state)
    names = {p.name for p in targets}
    assert {"main.bbl", "main.xdv"} <= names
    assert "main.pdf" not in names


def test_clean_Ca_includes_outdir_pdf(tmp_path, monkeypatch):
    """`-Ca` 在能确定主文件时额外删除 `Build/` 的 PDF。"""
    monkeypatch.chdir(tmp_path)
    (tmp_path / "Build").mkdir()
    (tmp_path / "Build" / "main.pdf").write_bytes(b"%PDF-1.4\n")
    (tmp_path / "main.aux").write_text("aux", encoding="utf-8")
    state = _clean_state(tmp_path)
    args = SimpleNamespace(Clean_any=True)
    targets = cli_compile._recursive_clean_targets(args, state)
    names = {p.name for p in targets}
    assert {"main.aux", "main.pdf"} <= names


def test_remove_paths_reports_partial_failure(tmp_path):
    """删除失败必须进 JSON 的 failed 列表，而不是只打日志。"""
    ok = tmp_path / "a.aux"
    ok.write_text("x", encoding="utf-8")
    missing = tmp_path / "b.aux"
    manager = FileMoveRemoveManager()
    removed, failed = manager.remove_paths([ok, missing])
    assert removed == [ok]
    assert failed == []  # FileNotFoundError 视为已不存在，不算失败


# ---------------------------------------------------------------- P1：产物校验


def _write_pdf(path: Path, pages: int = 1) -> None:
    from pypdf import PdfWriter

    writer = PdfWriter()
    for _ in range(pages):
        writer.add_blank_page(width=200, height=200)
    with path.open("wb") as handle:
        writer.write(handle)


def test_inspect_pdf_rejects_missing_empty_and_corrupt(tmp_path):
    missing = tmp_path / "missing.pdf"
    assert inspect_pdf(missing).reason == "missing"

    empty = tmp_path / "empty.pdf"
    empty.write_bytes(b"")
    assert inspect_pdf(empty).reason == "empty"

    fake = tmp_path / "fake.pdf"
    fake.write_text("这不是 PDF", encoding="utf-8")
    assert inspect_pdf(fake).reason == "not-pdf"

    corrupt = tmp_path / "corrupt.pdf"
    corrupt.write_bytes(b"%PDF-1.4\n" + "没有 xref".encode())
    assert inspect_pdf(corrupt).reason == "corrupt"

    good = tmp_path / "good.pdf"
    _write_pdf(good, 1)
    status = inspect_pdf(good)
    assert status.ok and status.pages == 1


def test_zero_page_pdf_is_not_deliverable(tmp_path):
    pdf = tmp_path / "empty-doc.pdf"
    _write_pdf(pdf, 0)
    status = inspect_pdf(pdf)
    assert not status.ok
    assert status.reason == "no-pages"


def test_validate_archive_rejects_stale_pdf(tmp_path, monkeypatch):
    """刚生成的旧 PDF 也不能被当成本轮成功产物。"""
    monkeypatch.chdir(tmp_path)
    build = tmp_path / "Build"
    build.mkdir()
    out_pdf = build / "main.pdf"
    _write_pdf(out_pdf)

    state = SimpleNamespace(
        output_name="main",
        outdir="Build",
        auxdir="Auxiliary",
        synctex=False,
        native_build=True,
        project_name="main",
        compiled_program="XeLaTeX",
        runtime_dict={},
    )
    recorded: list[str] = []

    class _Fail(Exception):
        pass

    def _raise(_state, message, **_kwargs):
        recorded.append(message)
        raise _Fail(message)

    monkeypatch.setattr(cli_compile, "_fail_compile", _raise)
    with pytest.raises(_Fail):
        cli_compile._validate_archive(
            state,
            cli_compile.ArchiveResult(had_pdf=False, moved=0, source_pdf=None),
        )
    assert recorded and "没有生成新 PDF" in recorded[0]


def test_validate_archive_accepts_fresh_pdf(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    build = tmp_path / "Build"
    build.mkdir()
    out_pdf = build / "main.pdf"
    _write_pdf(out_pdf)
    state = SimpleNamespace(
        output_name="main",
        outdir="Build",
        auxdir="Auxiliary",
        synctex=False,
        native_build=True,
        project_name="main",
        compiled_program="XeLaTeX",
        runtime_dict={},
    )
    monkeypatch.setattr(
        cli_compile, "_fail_compile", lambda *_a, **_k: pytest.fail("不应判失败")
    )
    cli_compile._validate_archive(
        state,
        cli_compile.ArchiveResult(had_pdf=True, moved=1, source_pdf=None),
    )


def test_archive_leftover_source_is_failure(tmp_path, monkeypatch):
    """搬移没完成时，源目录里仍留着 PDF；不能只看目标目录有没有文件。"""
    monkeypatch.chdir(tmp_path)
    state = SimpleNamespace(
        output_name="main",
        outdir="Build",
        auxdir="Auxiliary",
        synctex=False,
        native_build=True,
        project_name="main",
        compiled_program="XeLaTeX",
        runtime_dict={},
    )
    reasons: list[str] = []

    class _Fail(Exception):
        pass

    def _raise(_state, message, **_kwargs):
        reasons.append(message)
        raise _Fail(message)

    monkeypatch.setattr(cli_compile, "_fail_compile", _raise)
    with pytest.raises(_Fail):
        cli_compile._validate_archive(
            state,
            cli_compile.ArchiveResult(
                had_pdf=True, moved=0, source_pdf=Path("Auxiliary/main.pdf")
            ),
            )
    assert reasons and "归档失败" in reasons[0]


def test_archive_same_directory_does_not_claim_source_leftover(tmp_path, monkeypatch):
    """`-o .` 且辅助目录也是 `.` 时，PDF 本来就在目标位置，不能误判搬移失败。"""
    monkeypatch.chdir(tmp_path)
    _write_pdf(tmp_path / "main.pdf")
    state = SimpleNamespace(
        output_name="main",
        outdir=".",
        auxdir=".",
        synctex=False,
        native_build=True,
        out_files=["main.pdf"],
        aux_files=[],
        runtime_dict={},
        mro=FileMoveRemoveManager(),
    )
    archive = cli_compile._archive_outputs(state)
    assert archive.had_pdf is True
    assert archive.source_pdf is None


# ---------------------------------------------------------------- P1：收敛与诊断


def test_limit_and_tool_pending_are_not_converged(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    build_state = BuildState("Build", "main")
    for stop_reason, expected in (("limit", False), ("tool-pending", False), ("stable", True)):
        _persist_build_state(
            build_state,
            round_no=1,
            fingerprint="fp",
            dims={},
            signals={"permanent": [], "transient": []},
            stop_reason=stop_reason,
            project_name="main",
            build_key="key",
        )
        assert build_state.was_converged() is expected
        assert build_state.last_stop_reason() == stop_reason


def test_diagnostics_unavailable_is_not_zero_warnings(tmp_path):
    """日志缺失时 summary 必须带 available=False，门禁才能拒绝放行。"""
    summary = report_summary("main", str(tmp_path / "Build"), root_file="main.tex")
    assert isinstance(summary, LogSummary)
    assert summary.available is False
    assert summary.source == "unavailable"
    assert (summary.errors, summary.warnings) == (0, 0)


def test_diagnostics_reusable_requires_log_digest(tmp_path):
    auxdir = tmp_path / "Build"
    auxdir.mkdir()
    log = auxdir / "main.log"
    log.write_text("This is XeTeX\n", encoding="utf-8")
    tracker = BuildState(auxdir, "main")
    tracker.save_round(
        round_no=1,
        fingerprint="fp",
        dims={},
        stop_reason="stable",
        converged=True,
        diagnostics=tracker.log_record(),
    )
    assert cli_compile._diagnostics_reusable(tracker)

    log.unlink()
    assert not cli_compile._diagnostics_reusable(tracker)


def test_build_key_changes_with_max_runs(tmp_path):
    """轮次预算属于构建参数：0 与 8 不能共用复用基线。"""
    state = SimpleNamespace(
        args=SimpleNamespace(draft=False),
        compiled_program="XeLaTeX",
        interaction="",
        shell_escape="false",
        synctex=True,
        native_build=True,
        outdir="Build",
        auxdir="Auxiliary",
        extra_args=[],
        output_name="main",
        max_extra_compilations=0,
        project_name="main",
    )
    key0 = cli_compile._current_build_key(state)
    state.max_extra_compilations = 8
    assert key0 != cli_compile._current_build_key(state)


# ---------------------------------------------------------------- P1：预检


def test_preflight_nested_input_resolves_from_working_dir(tmp_path, monkeypatch):
    """`chapters/intro.tex` 里的 `\\input{chapters/section}` 不能再被拼成
    `chapters/chapters/section.tex`。"""
    monkeypatch.chdir(tmp_path)
    (tmp_path / "chapters").mkdir()
    (tmp_path / "main.tex").write_text(
        "\\documentclass{article}\n\\begin{document}\n\\input{chapters/intro}\n\\end{document}\n",
        encoding="utf-8",
    )
    (tmp_path / "chapters" / "intro.tex").write_text(
        "前言\n\\input{chapters/section}\n", encoding="utf-8"
    )
    (tmp_path / "chapters" / "section.tex").write_text("正文\n", encoding="utf-8")

    report = check_project("main", tmp_path)
    assert report.errors == []


def test_preflight_reports_real_line_number(tmp_path):
    (tmp_path / "main.tex").write_text(
        "\\documentclass{article}\n\\begin{document}\n\\input{missing}\n\\end{document}\n",
        encoding="utf-8",
    )
    report = check_project("main", tmp_path)
    issue = report.errors[0]
    assert issue.line == 3


def test_preflight_checks_graphics_inside_child_file(tmp_path):
    """子文件里的图片缺失也要报，且行号属于子文件。"""
    (tmp_path / "main.tex").write_text(
        "\\documentclass{article}\n\\begin{document}\n\\input{chapters/intro}\n\\end{document}\n",
        encoding="utf-8",
    )
    (tmp_path / "chapters").mkdir()
    (tmp_path / "chapters" / "intro.tex").write_text(
        "正文\n\\includegraphics{missing/fig}\n", encoding="utf-8"
    )
    report = check_project("main", tmp_path)
    warnings = [i for i in report.warnings if "图片不存在" in i.message]
    assert len(warnings) == 1
    assert warnings[0].line == 2
    assert warnings[0].file == "chapters/intro.tex"


# ---------------------------------------------------------------- P1：文献依赖


def test_tool_inputs_are_read_from_aux(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    auxdir = tmp_path / "Build"
    auxdir.mkdir()
    (auxdir / "main.aux").write_text(
        "\\bibstyle{plain}\n\\bibdata{refs/chapter1,refs/common}\n", encoding="utf-8"
    )
    (tmp_path / "refs").mkdir()
    (tmp_path / "refs" / "chapter1.bib").write_text("@book{a}", encoding="utf-8")
    (tmp_path / "refs" / "common.bib").write_text("@book{b}", encoding="utf-8")

    inputs = _tool_input_files("main", "Build", "main")
    assert {p.name for p in inputs} == {"chapter1.bib", "common.bib"}
    # 系统自带的 plain.bst 不在项目里，不进入依赖快照
    assert all(p.suffix == ".bib" for p in inputs)


def test_tool_inputs_from_bcf(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "Build").mkdir()
    (tmp_path / "Build" / "main.bcf").write_text(
        '<bcf:datasource type="file" datatype="bibtex">refs.bib</bcf:datasource>',
        encoding="utf-8",
    )
    (tmp_path / "refs.bib").write_text("@book{a}", encoding="utf-8")
    inputs = _tool_input_files("main", "Build", "main")
    assert [p.name for p in inputs] == ["refs.bib"]


# ---------------------------------------------------------------- P1：配置


def test_config_errors_consumes_load_errors(tmp_path, monkeypatch):
    from pytexmk.cli.cli_config import config_errors
    from pytexmk.config import ConfigParser

    monkeypatch.chdir(tmp_path)
    (tmp_path / ".pytexmkrc").write_text('build = [""\n', encoding="utf-8")
    cp = ConfigParser()
    monkeypatch.setattr(cp, "user_config_path", None)
    assert config_errors(cp.load_config(tmp_path), cp.load_errors)


def test_config_errors_rejects_numeric_subprojects(tmp_path, monkeypatch):
    from pytexmk.cli.cli_config import config_errors
    from pytexmk.config import ConfigParser

    monkeypatch.chdir(tmp_path)
    (tmp_path / ".pytexmkrc").write_text("[subprojects]\none = 100\n", encoding="utf-8")
    cp = ConfigParser()
    monkeypatch.setattr(cp, "user_config_path", None)
    assert config_errors(cp.load_config(tmp_path), cp.load_errors)


def test_config_errors_survives_wrong_section_types(tmp_path, monkeypatch):
    """`build`/`index` 被写成非表时，校验要报错而不是 AttributeError。"""
    from pytexmk.cli.cli_config import config_errors
    from pytexmk.config import ConfigParser

    monkeypatch.chdir(tmp_path)
    (tmp_path / ".pytexmkrc").write_text('build = "oops"\nindex = 3\n', encoding="utf-8")
    cp = ConfigParser()
    monkeypatch.setattr(cp, "user_config_path", None)
    assert config_errors(cp.load_config(tmp_path), cp.load_errors)


# ---------------------------------------------------------------- P1：LaTeXDiff


def test_latexdiff_flatten_preserves_inline_text_and_repeated_include(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "main.tex").write_text(
        "Before \\input{part} After\nAgain \\input{part}\n", encoding="utf-8"
    )
    (tmp_path / "part.tex").write_text("PIECE\n", encoding="utf-8")

    lda = LaTeXDiff_Aux("Build", [".pdf"], [".aux"], "Auxiliary")
    output = Path(lda.flatten_Latex("main") + ".tex")
    text = output.read_text(encoding="utf-8")
    assert text.count("PIECE") == 2, "同一子文件被两个位置正常引用，不能被当作循环只展开一次"
    assert "Before PIECE After" in text, "命令行两侧的正文被整段丢掉"
    lda.cleanup()


def test_latexdiff_flatten_nested_input_uses_project_root(tmp_path, monkeypatch):
    """`chapters/intro.tex` 里的 `\\input{chapters/section}` 按主文件目录解析，
    不能拼成 `chapters/chapters/section.tex`。"""
    monkeypatch.chdir(tmp_path)
    (tmp_path / "main.tex").write_text("\\input{chapters/intro}\n", encoding="utf-8")
    (tmp_path / "chapters").mkdir()
    (tmp_path / "chapters" / "intro.tex").write_text(
        "INTRO\n\\input{chapters/section}\n", encoding="utf-8"
    )
    (tmp_path / "chapters" / "section.tex").write_text("SECTION\n", encoding="utf-8")

    lda = LaTeXDiff_Aux("Build", [".pdf"], [".aux"], "Auxiliary")
    output = Path(lda.flatten_Latex("main") + ".tex")
    text = output.read_text(encoding="utf-8")
    assert "INTRO" in text and "SECTION" in text
    lda.cleanup()


def test_latexdiff_flatten_nested_main_path_uses_cwd(tmp_path, monkeypatch):
    """主文件本身在子目录时，`\\input` 仍以项目根（cwd）为基准。"""
    monkeypatch.chdir(tmp_path)
    (tmp_path / "chapters").mkdir()
    (tmp_path / "chapters" / "main.tex").write_text(
        "MAIN\n\\input{chapters/section}\n", encoding="utf-8"
    )
    (tmp_path / "chapters" / "section.tex").write_text("SECTION\n", encoding="utf-8")

    lda = LaTeXDiff_Aux("Build", [".pdf"], [".aux"], "Auxiliary")
    output = Path(lda.flatten_Latex("chapters/main") + ".tex")
    text = output.read_text(encoding="utf-8")
    assert "MAIN" in text and "SECTION" in text
    lda.cleanup()


def test_latexdiff_flatten_detects_cycle_without_recursing_forever(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "a.tex").write_text("A\n\\input{b}\n", encoding="utf-8")
    (tmp_path / "b.tex").write_text("B\n\\input{a}\n", encoding="utf-8")
    lda = LaTeXDiff_Aux("Build", [".pdf"], [".aux"], "Auxiliary")
    output = Path(lda.flatten_Latex("a") + ".tex")
    text = output.read_text(encoding="utf-8")
    assert "A" in text and "B" in text
    lda.cleanup()


def test_redirected_output_failure_keeps_old_file_and_cleans_tmp(tmp_path):
    """latexdiff 失败时目标保持原样，且不留下 `.<name>.<ns>.tmp`。"""
    import os
    import sys

    from pytexmk.subprocess_runner import MySubProcess

    target = tmp_path / "diff.tex"
    target.write_text("OLD\n", encoding="utf-8")
    runner = MySubProcess(".", ".")
    process, _stdout, _stderr = runner._execute_redirected(  # noqa: SLF001
        [sys.executable, "-c", "print('HALF'); raise SystemExit(1)"],
        tmp_path,
        os.environ.copy(),
        str(target),
        "test",
    )
    assert process.returncode == 1
    assert target.read_text(encoding="utf-8") == "OLD\n"
    assert list(tmp_path.glob(f".{target.name}.*.tmp")) == []


def test_latexdiff_does_not_overwrite_user_file(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "main.tex").write_text("body\n", encoding="utf-8")
    user_file = tmp_path / "main-flatten.tex"
    user_file.write_text("作者自己的文件\n", encoding="utf-8")
    lda = LaTeXDiff_Aux("Build", [".pdf"], [".aux"], "Auxiliary")
    output = Path(lda.flatten_Latex("main") + ".tex")
    assert output != user_file
    assert output.read_text(encoding="utf-8") == "body\n"
    assert user_file.read_text(encoding="utf-8") == "作者自己的文件\n"
    lda.cleanup()


# ---------------------------------------------------------------- P1：批量与别名


def test_submission_and_preflight_config_are_applied():
    """新增的投稿目录/保留导言区/预检开关必须真正进入 WorkflowState。"""
    from pytexmk.cli.cli_context import _apply_preflight_config, _apply_submission_config

    class _Logger:
        def info(self, *_a, **_k):
            pass

    state = SimpleNamespace(
        config_dict={
            "submission": {
                "output_dir": "./Submit/",
                "keep_preamble": True,
                "unicode_to_latex": False,
            },
            "preflight": {"enabled": False},
        },
        submission_output_dir="./Submission/",
        submission_keep_preamble=False,
        submission_unicode_to_latex=True,
        preflight_enabled=True,
        logger=_Logger(),
    )
    _apply_submission_config(state)
    _apply_preflight_config(state)

    assert state.submission_output_dir == "./Submit/"
    assert state.submission_keep_preamble is True
    assert state.submission_unicode_to_latex is False
    assert state.preflight_enabled is False


def test_explicit_file_alias_beats_config_default(tmp_path):
    """`-s one`（one="one/paper.tex"）不能被根配置的 default_file 抢走。"""
    from pytexmk.cli.cli_context import _apply_main_config

    class _Logger:
        def info(self, *_a, **_k):
            pass

    state = SimpleNamespace(
        config_dict={"default_file": "main", "compiled_program": ""},
        explicit_default=True,
        default_file="paper",
        logger=_Logger(),
    )
    _apply_main_config(state)
    assert state.default_file == "paper"

    # 没有显式选择时才允许配置兜底
    state.explicit_default = False
    _apply_main_config(state)
    assert state.default_file == "main"


# ---------------------------------------------------------------- P2：其他


def test_shell_escape_off_flag_is_distribution_specific():
    from pytexmk.compile import shell_escape_off_flag

    assert shell_escape_off_flag() in {"--disable-write18", "-no-shell-escape"}


def test_synctex_missing_coordinates_does_not_crash(monkeypatch):
    from pytexmk import synctex

    def _fake_run(*_args, **_kwargs):
        return 0, "Page:1\n"

    monkeypatch.setattr(synctex, "_run", _fake_run)
    report = synctex.SyncTeXReport()
    synctex._check_one("synctex", Path("main.pdf"), Path("main.tex"), 10, Path("."), report)
    assert not report.ok
    assert "缺少坐标" in report.errors[0]
    assert report.summary()  # 旧实现会在这里格式化 None 崩溃


def test_synctex_regex_accepts_signed_coordinates():
    from pytexmk import synctex

    assert synctex._X_RE.search("x:-12.5").group(1) == "-12.5"
    assert synctex._Y_RE.search("y:+3.0").group(1) == "+3.0"


def test_pdf_repair_without_recorder_is_read_only(tmp_path, monkeypatch):
    root = tmp_path
    out = root / "Build"
    out.mkdir()
    nested = out / "nested" / "old.pdf"
    nested.parent.mkdir()
    _write_pdf(nested)
    mtime = nested.stat().st_mtime

    pfo = PdfFileOperation()
    monkeypatch.chdir(root)
    assert pfo.pdf_repair("main", str(root), "Build", "Auxiliary") is False
    assert nested.stat().st_mtime == mtime


def test_pdf_repair_uses_auxdir_recorder_and_excludes_output_tree(tmp_path, monkeypatch):
    root = tmp_path
    out = root / "Build"
    out.mkdir()
    aux = root / "Auxiliary"
    aux.mkdir()
    (aux / "main.fls").write_text(
        "INPUT refs/figure.pdf\nINPUT Build/nested/old.pdf\n", encoding="utf-8"
    )
    (root / "refs").mkdir()
    referenced = root / "refs" / "figure.pdf"
    _write_pdf(referenced)
    nested = out / "nested" / "old.pdf"
    nested.parent.mkdir()
    _write_pdf(nested)

    pfo = PdfFileOperation()
    monkeypatch.chdir(root)
    called: list[Path] = []
    monkeypatch.setattr(pfo, "_repair_one", called.append)
    pfo.pdf_repair("main", str(root), "Build", "Auxiliary")
    assert called == [referenced]


# ---------------------------------------------------------------- 投稿包完整性


def test_submission_pack_always_contains_main_entry_and_all_bibs(tmp_path):
    """`.fls` 漏记主文件/多库项目：包内仍要有主入口与全部 .bib。"""
    from pytexmk.submission import build_pack

    root = tmp_path / "proj"
    (root / "refs").mkdir(parents=True)
    (root / "main.tex").write_text("\\documentclass{article}", encoding="utf-8")
    (root / "refs" / "one.bib").write_text("@book{a}", encoding="utf-8")
    (root / "refs" / "two.bib").write_text("@book{b}", encoding="utf-8")
    (root / "Build").mkdir()
    (root / "Auxiliary").mkdir()

    result = build_pack(
        root,
        "main",
        "Build",
        "Auxiliary",
        submit_dir="Submission",
        convert_unicode=False,
    )
    import zipfile

    with zipfile.ZipFile(result.zip_path) as archive:
        names = set(archive.namelist())
    assert "main.tex" in names
    assert {"refs/one.bib", "refs/two.bib"} <= names


def test_submission_pack_fails_without_main_entry(tmp_path):
    from pytexmk.submission import build_pack

    root = tmp_path / "empty"
    root.mkdir()
    with pytest.raises(FileNotFoundError):
        build_pack(
            root,
            "main",
            "Build",
            "Auxiliary",
            submit_dir="Submission",
            convert_unicode=False,
        )


def test_submission_original_mode_preserves_crlf_bytes(tmp_path):
    """`convert_unicode=False` 必须按字节复制，不能把 CRLF 归一成 LF。"""
    import zipfile

    from pytexmk.submission import build_pack

    root = tmp_path / "proj"
    root.mkdir()
    original = b"\\documentclass{article}\r\n\\begin{document}\r\nX\r\n\\end{document}\r\n"
    (root / "main.tex").write_bytes(original)
    (root / "Build").mkdir()
    (root / "Auxiliary").mkdir()

    result = build_pack(
        root,
        "main",
        "Build",
        "Auxiliary",
        submit_dir="Submission",
        convert_unicode=False,
    )
    with zipfile.ZipFile(result.zip_path) as archive:
        assert archive.read("main.tex") == original
