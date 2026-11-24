"""安静模式硬化：显示与 ``-interaction`` 解耦、不建 Live、读管道不再无限期阻塞。

背景（用户反馈）：``pytexmk -l`` / ``-p`` / ``-x`` 不加 ``-nq`` 时会"卡住不动"，
加上 ``-nq`` 则很快编完。排查发现 ``-nq`` 只改两件事，而这两件事各有一处死结：

1. 安静模式曾把 TeX 换成 ``-interaction=batchmode``：同一份文档"加不加 -nq"
   走的是两套 TeX 语义，出问题根本没法区分是 PyTeXMK 卡住还是 TeX 行为不同；
2. 安静模式用 ``console.status()`` 打转圈：Live 有一条每 100ms 写一次终端的
   刷新线程，且写终端时持着 Live 的锁 —— 只要那次写被阻塞（Windows 控制台被
   选中进入标记模式、终端渲染被挂起），主线程退出 spinner 时会永远等锁；
3. 读输出用主线程 ``readline()``，``poll()`` 只在读返回后才检查：管道被残留
   子进程握着时，子进程早就结束了也会永远等下去，安静模式下毫无提示。
"""

import sys
import time

import pytest

from pytexmk import subprocess_runner, ui_theme
from pytexmk.compile import CompileLaTeX, effective_interaction


def _compile(stdout_path=None, **kwargs):
    non_quiet = kwargs.pop("non_quiet", False)
    kwargs.setdefault("native", False)
    return CompileLaTeX(
        "main",
        "XeLaTeX",
        [".pdf"],
        [".aux"],
        "./Build/",
        "./Auxiliary/",
        non_quiet,
        **kwargs,
    )


# ---------------------------------------------------------------- 交互模式


@pytest.mark.parametrize("non_quiet", [True, False])
def test_quiet_and_non_quiet_use_the_same_interaction(non_quiet, tmp_path, monkeypatch):
    """``-q`` / ``-nq`` 只影响显示：两者的 ``-interaction`` 必须完全一致。"""
    monkeypatch.chdir(tmp_path)
    command = _compile(non_quiet=non_quiet)._latex_command()
    assert "-interaction=nonstopmode" in command
    assert "-interaction=batchmode" not in command


def test_effective_interaction_defaults_to_nonstopmode():
    assert effective_interaction(None) == "nonstopmode"
    assert effective_interaction("") == "nonstopmode"
    assert effective_interaction("batchmode") == "batchmode"


def test_explicit_batchmode_still_reaches_the_engine(tmp_path, monkeypatch):
    """想用 batchmode 的人还能显式要求，不被"解耦"吃掉。"""
    monkeypatch.chdir(tmp_path)
    command = _compile(interaction="batchmode")._latex_command()
    assert "-interaction=batchmode" in command


# ---------------------------------------------------------------- 不建 Live


def test_quiet_mode_never_creates_a_live(monkeypatch, tmp_path):
    """安静模式不得再建 ``console.status``（Live 刷新线程是死锁源头）。"""
    created = []

    def _explode(*args, **kwargs):
        created.append(args)
        raise AssertionError("安静模式不应创建 Live/status")

    monkeypatch.setattr(type(ui_theme.console), "status", _explode)
    runner = subprocess_runner.MySubProcess(
        str(tmp_path), str(tmp_path), "demo", stream_output=False
    )
    assert runner.run_command(
        [sys.executable, "-c", "print('hello')"], [], [], "echo", cwd=tmp_path
    ) is True
    assert created == []


def test_quiet_mode_prints_one_static_line(monkeypatch, capsys, tmp_path):
    """安静模式要留一行静态提示，否则长时间无输出会像"卡死"。"""
    runner = subprocess_runner.MySubProcess(
        str(tmp_path), str(tmp_path), "demo", stream_output=False
    )
    assert runner.run_command(
        [sys.executable, "-c", "print('hello')"], [], [], "echo", cwd=tmp_path
    ) is True
    out = capsys.readouterr().out
    assert "正在echo…" in out
    # 进度行只报"在跑什么"，不再附带"（安静模式，实时日志请加 -nq）"这类说明；
    # -nq 仍由 --help / 配置模板说明，长时间无输出的心跳里也仍有提示。
    assert "-nq" not in out


# ------------------------------------------------------------ 读管道兜底


def test_stall_heartbeat_keeps_user_informed(monkeypatch, capsys, tmp_path):
    """子进程长时间不出声时打一行心跳，而不是让用户对着空屏猜。"""
    monkeypatch.setattr(subprocess_runner, "_STALL_NOTICE_SECONDS", 0.3)
    monkeypatch.setattr(subprocess_runner, "_READER_POLL_SECONDS", 0.05)
    runner = subprocess_runner.MySubProcess(
        str(tmp_path), str(tmp_path), "demo", stream_output=False
    )
    assert runner.run_command(
        [sys.executable, "-c", "import time; time.sleep(1.2)"],
        [], [], "sleepy", cwd=tmp_path,
    ) is True
    assert "没有输出" in capsys.readouterr().out


def test_pipe_kept_open_by_grandchild_does_not_hang(monkeypatch, capsys, tmp_path):
    """子进程已退出、但派生的进程还握着 stdout 管道时，必须按宽限期收尾。

    这正是旧实现"永远卡住"的另一条路径：主线程阻塞在 ``readline()``，
    而 ``poll()`` 只在读返回后才检查。
    """
    monkeypatch.setattr(subprocess_runner, "_EOF_GRACE_SECONDS", 1.0)
    monkeypatch.setattr(subprocess_runner, "_READER_POLL_SECONDS", 0.05)
    script = (
        "import subprocess, sys;"
        "subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(8)']);"
        "print('parent-done', flush=True)"
    )
    runner = subprocess_runner.MySubProcess(
        str(tmp_path), str(tmp_path), "demo", stream_output=True
    )
    started = time.monotonic()
    assert runner.run_command(
        [sys.executable, "-c", script], [], [], "spawn", cwd=tmp_path
    ) is True
    elapsed = time.monotonic() - started
    assert elapsed < 8, f"子进程早已退出，不该陪后台进程等满整段时间（实测 {elapsed:.1f}s）"
    assert "输出管道仍未关闭" in capsys.readouterr().out
