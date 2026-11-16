"""``--jobname`` 双轨：源文件 stem 与输出 stem 分离的回归测试。"""

import argparse

import pytest

from pytexmk.compile import CompileLaTeX
from pytexmk.detection import CompilationDetector


def _detector(tmp_path, jobname=None):
    return CompilationDetector(
        project_name="main",
        compiled_program="PdfLaTeX",
        out_files=["alt.pdf"],
        aux_files=["alt.aux"],
        outdir=str(tmp_path),
        auxdir=str(tmp_path),
        non_quiet=False,
        MRO=None,
        jobname=jobname,
    )


def test_latex_command_uses_jobname_but_inputs_source(tmp_path):
    model = CompileLaTeX(
        "main",
        "PdfLaTeX",
        ["alt.pdf"],
        ["alt.aux"],
        str(tmp_path),
        str(tmp_path),
        True,
        native=True,
        jobname="alt",
    )
    command = model._latex_command()
    assert "-jobname=alt" in command
    assert command[-1] == "main.tex"


def test_detector_reads_jobname_aux(tmp_path):
    (tmp_path / "alt.aux").write_text("\\relax\n", encoding="utf-8")
    detector = _detector(tmp_path, jobname="alt")
    assert detector._locate(".aux").name == "alt.aux"
    cite_counter, _toc, _index = detector.prepare_LaTeX_output_files()
    assert "alt.aux" in cite_counter


def test_jobname_rejects_path_and_extension():
    from pytexmk.cli.cli_context import _resolve_output_name

    args = argparse.Namespace(jobname="alt")
    assert _resolve_output_name(args, "main") == "alt"
    args.jobname = "sub/alt"
    with pytest.raises(SystemExit) as exc:
        _resolve_output_name(args, "main")
    assert exc.value.code == 1
    args.jobname = "alt.pdf"
    with pytest.raises(SystemExit):
        _resolve_output_name(args, "main")
