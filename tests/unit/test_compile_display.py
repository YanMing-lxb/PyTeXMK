"""运行命令打印与 SyncTeX 配置的回归测试。

覆盖两件事：
* “运行命令”打印：按 ``total_len`` 对齐折行，每行不超过横幅宽度；含空格的参数加引号便于阅读；
* ``synctex = false``（配置驱动）：编译命令里不再出现 ``-synctex=1``、构建指纹变化、
  跳过编译时只要求 PDF。CLI 不再提供 ``--synctex/--no-synctex``。

注意：折行块只用于阅读对齐，不承诺原样粘贴执行，因此这里不断言续行符。
"""

import inspect
from pathlib import Path
from types import SimpleNamespace

from pytexmk import synctex as synctex_mod
from pytexmk.cli import cli_compile
from pytexmk.cli.cli_args import build_parser
from pytexmk.compile import CompileLaTeX
from pytexmk.subprocess_runner import (
    format_command,
    shorten_command,
    wrap_command,
)
from pytexmk.timing import get_text_len, total_len

PREFIX = " " * get_text_len("运行命令: ")


def _compiler(**kwargs) -> CompileLaTeX:
    kwargs.setdefault("shell_escape", False)
    kwargs.setdefault("native", False)
    return CompileLaTeX(
        "main", "XeLaTeX", [".pdf"], [".aux"], "./Build/", "./Auxiliary/", False, **kwargs
    )


# ---------------------------------------------------------------- 引号与折行


def test_format_command_quotes_only_when_needed():
    command = ["lualatex", r"-output-directory=D:\a b\Auxiliary", "-jobname=main"]
    text = format_command(command)
    assert text == 'lualatex "-output-directory=D:\\a b\\Auxiliary" -jobname=main'


def test_format_command_quotes_empty_argument():
    assert format_command(["x", ""]) == 'x ""'


def test_format_command_leaves_bare_program_name_alone():
    assert format_command(["lualatex", "-jobname=main", "main.tex"]) == "lualatex -jobname=main main.tex"


def test_wrap_keeps_rows_within_banner_width():
    command = [
        "lualatex", "-recorder", "-file-line-error", "-halt-on-error",
        "-interaction=batchmode", r"-output-directory=D:\a b\Auxiliary",
        "-jobname=main", "main.tex",
    ]
    rows = wrap_command(format_command(command), total_len, PREFIX)
    assert len(rows) > 1, "这条命令在 78 列内放不下，必须折行"
    for row in rows:
        assert get_text_len(_with_prefix(row)) <= total_len


def _with_prefix(row: str) -> str:
    """首行由调用方拼接前缀，续行已带等宽缩进，这里还原成实际打印出的一行。"""
    return row if row.startswith(" ") else "运行命令: " + row


def test_wrap_splits_overlong_argument_instead_of_overflowing():
    """单个参数比可用宽度还长时，按显示宽度切开，保证不超宽（允许在参数内部断）。"""
    long_path = "D:" + "\\verylongdirectoryname" * 8
    rows = wrap_command(format_command(["lualatex", long_path]), total_len, PREFIX)
    for row in rows:
        assert get_text_len(_with_prefix(row)) <= total_len
    joined = "".join(row.strip() for row in rows).replace("lualatex", "", 1)
    assert long_path in joined, "切开只是折行，不能丢字符"


def test_wrap_breaks_between_arguments_when_they_fit():
    command = ["dvipdfmx", "-V", "2.0", "-o=out/main.pdf", "Auxiliary/main.xdv"]
    text = format_command(command)
    rows = wrap_command(text, 30, PREFIX)
    rebuilt = " ".join(row.strip() for row in rows)
    assert rebuilt.split() == text.split()


def test_wrap_single_line_when_it_fits():
    rows = wrap_command("lualatex main.tex", total_len, PREFIX)
    assert rows == ["lualatex main.tex"]


# ------------------------------------------------------------ 打印宽度


def test_print_command_lines_fit_banner_width(tmp_path, monkeypatch, capsys):
    """正常情况下，打印出来每一行的显示宽度都不超过横幅宽度。"""
    from pytexmk.subprocess_runner import print_command

    monkeypatch.chdir(tmp_path)
    command = ["lualatex", "-recorder", "-file-line-error", "-halt-on-error",
               "-synctex=1", "-interaction=batchmode", "-output-directory=Auxiliary",
               "-jobname=main", "main.tex"]
    print_command(command)

    out = capsys.readouterr().out
    lines = [line.rstrip() for line in out.splitlines() if line.strip()]
    assert lines[0].startswith("运行命令:")
    assert max(get_text_len(line) for line in lines) <= total_len


def test_long_argument_breaks_after_path_separator():
    """超长路径优先在 ``\\`` 后断开，避免把目录名/中文词切成两半。"""
    from pytexmk.subprocess_runner import _split_by_width

    text = r'"-output-directory=D:\Document YM\Desktop Document\科研\论文\期刊论文\paper-01-dr-ym\Auxiliary"'
    chunks = _split_by_width(text, 68)
    assert len(chunks) > 1
    assert all(get_text_len(chunk) <= 68 for chunk in chunks)
    assert chunks[0].endswith("\\"), "应当在分隔符处断开"
    assert "".join(chunks) == text


