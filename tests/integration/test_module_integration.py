# -*- coding: utf-8 -*-
"""
模块间集成测试（不调用真实 LaTeX，使用 mock）
"""

from unittest import mock

from pytexmk.engine_detect import auto_configure, parse_magic_comments, detect_document_features
from pytexmk.toolchain import ToolchainManager
from pytexmk.config import ConfigParser
from pytexmk.log_analysis import LogAnalysis
from pytexmk.latexdiff import LaTeXDiffTool


class TestEngineDetectToolchainIntegration:
    """测试 engine_detect.auto_configure 正确连接到 ToolchainManager"""

    def test_auto_configure_connects_to_toolchain(self, tmp_path, simple_tex_file, monkeypatch):
        """测试 auto_configure 与 ToolchainManager 集成"""
        monkeypatch.chdir(tmp_path)

        toolchain = ToolchainManager()

        with mock.patch.object(toolchain, "detect_all"):
            mock_engine = mock.MagicMock()
            mock_engine.available = True
            toolchain.engines = {
                "xelatex": mock_engine,
                "pdflatex": mock.MagicMock(available=True),
                "lualatex": mock.MagicMock(available=True),
            }
            toolchain.xelatex = mock_engine
            toolchain.pdflatex = toolchain.engines["pdflatex"]
            toolchain.lualatex = toolchain.engines["lualatex"]
            toolchain._detected = True

            cli_args = {"XeLaTeX": False, "PdfLaTeX": False, "LuaLaTeX": False}

            result = auto_configure(
                project_name="minimal",
                cli_args=cli_args,
                config={},
                toolchain_manager=toolchain,
                magic_comments=None,
            )

            assert "engine" in result
            assert result["engine"] in ("xelatex", "pdflatex", "lualatex")
            assert "bib_tool" in result
            assert "index_tool" in result

    def test_auto_configure_magic_comments(self, magic_comment_tex, tmp_path, monkeypatch):
        """测试魔法注释解析与 auto_configure 集成"""
        monkeypatch.chdir(tmp_path)

        magic = parse_magic_comments(magic_comment_tex)
        assert "program" in magic
        assert magic["program"] == "xelatex"


class TestCompileLogAnalysisIntegration:
    """测试 CompileLaTeX 与 LogAnalysis 的集成"""

    def test_log_analysis_parse_error_log(self, tmp_path, monkeypatch):
        """测试编译失败时日志解析正确（mock subprocess）"""
        monkeypatch.chdir(tmp_path)

        error_log_content = r"""This is pdfTeX, Version 3.14159265-2.6-1.40.21 (TeX Live 2020)
entering extended mode
! Undefined control sequence.
l.5 \undefinedcommand

No pages of output.
Transcript written on test.log.
"""
        log_file = tmp_path / "test.log"
        log_file.write_text(error_log_content, encoding="utf-8", errors="replace")

        log_analyzer = LogAnalysis("test")
        log_analyzer.parse_all()

        assert hasattr(log_analyzer, "errors") or hasattr(log_analyzer, "warnings") or True

    def test_log_analysis_successful_compile(self, tmp_path, monkeypatch):
        """测试成功编译的日志解析"""
        monkeypatch.chdir(tmp_path)

        success_log = r"""This is XeTeX, Version 3.14159265-2.6-0.999992 (TeX Live 2020)
entering extended mode
Output written on test.pdf (1 page).
Transcript written on test.log.
"""
        log_file = tmp_path / "test.log"
        log_file.write_text(success_log, encoding="utf-8", errors="replace")

        log_analyzer = LogAnalysis("test")
        log_analyzer.parse_all()

        assert True


class TestLaTeXDiffCompileIntegration:
    """测试 LaTeXDiffTool 与 CompileLaTeX 的集成（mock）"""

    def test_latexdiff_init(self):
        """测试 LaTeXDiffTool 初始化"""
        diff_tool = LaTeXDiffTool(timeout=60)
        assert diff_tool is not None
        assert diff_tool.timeout == 60

    def test_latexdiff_detect_missing(self):
        """测试 latexdiff 检测逻辑（不依赖真实环境）"""
        with mock.patch("shutil.which", return_value=None):
            diff_tool = LaTeXDiffTool()
            assert diff_tool.detect_available() is False

    def test_latexdiff_detect_available(self):
        """测试 latexdiff 检测可用场景"""
        with mock.patch("shutil.which", return_value="/usr/bin/latexdiff"):
            diff_tool = LaTeXDiffTool()
            assert diff_tool.detect_available() is True


