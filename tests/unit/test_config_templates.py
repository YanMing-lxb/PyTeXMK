"""随包配置模板必须通过 ``--validate-config`` 的同一套检查。

``default_user_config.toml`` 曾经写着 ``non_quiet = false``——那是早年的键名，
运行时只认 ``quiet_mode``，于是 ``pytexmk -iu`` 生成的文件一上来就带着一个
"未知配置项"，``--validate-config`` 直接判失败。模板是用户复制的源头，
任何死键都必须在测试里被挡住。
"""

import tomllib
from pathlib import Path

import pytest

import pytexmk
from pytexmk.cli.cli_config import _semantic, _walk
from pytexmk.config import DEFAULT_CONFIG

DATA_DIR = Path(pytexmk.__file__).parent / "data"


@pytest.mark.parametrize(
    "file_name",
    ["default_project_config.toml", "default_user_config.toml"],
)
def test_bundled_config_template_validates_clean(file_name):
    template = DATA_DIR / file_name
    data = tomllib.loads(template.read_text(encoding="utf-8"))
    errors: list[str] = []
    _walk(DEFAULT_CONFIG, data, "", errors)
    _semantic(data, errors)
    assert errors == [], f"{file_name} 含非法配置：{errors}"


def test_templates_use_quiet_mode_not_legacy_non_quiet():
    """安静模式的唯一键名是 ``quiet_mode``；``non_quiet`` 是历史遗留。"""
    for file_name in ("default_project_config.toml", "default_user_config.toml"):
        data = tomllib.loads((DATA_DIR / file_name).read_text(encoding="utf-8"))
        assert data.get("quiet_mode") is True
        assert "non_quiet" not in data


def test_shell_escape_defaults_to_on():
    """shell-escape 默认开启：模板、运行时默认值、引擎默认参数三处必须一致。"""
    from dataclasses import fields

    from pytexmk.cli.cli_state import WorkflowState

    assert DEFAULT_CONFIG["build"]["shell_escape"] == "true"
    assert {f.name: f.default for f in fields(WorkflowState)}["shell_escape"] == "true"
    for file_name in ("default_project_config.toml", "default_user_config.toml"):
        data = tomllib.loads((DATA_DIR / file_name).read_text(encoding="utf-8"))
        assert data["build"]["shell_escape"] == "true"
