"""PyTeXMK CLI 主入口：命令行解析、编译调度与日志解析.

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
Date         : 2024-02-28 23:11:52 +0800
LastEditTime : 2025-05-15 18:54:18 +0800
Github       : https://github.com/YanMing-lxb/
FilePath     : /PyTeXMK/src/pytexmk/__main__.py
Description  :
 -----------------------------------------------------------------------
"""

import io
import os
import sys

# ---------------------------------------------------------------------------
# 【Windows 代码页硬兜底】：在任何其他代码（包括 argparse、rich、_ = set_language）
# 执行之前，强制把 stdin/stdout/stderr 统一切换为 UTF-8，避免 cp1252 / cp936
# 等默认代码页在打印中文帮助 / argparse --help 时抛出 UnicodeEncodeError。
#
# 为什么必须在入口做？
#   1. PyInstaller bootloader 在 Python 解释器启动前就已把控制台 I/O 绑定到了
#      系统默认代码页，只靠 workflow 层的 chcp / PYTHONUTF8 env 不可靠（
#      shell 跨 pwsh -> bash、exe 启动新控制台等场景都会失效）；
#   2. argparse.print_help() / rich / print 最终都走 sys.stdout.write()，
#      在这里提前 reconfigure / 重包装 TextIOWrapper 是最彻底的修复。
# ---------------------------------------------------------------------------
if sys.platform == "win32":
    os.environ.setdefault("PYTHONUTF8", "1")
    os.environ.setdefault("PYTHONIOENCODING", "utf-8:replace")

    def _force_utf8(name: str, stream, readable: bool, writable: bool):
        """尝试 reconfigure(encoding='utf-8')，失败则用 TextIOWrapper 降级重包。"""
        # 已经是 UTF-8 了就不重复处理
        try:
            current_encoding = (getattr(stream, "encoding", None) or "").lower().replace("_", "-")
        except Exception:
            current_encoding = ""
        if current_encoding in {"utf-8", "utf8"}:
            return stream

        # 优先走 Python 3.7+ 的 TextIOWrapper.reconfigure（更干净，不破坏 isatty）
        try:
            if readable and writable:
                stream.reconfigure(encoding="utf-8", errors="replace")
            elif writable:
                stream.reconfigure(encoding="utf-8", errors="replace")
            elif readable:
                stream.reconfigure(encoding="utf-8", errors="replace")
            return stream
        except Exception:
            pass

        # reconfigure 失败（比如 PyInstaller bootloader 下 stream 已被代理）→ 降级
        try:
            buffer = stream.buffer
        except AttributeError:
            return stream
        new_stream = io.TextIOWrapper(
            buffer,
            encoding="utf-8",
            errors="replace",
            line_buffering=True,
        )
        return new_stream

    try:
        sys.stdout = _force_utf8("stdout", sys.stdout, readable=False, writable=True)
        sys.stderr = _force_utf8("stderr", sys.stderr, readable=False, writable=True)
        sys.stdin  = _force_utf8("stdin",  sys.stdin,  readable=True,  writable=False)
        # argparse / click 等库会从 sys.stdout 取 encoding，确保它们也感知到 UTF-8
        try:
            import builtins
            builtins.print = print  # no-op，确保上面的 reassign 生效
        except Exception:
            pass
    except Exception:
        # 兜底：任何异常都不能阻止程序启动
        pass

from pytexmk.cli.check_version import UpdateChecker
from pytexmk.cli.cli_args import parse_args
from pytexmk.language import set_language

UC = UpdateChecker(1, 6)
_ = set_language("__main__")


def main():
    args = parse_args(UC)
    from pytexmk.cli.cli_workflow import run_workflow

    run_workflow(args)


if __name__ == "__main__":
    main()
