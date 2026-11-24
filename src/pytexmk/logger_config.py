"""
 =======================================================================
 ····Y88b···d88P················888b·····d888·d8b·······················
 ·····Y88b·d88P·················8888b···d8888·Y8P·······················
 ······Y88o88P··················88888b·d88888···························
 ·······Y888P··8888b···88888b···888Y88888P888·888·88888b·····d88b·······
 ········888······"88b·888·"88b·888·Y888P·888·888·888·"88b·d88P"88b·····
 ········888···d888888·888··888·888··Y8P··888·888·888··888·888··888·····
 ········888··888··888·888··888·888···"···888·888·888··888·Y88b·888·····
 ········888··"Y888888·888··888·888·······888·888·888··888··"Y88888·····
 ·······························································888·····
 ··························································Y8b·d88P·····
 ···························································"Y88P"······
 =======================================================================

 -----------------------------------------------------------------------
Author       : 焱铭
Date         : 2024-07-23 20:20:00 +0800
LastEditTime : 2025-05-06 22:08:13 +0800
Github       : https://github.com/YanMing-lxb/
FilePath     : /PyTeXMK/src/pytexmk/logger_config.py
Description  :
 -----------------------------------------------------------------------
"""

import logging
import shutil

from rich.console import Console
from rich.logging import RichHandler  # 导入rich库的日志处理模块
from rich.text import Text

from pytexmk.language import set_language
from pytexmk.ui_theme import console_stream, custom_theme

_ = set_language("logger_config")

#: 日志正文的最大显示宽度。终端更窄时跟随终端，避免在窄窗口里反复折行。
LOG_LINE_WIDTH = 100

#: 级别列宽 + 一个空格：``ERROR    `` / ``WARNING  `` 都是 9 列，
#: 续行按同样的宽度缩进，长警告与错误的首列才能对齐。
_LEVEL_PREFIX_WIDTH = 9


def _default_log_width() -> int:
    """终端比 100 列更窄时跟随终端，避免硬折行后被终端二次折断。"""
    columns = shutil.get_terminal_size((LOG_LINE_WIDTH, 24)).columns
    return max(40, min(LOG_LINE_WIDTH, columns))


class AlignedRichHandler(RichHandler):
    """把日志按固定宽度折行，并让续行与正文首列对齐。

    RichHandler 默认把整条消息塞进一个 ``expand`` 表格，宽度由终端决定：
    宽终端里长警告会拖出上百列，窄终端里续行又贴在最左侧。这里改为先按
    ``width - 9`` 折行，再给首行加级别前缀、续行加 9 个空格，保证两种终端
    下都是同一套版式。
    """

    def __init__(self, *, width: int | None = None, **kwargs) -> None:
        width = width or _default_log_width()
        kwargs.setdefault("markup", True)
        kwargs.setdefault("show_path", False)
        kwargs.setdefault("show_time", False)
        console = Console(
            theme=custom_theme,
            file=console_stream,
            width=width,
            highlight=False,
        )
        super().__init__(console=console, **kwargs)

    def emit(self, record: logging.LogRecord) -> None:
        try:
            message = self.format(record)
            if record.exc_info:
                if not record.exc_text:
                    record.exc_text = self.formatException(record.exc_info)
                message = f"{message}\n{record.exc_text}"
            renderable = self.render_message(record, message)
            body = renderable if isinstance(renderable, Text) else Text(str(renderable))
            prefix = self.get_level_text(record)
            prefix.append(" ")

            lines = body.wrap(
                self.console,
                max(1, self.console.width - _LEVEL_PREFIX_WIDTH),
            )
            for index, line in enumerate(lines):
                output = Text()
                if index == 0:
                    output.append_text(prefix)
                else:
                    output.append(" " * _LEVEL_PREFIX_WIDTH)
                line.rstrip()
                output.append_text(line)
                self.console.print(output, no_wrap=True, overflow="crop")
        except Exception:
            self.handleError(record)


def attach_pytexlogs_handlers_to_pytexmk_logger() -> None:
    """让独立库 ``pytexlogs`` 的日志跟随主程序的级别与输出通道（幂等）。

    0.5 的做法是把 pytexmk 的每个 handler 也挂到 pytexlogs 上，同时
    ``propagate`` 仍为 True：``basicConfig`` 已把 RichHandler 装在 root，
    于是每条库日志先经 pytexlogs 自己的 handler、再经 root 的同一个 handler，
    在 ``-vb`` 下打印两遍。这里改为**只对齐级别、清掉额外 handler**，让库日志
    统一经 root 输出一次。
    """
    ref_logger = logging.getLogger("pytexmk")
    remote_logger = logging.getLogger("pytexlogs")
    remote_logger.setLevel(ref_logger.level or logging.getLogger().level or logging.WARNING)
    remote_logger.propagate = True
    # 清掉此前（或库自身）挂上的 handler，避免与 root handler 重复输出
    for handler in list(remote_logger.handlers):
        remote_logger.removeHandler(handler)


# --------------------------------------------------------------------------------
# 定义日志记录器
# --------------------------------------------------------------------------------


def setup_logger(verbose):
    """
    配置并设置日志记录器。
    """
    FORMAT = "%(message)s"
    logger_name = "pytexmk"
    logger = logging.getLogger(logger_name)

    # 与 1.2.7 保持一致：-vb 只把级别抬到 INFO，不再升到 DEBUG。
    # 调试级的内部细节由 -vb 之外的手段（临时改代码/日志）查看，避免把
    # 正常使用中的输出淹掉。安静模式（-q/-nq）不参与这里的级别判定。
    level = logging.INFO if verbose else logging.WARNING

    # 避免重复添加 handler
    if logger.hasHandlers():
        # 但级别仍要按本次的 -vb 结论落一次：--watch 重入、测试里二次调用时
        # 早退会留下上一次的级别，导致 -vb 看起来没生效。
        logger.setLevel(level)
        logging.getLogger().setLevel(level)
        attach_pytexlogs_handlers_to_pytexmk_logger()
        return logger

    if verbose:
        print(_("启用 PyTeXMK 详细日志输出..."))

    handler = AlignedRichHandler(show_level=True, markup=True, show_path=False)
    handler.setFormatter(logging.Formatter(FORMAT))

    logging.basicConfig(level=level, format=FORMAT, datefmt="[%X]", handlers=[handler])
    logger.setLevel(level)

    attach_pytexlogs_handlers_to_pytexmk_logger()

    return logger
