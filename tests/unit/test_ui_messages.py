"""``ui_messages`` 的横幅与魔法注释表。

此前该模块没有任何直接用例：横幅在超长消息下会算出负 padding，魔法注释表
出错时静默返回 None，两条路径都没人验证。
"""
from io import StringIO

import pytest
from rich.console import Console

import pytexmk.ui_messages as ui_messages


@pytest.fixture
def captured(monkeypatch):
    buffer = StringIO()
    con = Console(file=buffer, width=400, force_terminal=False, color_system=None)
    monkeypatch.setattr(ui_messages, "console", con)
    return buffer


def test_plain_message_is_printed_as_is(captured):
    ui_messages.print_message("普通消息")
    assert "普通消息" in captured.getvalue()
    assert "|" not in captured.getvalue()


@pytest.mark.parametrize("state", ["additional", "running", "success", "unknown"])
def test_stateful_message_draws_banner(captured, state):
    ui_messages.print_message("编译中", state)
    out = captured.getvalue()
    assert "| 编译中 |" in out
    # 上下两条分隔线不能为空
    assert out.count("=") >= 2


def test_overlong_message_does_not_produce_negative_padding(captured):
    message = "x" * 200
    ui_messages.print_message(message, "success")
    assert f"| {message} |" in captured.getvalue()


def test_magic_comment_table_has_all_entries():
    table = ui_messages.magic_comment_desc_table()
    assert table is not None
    assert len(table.columns) == 3
    assert len(table.rows) == 4

    buffer = StringIO()
    Console(file=buffer, width=120, force_terminal=False, color_system=None).print(table)
    rendered = buffer.getvalue()
    for key in ("!TEX program", "!TEX root", "!TEX outdir", "!TEX auxdir"):
        assert key in rendered


def test_magic_comment_table_error_is_reported_not_raised(monkeypatch):
    def boom(*args, **kwargs):
        raise ValueError("模拟表格构造失败")

    monkeypatch.setattr(ui_messages.Table, "add_row", boom)
    assert ui_messages.magic_comment_desc_table() is None
