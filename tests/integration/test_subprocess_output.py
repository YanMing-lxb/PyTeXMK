"""子进程输出收尾：退出检测不能被子进程/孙进程的输出频率拖住。

报告里的可复现缺陷：``_EOF_GRACE_SECONDS`` 存在，但只有在"队列这轮为空"时
才检查 ``process.poll()``；孙进程持续写 stdout/stderr 时，队列永不为空，父进程
早已退出也永远看不到，宽限期形同虚设。重定向路径更直接：``communicate()`` 会
一直等 stderr 管道 EOF。

本文件覆盖：持续输出孙进程、静默孙进程、重定向 stderr、截断标记与退出码。
"""

import sys
import time

import pytest

from pytexmk import subprocess_runner


def _runner(tmp_path, *, stream=True):
    return subprocess_runner.MySubProcess(
        str(tmp_path), str(tmp_path), "demo", stream_output=stream
    )


def _short_grace(monkeypatch, seconds=0.6):
    monkeypatch.setattr(subprocess_runner, "_EOF_GRACE_SECONDS", seconds)
    monkeypatch.setattr(subprocess_runner, "_READER_POLL_SECONDS", 0.05)


def test_continuous_grandchild_output_does_not_extend_grace(monkeypatch, capsys, tmp_path):
    """父进程退出后孙进程仍持续写 stdout，收尾必须在宽限期内完成。"""
    _short_grace(monkeypatch)
    child = (
        "import sys, time\n"
        "for i in range(80):\n"
        "    print('tick', flush=True)\n"
        "    time.sleep(0.05)\n"
    )
    script = (
        "import subprocess, sys\n"
        f"subprocess.Popen([sys.executable, '-c', {child!r}])\n"
        "print('parent-done', flush=True)\n"
    )
    runner = _runner(tmp_path, stream=True)
    started = time.monotonic()
    assert runner.run_command(
        [sys.executable, "-c", script], [], [], "spawn", cwd=tmp_path
    ) is True
    elapsed = time.monotonic() - started

    assert elapsed < 2.5, f"父进程已退出，不应陪孙进程持续输出（实测 {elapsed:.1f}s）"
    assert runner.last_output_truncated is True
    out = capsys.readouterr().out
    assert "后续输出可能未收集" in out


def test_silent_grandchild_holding_stdout_is_bounded(monkeypatch, tmp_path):
    """流式路径：孙进程握着 stdout 不写，同样不能无限等。"""
    _short_grace(monkeypatch)
    script = (
        "import subprocess, sys\n"
        "subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(4)'])\n"
        "print('parent-done', flush=True)\n"
    )
    runner = _runner(tmp_path, stream=True)
    started = time.monotonic()
    assert runner.run_command(
        [sys.executable, "-c", script], [], [], "spawn", cwd=tmp_path
    ) is True
    elapsed = time.monotonic() - started

    assert elapsed < 2.5, f"流式收尾被静默孙进程拖住（实测 {elapsed:.1f}s）"
    assert runner.last_output_truncated is True


def test_continuous_grandchild_stderr_does_not_extend_redirected_grace(
    monkeypatch, capsys, tmp_path
):
    """重定向路径只读 stderr：孙进程持续写 stderr 也不能无限等。"""
    _short_grace(monkeypatch)
    child = (
        "import sys, time\n"
        "for i in range(80):\n"
        "    print('err', file=sys.stderr, flush=True)\n"
        "    time.sleep(0.05)\n"
    )
    script = (
        "import subprocess, sys\n"
        f"subprocess.Popen([sys.executable, '-c', {child!r}])\n"
        "print('parent-done', flush=True)\n"
    )
    target = tmp_path / "diff.tex"
    runner = _runner(tmp_path)
    started = time.monotonic()
    assert runner.run_command(
        [sys.executable, "-c", script],
        [],
        [],
        "spawn",
        stdout_path=str(target),
        cwd=tmp_path,
    ) is True
    elapsed = time.monotonic() - started

    assert elapsed < 2.5, f"重定向收尾被 stderr 拖住（实测 {elapsed:.1f}s）"
    assert target.read_text(encoding="utf-8") == "parent-done\n"
    assert runner.last_output_truncated is True


def test_silent_grandchild_holding_stderr_is_bounded(monkeypatch, tmp_path):
    """静默孙进程握着 stderr 不写：同样按宽限期收尾。"""
    _short_grace(monkeypatch)
    script = (
        "import subprocess, sys\n"
        "subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(4)'])\n"
        "print('parent-done', flush=True)\n"
    )
    target = tmp_path / "diff.tex"
    runner = _runner(tmp_path)
    started = time.monotonic()
    assert runner.run_command(
        [sys.executable, "-c", script],
        [],
        [],
        "spawn",
        stdout_path=str(target),
        cwd=tmp_path,
    ) is True
    elapsed = time.monotonic() - started

    assert elapsed < 2.5, f"父进程已退出，不该等孙进程睡满（实测 {elapsed:.1f}s）"
    assert runner.last_output_truncated is True


def test_failure_carries_truncation_and_exit_code(monkeypatch, tmp_path):
    """失败时保留真实退出码，并标记输出可能不完整。"""
    _short_grace(monkeypatch)
    child = "import time\nfor i in range(80):\n    print('tick', flush=True)\n    time.sleep(0.05)\n"
    script = (
        "import subprocess, sys\n"
        f"subprocess.Popen([sys.executable, '-c', {child!r}])\n"
        "print('parent-done', flush=True)\n"
        "raise SystemExit(3)\n"
    )
    runner = _runner(tmp_path)
    started = time.monotonic()
    with pytest.raises(subprocess_runner.SubprocessFailedError) as excinfo:
        runner.run_command(
            [sys.executable, "-c", script], [], [], "spawn", cwd=tmp_path
        )
    elapsed = time.monotonic() - started

    assert elapsed < 2.5
    assert excinfo.value.exit_code == 3
    assert excinfo.value.output_truncated is True


def test_normal_command_does_not_mark_truncation(monkeypatch, tmp_path):
    _short_grace(monkeypatch)
    runner = _runner(tmp_path, stream=False)
    assert runner.run_command(
        [sys.executable, "-c", "print('hello')"], [], [], "echo", cwd=tmp_path
    ) is True
    assert runner.last_output_truncated is False
