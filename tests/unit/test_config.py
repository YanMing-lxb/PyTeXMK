# -*- coding: utf-8 -*-
"""config 配置模块单元测试"""

import toml
import pytest
from pathlib import Path
from unittest.mock import patch

from pytexmk.config import ConfigParser


@pytest.fixture
def temp_dirs(tmp_path, monkeypatch):
    """创建临时 HOME 和 CWD 目录"""
    home_dir = tmp_path / "home"
    cwd_dir = tmp_path / "project"
    home_dir.mkdir()
    cwd_dir.mkdir()

    monkeypatch.setattr(Path, "home", lambda: home_dir)
    monkeypatch.chdir(cwd_dir)

    return home_dir, cwd_dir


@pytest.fixture
def isolated_config(temp_dirs):
    """创建隔离环境的 ConfigParser 实例（非交互模式，禁用项目配置）"""
    home_dir, cwd_dir = temp_dirs

    cp = ConfigParser(interactive=False)
    cp.user_config_path = home_dir / ".pytexmkrc"
    cp.project_config_path = cwd_dir / ".nonexistent_project_config"

    return cp


@pytest.fixture
def default_user_config():
    """读取默认用户配置内容"""
    data_dir = Path(__file__).parent.parent.parent / "src" / "pytexmk" / "data"
    with open(data_dir / "default_user_config.toml", "r", encoding="utf-8") as f:
        return toml.load(f)


class TestConfigParserInit:
    def test_interactive_mode_default(self):
        cp = ConfigParser()
        assert cp.interactive is True

    def test_non_interactive_mode(self):
        cp = ConfigParser(interactive=False)
        assert cp.interactive is False

    def test_is_dict_subclass(self):
        cp = ConfigParser(interactive=False)
        assert isinstance(cp, dict)

    def test_missing_key_returns_none(self):
        cp = ConfigParser(interactive=False)
        assert cp["nonexistent_key"] is None


class TestLoadNonexistentConfig:
    def test_creates_default_config(self, isolated_config, default_user_config):
        """加载不存在的配置文件时应创建默认配置"""
        config = isolated_config.init_config_file()

        assert config["default_file"] == default_user_config["default_file"]
        assert config["compiled_program"] == default_user_config["compiled_program"]
        assert "engine" in config
        assert "pvc" in config
        assert "compilation" in config
        assert config["engine"]["default"] == "xelatex"
        assert config["pvc"]["enabled"] is False
        assert config["compilation"]["default_run_count"] == 2

    def test_default_file_created(self, isolated_config):
        """配置文件应被创建到磁盘"""
        assert not isolated_config.user_config_path.exists()
        isolated_config.init_config_file()
        assert isolated_config.user_config_path.exists()


class TestLoadOldConfig:
    def test_old_config_autocompletes_new_sections(self, isolated_config):
        """包含旧配置的文件应自动补全新增配置项"""
        old_config = {
            "default_file": "main",
            "compiled_program": "XeLaTeX",
            "non_quiet": False,
            "quiet_mode": True,
            "project_config_auto_init": False,
            "pdf": {
                "pdf_preview_status": True,
                "pdf_viewer": "default",
            },
            "folder": {
                "auxdir": "./Auxiliary/",
                "outdir": "./Build/",
            },
            "index": {
                "index_style_file": "nomencl.ist",
                "input_suffix": ".nlo",
                "output_suffix": ".nls",
            },
            "latexdiff": {
                "old_tex_file": "old_file",
                "new_tex_file": "new_file",
                "diff_tex_file": "LaTeXDiff",
            },
        }

        with open(isolated_config.user_config_path, "w", encoding="utf-8") as f:
            toml.dump(old_config, f)

        config = isolated_config.init_config_file()

        assert "engine" in config
        assert config["engine"]["default"] == "xelatex"
        assert "bib" in config
        assert "pvc" in config
        assert "compilation" in config
        assert "output" in config
        assert "diff" in config
        assert config["index"]["default_tool"] == "auto"
        assert config["default_file"] == "main"
        assert config["folder"]["auxdir"] == "./Auxiliary/"


