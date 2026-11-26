"""第十一轮缺陷修复的回归：预检退出码、跳过路径诊断、draft 编码、原子写。"""

import subprocess
import sys
from types import SimpleNamespace

from pytexmk import subprocess_runner
from pytexmk.cli import cli_compile
from pytexmk.diagnostics import LogSummary
from pytexmk.file_ops import atomic_write_text
from pytexmk.subprocess_runner import MySubProcess
from pytexmk.tex_project import MainFileOperation


def _run_cli(tmp_path, *argv):
    """在临时项目里跑一次 CLI，返回 (退出码, stdout, stderr)。"""
    proc = subprocess.run(
        [sys.executable, "-m", "pytexmk.cli", *argv],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=180,
    )
    return proc.returncode, proc.stdout, proc.stderr


def test_preflight_block_exits_nonzero(tmp_path):
    """预检阻断必须是非零退出码，而不是继续编译。"""
    (tmp_path / "main.tex").write_text(
        "\\documentclass{article}\n\\begin{document}\nMissing end.\n", encoding="utf-8"
    )
    code, stdout, stderr = _run_cli(tmp_path, "-x", "main")

    assert code == 5, stderr[-2000:]
    assert "end{document}" in stdout + stderr


def test_skipped_finish_compile_reads_log_and_hints(capsys, monkeypatch):
    """跳过编译仍要生成摘要；错误计数可见，但不再自己拼 -r 出口。"""
    state = SimpleNamespace(
        project_name="main",
        output_name="main",
        auxdir="Auxiliary",
        runtime_dict={},
    )
    summary = LogSummary(
        warnings=2,
        errors=1,
        issues=[
            {"level": "warning", "file": "main.tex", "line": 3, "text": "Undefined reference"}
        ],
    )
    calls = {}

    def fake_summary(*_args, **kwargs):
        calls["summary_kwargs"] = kwargs
        return summary

    monkeypatch.setattr(cli_compile, "report_summary", fake_summary)

    cli_compile._finish_compile(state, status="skipped")

    assert "write_report" not in calls["summary_kwargs"]
    out = capsys.readouterr().out
    assert "pytexmk -r" not in out
    assert "1 个错误" in out


def test_compile_routes_skip_through_finish(monkeypatch):
    """跳过分支必须走 _finish_compile(status="skipped")，不能提前 return。"""
    state = SimpleNamespace(
        project_name="main",
        output_name="main",
        outdir="Build",
        auxdir="Auxiliary",
        runtime_dict={},
        preflight_enabled=False,
    )
    args = SimpleNamespace(clean=False, clean_out=False, pdf_repair=False)
    calls = {}

    monkeypatch.setattr(cli_compile, "_apply_build_overrides", lambda *_a, **_k: None)
    monkeypatch.setattr(cli_compile, "_can_skip_compile", lambda *_a: True)
    monkeypatch.setattr(cli_compile, "_report_skipped_compile", lambda *_a: None)

    def fake_finish(*_args, **kwargs):
        calls["finish"] = kwargs

    monkeypatch.setattr(cli_compile, "_finish_compile", fake_finish)

    assert cli_compile._compile(args, state) is True
    assert calls["finish"]["status"] == "skipped"


def test_draft_model_invalid_utf8_logs_without_traceback(tmp_path, monkeypatch, caplog):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "main.tex").write_bytes(
        "\\documentclass{article}\n\\begin{document}\n中文\n\\end{document}\n".encode("gb18030")
    )
    before = (tmp_path / "main.tex").read_bytes()

    MainFileOperation().draft_model("main", True)

    assert (tmp_path / "main.tex").read_bytes() == before
    assert "UTF-8" in caplog.text


def test_atomic_write_text_replaces_file_without_temp_residue(tmp_path):
    target = tmp_path / "config.toml"
    target.write_text("old", encoding="utf-8")

    atomic_write_text(target, "new\r\n")

    assert target.read_bytes() == b"new\r\n"
    assert not list(tmp_path.glob(".config.toml.tmp-*"))


def test_no_synctex_removes_stale_synctex(tmp_path):
    state = SimpleNamespace(outdir=str(tmp_path), output_name="main")
    stale = tmp_path / "main.synctex.gz"
    stale.write_bytes(b"old")

    cli_compile._discard_stale_synctex(state)

    assert not stale.exists()


def test_run_command_cleans_temp_fallback(tmp_path, monkeypatch):
    fallback = tmp_path / ".pytexmk-tmp"

    def fake_ensure(env, _path):
        fallback.mkdir(parents=True, exist_ok=True)
        return env, str(fallback)

    monkeypatch.setattr(subprocess_runner, "ensure_writable_temp", fake_ensure)
    runner = MySubProcess(tmp_path, tmp_path, stream_output=False)

    assert runner.run_command(
        [sys.executable, "-c", "print('ok')"],
        [],
        [],
        cwd=tmp_path,
    )
    assert not fallback.exists()
