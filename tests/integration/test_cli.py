# -*- coding: utf-8 -*-
"""
CLI 集成测试：使用 subprocess 运行 pytexmk 命令
"""

import os
import sys
import subprocess
from pathlib import Path


PROJECT_ROOT = Path(__file__).parent.parent.parent
CLI_TIMEOUT = 30


def run_cli(args, cwd=None, timeout=CLI_TIMEOUT):
    """
    运行 pytexmk CLI 命令的辅助函数

    参数:
        args: 命令行参数列表
        cwd: 工作目录
        timeout: 超时时间（秒）

    返回:
        subprocess.CompletedProcess 对象
    """
    cmd = [sys.executable, "-m", "pytexmk"] + args
    env = os.environ.copy()
    env["PYTHONPATH"] = str(PROJECT_ROOT / "src") + os.pathsep + env.get("PYTHONPATH", "")
    return subprocess.run(
        cmd,
        cwd=str(cwd) if cwd else None,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=timeout,
        env=env,
    )


class TestCLIVersionHelp:
    """测试版本号和帮助信息"""

    def test_version_output(self):
        """测试 python -m pytexmk --version 返回正确版本号，退出码 0"""
        from pytexmk.version import script_name, __version__

        result = run_cli(["--version"])
        assert result.returncode == 0
        assert script_name in result.stdout or script_name in result.stderr
        assert __version__ in result.stdout or __version__ in result.stderr

    def test_help_output(self):
        """测试 python -m pytexmk --help 返回帮助信息，退出码 0，包含 PyTeXMK 字样"""
        result = run_cli(["--help"])
        assert result.returncode == 0
        assert "PyTeXMK" in result.stdout

    def test_help_short_flag(self):
        """测试 -h 参数与 --help 效果一致"""
        result = run_cli(["-h"])
        assert result.returncode == 0
        assert "PyTeXMK" in result.stdout

    def test_help_contains_new_parameters(self):
        """测试帮助信息包含新参数说明（--pvc, --engine, --xindy 等）"""
        result = run_cli(["--help"])
        help_text = result.stdout

        assert "--pvc" in help_text or "--continuous" in help_text
        assert "--engine" in help_text
        assert "-x" in help_text or "--XeLaTeX" in help_text
        assert "-p" in help_text or "--PdfLaTeX" in help_text
        assert "-l" in help_text or "--LuaLaTeX" in help_text
        assert "--bib" in help_text
        assert "--index" in help_text
        assert "--timeout" in help_text
        assert "--non-interactive" in help_text


class TestCLIErrorHandling:
    """测试错误处理"""

    def test_empty_directory_no_crash(self, tmp_dir):
        """测试在空目录（无 tex 文件）给出正确错误提示，不崩溃"""
        result = run_cli([], cwd=tmp_dir)
        combined_output = result.stdout + result.stderr
        assert (
            result.returncode == 0
            or "No .tex files found" in combined_output
            or "未找到" in combined_output
            or "错误" in combined_output
        )

    def test_nonexistent_file_error(self, tmp_dir):
        """测试 python -m pytexmk non_existent_file.tex 给出友好错误信息"""
        result = run_cli(["non_existent_file.tex"], cwd=tmp_dir)
        combined_output = result.stdout + result.stderr
        assert (
            "non_existent" in combined_output
            or "找不到" in combined_output
            or "错误" in combined_output
            or result.returncode != 0
        )

    def test_invalid_engine_argument(self, tmp_dir):
        """测试 --engine invalid_engine 通过 argparse 验证参数选择"""
        result = run_cli(["--engine", "invalid_engine"], cwd=tmp_dir)
        assert result.returncode != 0
        assert (
            "invalid" in (result.stderr or "").lower()
            or "invalid" in (result.stdout or "").lower()
            or "choice" in (result.stderr or "").lower()
        )


class TestCLIEngineFlags:
    """测试引擎参数识别"""

    def test_pdflatex_flag_in_help(self):
        """测试 -p/--PdfLaTeX 参数在帮助信息中存在"""
        result = run_cli(["--help"])
        assert "-p" in result.stdout or "--PdfLaTeX" in result.stdout or "PdfLaTeX" in result.stdout

    def test_xelatex_flag_in_help(self):
        """测试 -x/--XeLaTeX 参数在帮助信息中存在"""
        result = run_cli(["--help"])
        assert "-x" in result.stdout or "--XeLaTeX" in result.stdout or "XeLaTeX" in result.stdout

    def test_lualatex_flag_in_help(self):
        """测试 -l/--LuaLaTeX 参数在帮助信息中存在"""
        result = run_cli(["--help"])
        assert "-l" in result.stdout or "--LuaLaTeX" in result.stdout or "LuaLaTeX" in result.stdout


class TestCLINonInteractive:
    """测试非交互模式"""

    def test_non_interactive_flag_in_help(self):
        """测试 --non-interactive 参数在帮助信息中存在"""
        result = run_cli(["--help"])
        assert "--non-interactive" in result.stdout
