"""极简 TeX 源扫描辅助：把注释、verbatim 与行内 ``\\verb`` 屏蔽成空格。

目的不是做完整 TeX 词法分析，而是让“按正则找命令”的调用方（preflight、
LaTeXDiff 压平、投稿兼容性扫描）不会把注释或 verbatim 里的 ``\\input`` /
``\\usepackage`` 当成真实命令。返回值与输入**等长**，换行保持不变，因此
调用方仍可直接用命中的下标切片原文。
"""

import re

#: 内容不是代码、不能被命令扫描命中的环境。只列最常用的几个：
#: 自定义环境仍按普通正文处理，避免为了“猜作者语义”引入误判。
_VERBATIM_ENVIRONMENTS = frozenset(
    {
        "verbatim",
        "verbatim*",
        "Verbatim",
        "Verbatim*",
        "lstlisting",
        "minted",
        "comment",
        "filecontents",
        "filecontents*",
    }
)

_BEGIN_RE = re.compile(r"\\begin\s*\{([^{}]*)\}")
_VERB_RE = re.compile(r"\\(?:verb|Verb)(?:\*)?(?![A-Za-z@])")


def _blank(chars: list[str], start: int, end: int) -> None:
    """把 ``[start, end)`` 变成空格，保留换行以维持行号与切片位置。"""
    for index in range(start, min(end, len(chars))):
        if chars[index] not in "\r\n":
            chars[index] = " "


def mask_tex_noncode(text: str) -> str:
    """返回与 ``text`` 等长的副本：注释、verbatim 环境、``\\verb`` 内容为空格。

    * ``%`` 注释从百分号屏蔽到行尾；``\\%`` 是转义百分号，不当作注释。
    * ``\\begin{verbatim}`` 等环境整段屏蔽（含 ``\\begin``/``\\end``）。
    * ``\\verb|...|`` / ``\\Verb|...|`` 屏蔽到同一行内的配对分隔符。
    """
    chars = list(text)
    index = 0
    length = len(text)
    while index < length:
        char = text[index]

        if char == "%":
            line_end = text.find("\n", index)
            if line_end < 0:
                line_end = length
            _blank(chars, index, line_end)
            index = line_end
            continue

        if char == "\\":
            verb = _VERB_RE.match(text, index)
            if verb is not None:
                delimiter_at = verb.end()
                if delimiter_at < length and not text[delimiter_at].isspace():
                    delimiter = text[delimiter_at]
                    line_end = text.find("\n", delimiter_at)
                    if line_end < 0:
                        line_end = length
                    closing = text.find(delimiter, delimiter_at + 1, line_end)
                    end = closing + 1 if closing >= 0 else line_end
                    _blank(chars, index, end)
                    index = end
                    continue

            begin = _BEGIN_RE.match(text, index)
            if begin is not None and begin.group(1) in _VERBATIM_ENVIRONMENTS:
                environment = begin.group(1)
                end_re = re.compile(r"\\end\s*\{" + re.escape(environment) + r"\}")
                closing = end_re.search(text, begin.end())
                end = closing.end() if closing is not None else length
                _blank(chars, index, end)
                index = end
                continue

            # 普通控制序列：跳过命令名，避免把 `\%` 当成注释开头。
            index += 2
            continue

        index += 1

    return "".join(chars)


def first_comment_index(line: str) -> int:
    """返回行内第一个未转义 ``%`` 的下标；没有注释返回 ``len(line)``。"""
    index = 0
    length = len(line)
    while index < length:
        char = line[index]
        if char == "\\":
            index += 2
            continue
        if char == "%":
            return index
        index += 1
    return length
