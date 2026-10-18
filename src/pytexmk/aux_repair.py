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
Date         : 2026-10-17 23:20:00 +0800
Github       : https://github.com/YanMing-lxb/
FilePath     : /PyTeXMK/src/pytexmk/aux_repair.py
Description  :
 -----------------------------------------------------------------------
模块职责边界（架构 FR-A3）：负责【编译前辅助文件健康检查与自愈】。
  具体职责：
    1. 识别被中断的编译留下的"截断辅助文件"（.aux/.toc/.out/.bbl/.nlo 等）。
    2. 删除损坏文件，交给下一次编译重新生成，避免"越编译越坏"的死循环。
  调用依赖关系拓扑：
    cli.cli_compile 在把辅助文件搬回项目根目录之后、调用 RUN 之前调用本模块。
  下游依赖：
    language / Path / logging。
 -----------------------------------------------------------------------
为什么需要这个模块：
  用户在编译过程中按下 Ctrl+C、或关闭终端、或强制结束进程时，LaTeX 正在写
  .aux 文件的中间状态会被留在磁盘上。这种半截文件末尾通常是
  `\\@writefile{toc}{\\contentsline ...` 这样的未闭合命令，下一次编译读到它
  会直接报
      ! File ended while scanning use of \\@writefile.
      ==> Fatal error occurred, no output PDF file produced!
  并且这个错误每次都会重现 —— 因为坏文件还在，LaTeX 还没来得及重写它就先崩了。
  此时唯一的出路是手动删除辅助文件（或 pytexmk -c），但普通用户很难自己判断
  该删哪个文件。本模块把这一步自动化：编译前检查、发现即删除并给出提示。
 -----------------------------------------------------------------------
"""

import logging
from pathlib import Path

from pytexmk.language import set_language

_ = set_language("aux_repair")

# 只检查"行式写入、括号必须配平"的辅助文件。
# 不检查 .log / .pdf / .synctex.gz 等非结构化或二进制产物。
CHECKED_SUFFIXES: tuple[str, ...] = (
    ".aux",
    ".toc",
    ".lof",
    ".lot",
    ".out",
    ".bbl",
    ".idx",
    ".ind",
    ".nlo",
    ".nls",
    ".glo",
    ".gls",
    ".nav",
    ".snm",
)

# 辅助文件按行写入，正常情况下总以换行结束。
# 若文件大小正好落在缓冲区边界上又没有结尾换行，几乎必然是写入中途被打断。
_BUFFER_BOUNDARY = 4096


def _brace_balance(text: str) -> int:
    """统计未转义花括号的净值（`{` 计 +1，`}` 计 -1）。

    需要正确跳过 `\\{` / `\\}` 这类转义花括号，以及 `\\\\{`（换行命令后紧跟
    真正生效的左括号）这种情况，因此按"前置反斜杠个数的奇偶性"判断：
    奇数个反斜杠表示该花括号被转义，偶数个表示它是结构性的花括号。
    """
    balance = 0
    backslashes = 0
    for ch in text:
        if ch == "\\":
            backslashes += 1
            continue
        if ch == "{":
            if backslashes % 2 == 0:
                balance += 1
        elif ch == "}":
            if backslashes % 2 == 0:
                balance -= 1
                # 出现"多出来的右括号"时不必继续统计，已经能断定文件损坏
                if balance < 0:
                    return balance
        backslashes = 0
    return balance


def _decode_for_check(path: Path) -> str | None:
    """尽力把辅助文件解码成文本用于结构检查；读不了就跳过检查。"""
    try:
        data = path.read_bytes()
    except OSError:
        return None
    for encoding in ("utf-8", "latin-1"):
        try:
            return data.decode(encoding)
        except UnicodeDecodeError:
            continue
    return None


def find_truncated_aux_files(dirs: list[Path], project_name: str | None = None) -> list[Path]:
    """返回检测到的截断辅助文件列表（不修改磁盘）。

    判定规则（满足任一即视为截断）：

    1. 花括号不配平 —— 这是最可靠的信号。完整的辅助文件里每条命令都闭合，
       被中途打断时最后一条命令通常只剩左半边，例如
       ``\\@writefile{toc}{\\contentsline {section}``。
    2. 文件大小正好是 4 KiB 的整数倍、却又不以换行结尾 —— 操作系统缓冲区
       恰好写满一块时被终止，这种文件可能"看起来配平"但结尾仍在半句中间。

    空文件不在此列：``.spl`` 等文件本来就允许为空。
    """
    truncated: list[Path] = []
    seen: set[Path] = set()

    for folder in dirs:
        base = Path(folder)
        if not base.is_dir():
            continue
        for suffix in CHECKED_SUFFIXES:
            if project_name:
                candidates = [base / f"{project_name}{suffix}"]
            else:
                candidates = sorted(base.glob(f"*{suffix}"))
            for path in candidates:
                if not path.is_file() or path in seen:
                    continue
                seen.add(path)
                try:
                    size = path.stat().st_size
                except OSError:
                    continue
                if size == 0:
                    continue
                text = _decode_for_check(path)
                if text is None:
                    continue
                if _brace_balance(text) != 0:
                    truncated.append(path)
                    continue
                if size % _BUFFER_BOUNDARY == 0 and not text.endswith(("\n", "\r")):
                    truncated.append(path)
    return truncated


def repair_auxiliary_files(
    dirs: list[Path],
    project_name: str | None = None,
    logger: logging.Logger | None = None,
) -> list[Path]:
    """删除截断的辅助文件，返回被删除的路径列表。

    删除是安全的：这些文件本来就是 LaTeX 的中间产物，下一次编译会完整重建。
    保留一个"被删除"的返回值，供调用方打印提示并计入日志。
    """
    log = logger or logging.getLogger(__name__)
    repaired: list[Path] = []
    for path in find_truncated_aux_files(dirs, project_name):
        try:
            path.unlink()
        except OSError as exc:
            log.error(_("删除损坏的辅助文件失败: %(path)s --> %(err)s") % {"path": str(path), "err": str(exc)})
            continue
        log.warning(_("检测到被中断的编译留下的损坏辅助文件，已删除并将在本次编译中重建: %(path)s") % {"path": str(path)})
        repaired.append(path)
    return repaired
