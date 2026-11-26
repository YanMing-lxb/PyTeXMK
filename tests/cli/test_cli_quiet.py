"""安静模式解析（``-nq`` / 配置文件 ``quiet_mode``）。

口径（与 1.2.7 对齐）：

* 控制台日志级别只看 ``-vb``：``-vb`` → INFO，否则 WARNING；``-nq``
  不再影响级别（0.6 曾让 ``-nq`` 把级别抬到 INFO，等于把"刷屏"当成它的职责）；
* ``-nq`` 只控制**显示**：子进程输出是否实时打到终端（``stream_output``）；
  TeX 的 ``-interaction`` 不随安静模式变化（默认都是 ``nonstopmode``，
  要 batchmode 得在配置里写 ``[build] interaction``，命令行没有该开关）；
* 优先级：命令行 ``-nq`` > 配置文件 ``quiet_mode`` > 内置默认（安静）。
"""

import logging
import sys
from io import StringIO
from types import SimpleNamespace

import pytest
from rich.console import Console

from pytexmk import subprocess_runner, ui_theme
from pytexmk.cli import cli_args, cli_context
from pytexmk.logger_config import setup_logger


class _StubState:
    """``_apply_quiet_mode`` 只需要这些字段。"""

    def __init__(self, quiet_mode):
        self.config_dict = {"quiet_mode": quiet_mode}
        self.non_quiet = False
        self.logger = logging.getLogger("pytexmk")


def _args(*, non_quiet=False, verbose=False, document=None):
    return SimpleNamespace(
        non_quiet=non_quiet, verbose=verbose, document=document
    )


@pytest.fixture(autouse=True)
def _restore_log_levels():
    root = logging.getLogger()
    pkg = logging.getLogger("pytexmk")
    before = (root.level, pkg.level)
    yield
    root.setLevel(before[0])
    pkg.setLevel(before[1])


class TestQuietResolution:
    """优先级：命令行 > 配置文件 > 内置默认（quiet）。"""

    def test_non_quiet_flag_beats_config_quiet(self):
        """配置文件 quiet_mode=true 时，-nq 必须回到非安静模式。"""
        state = _StubState(quiet_mode=True)
        cli_context._apply_quiet_mode(state, _args(non_quiet=True))
        assert state.non_quiet is True

    def test_config_quiet_when_no_flag(self):
        state = _StubState(quiet_mode=True)
        cli_context._apply_quiet_mode(state, _args())
        assert state.non_quiet is False

    def test_config_non_quiet_when_no_flag(self):
        state = _StubState(quiet_mode=False)
        cli_context._apply_quiet_mode(state, _args())
        assert state.non_quiet is True


class TestConsoleLevelStaysOutOfQuietMode:
    """安静模式不得改动控制台级别；级别只由 ``-vb`` 决定（1.2.7 口径）。"""

    def test_verbose_raises_level_to_info_not_debug(self):
        setup_logger(verbose=True)
        assert logging.getLogger("pytexmk").level == logging.INFO
        assert logging.getLogger("pytexmk").level != logging.DEBUG

    def test_non_quiet_flag_does_not_raise_level(self):
        pkg = logging.getLogger("pytexmk")
        pkg.setLevel(logging.WARNING)
        cli_context._apply_quiet_mode(_StubState(True), _args(non_quiet=True))
        assert pkg.level == logging.WARNING


class TestSubprocessStreaming:
    """``-nq`` 的可见效果：子进程输出逐行打到终端；``-q`` 只留结论。"""

    @staticmethod
    def _run(monkeypatch, stream_output: bool) -> str:
        buffer = StringIO()
        fake_console = Console(
            file=buffer,
            width=200,
            force_terminal=False,
            no_color=True,
            theme=ui_theme.custom_theme,
        )
        monkeypatch.setattr(subprocess_runner, "console", fake_console)
        # 标记不能出现在命令行本身（否则"运行命令: …"那一行会误命中）
        command = [sys.executable, "-c", "print(''.join(['child', 'hello']))"]
        process = subprocess_runner.MySubProcess(
            ".", ".", "demo", stream_output=stream_output
        )
        assert process.run_command(command, [], [], "echo") is True
        return buffer.getvalue()

    def test_non_quiet_streams_child_stdout(self, monkeypatch):
        assert "childhello" in self._run(monkeypatch, True)

    def test_quiet_suppresses_child_stdout(self, monkeypatch):
        assert "childhello" not in self._run(monkeypatch, False)


def test_quiet_flag_is_removed():
    """``-q`` 已删除；只剩 ``-nq`` 这一种显示覆盖。"""
    parser = cli_args.build_parser()
    with pytest.raises(SystemExit) as exc:
        parser.parse_args(["-q"])
    assert exc.value.code == 2
