"""终端日志折行与续行对齐的回归测试。"""

import logging
from io import StringIO

from rich.console import Console

from pytexmk.logger_config import AlignedRichHandler
from pytexmk.ui_theme import custom_theme


def _logger(width: int) -> tuple[logging.Logger, StringIO]:
    buffer = StringIO()
    console = Console(
        file=buffer,
        width=width,
        no_color=True,
        force_terminal=False,
        theme=custom_theme,
    )
    handler = AlignedRichHandler(width=width)
    handler.console = console
    handler.setFormatter(logging.Formatter("%(message)s"))
    logger = logging.getLogger(f"pytexmk_test_{width}_{id(buffer)}")
    logger.handlers = [handler]
    logger.propagate = False
    logger.setLevel(logging.WARNING)
    return logger, buffer


def test_long_warning_wraps_and_aligns_continuation():
    width = 60
    logger, buffer = _logger(width)
    logger.warning("word " * 40)

    lines = buffer.getvalue().splitlines()
    assert len(lines) > 1
    assert lines[0].startswith("WARNING  word")
    assert all(line.startswith(" " * 9) for line in lines[1:])
    assert all(len(line) <= width for line in lines)
    assert all(not line.endswith(" ") for line in lines)


def test_error_prefix_and_markup_are_preserved():
    width = 50
    logger, buffer = _logger(width)
    logger.error("不支持绝对路径: [bold cyan]/tmp/demo.tex[/bold cyan] " + "x" * 60)

    text = buffer.getvalue()
    assert text.startswith("ERROR    不支持绝对路径: /tmp/demo.tex")
    assert "[bold cyan]" not in text and "[/bold cyan]" not in text
    assert all(len(line) <= width for line in text.splitlines())
