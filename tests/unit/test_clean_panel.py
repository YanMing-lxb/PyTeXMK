"""``-c/-C/-ca/-Ca`` 完成面板：数量、分组、用时，失败逐条列出；不再打时长表。"""

import datetime
from pathlib import Path
from types import SimpleNamespace

from pytexmk.cli import cli_compile


def _args(**flags):
    defaults = {
        "clean": False,
        "clean_out": False,
        "clean_recursive": False,
        "clean_recursive_out": False,
    }
    defaults.update(flags)
    return SimpleNamespace(**defaults)


def _state(tmp_path: Path) -> SimpleNamespace:
    return SimpleNamespace(
        start_perf=None,
        start_time=datetime.datetime.now(tz=datetime.UTC) - datetime.timedelta(seconds=1),
    )


def _result(tmp_path: Path, *, files=3, build=0, folders=1, failed=()):
    removed = [Path("Auxiliary") / f"main.{i}.aux" for i in range(files)]
    build_paths = [Path("Build") / "main.pdf"] if build else []
    return cli_compile._CleanResult(
        removed=removed + build_paths,
        failed=list(failed),
        source_count=files,
        build_count=build,
        build_paths=build_paths,
        folder_count=folders,
    )


def test_plain_clean_shows_counts_without_build_rows(tmp_path, capsys):
    cli_compile._print_clean_report(_args(clean=True), _result(tmp_path), state=_state(tmp_path))

    out = capsys.readouterr().out
    assert "清理完成" in out
    assert "方式           : 辅助文件" in out
    assert "已删除文件     : 3 个" in out
    assert "用时" in out
    assert "对应文件夹" not in out
    assert "Build" not in out
    assert "运行时长统计表" not in out


def test_clean_out_without_outputs_has_no_empty_parentheses(tmp_path, capsys):
    """没有输出可删时只报 `0 个`，不留 `0 个（）` 的空括号。"""
    cli_compile._print_clean_report(
        _args(clean_out=True),
        _result(tmp_path, files=1, build=0),
        state=_state(tmp_path),
    )

    out = capsys.readouterr().out
    assert "Build          : 0 个" in out
    assert "（）" not in out


def test_recursive_build_row_counts_only_deleted_outputs(tmp_path, capsys, monkeypatch):
    """`-Ca` 删失败时 Build 行只算真正删掉的输出，失败项留在失败块。"""
    pdf = Path("Build/main.pdf")
    synctex = Path("Build/main.synctex.gz")
    aux = Path("Auxiliary/main.aux")
    monkeypatch.setattr(
        cli_compile, "_recursive_clean_targets", lambda args, state: [aux, pdf, synctex]
    )
    monkeypatch.setattr(
        cli_compile, "_recursive_build_targets", lambda args, state: [pdf, synctex]
    )
    monkeypatch.setattr(cli_compile, "exit_pytexmk", lambda code: None)

    class Mro:
        def remove_paths(self, targets):
            return [aux, synctex], [(pdf, "PermissionError: 文件被占用")]

    state = SimpleNamespace(
        mro=Mro(),
        runtime_dict={},
        start_perf=None,
        start_time=datetime.datetime.now(tz=datetime.UTC) - datetime.timedelta(seconds=1),
    )
    cli_compile.clean_recursive(_args(clean_recursive_out=True), state)

    out = capsys.readouterr().out
    assert "已删除文件     : 2 个" in out
    assert "Build          : 1 个（main.synctex.gz）" in out
    assert "+-- [失败] · 1" in out
    assert "main.pdf --> PermissionError" in out


def test_clean_out_adds_build_row_only(tmp_path, capsys):
    """-C 只多一行 Build；范围固定，不需要“对应文件夹”。"""
    cli_compile._print_clean_report(
        _args(clean_out=True),
        _result(tmp_path, files=3, build=1, folders=2),
        state=_state(tmp_path),
    )

    out = capsys.readouterr().out
    assert "方式           : 辅助文件 + 输出" in out
    assert "已删除文件     : 4 个" in out
    assert "对应文件夹" not in out
    assert "Build          : 1 个（main.pdf）" in out


def test_recursive_clean_labels_modes(tmp_path, capsys):
    cli_compile._print_clean_report(
        _args(clean_recursive=True),
        _result(tmp_path, folders=4),
        state=_state(tmp_path),
    )
    out = capsys.readouterr().out
    assert "方式           : 全项目辅助文件" in out
    assert "对应文件夹     : 4 个" in out
    assert "Build" not in out

    cli_compile._print_clean_report(
        _args(clean_recursive_out=True),
        _result(tmp_path, build=1, folders=4),
        state=_state(tmp_path),
    )
    out = capsys.readouterr().out
    assert "方式           : 全项目辅助文件 + 输出" in out
    assert "对应文件夹     : 4 个" in out
    assert "Build          : 1 个（main.pdf）" in out


def test_failures_are_listed_in_full_only_when_present(tmp_path, capsys):
    failed = [
        (Path("Auxiliary/main.aux"), "PermissionError: 文件被占用"),
        (Path("Auxiliary/main.log"), "PermissionError: 文件被占用"),
    ]
    cli_compile._print_clean_report(
        _args(clean=True), _result(tmp_path, failed=failed), state=_state(tmp_path)
    )

    out = capsys.readouterr().out
    assert "+-- [失败] · 2" in out
    assert "main.aux --> PermissionError" in out
    assert "main.log --> PermissionError" in out

    capsys.readouterr()
    cli_compile._print_clean_report(_args(clean=True), _result(tmp_path), state=_state(tmp_path))
    assert "失败" not in capsys.readouterr().out


def test_clean_result_still_unpacks_as_two_values(tmp_path):
    result = _result(tmp_path, files=2)
    removed, failed = result
    assert len(removed) == 2 and failed == []


def test_long_failure_reason_wraps_and_aligns(tmp_path, capsys):
    """超宽原因不截断：换行并缩进到原因列，仍是“一处一块”。"""
    from pytexmk.timing import get_text_len

    reason = "[WinError 32] 另一个程序正在使用此文件，进程无法访问，请关闭预览器后重试。"
    cli_compile._print_clean_report(
        _args(clean=True),
        _result(tmp_path, failed=[(Path("Auxiliary/main.aux"), reason)]),
        state=_state(tmp_path),
    )

    out = capsys.readouterr().out
    assert "…" not in out
    lines = out.splitlines()
    start = next(i for i, line in enumerate(lines) if "[失败]" in line) + 1
    block: list[str] = []
    for line in lines[start:]:
        if line.startswith("="):
            break
        if line.strip():
            block.append(line)
    assert block[0].startswith("    Auxiliary")
    reason_col = block[0].index("--> ") + len("--> ")
    assert block[1].startswith(" " * reason_col)
    assert len(block) > 1  # 确实换了行
    assert block[0].rstrip().endswith(("，", "。", "；"))  # 优先在标点处断
    assert all(get_text_len(line) <= 78 for line in block)


def test_old_green_sentence_is_gone(tmp_path, capsys):
    cli_compile._print_clean_report(_args(clean=True), _result(tmp_path), state=_state(tmp_path))
    out = capsys.readouterr().out
    assert "的指令" not in out