class TestNonInteractiveMode:
    def test_no_input_called(self, isolated_config):
        """非交互模式下不应调用 input()"""
        incomplete_config = {
            "default_file": "main",
            "non_quiet": False,
            "quiet_mode": True,
            "project_config_auto_init": False,
        }
        with open(isolated_config.user_config_path, "w", encoding="utf-8") as f:
            toml.dump(incomplete_config, f)

        with patch("builtins.input", side_effect=Exception("input() should not be called")):
            isolated_config.init_config_file()


class TestTypeConversion:
    def test_string_true_to_bool(self, isolated_config):
        """字符串 'true' 应转换为 bool True"""
        test_config = {
            "default_file": "main",
            "compiled_program": "XeLaTeX",
            "non_quiet": "true",
            "quiet_mode": False,
            "project_config_auto_init": False,
        }
        with open(isolated_config.user_config_path, "w", encoding="utf-8") as f:
            toml.dump(test_config, f)

        config = isolated_config.init_config_file()

        assert config["non_quiet"] is True
        assert config["quiet_mode"] is False

    def test_string_false_to_bool(self, isolated_config):
        """字符串 'false' 应转换为 bool False"""
        test_config = {
            "default_file": "main",
            "compiled_program": "XeLaTeX",
            "non_quiet": "false",
            "quiet_mode": True,
            "project_config_auto_init": False,
        }
        with open(isolated_config.user_config_path, "w", encoding="utf-8") as f:
            toml.dump(test_config, f)

        config = isolated_config.init_config_file()

        assert config["non_quiet"] is False

    def test_string_int_to_int(self, isolated_config):
        """字符串数字应转换为 int"""
        test_config = {
            "default_file": "main",
            "compiled_program": "XeLaTeX",
            "non_quiet": False,
            "quiet_mode": True,
            "project_config_auto_init": False,
            "engine": {
                "default": "xelatex",
                "auto_detect": True,
                "fallback_order": ["xelatex"],
                "timeout": "600",
            },
        }
        with open(isolated_config.user_config_path, "w", encoding="utf-8") as f:
            toml.dump(test_config, f)

        config = isolated_config.init_config_file()

        assert config["engine"]["timeout"] == 600
        assert isinstance(config["engine"]["timeout"], int)

    def test_string_float_to_float(self, isolated_config):
        """字符串数字应转换为 float"""
        test_config = {
            "default_file": "main",
            "compiled_program": "XeLaTeX",
            "non_quiet": False,
            "quiet_mode": True,
            "project_config_auto_init": False,
            "pvc": {
                "enabled": False,
                "debounce": "2.5",
                "auto_open_preview": False,
                "watch_extensions": [".tex"],
                "exclude_dirs": ["build"],
            },
        }
        with open(isolated_config.user_config_path, "w", encoding="utf-8") as f:
            toml.dump(test_config, f)

        config = isolated_config.init_config_file()

        assert config["pvc"]["debounce"] == 2.5
        assert isinstance(config["pvc"]["debounce"], float)


