"""PyTeXMK CLI 分派工作流：入口串接各阶段，具体实现见同目录 cli_* 模块。"""

import argparse
from pathlib import Path

from ..config import ConfigParser
from ..language import set_language
from ..logger_config import setup_logger
from ..ui_theme import console
from ..version import __version__
from . import cli_compile, cli_context, cli_early, cli_latexdiff

_ = set_language("cli_workflow")


def run_workflow(args: argparse.Namespace) -> None:
    """PyTeXMK 主流程：早退出子命令 → 上下文解析 → 编译分派 → 收尾。"""
    if getattr(args, "completion", None):
        # 补全脚本必须是纯文本：必须在版本横幅之前输出，不能混入 rich 样式
        from .cli_completion import completion_text

        print(completion_text(args.completion))
        return

    console.print(
        _("PyTeXMK 版本: %(version)s")
        % {"version": f"[i bold green]{__version__}[/i bold green]"}
    )
    console.print(_("[bold green]PyTeXMK 开始运行...[/bold green]"))

    logger = setup_logger(bool(args.verbose))
    cp = ConfigParser()

    # 早退出子命令：--doctor / -r / -i / -iu / -ls，命中后直接结束进程
    cli_early.handle(args, cp, logger)

    # -A：按根配置 [subprojects] 逐个编译，最后汇总失败项
    if getattr(args, "all_subprojects", False):
        _run_all_subprojects(args, cp, logger)
        return

    # --watch：先完整跑一次，再轮询源码变化；退出条件只有 Ctrl+C
    if getattr(args, "watch", False):
        from .cli_watch import watch_loop

        watch_loop(args)
        return

    # 上下文解析与「配置文件」层参数合并（-pv FILE 会在这一步预览后退出）
    state = cli_context.build(args, cp, logger)

    # 决定本次目标（主文件名 或 LaTeXDiff 新旧文件对），再用魔法注释做最后一层覆盖
    cli_context.resolve_target(args, state)
    cli_context.apply_magic_comments(state)

    # --explain 只读配置，不应被 -c 等清理动作抢先执行
    if getattr(args, "explain", False):
        from .cli_config import explain

        explain(state)
        return

    # -ca / -Ca：清理所有辅助文件后收工
    if cli_compile.handle_clean_any(args, state):
        return

    if state.is_latexdiff:
        cli_latexdiff.run(args, state)
    elif state.project_name:
        cli_compile.run(args, state)

    cli_compile.finalize(state)


def _run_all_subprojects(args, cp, logger) -> None:  # noqa: ANN001
    """``-A/--all-subprojects``：逐个编译子项目，任一失败不中断其余项目。"""
    import copy
    import os

    from rich.table import Table

    from ..lifecycle import EXIT_COMPILE_FAILED, EXIT_ERROR, exit_pytexmk

    config = cp.load_config(Path("."))
    subprojects = config.get("subprojects") or {}
    if not isinstance(subprojects, dict) or not subprojects:
        logger.error(_("根配置里没有 [subprojects] 清单，无法批量编译；可先运行 pytexmk -ls"))
        exit_pytexmk(EXIT_ERROR)

    original_cwd = Path.cwd()
    results: list[tuple[str, int, str]] = []
    for name in sorted(subprojects):
        sub_args = copy.copy(args)
        sub_args.subproject = name
        sub_args.all_subprojects = False
        sub_args.document = None
        sub_args.LaTeXDiff = None
        sub_args.LaTeXDiff_compile = None
        os.chdir(original_cwd)
        console.print(f"[bold cyan]▶ 子项目: {name}[/bold cyan]")
        try:
            run_workflow(sub_args)
            results.append((name, 0, _("成功")))
        except SystemExit as exc:
            code = int(exc.code or 0)
            results.append((name, code, _("失败（退出码 %(c)s）") % {"c": code}))
        except Exception as exc:  # noqa: BLE001 - 单个子项目异常不能拖垮批量
            logger.exception("子项目 %s 编译异常", name)
            results.append((name, EXIT_COMPILE_FAILED, str(exc)))

    os.chdir(original_cwd)

    table = Table(title=_("批量编译汇总"))
    table.add_column(_("子项目"), style="cyan")
    table.add_column(_("结果"))
    table.add_column(_("退出码"))
    for name, code, status in results:
        style = "green" if code == 0 else "red"
        table.add_row(name, f"[{style}]{status}[/{style}]", str(code))
    console.print(table)

    failed = [name for name, code, _ in results if code != 0]
    if failed:
        console.print("[bold red]" + _("失败子项目: ") + ", ".join(failed) + "[/bold red]")
        exit_pytexmk(EXIT_COMPILE_FAILED)
    exit_pytexmk()
