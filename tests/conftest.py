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

# 测试进程统一按中文源语言解析。GitHub 等英文 locale 机器上若不固定，
# ``set_language`` 会加载英文 .mo，而用例断言的是中文源码文案，造成跨平台误报。
# 必须在首次导入 ``pytexmk.language`` 之前设置：语言探测与翻译结果都带
# ``@functools.cache``，导入后再改环境变量不会生效。LANGUAGE 在探测顺序里
# 优先级最高，直接覆盖；其余三项只在未设置时兜底。
os.environ["LANGUAGE"] = "zh_CN.UTF-8"
for _env in ("LC_ALL", "LC_CTYPE", "LANG"):
    os.environ.setdefault(_env, "zh_CN.UTF-8")

from pytexmk import language  # noqa: E402
from pytexmk.config import ConfigParser  # noqa: E402

_LAYER_MARKERS = {
    "unit": "unit",
    "cli": "cli",
    "integration": "integration",
    "regressions": "regression",
}


@pytest.fixture(scope="session", autouse=True)
def _pin_chinese_locale():
    """固定测试语言为中文，并清掉语言探测/翻译缓存。

    ``get_locale_lang`` 与 ``set_language`` 都带 ``@functools.cache``；若进程在
    环境变量设置前已加载过某个翻译域，必须清缓存后重新探测，否则首次 locale
    会粘住。守卫断言失败时直接报「语言未固定」，而不是散成多条文案断言。
    """
    language.get_locale_lang.cache_clear()
    language.set_language.cache_clear()
    assert language.get_locale_lang().startswith("zh"), (
        "测试语言未固定为中文；请检查 LANGUAGE/LC_ALL/LANG 环境变量"
    )
    yield


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
        for _env in ("LANGUAGE", "LC_ALL", "LC_CTYPE", "LANG"):
            env.setdefault(_env, "zh_CN.UTF-8")
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
