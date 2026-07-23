# -*- coding: utf-8 -*-
"""Toolchain 工具链模块单元测试"""

from unittest.mock import MagicMock

import pytest

from pytexmk.exceptions import ToolchainNotFoundError
from pytexmk.toolchain import (
    detect_tool_available,
    ToolchainBase,
    PdfLaTeXEngine,
    XeLaTeXEngine,
    LuaLaTeXEngine,
    BibTeXTool,
    BiberTool,
    MakeindexTool,
    XindyTool,
    DvipdfmxTool,
    ToolchainManager,
)


class TestDetectToolAvailable:
    """detect_tool_available 函数测试"""

    def test_detect_tool_not_found(self, mocker):
        """测试工具不存在时返回 False"""
        mocker.patch("shutil.which", return_value=None)
        available, version = detect_tool_available("nonexistent_tool")
        assert available is False
        assert version is None

    def test_detect_tool_found_with_version(self, mocker):
        """测试工具存在且能获取版本"""
        mocker.patch("shutil.which", return_value="/usr/bin/xelatex")
        mock_run = mocker.patch("subprocess.run")
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="XeTeX 3.14159265-2.6-0.999996 (TeX Live 2025)\n",
            stderr="",
        )
        available, version = detect_tool_available("xelatex")
        assert available is True
        assert "XeTeX" in version

    def test_detect_tool_found_no_version_output(self, mocker):
        """测试工具存在但 --version 无输出"""
        mocker.patch("shutil.which", return_value="/usr/bin/sometool")
        mock_run = mocker.patch("subprocess.run")
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="",
            stderr="",
        )
        available, version = detect_tool_available("sometool")
        assert available is True
        assert version is None

    def test_detect_tool_custom_path(self, mocker):
        """测试使用自定义路径"""
        mock_run = mocker.patch("subprocess.run")
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="pdfTeX 3.141592653\n",
            stderr="",
        )
        available, version = detect_tool_available("pdflatex", custom_path="/custom/path/pdflatex")
        assert available is True
        mock_run.assert_called_once()
        cmd = mock_run.call_args[0][0]
        assert cmd[0] == "/custom/path/pdflatex"

    def test_detect_tool_timeout(self, mocker):
        """测试 --version 超时时仍然认为工具可用"""
        import subprocess

        mocker.patch("shutil.which", return_value="/usr/bin/slowtool")
        mock_run = mocker.patch("subprocess.run")
        mock_run.side_effect = subprocess.TimeoutExpired(cmd="slowtool", timeout=10)
        available, version = detect_tool_available("slowtool")
        assert available is True
        assert version is None


class TestPdfLaTeXEngine:
    """PdfLaTeXEngine 测试"""

    def test_build_command_default(self):
        """测试默认参数构建命令"""
        engine = PdfLaTeXEngine()
        cmd = engine.build_command(project_name="test")
        assert cmd[0] == "pdflatex"
        assert "-shell-escape" in cmd
        assert "-file-line-error" in cmd
        assert "-halt-on-error" in cmd
        assert "-interaction=batchmode" in cmd
        assert "-synctex=1" in cmd
        assert cmd[-1] == "test.tex"
        assert "-no-pdf" not in cmd

    def test_build_command_non_quiet(self):
        """测试非静默模式"""
        engine = PdfLaTeXEngine()
        cmd = engine.build_command(project_name="test", non_quiet=True)
        assert "-interaction=nonstopmode" in cmd
        assert "-interaction=batchmode" not in cmd

    def test_build_command_with_outdir(self):
        """测试输出目录参数"""
        engine = PdfLaTeXEngine()
        cmd = engine.build_command(project_name="test", outdir="build")
        assert "-output-directory=build" in cmd

    def test_build_command_no_synctex(self):
        """测试禁用 synctex"""
        engine = PdfLaTeXEngine()
        cmd = engine.build_command(project_name="test", synctex=False)
        assert "-synctex=1" not in cmd

    def test_build_command_extra_args(self):
        """测试额外参数"""
        engine = PdfLaTeXEngine()
        cmd = engine.build_command(project_name="test", extra_args=["-draftmode"])
        assert "-draftmode" in cmd


