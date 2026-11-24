"""CLI 启动器：`--version` 快速路径必须只输出一行版本号。"""

import sys

from pytexmk._launcher import main
from pytexmk.version import __version__, script_name


def _run_version(monkeypatch, capsys, flag: str) -> str:
    monkeypatch.setattr(sys, "argv", ["pytexmk", flag])
    main()
    return capsys.readouterr().out


def test_version_fast_path_long_flag(monkeypatch, capsys):
    assert _run_version(monkeypatch, capsys, "--version") == f"{script_name} {__version__}\n"


def test_version_fast_path_short_flag(monkeypatch, capsys):
    assert _run_version(monkeypatch, capsys, "-v") == f"{script_name} {__version__}\n"