class TestConfigValidation:
    def test_invalid_engine_produces_warning(self, isolated_config, caplog):
        """非法 engine 值应产生警告"""
        import logging

        test_config = {
            "default_file": "main",
            "compiled_program": "XeLaTeX",
            "non_quiet": False,
            "quiet_mode": True,
            "project_config_auto_init": False,
            "engine": {
                "default": "invalid_engine",
                "auto_detect": True,
                "fallback_order": ["xelatex"],
                "timeout": 300,
            },
        }
        with open(isolated_config.user_config_path, "w", encoding="utf-8") as f:
            toml.dump(test_config, f)

        with caplog.at_level(logging.WARNING):
            isolated_config.init_config_file()

        assert any("未知的默认引擎" in record.message for record in caplog.records)

    def test_invalid_timeout_produces_warning(self, isolated_config, caplog):
        """非正数 timeout 应产生警告"""
        import logging

        test_config = {
            "default_file": "main",
            "compiled_program": "XeLaTeX",
            "non_quiet": False,
            "quiet_mode": True,
            "project_config_auto_init": False,
            "engine": {
                "default": "xelatex",
                "auto_detect": True,
                "fallback_order": ["xelatex"],
                "timeout": -10,
            },
        }
        with open(isolated_config.user_config_path, "w", encoding="utf-8") as f:
            toml.dump(test_config, f)

        with caplog.at_level(logging.WARNING):
            isolated_config.init_config_file()

        assert any("编译超时必须是正数" in record.message for record in caplog.records)

    def test_valid_config_no_warnings(self, isolated_config, caplog):
        """合法配置不应产生验证警告"""
        import logging

        with caplog.at_level(logging.WARNING):
            isolated_config.init_config_file()

        warning_messages = [r.message for r in caplog.records if r.levelno >= logging.WARNING]
        validation_warnings = [m for m in warning_messages if "未知" in m or "必须是" in m]
        assert len(validation_warnings) == 0


class TestDotNotationAccess:
    def test_get_nested_key(self, isolated_config):
        """get() 方法支持点号访问"""
        config = isolated_config.init_config_file()
        assert config.get("engine.default") == "xelatex"
        assert config.get("pvc.enabled") is False
        assert config.get("compilation.default_run_count") == 2

    def test_get_nonexistent_key_returns_default(self, isolated_config):
        """get() 访问不存在的键应返回默认值"""
        config = isolated_config.init_config_file()
        assert config.get("nonexistent.key") is None
        assert config.get("nonexistent.key", "default_val") == "default_val"

    def test_get_nested_nonexistent(self, isolated_config):
        """get() 访问嵌套不存在的键应返回默认值"""
        config = isolated_config.init_config_file()
        assert config.get("engine.nonexistent") is None

    def test_convenience_methods(self, isolated_config):
        """便捷方法应返回对应的配置节"""
        config = isolated_config.init_config_file()

        engine_cfg = config.get_engine_config()
        assert isinstance(engine_cfg, dict)
        assert "default" in engine_cfg
        assert engine_cfg["default"] == "xelatex"

        pvc_cfg = config.get_pvc_config()
        assert isinstance(pvc_cfg, dict)
        assert "enabled" in pvc_cfg

        compilation_cfg = config.get_compilation_config()
        assert isinstance(compilation_cfg, dict)
        assert "default_run_count" in compilation_cfg

        bib_cfg = config.get_bib_config()
        assert isinstance(bib_cfg, dict)
        assert "default_tool" in bib_cfg

        index_cfg = config.get_index_config()
        assert isinstance(index_cfg, dict)

        output_cfg = config.get_output_config()
        assert isinstance(output_cfg, dict)
        assert "outdir" in output_cfg

        diff_cfg = config.get_diff_config()
        assert isinstance(diff_cfg, dict)
        assert "flatten" in diff_cfg


class TestProjectConfigOverride:
    def test_project_config_overrides_user_config(self, temp_dirs):
        """项目配置应覆盖用户配置（递归合并）"""
        home_dir, cwd_dir = temp_dirs

        user_config = {
            "default_file": "user_main",
            "compiled_program": "XeLaTeX",
            "non_quiet": False,
            "quiet_mode": True,
            "project_config_auto_init": True,
            "engine": {
                "default": "xelatex",
                "auto_detect": True,
                "timeout": 300,
                "fallback_order": ["xelatex", "lualatex", "pdflatex"],
            },
        }

        project_config = {
            "default_file": "project_main",
            "engine": {
                "default": "lualatex",
                "timeout": 600,
            },
        }

        cp = ConfigParser(interactive=False)
        cp.user_config_path = home_dir / ".pytexmkrc"
        cp.project_config_path = cwd_dir / ".pytexmkrc"

        with open(cp.user_config_path, "w", encoding="utf-8") as f:
            toml.dump(user_config, f)
        with open(cp.project_config_path, "w", encoding="utf-8") as f:
            toml.dump(project_config, f)

        config = cp.init_config_file()

        assert config["default_file"] == "project_main"
        assert config["engine"]["default"] == "lualatex"
        assert config["engine"]["timeout"] == 600
        assert config["engine"]["auto_detect"] is True
        assert config["engine"]["fallback_order"] == ["xelatex", "lualatex", "pdflatex"]