class TestXeLaTeXEngine:
    """XeLaTeXEngine 测试"""

    def test_build_command_default_no_pdf(self):
        """测试默认带 -no-pdf"""
        engine = XeLaTeXEngine()
        cmd = engine.build_command(project_name="test")
        assert cmd[0] == "xelatex"
        assert "-no-pdf" in cmd
        assert cmd[-1] == "test.tex"

    def test_build_command_no_pdf_false(self):
        """测试 no_pdf=False 时不添加 -no-pdf"""
        engine = XeLaTeXEngine()
        cmd = engine.build_command(project_name="test", no_pdf=False)
        assert "-no-pdf" not in cmd

    def test_build_command_parameter_order(self):
        """测试参数顺序与原代码一致"""
        engine = XeLaTeXEngine()
        cmd = engine.build_command(project_name="test")
        idx_interaction = cmd.index("-interaction=batchmode")
        idx_synctex = cmd.index("-synctex=1")
        idx_nopdf = cmd.index("-no-pdf")
        idx_tex = cmd.index("test.tex")
        assert idx_interaction < idx_synctex
        assert idx_synctex < idx_nopdf
        assert idx_nopdf < idx_tex


class TestLuaLaTeXEngine:
    """LuaLaTeXEngine 测试"""

    def test_build_command_default(self):
        """测试默认参数"""
        engine = LuaLaTeXEngine()
        cmd = engine.build_command(project_name="test")
        assert cmd[0] == "lualatex"
        assert "-shell-escape" in cmd
        assert "-interaction=batchmode" in cmd
        assert "-no-pdf" not in cmd
        assert cmd[-1] == "test.tex"


class TestBibTools:
    """BibTeX 和 Biber 工具测试"""

    def test_bibtex_build_command(self):
        """测试 BibTeX 命令构建"""
        tool = BibTeXTool()
        cmd = tool.build_command(project_name="test")
        assert cmd == ["bibtex", "test"]

    def test_biber_build_command_quiet(self):
        """测试 Biber 静默模式"""
        tool = BiberTool()
        cmd = tool.build_command(project_name="test", quiet=True)
        assert "--quiet" in cmd
        assert "test" in cmd

    def test_biber_build_command_with_outdir(self):
        """测试 Biber 输出目录"""
        tool = BiberTool()
        cmd = tool.build_command(project_name="test", outdir="build", quiet=False)
        assert "--output-directory=build" in cmd
        assert "--quiet" not in cmd


class TestIndexTools:
    """Makeindex 和 Xindy 工具测试"""

    def test_makeindex_default(self):
        """测试 Makeindex 默认命令"""
        tool = MakeindexTool()
        cmd = tool.build_command(project_name="test")
        assert cmd == ["makeindex", "test.idx"]

    def test_makeindex_nomencl(self):
        """测试 nomencl 格式的 makeindex 命令"""
        tool = MakeindexTool()
        cmd = tool.build_command(
            project_name="test",
            style_file="nomencl.ist",
            out_ext="nls",
            in_ext="nlo",
        )
        assert "-s" in cmd
        assert "nomencl.ist" in cmd
        assert "-o" in cmd
        assert "test.nls" in cmd
        assert "test.nlo" in cmd

    def test_makeindex_glossaries(self):
        """测试 glossaries 格式的 makeindex 命令"""
        tool = MakeindexTool()
        cmd = tool.build_command(
            project_name="test",
            style_file="test.ist",
            out_ext="gls",
            in_ext="glo",
        )
        assert "test.ist" in cmd
        assert "test.gls" in cmd
        assert "test.glo" in cmd

    def test_xindy_default(self):
        """测试 Xindy 默认命令"""
        tool = XindyTool()
        cmd = tool.build_command(project_name="test")
        assert "xindy" in cmd[0]
        assert "-L" in cmd
        assert "general" in cmd
        assert "-C" in cmd
        assert "utf8" in cmd
        assert "-o" in cmd
        assert "test.ind" in cmd
        assert "test.idx" in cmd

    def test_xindy_nomencl(self):
        """测试 nomencl 格式的 xindy 命令"""
        tool = XindyTool()
        cmd = tool.build_command(
            project_name="test",
            module="nomencl",
            out_ext="nls",
            in_ext="nlo",
        )
        assert "-M" in cmd
        assert "nomencl" in cmd
        assert "test.nls" in cmd
        assert "test.nlo" in cmd

    def test_xindy_quiet(self):
        """测试 Xindy 静默模式"""
        tool = XindyTool()
        cmd = tool.build_command(project_name="test", quiet=True)
        assert "-q" in cmd

    def test_xindy_log_file(self):
        """测试 Xindy 日志文件"""
        tool = XindyTool()
        cmd = tool.build_command(project_name="test", log_file="test.ilg")
        assert "-t" in cmd
        assert "test.ilg" in cmd


