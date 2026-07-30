import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from pytexmk.pytexlogs import (
    AsymptoteParser,
    MintedParser,
    PythontexParser,
)


def test_pythontex_parser():
    stderr_text = """\
This is pythontex version 0.18
Warning (pythontex): old format file found, regenerating
Traceback (most recent call last):
  File "test.py", line 5, in <module>
    print(1/0)
ZeroDivisionError: division by zero
PythonTeX: processed 42 code blocks
"""
    parser = PythontexParser(root_file="main.tex")
    result = parser.parse(stderr_text)

    assert result.tool_name == "pythontex"
    assert result.category == "code"
    assert result.importance == "high"
    assert result.stats["code_blocks_processed"] == 42
    assert result.stats["py_errors"] == 1
    assert len(result.errors) == 1
    assert "ZeroDivisionError" in result.errors[0].text
    assert len(result.warnings) == 1
    assert "old format file found" in result.warnings[0].text
    print("PythontexParser 自检通过 ✓")


def test_minted_parser():
    stderr_text = """\
Package minted Warning: old style environment used on input line 10
Package minted Warning: undefined color, using black instead
Error: no lexer for name 'fakelanguage'
"""
    parser = MintedParser(root_file="main.tex")
    result = parser.parse(stderr_text)

    assert result.tool_name == "minted"
    assert result.category == "code"
    assert result.importance == "medium"
    assert result.stats["code_highlighted"] == 0
    assert len(result.warnings) == 2
    assert "old style environment" in result.warnings[0].text
    assert "undefined color" in result.warnings[1].text
    assert len(result.errors) == 1
    assert "fakelanguage" in result.errors[0].text
    assert "Pygments" in result.errors[0].text
    print("MintedParser 自检通过 ✓")


def test_asymptote_parser():
    stderr_text = """\
Loading config.asy
Loading graph.asy
WARNING: Obsolete command used
Output written on figure1.pdf
Output written on figure2.eps
Error: could not load module 'nonexistent'
"""
    parser = AsymptoteParser(root_file="main.tex")
    result = parser.parse(stderr_text)

    assert result.tool_name == "asymptote"
    assert result.category == "graphics"
    assert result.importance == "medium"
    assert result.stats["figures_processed"] == 2
    assert result.stats["loading_asy_files"] == ["config.asy", "graph.asy"]
    assert len(result.errors) == 1
    assert "could not load module" in result.errors[0].text
    assert len(result.warnings) == 1
    assert "Obsolete command" in result.warnings[0].text
    infos = [e for e in result.entries if e.level.value == "info"]
    assert len(infos) == 2
    print("AsymptoteParser 自检通过 ✓")


if __name__ == "__main__":
    test_pythontex_parser()
    test_minted_parser()
    test_asymptote_parser()
    print("\n全部日志解析器自检通过！")
