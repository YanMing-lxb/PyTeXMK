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

from rich.logging import RichHandler  # 导入rich库的日志处理模块

from pytexmk.language import set_language

_ = set_language("logger_config")


def attach_pytexlogs_handlers_to_pytexmk_logger() -> None:
    """把独立库 pytexlogs logger 的 handlers/level 与主程序 pytexmk logger 对齐。

    允许幂等调用（多次调用不重复添加 handler）。
    """
    ref_logger = logging.getLogger("pytexmk")
    remote_logger = logging.getLogger("pytexlogs")
    remote_logger.setLevel(ref_logger.level)
    remote_logger.propagate = ref_logger.propagate
    existing = {
        type(h).__name__ + repr(getattr(h, "baseFilename", ""))
        for h in remote_logger.handlers
    }
    for h in ref_logger.handlers:
        key = type(h).__name__ + repr(getattr(h, "baseFilename", ""))
        if key not in existing:
            remote_logger.addHandler(h)


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

    # 避免重复添加 handler
    if logger.hasHandlers():
        return logger

    level = logging.INFO if verbose else logging.WARNING
    print(_("启用 PyTeXMK 详细日志输出...") if verbose else "")

    handler = RichHandler(
        show_level=True, show_time=False, markup=True, show_path=False
    )
    handler.setFormatter(logging.Formatter(FORMAT))

    logging.basicConfig(level=level, format=FORMAT, datefmt="[%X]", handlers=[handler])

    attach_pytexlogs_handlers_to_pytexmk_logger()

    return logger
