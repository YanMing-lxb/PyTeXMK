"""共享 fixture：构造与真实 HOME 隔离的 ConfigParser。"""
import pytest

from pytexmk.config import ConfigParser


@pytest.fixture
def make_parser():
    """返回一个函数：把用户 rc 路径指向临时目录，避免读取真实 ~/.pytexmkrc。"""

    def _make(user_config_dir) -> ConfigParser:
        parser = ConfigParser()
        parser.user_config_path = user_config_dir / ".pytexmkrc"
        return parser

    return _make