"""PyTeXMK 生命周期管理：统一退出流程。"""
import sys

from pytexmk.language import set_language
from pytexmk.ui_theme import console

_ = set_language("lifecycle")

# 退出码约定（遵循 Unix 惯例：0=成功，非 0=错误）
EXIT_OK = 0                          # 成功完成（默认）
EXIT_ERROR = 1                       # 一般性错误：参数/路径/主文件等
EXIT_PROJECT_NOT_FOUND = 3           # -s 子项目别名未命中
EXIT_CONFIG_ERROR = 4                # 配置文件解析失败
EXIT_COMPILE_FAILED = 5              # LaTeX/Bib/Index 子进程编译失败

# 退出码 → 简短原因说明（国际化，仅当 exit_code != EXIT_OK 时打印）
_EXIT_REASONS: dict[int, str] = {
    EXIT_ERROR: _("PyTeXMK 遇到错误，已退出"),
    EXIT_PROJECT_NOT_FOUND: _("未找到指定的子项目，已退出"),
    EXIT_CONFIG_ERROR: _("配置文件错误，已退出"),
    EXIT_COMPILE_FAILED: _("编译失败，已退出"),
}


def exit_pytexmk(exit_code: int = EXIT_OK) -> None:
    """以指定退出码终止 PyTeXMK 进程。

    退出码 != 0 时打印一行红色原因说明；exit_code == 0（正常完成）时静默退出。
    """
    if exit_code != EXIT_OK:
        reason = _EXIT_REASONS.get(exit_code, _("PyTeXMK 已异常退出"))
        try:
            console.print(f"[bold red]{reason}[/bold red]")
        except Exception:  # noqa: BLE001
            print(reason, file=sys.stderr)
    sys.exit(exit_code)