def test_print_command_keeps_long_argument_rows_within_width(tmp_path, monkeypatch, capsys):
    """外部深层路径这种超长参数，也要保证每行不超过横幅宽度。"""
    from pytexmk.subprocess_runner import print_command

    monkeypatch.chdir(tmp_path)
    bulky = "-output-directory=" + "D:\\" + "\\".join(["深层目录"] * 8)
    print_command(["xelatex", bulky, "main.tex"])

    out = capsys.readouterr().out
    lines = [line.rstrip() for line in out.splitlines() if line.strip()]
    assert max(get_text_len(line) for line in lines) <= total_len
    assert "列上限" not in out, "折行块只求对齐，不需要再解释超宽"


# ---------------------------------------------------------------- 路径缩写


def test_shorten_command_relativizes_paths_inside_cwd(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    aux = tmp_path / "Auxiliary"
    command = ["xelatex", f"-output-directory={aux}", "-jobname=main", "main.tex"]
    assert shorten_command(command, tmp_path) == [
        "xelatex",
        "-output-directory=Auxiliary",
        "-jobname=main",
        "main.tex",
    ]


def test_shorten_command_keeps_absolute_when_working_directory_differs(tmp_path, monkeypatch):
    elsewhere = tmp_path / "elsewhere"
    elsewhere.mkdir()
    monkeypatch.chdir(elsewhere)
    aux = tmp_path / "Auxiliary"
    assert shorten_command([f"-output-directory={aux}"], tmp_path) == [f"-output-directory={aux}"]


def test_shorten_command_keeps_paths_outside_cwd(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    outside = tmp_path.parent / "Build"
    assert shorten_command([str(outside)], tmp_path) == [str(outside)]


# ---------------------------------------------------------------- SyncTeX 开关


def test_latex_command_keeps_synctex_by_default():
    assert "-synctex=1" in _compiler()._latex_command()


def test_no_synctex_drops_the_flag():
    command = _compiler(synctex=False)._latex_command()
    assert "-synctex=1" not in command
    # 其余定位相关开关不受影响：-recorder 仍是投稿打包/依赖收集的前提
    assert "-recorder" in command


def _build_key_state(tmp_path, synctex: bool) -> SimpleNamespace:
    return SimpleNamespace(
        compiled_program="XeLaTeX",
        interaction="batchmode",
        non_quiet=False,
        shell_escape="false",
        synctex=synctex,
        native_build=True,
        outdir=str(tmp_path / "Build"),
        auxdir=str(tmp_path / "Auxiliary"),
        extra_args=[],
        output_name="main",
        args=SimpleNamespace(draft=False),
    )


def _write_valid_pdf(path: Path) -> None:
    """写一份最小但可解析的 PDF（pypdf 能读出 1 页）。"""
    from pypdf import PdfWriter

    writer = PdfWriter()
    writer.add_blank_page(width=100, height=100)
    with path.open("wb") as handle:
        writer.write(handle)


def test_build_key_changes_with_synctex_toggle(tmp_path):
    assert cli_compile._current_build_key(
        _build_key_state(tmp_path, True)
    ) != cli_compile._current_build_key(_build_key_state(tmp_path, False))


def test_outputs_present_needs_pdf_only_when_synctex_disabled(tmp_path):
    _write_valid_pdf(tmp_path / "main.pdf")
    enabled = SimpleNamespace(outdir=str(tmp_path), output_name="main", synctex=True)
    disabled = SimpleNamespace(outdir=str(tmp_path), output_name="main", synctex=False)
    assert not cli_compile._outputs_present(enabled)
    assert cli_compile._outputs_present(disabled)


def test_check_signature_has_no_page_parameter():
    assert "page" not in inspect.signature(synctex_mod.check).parameters


def test_cli_synctex_flags_are_removed():
    import pytest

    parser = build_parser()
    with pytest.raises(SystemExit) as exc:
        parser.parse_args(["--no-synctex"])
    assert exc.value.code == 2
    with pytest.raises(SystemExit) as exc:
        parser.parse_args(["--synctex"])
    assert exc.value.code == 2


def test_cli_has_no_continuation_flag():
    """折行块不再承诺可粘贴执行，续行符相关开关一并撤掉。"""
    parser = build_parser()
    names = {option for action in parser._actions for option in action.option_strings}
    assert "--command-line-continuation" not in names


def _override_state(tmp_path) -> SimpleNamespace:
    return SimpleNamespace(
        native_build=True,
        shell_escape="auto",
        synctex=True,
        interaction="",
        extra_args=[],
        max_extra_compilations=8,
        outdir=str(tmp_path / "Build"),
        auxdir=str(tmp_path / "Auxiliary"),
        preview_after_compile=False,
        non_quiet=False,
    )


def test_apply_build_overrides_leaves_synctex_to_config(tmp_path):
    """CLI 只合入 interaction/extra_args；synctex 等构建开关由配置驱动。"""
    args = SimpleNamespace(
        interaction=None, extra_args=["-8bit"],
    )
    state = _override_state(tmp_path)
    cli_compile._apply_build_overrides(args, state)
    assert state.synctex is True
    assert state.extra_args == ["-8bit"]
