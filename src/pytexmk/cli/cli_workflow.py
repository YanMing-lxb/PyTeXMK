"""PyTeXMK CLI 分派工作流：入口串接各阶段，具体实现见同目录 cli_* 模块。"""

import argparse

from ..config import ConfigParser
from ..language import set_language
from ..logger_config import setup_logger
from ..ui_theme import console
from ..version import __version__
from . import cli_compile, cli_context, cli_early, cli_latexdiff

_ = set_language("cli_workflow")


def run_workflow(args: argparse.Namespace) -> None:
    """PyTeXMK 主流程：早退出子命令 → 上下文解析 → 编译分派 → 收尾。"""
    console.print(
        _("PyTeXMK 版本: %(version)s")
        % {"version": f"[i bold green]{__version__}[/i bold green]"}
    )
    console.print(_("[bold green]PyTeXMK 开始运行...[/bold green]"))

    logger = setup_logger(bool(args.verbose))
    cp = ConfigParser()

    # 早退出子命令：-r / -i / -iu / -ls，命中后直接结束进程
    cli_early.handle(args, cp, logger)

    # 上下文解析与「配置文件」层参数合并（-pv FILE 会在这一步预览后退出）
    state = cli_context.build(args, cp, logger)

    # 决定本次目标（主文件名 或 LaTeXDiff 新旧文件对），再用魔法注释做最后一层覆盖
    cli_context.resolve_target(args, state)
    cli_context.apply_magic_comments(state)

    # -ca / -Ca：清理所有辅助文件后收工
    if cli_compile.handle_clean_any(args, state):
        return

    if state.is_latexdiff:
        cli_latexdiff.run(args, state)
    elif state.project_name:
        cli_compile.run(args, state)

    cli_compile.finalize(state)
