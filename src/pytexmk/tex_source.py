"""极简 TeX 源扫描辅助：把注释、verbatim 与行内 ``\\verb`` 屏蔽成空格。

目的不是做完整 TeX 词法分析，而是让“按正则找命令”的调用方（preflight、
投稿兼容性扫描）不会把注释或 verbatim 里的 ``\\input`` / ``\\usepackage``
当成真实命令。返回值与输入**等长**，换行保持不变，因此调用方仍可直接用
命中的下标切片原文。
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
        "comment*",
        "filecontents",
        "filecontents*",
    }
)

_BEGIN_RE = re.compile(r"\\begin\s*\{([^{}]*)\}")
_VERB_RE = re.compile(r"\\(?:verb|Verb)(?:\*)?(?![A-Za-z@])")
#: 参数按“字面字符”读取的 URL 系命令：``%`` 在这里是正文，不起注释作用。
#: 只覆盖第一个花括号参数（``\href`` 的第二个参数仍是普通正文）。
_URL_ARG_RE = re.compile(r"\\(?:url|nolinkurl|path|href)(?![A-Za-z@])\s*")
#: ``\lstinline`` 的参数同样是代码原文，``%`` 在里面是代码字符而不是注释。
_LSTINLINE_RE = re.compile(r"\\lstinline(?![A-Za-z@])")


def _blank(chars: list[str], start: int, end: int) -> None:
    """把 ``[start, end)`` 变成空格，保留换行以维持行号与切片位置。"""
    for index in range(start, min(end, len(chars))):
        if chars[index] not in "\r\n":
            chars[index] = " "


def _brace_end(text: str, open_index: int) -> int:
    """返回与 ``open_index`` 处 ``{`` 配对的 ``}`` 下标；未闭合返回 ``-1``。"""
    depth = 0
    index = open_index
    length = len(text)
    while index < length:
        char = text[index]
        if char == "\\":
            index += 2
            continue
        if char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                return index
        index += 1
    return -1


def mask_tex_noncode(text: str) -> str:
    """返回与 ``text`` 等长的副本：注释、verbatim 环境、``\\verb`` 内容为空格。

    * ``%`` 注释从百分号屏蔽到行尾；``\\%`` 是转义百分号，不当作注释。
    * ``\\begin{verbatim}`` 等环境整段屏蔽（含 ``\\begin``/``\\end``）。
    * ``\\verb|...|`` / ``\\Verb|...|`` 屏蔽到同一行内的配对分隔符。
    * ``\\url``/``\\nolinkurl``/``\\path``/``\\href`` 的首个参数按字面读取，
      其中的 ``%`` 不当作注释（``\\href`` 的第二个参数仍按普通正文解析）。
    * ``\\lstinline``（任意分隔符或花括号形式）的代码参数同样按字面读取。

    ``\\iffalse … \\fi`` 不做特殊识别：条件块要靠配对深度判定，注释或宏式
    条件（``\\ifthenelse{}`` 等）一掺进来就极易算错，漏屏蔽会静默放过整篇正文。
    块内字符按正文统计（可能多报几个），换取永不少报。
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

            # ``\lstinline[opts]!code!`` / ``\lstinline{code}`` 与 ``\verb`` 同类。
            lstinline = _LSTINLINE_RE.match(text, index)
            if lstinline is not None:
                cursor = lstinline.end()
                if cursor < length and text[cursor] == "[":
                    line_end = text.find("\n", cursor)
                    line_end = length if line_end < 0 else line_end
                    bracket = text.find("]", cursor + 1, line_end)
                    if bracket >= 0:
                        cursor = bracket + 1
                        while cursor < line_end and text[cursor].isspace():
                            cursor += 1
                if cursor < length and text[cursor] == "{":
                    closing = _brace_end(text, cursor)
                    end = closing + 1 if closing >= 0 else length
                elif cursor < length and not text[cursor].isspace():
                    delimiter = text[cursor]
                    line_end = text.find("\n", cursor)
                    line_end = length if line_end < 0 else line_end
                    closing = text.find(delimiter, cursor + 1, line_end)
                    end = closing + 1 if closing >= 0 else line_end
                else:
                    # 后面没有代码参数（无分隔符），只跳过命令名，别把正文当作代码。
                    index = cursor
                    continue
                _blank(chars, index, end)
                index = end
                continue

            # ``\url{...}`` 一族按字面读取参数，里面的 ``%`` 不是注释起点。
            url = _URL_ARG_RE.match(text, index)
            if url is not None:
                cursor = url.end()
                if cursor < length and text[cursor] == "[":
                    line_end = text.find("\n", cursor)
                    line_end = length if line_end < 0 else line_end
                    bracket = text.find("]", cursor + 1, line_end)
                    if bracket >= 0:
                        cursor = bracket + 1
                        while cursor < line_end and text[cursor].isspace():
                            cursor += 1
                if cursor < length and text[cursor] == "{":
                    closing = _brace_end(text, cursor)
                    if closing >= 0:
                        _blank(chars, cursor + 1, closing)
                        index = closing + 1
                    else:
                        line_end = text.find("\n", cursor)
                        line_end = length if line_end < 0 else line_end
                        _blank(chars, cursor, line_end)
                        index = line_end
                    continue
                index = url.end()
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