class TestBackwardCompatibility:
    def test_dict_style_access(self, isolated_config):
        """旧方式 config['key'] 仍可访问"""
        config = isolated_config.init_config_file()

        assert config["default_file"] == "main"
        assert config["compiled_program"] == "XeLaTeX"
        assert isinstance(config["pdf"], dict)
        assert isinstance(config["folder"], dict)
        assert config["folder"]["outdir"] == "./Build/"
        assert isinstance(config["index"], dict)
        assert isinstance(config["latexdiff"], dict)

    def test_quiet_mode_compatibility(self, isolated_config):
        """quiet_mode 和 non_quiet 应同时存在且互反"""
        config = isolated_config.init_config_file()

        assert "quiet_mode" in config
        assert "non_quiet" in config
        assert config["quiet_mode"] == (not config["non_quiet"])

    def test_old_config_sections_preserved(self, isolated_config):
        """旧配置节 [folder] [latexdiff] 等应保留"""
        config = isolated_config.init_config_file()

        assert "folder" in config
        assert "auxdir" in config["folder"]
        assert "outdir" in config["folder"]
        assert "latexdiff" in config
        assert "old_tex_file" in config["latexdiff"]
        assert "new_tex_file" in config["latexdiff"]
        assert "diff_tex_file" in config["latexdiff"]


class TestDeepUpdate:
    def test_deep_update_nested(self, isolated_config):
        """_deep_update 应递归合并嵌套字典"""
        base = {
            "a": 1,
            "nested": {
                "x": 10,
                "y": 20,
            },
        }
        override = {
            "a": 2,
            "nested": {
                "y": 30,
                "z": 40,
            },
        }

        result = isolated_config._deep_update(base, override)

        assert result["a"] == 2
        assert result["nested"]["x"] == 10
        assert result["nested"]["y"] == 30
        assert result["nested"]["z"] == 40

    def test_deep_update_does_not_modify_original(self, isolated_config):
        """_deep_update 不应修改原始字典"""
        base = {"a": 1, "nested": {"x": 10}}
        override = {"nested": {"y": 20}}

        result = isolated_config._deep_update(base, override)

        assert "y" not in base["nested"]
        assert result is not base


class TestConvertConfigValue:
    def test_convert_bool_variants(self, isolated_config):
        """测试各种 bool 字符串转换"""
        assert isolated_config._convert_config_value("test", "true", False) is True
        assert isolated_config._convert_config_value("test", "True", False) is True
        assert isolated_config._convert_config_value("test", "yes", False) is True
        assert isolated_config._convert_config_value("test", "1", False) is True
        assert isolated_config._convert_config_value("test", "on", False) is True
        assert isolated_config._convert_config_value("test", "false", True) is False
        assert isolated_config._convert_config_value("test", "no", True) is False
        assert isolated_config._convert_config_value("test", "0", True) is False

    def test_convert_int_from_string(self, isolated_config):
        assert isolated_config._convert_config_value("test", "123", 0) == 123

    def test_convert_float_from_string(self, isolated_config):
        assert isolated_config._convert_config_value("test", "3.14", 0.0) == pytest.approx(3.14)

    def test_convert_list_from_comma_string(self, isolated_config):
        result = isolated_config._convert_config_value("test", "a, b, c", [])
        assert result == ["a", "b", "c"]

    def test_same_type_returns_as_is(self, isolated_config):
        assert isolated_config._convert_config_value("test", 42, 0) == 42
        assert isolated_config._convert_config_value("test", "hello", "") == "hello"

    def test_none_returns_default(self, isolated_config):
        assert isolated_config._convert_config_value("test", None, "default") == "default"
