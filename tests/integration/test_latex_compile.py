# -*- coding: utf-8 -*-
"""
真实 LaTeX 编译测试（标记为 requires_latex 和 slow，默认跳过）
"""

import os
import sys
import shutil
import subprocess
from pathlib import Path

import pytest


COMPILE_TIMEOUT = 120
PROJECT_ROOT = Path(__file__).parent.parent.parent


def is_tool_available(name: str) -> bool:
    """检测工具是否在 PATH 中可用"""
    return shutil.which(name) is not None


def run_pytexmk(args, cwd, timeout=COMPILE_TIMEOUT):
    """运行 pytexmk 命令进行编译"""
    cmd = [sys.executable, "-m", "pytexmk", "--non-interactive"] + args
    env = os.environ.copy()
    env["PYTHONPATH"] = str(PROJECT_ROOT / "src") + os.pathsep + env.get("PYTHONPATH", "")
    return subprocess.run(
        cmd,
        cwd=str(cwd),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=timeout,
        env=env,
    )


pytestmark = [pytest.mark.slow, pytest.mark.requires_latex]


class TestMinimalCompilation:
    """测试 minimal.tex 编译"""

    @pytest.mark.skipif(not is_tool_available("xelatex"), reason="xelatex 不在 PATH 中")
    def test_minimal_xelatex(self, simple_tex_file, tmp_path, monkeypatch):
        """测试 minimal.tex 能被 XeLaTeX 成功编译"""
        monkeypatch.chdir(tmp_path)
        result = run_pytexmk(
            ["--engine", "xelatex", "--outdir", "output", "-n", "1", "minimal"],
            cwd=tmp_path,
        )

        pdf_file = tmp_path / "output" / "minimal.pdf"
        assert pdf_file.exists(), f"PDF 未生成: stdout={result.stdout}, stderr={result.stderr}"
        assert pdf_file.stat().st_size > 0

    @pytest.mark.skipif(not is_tool_available("pdflatex"), reason="pdflatex 不在 PATH 中")
    def test_minimal_pdflatex(self, simple_tex_file, tmp_path, monkeypatch):
        """测试 minimal.tex 能被 PdfLaTeX 成功编译"""
        monkeypatch.chdir(tmp_path)
        result = run_pytexmk(
            ["--engine", "pdflatex", "--outdir", "output", "-n", "1", "minimal"],
            cwd=tmp_path,
        )

        pdf_file = tmp_path / "output" / "minimal.pdf"
        assert pdf_file.exists(), f"PDF 未生成: stdout={result.stdout}, stderr={result.stderr}"
        assert pdf_file.stat().st_size > 0


class TestChineseCompilation:
    """测试中文 ctex 文档编译"""

    @pytest.mark.skipif(not is_tool_available("xelatex"), reason="xelatex 不在 PATH 中")
    def test_chinese_ctex_xelatex(self, chinese_tex_file, tmp_path, monkeypatch):
        """测试中文 ctex 文档能被 XeLaTeX 编译"""
        monkeypatch.chdir(tmp_path)
        result = run_pytexmk(
            ["--engine", "xelatex", "--outdir", "output", "-n", "1", "ctex_test"],
            cwd=tmp_path,
        )

        pdf_file = tmp_path / "output" / "ctex_test.pdf"
        assert pdf_file.exists(), f"PDF 未生成: stdout={result.stdout}, stderr={result.stderr}"
        assert pdf_file.stat().st_size > 0


class TestBibtexCompilation:
    """测试 bibtex 参考文献文档"""

    @pytest.mark.skipif(
        not (is_tool_available("xelatex") and is_tool_available("bibtex")), reason="xelatex 或 bibtex 不在 PATH 中"
    )
    def test_bibtex_document(self, bib_tex_file, tmp_path, monkeypatch):
        """测试 bibtex 参考文献文档编译"""
        monkeypatch.chdir(tmp_path)
        result = run_pytexmk(
            ["--engine", "xelatex", "--outdir", "output", "-n", "3", "bib_test"],
            cwd=tmp_path,
            timeout=180,
        )

        pdf_file = tmp_path / "output" / "bib_test.pdf"
        assert pdf_file.exists(), f"PDF 未生成: stdout={result.stdout}, stderr={result.stderr}"
        assert pdf_file.stat().st_size > 0


class TestOutputDirectory:
    """测试编译后 PDF 文件存在于 outdir"""

    @pytest.mark.skipif(not is_tool_available("xelatex"), reason="xelatex 不在 PATH 中")
    def test_pdf_in_output_directory(self, simple_tex_file, tmp_path, monkeypatch):
        """测试编译后 PDF 文件存在于指定 outdir"""
        monkeypatch.chdir(tmp_path)
        outdir = "my_output"
        result = run_pytexmk(
            ["--engine", "xelatex", "--outdir", outdir, "-n", "1", "minimal"],
            cwd=tmp_path,
        )

        pdf_file = tmp_path / outdir / "minimal.pdf"
        assert pdf_file.exists(), f"PDF 未在指定输出目录生成: stdout={result.stdout}, stderr={result.stderr}"


class TestLogAnalysis:
    """测试日志解析无致命错误"""

    @pytest.mark.skipif(not is_tool_available("xelatex"), reason="xelatex 不在 PATH 中")
    def test_log_no_fatal_errors(self, simple_tex_file, tmp_path, monkeypatch):
        """测试成功编译的日志无致命错误"""
        monkeypatch.chdir(tmp_path)
        run_pytexmk(
            ["--engine", "xelatex", "--outdir", "output", "-n", "1", "minimal"],
            cwd=tmp_path,
        )

        log_file = tmp_path / "minimal.log"
        if not log_file.exists():
            log_file = tmp_path / "output" / "minimal.log"

        if log_file.exists():
            log_content = log_file.read_text(encoding="utf-8", errors="replace")
            assert "Fatal error" not in log_content
            assert "Emergency stop" not in log_content
