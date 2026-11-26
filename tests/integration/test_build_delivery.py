import logging
import os
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest
from pypdf import PdfWriter

from pytexmk.build_state import BuildState
from pytexmk.cli import cli_compile, cli_watch, cli_workflow
from pytexmk.cli.cli_state import WorkflowState
from pytexmk.compile_engine import _iter_source_files
from pytexmk.context import AmbiguousProjectError, ContextResolver
from pytexmk.detection import BibEngine, CompilationDetector
from pytexmk.file_ops import FileMoveRemoveManager
from pytexmk.preflight import check_project
from pytexmk.subprocess_runner import MySubProcess, SubprocessFailedError

_DOCUMENT = r"\documentclass{article}\begin{document}Text\end{document}"


def _state(tmp_path, *, native=True):
    state = WorkflowState(args=SimpleNamespace(), logger=logging.getLogger("test"))
    state.project_name = state.output_name = "main"
    state.outdir = str(tmp_path / "custom-output")
    state.auxdir = str(tmp_path / "custom-aux")
    state.native_build = native
    for folder in (state.outdir, state.auxdir):
        Path(folder).mkdir()
    state.refresh_file_lists()
    return state


def _write_pdf(path):
    writer = PdfWriter()
    writer.add_blank_page(width=100, height=100)
    writer.write(path)


@pytest.mark.parametrize("same_directory", [False, True])
def test_recent_pdf_is_preserved_when_engine_outputs_nothing(tmp_path, same_directory):
    state = _state(tmp_path)
    if same_directory:
        state.outdir = state.auxdir
    old_pdf = Path(state.outdir) / "main.pdf"
    _write_pdf(old_pdf)
    old_content = old_pdf.read_bytes()

    before = cli_compile.capture_engine_outputs(state)
    with pytest.raises(SystemExit) as exc:
        cli_compile.publish_compiled_outputs(state, before)
    assert exc.value.code == 5
    assert old_pdf.read_bytes() == old_content


def test_publication_failure_does_not_pair_new_synctex_with_previous_pdf(tmp_path, monkeypatch):
    state = _state(tmp_path)
    aux, out = Path(state.auxdir), Path(state.outdir)
    _write_pdf(out / "main.pdf")
    (out / "main.synctex.gz").write_bytes(b"previous")
    before = cli_compile.capture_engine_outputs(state)
    _write_pdf(aux / "main.pdf")
    (aux / "main.synctex.gz").write_bytes(b"current")

    def fail_after_staging(files, source, dest):
        assert files == ["main.pdf"]
        (Path(source) / files[0]).rename(Path(dest) / ".pdf-recovery")
        return 0

    monkeypatch.setattr(state.mro, "move_specific_files", fail_after_staging)
    with pytest.raises(SystemExit) as exc:
        cli_compile.publish_compiled_outputs(state, before)
    assert exc.value.code == 5
    assert (out / "main.synctex.gz").read_bytes() == b"previous"
    assert (out / ".pdf-recovery").is_file()


def test_no_pages_in_final_log_rejects_pdf_left_by_earlier_round(tmp_path):
    state = _state(tmp_path)
    before = cli_compile.capture_engine_outputs(state)
    aux = Path(state.auxdir)
    _write_pdf(aux / "main.pdf")
    (aux / "main.log").write_text("This is pdfTeX\nNo pages of output.\n", encoding="utf-8")

    with pytest.raises(SystemExit) as exc:
        cli_compile.publish_compiled_outputs(state, before)
    assert exc.value.code == 5
    assert not (Path(state.outdir) / "main.pdf").exists()


@pytest.mark.parametrize("same_directory", [False, True])
def test_archiving_new_pdf_replaces_old_synctex_format(tmp_path, same_directory):
    state = _state(tmp_path)
    if same_directory:
        state.outdir = state.auxdir
    aux, out = Path(state.auxdir), Path(state.outdir)
    (out / "main.synctex.gz").write_bytes(b"previous")
    before = cli_compile.capture_engine_outputs(state)

    _write_pdf(aux / "main.pdf")
    (aux / "main.synctex").write_bytes(b"current")
    cli_compile.publish_compiled_outputs(state, before)

    assert (out / "main.synctex").read_bytes() == b"current"
    assert not (out / "main.synctex.gz").exists()


def test_preflight_and_cache_use_explicit_non_tex_input(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "main.tex").write_text(
        _DOCUMENT.replace("Text", r"\input{body.txt}"), encoding="utf-8"
    )
    body = tmp_path / "body.txt"
    body.write_text("old", encoding="utf-8")
    assert check_project("main", tmp_path).ok

    aux = tmp_path / "Auxiliary"
    aux.mkdir()
    generated = aux / "generated.txt"
    generated.write_text("generated", encoding="utf-8")
    (aux / "main.fls").write_text(
        f"PWD {tmp_path}\nINPUT ./main.tex\nINPUT body.txt\n"
        "INPUT Auxiliary/generated.txt\nOUTPUT Auxiliary/generated.txt\n",
        encoding="utf-8",
    )
    tracker = BuildState(aux, "main")

    def inputs():
        return list(_iter_source_files("main", str(aux)))

    assert body in inputs()
    assert generated not in inputs()
    tracker.save_round(round_no=1, fingerprint="f", dims={}, sources=tracker.source_snapshot(inputs()))
    assert tracker.sources_unchanged(inputs())
    body.write_text("new and longer", encoding="utf-8")
    assert not tracker.sources_unchanged(inputs())