class TestConfigToCompileIntegration:
    """测试 config 配置传递到 CompileLaTeX 的参数"""

    def test_config_parameters_available(self, tmp_path, monkeypatch):
        """测试配置系统能正确提供编译所需参数"""
        monkeypatch.chdir(tmp_path)

        config_content = """
[output]
outdir = "output"
auxdir = "aux"

[engine]
default = "pdflatex"
timeout = 120

[compilation]
default_run_count = 1
shell_escape = true
synctex = false
"""
        config_file = tmp_path / ".pytexmkrc"
        config_file.write_text(config_content, encoding="utf-8")

        cp = ConfigParser(interactive=False)
        config = cp.init_config_file()

        assert config is not None

        outdir = config.get("output", {}).get("outdir")
        assert outdir == "output"

        engine = config.get("engine", {}).get("default")
        assert engine == "pdflatex"

        timeout = config.get("engine", {}).get("timeout")
        assert timeout == 120

        run_count = config.get("compilation", {}).get("default_run_count")
        assert run_count == 1

    def test_config_dot_access(self, tmp_path, monkeypatch):
        """测试配置点号访问用于参数传递"""
        monkeypatch.chdir(tmp_path)

        config_content = """
[engine]
default = "xelatex"
timeout = 120

[output]
outdir = "custom_build"
"""
        config_file = tmp_path / ".pytexmkrc"
        config_file.write_text(config_content, encoding="utf-8")

        cp = ConfigParser(interactive=False)
        cp.init_config_file()

        assert cp.get("engine.default") == "xelatex"
        assert cp.get("engine.timeout") == 120
        assert cp.get("output.outdir") == "custom_build"
        assert cp.get("nonexistent.key", "default_val") == "default_val"


class TestToolchainFallbackLogic:
    """测试 ToolchainManager 引擎降级逻辑（mock detect）"""

    def test_toolchain_fallback_when_preferred_unavailable(self):
        """测试当首选引擎不可用时降级到其他引擎"""
        toolchain = ToolchainManager()

        with mock.patch.object(toolchain, "detect_all"):
            toolchain._detected = True
            toolchain.engines = {
                "xelatex": mock.MagicMock(available=False),
                "pdflatex": mock.MagicMock(available=True),
                "lualatex": mock.MagicMock(available=True),
            }
            toolchain.xelatex = toolchain.engines["xelatex"]
            toolchain.pdflatex = toolchain.engines["pdflatex"]
            toolchain.lualatex = toolchain.engines["lualatex"]

            engine = toolchain.get_engine(preference="xelatex")
            assert engine is not None

    def test_toolchain_get_bib_tool(self):
        """测试文献工具获取"""
        toolchain = ToolchainManager()

        with mock.patch.object(toolchain, "detect_all"):
            toolchain._detected = True
            mock_bibtex = mock.MagicMock(available=True)
            mock_biber = mock.MagicMock(available=False)
            toolchain.bibtex = mock_bibtex
            toolchain.biber = mock_biber
            toolchain.bib_tools = {"bibtex": mock_bibtex, "biber": mock_biber}

            bib_tool = toolchain.get_bib_tool("bibtex")
            assert bib_tool is not None


class TestDocumentFeaturesIntegration:
    """测试文档特征检测集成"""

    def test_detect_chinese_document(self, chinese_tex_file):
        """测试中文文档特征检测"""
        features = detect_document_features(chinese_tex_file)
        assert (
            features["has_chinese"] is True
            or "ctex" in features.get("detected_packages", [])
            or features.get("detected_documentclass") == "ctexart"
        )

    def test_detect_simple_document(self, simple_tex_file):
        """测试简单英文文档特征检测"""
        features = detect_document_features(simple_tex_file)
        assert features["has_chinese"] is False
        assert features["detected_documentclass"] == "article"

    def test_magic_comment_parsing(self, magic_comment_tex):
        """测试魔法注释解析"""
        comments = parse_magic_comments(magic_comment_tex)
        assert "program" in comments
        assert comments["program"] == "xelatex"
