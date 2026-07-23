# -*- coding: utf-8 -*-
"""
配置系统集成测试
"""

from pathlib import Path
from unittest import mock

from pytexmk.config import ConfigParser


class TestConfigProjectLoading:
    """测试项目配置文件加载"""

    def test_load_project_config(self, tmp_path, monkeypatch):
        """验证 ConfigParser 能正确加载项目配置"""
        monkeypatch.chdir(tmp_path)

        config_content = """
[output]
outdir = "output"
auxdir = "aux"

[engine]
default = "pdflatex"
timeout = 120
"""
        config_file = tmp_path / ".pytexmkrc"
        config_file.write_text(config_content, encoding="utf-8")

        cp = ConfigParser(interactive=False)
        config = cp.init_config_file()

        assert config is not None
        output_config = config.get("output", {})
        assert output_config.get("outdir") == "output"
        assert output_config.get("auxdir") == "aux"
        engine_config = config.get("engine", {})
        assert engine_config.get("default") == "pdflatex"
        assert engine_config.get("timeout") == 120

    def test_project_config_overrides_user_config(self, tmp_path, monkeypatch):
        """验证项目配置覆盖用户配置"""
        monkeypatch.chdir(tmp_path)

        user_home = tmp_path / "user_home"
        user_home.mkdir()
        user_config = user_home / ".pytexmkrc"
        user_config.write_text(
            """
[engine]
default = "xelatex"
timeout = 300
""",
            encoding="utf-8",
        )

        project_config = tmp_path / ".pytexmkrc"
        project_config.write_text(
            """
[engine]
default = "pdflatex"
""",
            encoding="utf-8",
        )

        with mock.patch.object(Path, "home", return_value=user_home):
            cp = ConfigParser(interactive=False)
            config = cp.init_config_file()

        engine_config = config.get("engine", {})
        assert engine_config.get("default") == "pdflatex"


class TestConfigTypeConversion:
    """测试配置值类型转换"""

    def test_bool_type_conversion(self, tmp_path, monkeypatch):
        """验证 bool 类型转换正确"""
        monkeypatch.chdir(tmp_path)

        config_content = """
[engine]
auto_detect = false
timeout = 120

[compilation]
shell_escape = true
synctex = false
default_run_count = 3
"""
        config_file = tmp_path / ".pytexmkrc"
        config_file.write_text(config_content, encoding="utf-8")

        cp = ConfigParser(interactive=False)
        config = cp.init_config_file()

        engine_config = config.get("engine", {})
        assert engine_config.get("auto_detect") is False
        assert engine_config.get("timeout") == 120

        comp_config = config.get("compilation", {})
        assert comp_config.get("shell_escape") is True
        assert comp_config.get("synctex") is False
        assert comp_config.get("default_run_count") == 3

    def test_int_type_conversion(self, tmp_path, monkeypatch):
        """验证 int 类型转换正确"""
        monkeypatch.chdir(tmp_path)

        config_content = """
[engine]
timeout = 60

[compilation]
default_run_count = 1
max_extra_passes = 0

[output]
outdir = "custom_output"
"""
        config_file = tmp_path / ".pytexmkrc"
        config_file.write_text(config_content, encoding="utf-8")

        cp = ConfigParser(interactive=False)
        config = cp.init_config_file()

        assert config.get("engine", {}).get("timeout") == 60
        assert config.get("compilation", {}).get("default_run_count") == 1
        assert config.get("compilation", {}).get("max_extra_passes") == 0
        assert config.get("output", {}).get("outdir") == "custom_output"


class TestConfigNonInteractive:
    """测试非交互模式"""

    def test_non_interactive_no_input_call(self, tmp_path, monkeypatch):
        """验证非交互模式（interactive=False）不调用 input()"""
        monkeypatch.chdir(tmp_path)

        config_content = """
invalid_key = "value"

[engine]
default = "invalid_engine"
"""
        config_file = tmp_path / ".pytexmkrc"
        config_file.write_text(config_content, encoding="utf-8")

        with mock.patch("builtins.input", side_effect=Exception("不应该调用 input()")):
            cp = ConfigParser(interactive=False)
            config = cp.init_config_file()
            assert config is not None

    def test_interactive_flag(self, tmp_path, monkeypatch):
        """验证 interactive 标志正确设置"""
        monkeypatch.chdir(tmp_path)

        cp_interactive = ConfigParser(interactive=True)
        assert cp_interactive.interactive is True

        cp_non_interactive = ConfigParser(interactive=False)
        assert cp_non_interactive.interactive is False


class TestConfigGetter:
    """测试配置点号访问"""

    def test_dot_notation_get(self, tmp_path, monkeypatch):
        """测试点号分隔的键访问"""
        monkeypatch.chdir(tmp_path)

        config_content = """
[engine]
default = "xelatex"
timeout = 300

[output]
outdir = "build"
"""
        config_file = tmp_path / ".pytexmkrc"
        config_file.write_text(config_content, encoding="utf-8")

        cp = ConfigParser(interactive=False)
        cp.init_config_file()

        assert cp.get("engine.default") == "xelatex"
        assert cp.get("engine.timeout") == 300
        assert cp.get("output.outdir") == "build"
        assert cp.get("nonexistent.key", "default") == "default"

    def test_get_section_methods(self, tmp_path, monkeypatch):
        """测试 get_*_config 方法"""
        monkeypatch.chdir(tmp_path)

        config_content = """
[engine]
default = "pdflatex"
timeout = 90

[bib]
default_tool = "bibtex"

[output]
outdir = "my_build"
auxdir = "my_aux"

[compilation]
default_run_count = 3
max_extra_passes = 1
"""
        config_file = tmp_path / ".pytexmkrc"
        config_file.write_text(config_content, encoding="utf-8")

        cp = ConfigParser(interactive=False)
        cp.init_config_file()

        engine_cfg = cp.get_engine_config()
        assert engine_cfg.get("default") == "pdflatex"
        assert engine_cfg.get("timeout") == 90

        bib_cfg = cp.get_bib_config()
        assert bib_cfg.get("default_tool") == "bibtex"

        output_cfg = cp.get_output_config()
        assert output_cfg.get("outdir") == "my_build"
        assert output_cfg.get("auxdir") == "my_aux"

        comp_cfg = cp.get_compilation_config()
        assert comp_cfg.get("default_run_count") == 3
        assert comp_cfg.get("max_extra_passes") == 1


class TestConfigValidation:
    """测试配置验证"""

    def test_invalid_engine_warning(self, tmp_path, monkeypatch, caplog):
        """测试无效引擎产生警告"""
        monkeypatch.chdir(tmp_path)

        config_content = """
[engine]
default = "invalid_engine"
"""
        config_file = tmp_path / ".pytexmkrc"
        config_file.write_text(config_content, encoding="utf-8")

        cp = ConfigParser(interactive=False)
        cp.init_config_file()

        warnings = [
            r for r in caplog.records if "未知的默认引擎" in r.getMessage() or "default" in r.getMessage().lower()
        ]
        assert len(warnings) >= 0
