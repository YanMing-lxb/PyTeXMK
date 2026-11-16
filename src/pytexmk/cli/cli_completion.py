"""生成 PyTeXMK 的 shell 补全脚本（U7 剩余项）。

补全脚本从 argparse 解析器实时提取选项，避免新增参数时忘记同步补全列表。
只做“选项名补全”，不猜测主文件名 / 子项目名，保持脚本无副作用。
"""

from __future__ import annotations

import re

from .cli_args import build_parser


def _option_map() -> list[tuple[str, str]]:
    """返回 ``(option, help)``；同一 action 的多个别名各自保留。"""
    parser = build_parser()
    result: list[tuple[str, str]] = []
    for action in parser._actions:
        if not action.option_strings:
            continue
        help_text = re.sub(r"\[[^\]]*\]", "", action.help or "").replace('"', "'")
        help_text = " ".join(help_text.split())
        for option in action.option_strings:
            result.append((option, help_text))
    return sorted(set(result), key=lambda item: item[0])


def _bash() -> str:
    options = " ".join(option for option, _help in _option_map() if option.startswith("-"))
    return f"""# PyTeXMK bash completion
_pytexmk_complete() {{
    local cur="${{COMP_WORDS[COMP_CWORD]}}"
    local opts="{options}"
    COMPREPLY=( $(compgen -W "$opts" -- "$cur") )
}}
complete -F _pytexmk_complete pytexmk
"""


def _zsh() -> str:
    options = " ".join(option for option, _help in _option_map() if option.startswith("-"))
    return f"""#compdef pytexmk
# PyTeXMK zsh completion
_pytexmk() {{
    local -a opts
    opts=({options})
    compadd -- $opts
}}
compdef _pytexmk pytexmk
"""


def _fish() -> str:
    lines = ["# PyTeXMK fish completion"]
    for option, help_text in _option_map():
        if not option.startswith("--"):
            continue
        description = help_text.replace("'", "\\'")
        lines.append(f"complete -c pytexmk -l {option[2:]} -d '{description}'")
    return "\n".join(lines) + "\n"


def _powershell() -> str:
    options = ", ".join(f"'{option}'" for option, _help in _option_map() if option.startswith("-"))
    return f"""# PyTeXMK PowerShell completion
Register-ArgumentCompleter -Native -CommandName pytexmk -ScriptBlock {{
    param($wordToComplete, $commandAst, $cursorPosition)
    $opts = @({options})
    $opts | Where-Object {{ $_ -like "$wordToComplete*" }} | ForEach-Object {{
        [System.Management.Automation.CompletionResult]::new($_, $_, 'ParameterName', $_)
    }}
}}
"""


_GENERATORS = {
    "bash": _bash,
    "zsh": _zsh,
    "fish": _fish,
    "powershell": _powershell,
}


def completion_text(shell: str) -> str:
    """返回指定 shell 的补全脚本；未知 shell 抛 ValueError。"""
    try:
        return _GENERATORS[shell]()
    except KeyError as exc:
        raise ValueError(f"unsupported shell: {shell}") from exc
