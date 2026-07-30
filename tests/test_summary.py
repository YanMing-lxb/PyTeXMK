import sys
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from pytexmk.pytexlogs import (
    CATEGORY_LABEL,
    CATEGORY_ORDER,
    IMPORTANCE_LABEL,
    LogEntry,
    LogLevel,
    ParsedLog,
    print_summary,
)


def build_test_logs() -> list[ParsedLog]:
    bib_plog = ParsedLog(
        category="bibliography",
        tool_name="bibtex",
        importance="high",
        entries=[
            LogEntry(
                level=LogLevel.ERROR,
                file="main.bib",
                line=15,
                text="Undefined reference 'Author2024'",
            ),
            LogEntry(
                level=LogLevel.WARNING,
                file="main.bib",
                line=22,
                text="Missing journal field",
            ),
            LogEntry(
                level=LogLevel.WARNING,
                file="refs.bib",
                line=8,
                text="Duplicate key 'Smith2023'",
            ),
        ],
    )

    idx_plog = ParsedLog(
        category="index",
        tool_name="makeindex",
        importance="medium",
        entries=[
            LogEntry(
                level=LogLevel.WARNING,
                file="main.idx",
                line=100,
                text="Unmatched braces in index entry",
            ),
            LogEntry(
                level=LogLevel.INFO,
                file="main.idx",
                line=1,
                text="Using dot separator",
            ),
            LogEntry(
                level=LogLevel.INFO,
                file="main.idx",
                line=50,
                text="Output written to main.ind",
            ),
            LogEntry(
                level=LogLevel.INFO,
                file="main.ind",
                line=1,
                text="Loaded 42 index entries",
            ),
        ],
    )

    code_plog = ParsedLog(
        category="code",
        tool_name="pythontex",
        importance="high",
        entries=[
            LogEntry(
                level=LogLevel.ERROR,
                file="main.tex",
                line=77,
                text="ZeroDivisionError: division by zero",
            ),
        ],
    )

    return [bib_plog, idx_plog, code_plog]


def test_constants():
    assert CATEGORY_ORDER == [
        "bibliography",
        "index",
        "glossary",
        "code",
        "graphics",
        "compile",
    ]
    assert CATEGORY_LABEL["bibliography"] == "参考文献"
    assert CATEGORY_LABEL["index"] == "索引"
    assert CATEGORY_LABEL["glossary"] == "术语/词汇表"
    assert CATEGORY_LABEL["code"] == "代码执行"
    assert CATEGORY_LABEL["graphics"] == "图形/绘图"
    assert CATEGORY_LABEL["compile"] == "一般编译"
    assert IMPORTANCE_LABEL == {"high": "高", "medium": "中", "low": "低"}
    print("常量定义验证通过 ✓")


def test_summary_full_output():
    logs = build_test_logs()
    buf = StringIO()
    with redirect_stdout(buf):
        result = print_summary(
            logs,
            ref_change_report="引用变更报告：新增 3 条，删除 1 条",
            non_quiet=True,
            use_logger=False,
            show_info=True,
        )
    stdout_output = buf.getvalue()

    assert "错误汇总" in result
    assert "错误汇总" in stdout_output
    assert "警告汇总" in result
    assert "警告汇总" in stdout_output
    assert "提示汇总" in result
    assert "提示汇总" in stdout_output

    assert "参考文献" in result
    assert "参考文献" in stdout_output
    assert "索引" in result
    assert "索引" in stdout_output
    assert "代码执行" in result or "代码" in result
    assert "代码执行" in stdout_output or "代码" in stdout_output

    assert "Undefined reference 'Author2024'" in result
    assert "main.bib:15 --> Undefined reference 'Author2024'" in result
    assert "ZeroDivisionError: division by zero" in result
    assert "main.tex:77 --> ZeroDivisionError: division by zero" in result
    assert "Missing journal field" in result
    assert "Unmatched braces in index entry" in result

    assert "引用变更报告：新增 3 条，删除 1 条" in result
    assert "引用变更报告：新增 3 条，删除 1 条" in stdout_output

    print("完整输出（non_quiet=True, show_info=True）验证通过 ✓")


def test_summary_non_quiet_false():
    logs = build_test_logs()
    buf = StringIO()
    with redirect_stdout(buf):
        result = print_summary(
            logs,
            ref_change_report=None,
            non_quiet=False,
            use_logger=False,
            show_info=True,
        )
    stdout_output = buf.getvalue()

    assert "错误汇总" in result
    assert "错误汇总" in stdout_output

    assert "警告汇总" not in result
    assert "警告汇总" not in stdout_output
    assert "提示汇总" not in result
    assert "提示汇总" not in stdout_output

    assert "参考文献" in result
    assert "代码" in result

    print("non_quiet=False（仅错误组）验证通过 ✓")


def test_summary_hide_info():
    logs = build_test_logs()
    buf = StringIO()
    with redirect_stdout(buf):
        result = print_summary(
            logs,
            ref_change_report=None,
            non_quiet=True,
            use_logger=False,
            show_info=False,
        )
    stdout_output = buf.getvalue()

    assert "错误汇总" in result
    assert "警告汇总" in result
    assert "提示汇总" not in result
    assert "提示汇总" not in stdout_output

    assert "Using dot separator" not in result
    assert "Output written to main.ind" not in result

    print("show_info=False（隐藏提示组）验证通过 ✓")


def test_return_string():
    logs = build_test_logs()
    result = print_summary(logs, use_logger=False)
    assert isinstance(result, str)
    assert len(result) > 0
    print("返回字符串验证通过 ✓")


if __name__ == "__main__":
    test_constants()
    test_summary_full_output()
    test_summary_non_quiet_false()
    test_summary_hide_info()
    test_return_string()
    print("\n所有验证测试通过！✓")
