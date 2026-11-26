"""PyTeXMK CLI 早退出子命令：配置初始化 / 子项目清单 / 配置查看。"""

from pathlib import Path

from ..config import ConfigParser
from ..language import set_language
from ..lifecycle import EXIT_CONFIG_ERROR, exit_pytexmk
from ..subproject_scanner import (
    discover_subprojects,
    print_subproject_table,
    write_subprojects_to_rc,
)
from ..ui_theme import console

_ = set_language("cli_workflow")


def handle(args, cp: ConfigParser, logger) -> None:
    """处理 -i / -iu / -ls / --show-config 早退出子命令。

    命中任意一个子命令都会在执行完后直接结束进程；全部未命中时直接返回，
    由调用方继续编译流程，普通运行不会自动创建用户 / 项目配置文件。
    """
    logger.info("-" * 70)
    if getattr(args, "show_config", False):
        from .cli_config import show_config

        show_config(cp)
        if cp.load_errors:
            exit_pytexmk(EXIT_CONFIG_ERROR)
        exit_pytexmk()
    if args.init:
        if not cp.init_project_config():
            exit_pytexmk(EXIT_CONFIG_ERROR)
        console.print(
            _("[bold green]已生成根项目配置文件 [/bold green]")
            + str(Path.cwd() / ".pytexmkrc")
        )
        exit_pytexmk()
    if args.init_user:
        if not cp.init_user_config():
            exit_pytexmk(EXIT_CONFIG_ERROR)
        console.print(
            _("[bold green]已生成用户配置文件 ~/.pytexmkrc[/bold green]")
        )
        exit_pytexmk()
    if args.list_subprojects:
        _list_subprojects(cp)


def _list_subprojects(cp: ConfigParser) -> None:
    """发现子项目，输出清单并写回根配置的 ``[subprojects]`` 段。

    写回会保留手写别名、段内注释与原有条目次序，避免一次同步改变 ``-ap``
    的编译顺序。配置缺失时先用内置模板创建根配置，再写入清单；配置解析
    失败以配置错误码退出，绝不用默认配置覆盖用户文件。
    """
    root_path = Path.cwd()
    entries = discover_subprojects(root_path, cp.load_config(root_path))
    rc_path = root_path / ".pytexmkrc"
    print_subproject_table(entries)

    if getattr(cp, "load_errors", None):
        exit_pytexmk(EXIT_CONFIG_ERROR)
        return

    if not rc_path.exists():
        if not cp.init_project_config():
            console.print(_("[bold red]无法创建根配置文件 .pytexmkrc[/bold red]"))
            exit_pytexmk(EXIT_CONFIG_ERROR)
            return
        console.print(
            _("[bold green]已生成根项目配置文件 [/bold green]") + str(rc_path)
        )

    before = rc_path.read_text(encoding="utf-8")
    if write_subprojects_to_rc(rc_path, entries):
        after = rc_path.read_text(encoding="utf-8")
        if before == after:
            console.print(
                _("[bold green].pytexmkrc 中的 \\[subprojects] 段已是当前清单，未改动[/bold green]")
            )
        else:
            console.print(
                _("[bold green]已更新 .pytexmkrc 中的 \\[subprojects] 段[/bold green]")
            )
    else:
        console.print(
            _("[yellow]无法写入根 .pytexmkrc ，子项目清单仅在本次运行中有效[/yellow]")
        )
        exit_pytexmk(EXIT_CONFIG_ERROR)
        return
    exit_pytexmk()
