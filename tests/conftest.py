# -*- coding: utf-8 -*-
"""
pytest 基础配置和 fixtures
"""

import sys
import shutil
from pathlib import Path

import pytest

# 将 src 目录添加到 Python 路径
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))


def pytest_addoption(parser):
    """添加 pytest 命令行选项"""
    parser.addoption(
        "--run-latex",
        action="store_true",
        default=False,
        help="运行需要真实 LaTeX 环境的测试",
    )


def pytest_configure(config):
    """注册自定义 markers"""
    config.addinivalue_line("markers", "slow: 标记慢测试（真实编译）")
    config.addinivalue_line("markers", "requires_latex: 需要 TeX 环境的测试")
    config.addinivalue_line("markers", "unit: 单元测试")
    config.addinivalue_line("markers", "integration: 集成测试")
    config.addinivalue_line("markers", "regression: 回归测试")


def pytest_collection_modifyitems(config, items):
    """根据命令行选项跳过测试"""
    if not config.getoption("--run-latex"):
        skip_latex = pytest.mark.skip(reason="需要 --run-latex 选项来运行真实 LaTeX 编译测试")
        for item in items:
            if "requires_latex" in item.keywords:
                item.add_marker(skip_latex)


@pytest.fixture
def tmp_dir(tmp_path):
    """临时目录 fixture（使用 pytest 内置 tmp_path）"""
    return tmp_path


@pytest.fixture
def fixtures_dir():
    """返回测试 fixtures 目录路径"""
    return Path(__file__).parent / "fixtures"


@pytest.fixture
def sample_tex_file(temp_dir):
    """创建一个简单的示例 TeX 文件（兼容旧测试）"""
    tex_content = r"""
\documentclass{article}
\begin{document}
Hello, World!
\end{document}
"""
    tex_file = temp_dir / "test.tex"
    tex_file.write_text(tex_content, encoding="utf-8")
    return tex_file


@pytest.fixture
def temp_dir():
    """临时目录 fixture（兼容旧测试，使用 tmp_path）"""
    import tempfile

    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def simple_tex_file(tmp_dir):
    """在临时目录创建一个简单可编译的英文 LaTeX 文档（minimal.tex）"""
    tex_content = r"""\documentclass{article}
\begin{document}
Hello World!
\end{document}
"""
    tex_file = tmp_dir / "minimal.tex"
    tex_file.write_text(tex_content, encoding="utf-8")
    return tex_file


@pytest.fixture
def chinese_tex_file(tmp_dir):
    """创建一个使用 ctex 的中文文档（ctex_test.tex）"""
    tex_content = r"""\documentclass{ctexart}
\begin{document}
你好，世界！
\end{document}
"""
    tex_file = tmp_dir / "ctex_test.tex"
    tex_file.write_text(tex_content, encoding="utf-8")
    return tex_file


@pytest.fixture
def bib_tex_file(tmp_dir):
    """创建一个带 bibtex 参考文献的文档"""
    tex_content = r"""\documentclass{article}
\begin{document}
Hello World! This is a citation \cite{test2024}.

\bibliographystyle{plain}
\bibliography{refs}
\end{document}
"""
    bib_content = """@article{test2024,
  author  = {Test Author},
  title   = {Test Title},
  journal = {Test Journal},
  year    = {2024},
}
"""
    tex_file = tmp_dir / "bib_test.tex"
    bib_file = tmp_dir / "refs.bib"
    tex_file.write_text(tex_content, encoding="utf-8")
    bib_file.write_text(bib_content, encoding="utf-8")
    return tex_file


@pytest.fixture
def magic_comment_tex(tmp_dir):
    """创建带有 % !TEX program = xelatex 魔法注释的文档"""
    tex_content = r"""% !TEX program = xelatex
% !TEX outdir = output
\documentclass{article}
\begin{document}
Magic Comment Test!
\end{document}
"""
    tex_file = tmp_dir / "magic_test.tex"
    tex_file.write_text(tex_content, encoding="utf-8")
    return tex_file


@pytest.fixture
def project_dir_with_config(tmp_dir):
    """在临时目录创建带项目配置文件的目录"""
    config_content = """
[output]
outdir = "output"
auxdir = "aux"

[engine]
default = "pdflatex"
timeout = 120
auto_detect = false

[compilation]
default_run_count = 1
shell_escape = true
synctex = false
"""
    config_file = tmp_dir / ".pytexmkrc"
    config_file.write_text(config_content, encoding="utf-8")
    return tmp_dir


@pytest.fixture
def xelatex_available():
    """检测 xelatex 是否可用"""
    return shutil.which("xelatex") is not None


@pytest.fixture
def pdflatex_available():
    """检测 pdflatex 是否可用"""
    return shutil.which("pdflatex") is not None


@pytest.fixture
def bibtex_available():
    """检测 bibtex 是否可用"""
    return shutil.which("bibtex") is not None