class TestDvipdfmxTool:
    """DvipdfmxTool 测试"""

    def test_build_command_default(self):
        """测试默认 DVIPDFMX 命令"""
        tool = DvipdfmxTool()
        cmd = tool.build_command(project_name="test")
        assert cmd == ["dvipdfmx", "-V", "2.0", "test"]

    def test_build_command_quiet(self):
        """测试静默模式"""
        tool = DvipdfmxTool()
        cmd = tool.build_command(project_name="test", quiet=True)
        assert "-q" in cmd
        assert "-V" in cmd
        idx_q = cmd.index("-q")
        idx_V = cmd.index("-V")
        assert idx_q < idx_V

    def test_build_command_custom_version(self):
        """测试自定义 PDF 版本"""
        tool = DvipdfmxTool()
        cmd = tool.build_command(project_name="test", version="1.7")
        assert "1.7" in cmd


class TestToolchainManager:
    """ToolchainManager 测试"""

    def test_init_creates_all_tools(self):
        """测试初始化时创建所有工具实例"""
        mgr = ToolchainManager()
        assert "pdflatex" in mgr.engines
        assert "xelatex" in mgr.engines
        assert "lualatex" in mgr.engines
        assert "bibtex" in mgr.bib_tools
        assert "biber" in mgr.bib_tools
        assert "makeindex" in mgr.index_tools
        assert "xindy" in mgr.index_tools
        assert isinstance(mgr.dvipdfmx, DvipdfmxTool)

    def test_detect_all(self, mocker):
        """测试 detect_all 返回正确的可用性字典"""
        mocker.patch("shutil.which", return_value="/usr/bin/fake")
        mock_run = mocker.patch("subprocess.run")
        mock_run.return_value = MagicMock(returncode=0, stdout="Fake version 1.0\n", stderr="")

        mgr = ToolchainManager()
        result = mgr.detect_all()
        assert isinstance(result, dict)
        assert "pdflatex" in result
        assert "xelatex" in result
        assert "dvipdfmx" in result
        assert mgr._detected is True

    def test_get_engine_preference_available(self):
        """测试首选引擎可用时直接返回"""
        mgr = ToolchainManager()
        mgr.engines["xelatex"].available = True
        mgr.engines["lualatex"].available = False
        mgr.engines["pdflatex"].available = False
        mgr._detected = True

        engine = mgr.get_engine(preference="xelatex", auto_detect=False)
        assert isinstance(engine, XeLaTeXEngine)

    def test_get_engine_fallback_order(self):
        """测试引擎降级顺序 xelatex -> lualatex -> pdflatex"""
        mgr = ToolchainManager()
        mgr.engines["xelatex"].available = False
        mgr.engines["lualatex"].available = True
        mgr.engines["pdflatex"].available = True
        mgr._detected = True

        engine = mgr.get_engine(preference="xelatex", auto_detect=False)
        assert isinstance(engine, LuaLaTeXEngine)

    def test_get_engine_all_unavailable_raises(self):
        """测试所有引擎不可用时抛出异常"""
        mgr = ToolchainManager()
        mgr.engines["xelatex"].available = False
        mgr.engines["lualatex"].available = False
        mgr.engines["pdflatex"].available = False
        mgr._detected = True

        with pytest.raises(ToolchainNotFoundError):
            mgr.get_engine(preference="xelatex", auto_detect=False)

    def test_get_engine_default_priority(self):
        """测试默认优先级顺序：xelatex 优先"""
        mgr = ToolchainManager()
        mgr.engines["xelatex"].available = True
        mgr.engines["lualatex"].available = True
        mgr.engines["pdflatex"].available = True
        mgr._detected = True

        engine = mgr.get_engine(auto_detect=False)
        assert isinstance(engine, XeLaTeXEngine)

    def test_get_index_tool_xindy_available(self):
        """测试请求 xindy 且可用时返回 xindy"""
        mgr = ToolchainManager()
        mgr.index_tools["makeindex"].available = True
        mgr.index_tools["xindy"].available = True
        mgr._detected = True

        tool = mgr.get_index_tool(index_engine="xindy")
        assert isinstance(tool, XindyTool)

    def test_get_index_tool_xindy_fallback(self):
        """测试 xindy 不可用时回退到 makeindex"""
        mgr = ToolchainManager()
        mgr.index_tools["makeindex"].available = True
        mgr.index_tools["xindy"].available = False
        mgr._detected = True

        tool = mgr.get_index_tool(index_engine="xindy")
        assert isinstance(tool, MakeindexTool)

    def test_get_bib_tool_exists(self):
        """测试获取已存在的 bib 工具"""
        mgr = ToolchainManager()
        mgr.bib_tools["bibtex"].available = True
        mgr._detected = True

        tool = mgr.get_bib_tool("bibtex")
        assert isinstance(tool, BibTeXTool)

    def test_get_bib_tool_invalid_raises(self):
        """测试获取不存在的 bib 工具抛出异常"""
        mgr = ToolchainManager()
        mgr._detected = True

        with pytest.raises(ToolchainNotFoundError):
            mgr.get_bib_tool("nonexistent")

    def test_select_bib_tool_biber(self):
        """测试 aux 内容包含 biber 特征时选择 biber"""
        mgr = ToolchainManager()
        mgr.bib_tools["biber"].available = True
        mgr.bib_tools["bibtex"].available = True
        mgr._detected = True

        aux_content = r"\abx@aux@refcontext{nty/global//global/global}"
        tool, bib_file = mgr.select_bib_tool(aux_content)
        assert isinstance(tool, BiberTool)

    def test_select_bib_tool_bibtex(self):
        """测试 aux 内容包含 bibtex 特征时选择 bibtex"""
        mgr = ToolchainManager()
        mgr.bib_tools["biber"].available = False
        mgr.bib_tools["bibtex"].available = True
        mgr._detected = True

        aux_content = r"\bibdata{refs}"
        tool, bib_file = mgr.select_bib_tool(aux_content)
        assert isinstance(tool, BibTeXTool)
        assert bib_file == "refs"

    def test_select_bib_tool_none(self):
        """测试不包含参考文献特征时返回 None"""
        mgr = ToolchainManager()
        mgr._detected = True

        aux_content = r"\relax"
        tool, bib_file = mgr.select_bib_tool(aux_content)
        assert tool is None
        assert bib_file is None

    def test_select_index_tools_makeidx(self):
        """测试检测 makeidx 索引"""
        mgr = ToolchainManager()
        mgr.index_tools["makeindex"].available = True
        mgr.index_tools["xindy"].available = False
        mgr._detected = True

        aux_content = r"\makeindex"
        tools = mgr.select_index_tools(aux_content, "test")
        assert len(tools) >= 1
        tool, params = tools[-1]
        assert isinstance(tool, MakeindexTool)
        assert params["project_name"] == "test"

    def test_custom_path_config(self, mocker):
        """测试自定义路径配置"""
        config = {"xelatex_path": "/custom/xelatex"}
        mock_detect = mocker.patch.object(ToolchainBase, "detect", return_value=True)
        mgr = ToolchainManager(config=config)
        mgr.detect_all()
        assert mock_detect.called
