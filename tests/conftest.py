"""共享 fixture、分层标记与真实 CLI 启动器。

测试按目录分层（unit / cli / integration / regressions），标记由本文件的
``pytest_collection_modifyitems`` 依据父目录自动打上，新增文件不必手写
``@pytest.mark.unit``。运行范围用 ``-m`` 选择即可。
"""
import os
import subprocess
import sys
from pathlib import Path

import pytest

from pytexmk.config import ConfigParser

_LAYER_MARKERS = {
    "unit": "unit",
    "cli": "cli",
    "integration": "integration",
    "regressions": "regression",
}


def pytest_collection_modifyitems(config, items):
    """按测试文件所在目录补充分层标记，避免逐文件手写装饰器。"""
    for item in items:
        marker = _LAYER_MARKERS.get(Path(str(item.fspath)).parent.name)
        if marker:
            item.add_marker(getattr(pytest.mark, marker))


@pytest.fixture(scope="session")
def repo_root() -> Path:
    """仓库根目录。测试不再各自数 ``parents`` 层数，避免目录调整后静默指错。"""
    return Path(__file__).resolve().parents[1]


@pytest.fixture
def run_cli(repo_root):
    """返回启动器：在指定项目目录里跑真实 CLI，返回 CompletedProcess。

    子进程统一带 ``PYTHONPATH=<repo>/src``，不依赖当前 shell 是否已 editable 安装。
    """

    def _run(project: Path, *argv: str, timeout: int = 120) -> subprocess.CompletedProcess:
        env = dict(os.environ)
        env["PYTHONPATH"] = str(repo_root / "src") + os.pathsep + env.get("PYTHONPATH", "")
        return subprocess.run(
            [sys.executable, "-m", "pytexmk", *argv],
            cwd=project,
            env=env,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout,
        )

    return _run


@pytest.fixture
def make_parser():
    """返回一个函数：把用户 rc 路径指向临时目录，避免读取真实 ~/.pytexmkrc。"""

    def _make(user_config_dir) -> ConfigParser:
        parser = ConfigParser()
        parser.user_config_path = user_config_dir / ".pytexmkrc"
        return parser

    return _make