def test_bibtex_checks_local_style_timestamp(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "main.aux").write_text(
        r"\citation{x}\bibstyle{custom}\bibdata{refs}", encoding="utf-8"
    )
    for name in ("refs.bib", "main.bbl", "custom.bst"):
        (tmp_path / name).write_text("data", encoding="utf-8")
    bbl = tmp_path / "main.bbl"
    style = tmp_path / "custom.bst"
    for path, timestamp in ((tmp_path / "refs.bib", 100), (style, 100), (bbl, 200)):
        os.utime(path, (timestamp, timestamp))

    detector = CompilationDetector("main", "PdfLaTeX", [], [], ".", ".", False, FileMoveRemoveManager())
    citations = detector._generate_citation_counter()
    assert detector.bib_judgment(citations)[:2] == (BibEngine.BIBTEX, 0)
    os.utime(style, (300, 300))
    assert detector.bib_judgment(citations)[:2] == (BibEngine.BIBTEX, 2)


def test_watch_ignores_generated_pdf_but_not_edited_figure(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    state = _state(tmp_path)
    out = Path(state.outdir)
    fig = out / "figure.pdf"
    fig.write_bytes(b"initial figure")
    builds, sleeps = [], []

    def workflow(args, *, before_build):
        before_build(state)
        builds.append(len(builds))
        (out / "main.pdf").write_bytes(b"generated" + bytes(builds))
        assert len(builds) <= 2

    def sleep(seconds):
        sleeps.append(seconds)
        if len(sleeps) == 1:
            fig.write_bytes(b"edited figure")
        if len(sleeps) == 3:
            raise KeyboardInterrupt

    monkeypatch.setattr(cli_workflow, "run_workflow", workflow)
    monkeypatch.setattr(cli_watch.time, "sleep", sleep)
    cli_watch.watch_loop(SimpleNamespace(watch=True, force_rebuild=True))
    assert builds == [0, 1]
    assert sleeps == [1, 0.4, 1]


def test_ambiguous_leaf_requires_full_subproject_alias(tmp_path):
    candidates = {f"{folder}/review": tmp_path / folder / "review" for folder in ("one", "two")}
    with pytest.raises(AmbiguousProjectError, match="one/review.*two/review"):
        ContextResolver._match("review", candidates)
    assert ContextResolver._match("two/review", candidates) == ("two/review", candidates["two/review"])


@pytest.mark.parametrize(("mode", "expected"), [
    ("init", 4), ("repair", 1), ("clean", 1), ("report", 9), ("encoding", 4),
])
def test_cli_reports_operations_that_failed(tmp_path, mode, expected):
    (tmp_path / "main.tex").write_text(_DOCUMENT, encoding="utf-8")
    aux = tmp_path / "Auxiliary"
    aux.mkdir()
    if mode == "init":
        (tmp_path / ".pytexmkrc").mkdir()
        flags = ["-i"]
    elif mode == "repair":
        (tmp_path / "figure.pdf").write_bytes(b"not a PDF")
        flags = ["-rp", "figure.pdf"]
    elif mode == "clean":
        (aux / "main.aux").mkdir()
        flags = ["-c"]
    elif mode == "report":
        (aux / "main.log").write_text("This is pdfTeX, Version 3.14159\n", encoding="utf-8")
        (aux / "main.pytexmk-report.json").mkdir()
        flags = ["-r"]
    else:
        (tmp_path / ".pytexmkrc").write_bytes(b"\xff")
        flags = ["-e"]

    env = {**os.environ, "HOME": str(tmp_path), "USERPROFILE": str(tmp_path), "PYTHONIOENCODING": "utf-8"}
    result = subprocess.run(
        [sys.executable, "-m", "pytexmk", *flags],
        cwd=tmp_path, env=env, capture_output=True, encoding="utf-8", timeout=15,
    )
    assert result.returncode == expected, result.stdout + result.stderr
    assert "Traceback" not in result.stderr


def test_retry_preserves_recovery_file_when_publish_and_rollback_fail(tmp_path, monkeypatch):
    manager = FileMoveRemoveManager()
    dest = tmp_path / "Build" / "main.pdf"
    dest.parent.mkdir()
    dest.write_bytes(b"previous")
    src = tmp_path / "main.pdf"
    src.write_bytes(b"recover me")

    move = manager._move_with_retry

    def fail_rollback(source, target):
        if target == src:
            raise PermissionError("rollback is blocked")
        move(source, target)

    def fail_publish(source, target):
        raise PermissionError("publish is blocked")

    with monkeypatch.context() as patch:
        patch.setattr(manager, "_move_with_retry", fail_rollback)
        patch.setattr(Path, "replace", fail_publish)
        assert manager._replace(src, dest, dest.parent.name) is False

    recovery, = dest.parent.glob(".main.pdf.pytexmk-*.tmp")
    assert dest.read_bytes() == b"previous"
    assert recovery.read_bytes() == b"recover me"
    src.write_bytes(b"next build")
    assert manager._replace(src, dest, dest.parent.name) is True
    assert dest.read_bytes() == b"next build"
    assert recovery.read_bytes() == b"recover me"


def test_subprocess_cannot_report_success_if_redirected_publish_fails(tmp_path, monkeypatch):
    target = tmp_path / "diff.tex"
    target.write_bytes(b"original")

    def fail_replace(source, destination):
        raise PermissionError("target is locked")

    monkeypatch.setattr(Path, "replace", fail_replace)
    runner = MySubProcess(str(tmp_path), str(tmp_path))
    with pytest.raises(SubprocessFailedError):
        runner.run_command(
            [sys.executable, "-c", "print('new')"], [], [],
            stdout_path=str(target), cwd=tmp_path,
        )
    assert target.read_bytes() == b"original"
    assert not list(tmp_path.glob(".diff.tex.*.tmp"))
