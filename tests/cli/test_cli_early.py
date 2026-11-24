"""``cli_early`` 早退出子命令的分派与退出码。

-i / -iu / --show-config / -ls 一旦命中就必须结束进程；普通编译不能被它们
误吞。此前这些分支只由 CLI 黑盒用例间接走过，退出码写错无人发现。
"""
import logging
from types import SimpleNamespace

import pytest

from pytexmk.cli import cli_config, cli_early
from pytexmk.lifecycle import EXIT_CONFIG_ERROR

LOGGER = logging.getLogger("test.cli_early")


def _args(**overrides):
    values = {
        "show_config": False,
        "init": False,
        "init_user": False,
        "list_subprojects": False,
    }
    values.update(overrides)
    return SimpleNamespace(**values)


@pytest.fixture
def silent_console(monkeypatch):
    printed: list[str] = []

    def fake_print(*args, **kwargs):
        printed.append(str(args[0]) if args else "")

    monkeypatch.setattr(cli_early, "console", SimpleNamespace(print=fake_print))
    return printed


def test_no_subcommand_does_not_exit(monkeypatch):
    exited: list[int] = []
    monkeypatch.setattr(cli_early, "exit_pytexmk", lambda code=0: exited.append(code))

    cli_early.handle(_args(), SimpleNamespace(), LOGGER)

    assert exited == []


def test_show_config_without_errors_exits_zero(monkeypatch, silent_console):
    seen: list[object] = []
    monkeypatch.setattr(cli_config, "show_config", lambda cp: seen.append(cp))
    cp = SimpleNamespace(load_errors=[])

    with pytest.raises(SystemExit) as exc:
        cli_early.handle(_args(show_config=True), cp, LOGGER)

    assert exc.value.code == 0
    assert seen == [cp]


def test_show_config_with_load_errors_exits_config_error(monkeypatch, silent_console):
    monkeypatch.setattr(cli_config, "show_config", lambda cp: None)
    cp = SimpleNamespace(load_errors=["broken"])

    with pytest.raises(SystemExit) as exc:
        cli_early.handle(_args(show_config=True), cp, LOGGER)

    assert exc.value.code == EXIT_CONFIG_ERROR


@pytest.mark.parametrize(("ok", "expected"), [(True, 0), (False, EXIT_CONFIG_ERROR)])
def test_init_project_config_exit_code(monkeypatch, silent_console, ok, expected):
    cp = SimpleNamespace(init_project_config=lambda: ok)

    with pytest.raises(SystemExit) as exc:
        cli_early.handle(_args(init=True), cp, LOGGER)

    assert exc.value.code == expected


@pytest.mark.parametrize(("ok", "expected"), [(True, 0), (False, EXIT_CONFIG_ERROR)])
def test_init_user_config_exit_code(monkeypatch, silent_console, ok, expected):
    cp = SimpleNamespace(init_user_config=lambda: ok)

    with pytest.raises(SystemExit) as exc:
        cli_early.handle(_args(init_user=True), cp, LOGGER)

    assert exc.value.code == expected


def test_list_subprojects_delegates(monkeypatch):
    seen: list[object] = []
    monkeypatch.setattr(cli_early, "_list_subprojects", lambda cp: seen.append(cp))
    cp = SimpleNamespace()

    cli_early.handle(_args(list_subprojects=True), cp, LOGGER)

    assert seen == [cp]
