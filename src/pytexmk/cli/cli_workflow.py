"""PyTeXMK CLI 分派工作流：入口串接各阶段，具体实现见同目录 cli_* 模块。"""

import argparse
from collections.abc import Callable
from pathlib import Path

from ..config import ConfigParser
from ..language import set_language
from ..logger_config import setup_logger
from ..ui_theme import console
from ..version import __version__
from . import cli_compile, cli_context, cli_early
from .cli_state import WorkflowState

_ = set_language("cli_workflow")


def run_workflow(
    args: argparse.Namespace,
    *,
    before_build: Callable[[WorkflowState], None] | None = None,
) -> None:
    """PyTeXMK 主流程：早退出子命令 → 上下文解析 → 编译分派 → 收尾。"""
    console.print(
        _("PyTeXMK 版本: %(version)s")
        % {"version": f"[i bold green]{__version__}[/i bold green]"}
    )
    console.print(_("[bold green]PyTeXMK 开始运行...[/bold green]"))

    logger = setup_logger(bool(args.verbose))
    cp = ConfigParser()

    # 早退出子命令：-i / -iu / -ls / --show-config，命中后直接结束进程
    cli_early.handle(args, cp, logger)

    # -ap：按根配置 [subprojects] 逐个编译，最后汇总失败项
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

    # -c/-C：只清当前主文件（-C 额外到根目录并删输出）；找不到唯一主文件时退出 1。
    # -ca/-Ca：递归全项目，不要求唯一主文件；-Ca 能确定主文件时才删输出。
    clean_requested = (
        args.clean
        or args.clean_out
        or args.clean_recursive
        or args.clean_recursive_out
    )
    if clean_requested and not getattr(args, "explain", False):
        if args.clean or args.clean_out:
            cli_context.resolve_target(args, state)
            cli_context.apply_magic_comments(state)
            cli_compile.clean_main(args, state)
        else:
            cli_context.resolve_clean_target(args, state)
            cli_context.apply_magic_comments(state)
            cli_compile.clean_recursive(args, state)
        return

    # 决定本次要编译的主文件，再用魔法注释做最后一层覆盖
    cli_context.resolve_target(args, state)
    cli_context.apply_magic_comments(state)

    # -r：只从最近一次编译日志生成报告，不进入编译流程。
    if getattr(args, "report", False):
        from .cli_report import handle as report_handle

        report_handle(state)
        return

    # -e/--explain 只读配置，不应被 -c 等清理动作抢先执行
    if getattr(args, "explain", False):
        from .cli_config import explain

        # 解释的是“真正会执行的计划”：命令行的构建覆盖项（目前只有 -pa）必须与
        # 编译共用同一套合并逻辑，否则 explain 显示的是配置默认值，实际编译又是另一套。
        cli_compile.apply_effective_build_plan(args, state)
        explain(state)
        return

    if before_build is not None:
        before_build(state)
    if state.project_name:
        cli_compile.run(args, state)

    cli_compile.finalize(state)


def _run_all_subprojects(args, cp, logger) -> None:
    """``-ap/--all-subprojects``：逐个编译子项目，任一失败不中断其余项目。"""
    import contextlib
    import copy

    from rich.table import Table

    from ..lifecycle import EXIT_COMPILE_FAILED, EXIT_ERROR, exit_pytexmk

    config = cp.load_config(Path())
    subprojects = config.get("subprojects") or {}
    if not isinstance(subprojects, dict) or not subprojects:
        logger.error(_("根配置里没有 [subprojects] 清单，无法批量编译；可先运行 pytexmk -ls"))
        exit_pytexmk(EXIT_ERROR)

    original_cwd = Path.cwd()
    results: list[tuple[str, int, str]] = []

    # 按 `.pytexmkrc` 里 [subprojects] 的书写顺序执行（README 承诺的顺序）；
    # 0.5 用 sorted() 按字母序，与文档口径不一致，且用户无法通过排序控制先编哪个。
    for name in subprojects:
        sub_args = copy.copy(args)
        sub_args.subproject = name
        sub_args.all_subprojects = False
        # 子项目绝不能继承 -ap 的 watch：否则第一个子项目进入 watch_loop
        # 后不再返回，批量编译永远走不到第二个。
        sub_args.watch = False
        sub_args.document = None
        # 每个子项目调用前都回到原始 cwd；with 块保证异常/SystemExit 时也能还原，
        # 不会把下一个子项目留在上一个项目的 Build 目录里。
        with contextlib.chdir(original_cwd):
            console.print(f"[bold cyan]▶ 子项目: {name}[/bold cyan]")
            try:
                run_workflow(sub_args)
                results.append((name, 0, _("成功")))
            except SystemExit as exc:
                code = int(exc.code or 0)
                results.append((name, code, _("失败（退出码 %(c)s）") % {"c": code}))
            except Exception as exc:
                logger.exception("子项目 %s 编译异常", name)
                results.append((name, EXIT_COMPILE_FAILED, str(exc)))

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
        # 退出码与首个失败子项目一致（旧实现固定 5，把配置错误 4 也报成编译失败）
        first_failure = next(code for _name, code, _status in results if code != 0)
        exit_pytexmk(first_failure)
    exit_pytexmk()
