"""``ui_theme`` 的可切换输出流。

`--json` 要把整个 console 切到 stderr；没有显式切换时又必须跟随当前
`sys.stdout`（否则 pytest capsys / redirect_stdout 全部失效）。
"""
import io
import sys
from types import SimpleNamespace

import pytexmk.ui_theme as ui_theme


def test_switch_to_and_restore():
    stream = ui_theme._SwappableStream()
    first = io.StringIO()
    second = io.StringIO()

    stream.switch_to(first)
    stream.write("a")
    stream.restore()

    original = sys.stdout
    sys.stdout = second
    try:
        stream.write("b")
    finally:
        sys.stdout = original

    assert first.getvalue() == "a"
    assert second.getvalue() == "b"


def test_default_target_follows_sys_stdout_dynamically():
    stream = ui_theme._SwappableStream()
    original = sys.stdout
    buffer = io.StringIO()
    sys.stdout = buffer
    try:
        stream.write("dynamic")
    finally:
        sys.stdout = original
    assert buffer.getvalue() == "dynamic"


def test_isatty_encoding_errors_fall_back():
    stream = ui_theme._SwappableStream(SimpleNamespace(write=lambda text: None, flush=lambda: None))
    assert stream.isatty() is False
    assert stream.encoding == "utf-8"
    assert stream.errors == "strict"
    stream.close()  # 代理关闭不能影响真实流


def test_close_does_not_close_underlying_stream():
    buffer = io.StringIO()
    stream = ui_theme._SwappableStream(buffer)
    stream.close()
    stream.write("still-open")
    assert buffer.getvalue() == "still-open"


def test_fileno_delegates(tmp_path):
    with open(tmp_path / "out.txt", "w", encoding="utf-8") as handle:
        stream = ui_theme._SwappableStream(handle)
        assert stream.fileno() == handle.fileno()
