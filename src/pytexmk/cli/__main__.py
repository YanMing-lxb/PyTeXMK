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
    # 只影响本进程之后的子进程（TeX 工具链）：PYTHONUTF8/PYTHONIOENCODING 在解释器
    # 启动时就已经读取完毕，对当前进程的 stdio 不再生效。当前进程真正靠下面的
    # _force_utf8() 重设编码。
    os.environ.setdefault("PYTHONUTF8", "1")
    os.environ.setdefault("PYTHONIOENCODING", "utf-8:replace")

    def _force_utf8(name: str, stream, readable: bool, writable: bool):
        """尝试 reconfigure(encoding='utf-8')，失败则用 TextIOWrapper 降级重包。"""
        # 已经是 UTF-8 了就不重复处理
        try:
            current_encoding = (getattr(stream, "encoding", None) or "").lower().replace("_", "-")
        except AttributeError:
            current_encoding = ""
        if current_encoding in {"utf-8", "utf8"}:
            return stream

        # 优先走 Python 3.7+ 的 TextIOWrapper.reconfigure（更干净，不破坏 isatty）
        try:
            if readable or writable:
                stream.reconfigure(encoding="utf-8", errors="replace")
        except AttributeError, io.UnsupportedOperation:
            pass
        else:
            return stream

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

    #: 保留被替换掉的原始 TextIOWrapper 引用：旧包装器一旦被 GC 回收会连带
    #: 关闭底层 buffer，导致新的包装器读到 "I/O operation on closed file"。
    _REPLACED_STREAMS: list[object] = []

    def _swap(name: str, stream, readable: bool, writable: bool):
        new_stream = _force_utf8(name, stream, readable=readable, writable=writable)
        if new_stream is not stream:
            _REPLACED_STREAMS.append(stream)
        return new_stream

    sys.stdout = _swap("stdout", sys.stdout, readable=False, writable=True)
    sys.stderr = _swap("stderr", sys.stderr, readable=False, writable=True)
    sys.stdin = _swap("stdin", sys.stdin, readable=True, writable=False)

_VERSION_FLAGS = frozenset({"-v", "--version"})


def _print_version_and_return() -> bool:
    """``python -m pytexmk.cli --version`` 的轻量快速路径。

    ``_launcher`` 只覆盖安装入口与 ``python -m pytexmk``；直接跑
    ``python -m pytexmk.cli`` 时曾先导入 ``cli_args``（连带 rich/argparse），
    使版本号查询多花约 70 ms。这里在导入 CLI 解析器之前直接返回。
    """
    if len(sys.argv) == 2 and sys.argv[1] in _VERSION_FLAGS:
        from pytexmk.version import __version__, script_name

        print(f"{script_name} {__version__}")
        return True
    return False


def main():
    if _print_version_and_return():
        return

    from pytexmk.cli.cli_args import parse_args

    args = parse_args()

    from pytexmk.cli.cli_workflow import run_workflow

    try:
        run_workflow(args)
    except KeyboardInterrupt:
        try:
            # 确保 console 已初始化（如果在 _ = set_language 之前就按 Ctrl+C）
            from pytexmk.ui_theme import console

            console.print()
            console.print("[bold yellow]PyTeXMK 已被用户中断[/bold yellow]")
        except Exception:
            # console 还没初始化成功就被 Ctrl+C，直接 print 兜底
            print("\nPyTeXMK 已被用户中断", file=sys.stderr)
        sys.exit(130)  # 标准 SIGINT 退出码 (128 + 2)


if __name__ == "__main__":
    main()
