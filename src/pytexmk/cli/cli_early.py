"""PyTeXMK CLI 早退出子命令：README / 配置初始化 / 子项目清单。"""

import webbrowser
from pathlib import Path

from ..config import ConfigParser
from ..language import get_locale_lang, set_language
from ..lifecycle import exit_pytexmk
from ..paths import get_app_path
from ..subproject_scanner import (
    discover_subprojects,
    print_subproject_table,
    write_subprojects_to_rc,
)
from ..ui_theme import console

_ = set_language("cli_workflow")


def handle(args, cp: ConfigParser, logger) -> None:
    """处理 -r / -i / -iu / -ls 早退出子命令。

    命中任意一个子命令都会在执行完后直接结束进程；全部未命中时直接返回，
    由调用方继续编译流程。
    """
    if args.readme:
        _open_readme(logger)
        exit_pytexmk()

    logger.info("-" * 70)
    if args.init:
        if cp.init_project_config(args.force):
            console.print(
                _("[bold green]已生成根项目配置文件 [/bold green]")
                + str(Path.cwd() / ".pytexmkrc")
            )
        exit_pytexmk()
    if args.init_user:
        if cp.init_user_config(args.force):
            console.print(
                _("[bold green]已生成用户配置文件 ~/.pytexmkrc[/bold green]")
            )
        exit_pytexmk()
    if args.list_subprojects:
        _list_subprojects(cp)


def _open_readme(logger) -> None:
    """根据系统语言打开对应的本地 README.html；出错只记录日志，不中断退出流程。

    中文系统 → README.html，其他语言 → README.en.html，目标文件不存在时 fallback 到另一个。
    """
    try:
        app_path = get_app_path()
        data_dir = app_path / "data"

        # 根据系统语言优先选择对应的 README
        locale_lang = get_locale_lang()
        if locale_lang.startswith("zh"):
            preferred = "README.html"
            fallback = "README.en.html"
        else:
            preferred = "README.en.html"
            fallback = "README.html"

        # 优先尝试首选文件，不存在则回退到另一个
        readme_path = data_dir / preferred
        if not readme_path.exists():
            fallback_path = data_dir / fallback
            if fallback_path.exists():
                readme_path = fallback_path
            else:
                logger.error(
                    _("README.html / README.en.html 文件均未找到，目录: %(args)s")
                    % {"args": str(data_dir)}
                )
                return

        console.print(_("[bold green]正在打开 README 文件...[/bold green]"))
        local_path = f"file://{readme_path.resolve().as_posix()}"
        logger.info(_("README 本地路径: %(args)s") % {"args": local_path})
        webbrowser.open(local_path)
    except Exception as e:  # noqa: BLE001
        logger.error(_("打开 README 文件出错: ") + str(e))


def _list_subprojects(cp: ConfigParser) -> None:
    """发现子项目并输出清单，同时把结果写回根 .pytexmkrc 的 [subprojects] 段。"""
    root_path = Path.cwd()
    entries = discover_subprojects(root_path, cp.load_config(root_path))
    rc_path = root_path / ".pytexmkrc"
    if rc_path.exists():
        write_subprojects_to_rc(rc_path, entries)
        console.print(
            _("[bold green]已更新 .pytexmkrc 中的 \\[subprojects\\] 段[/bold green]")
        )
    else:
        console.print(
            _("[yellow]未找到根 .pytexmkrc , 请先运行 pytexmk -i 后再运行 -ls[/yellow]")
        )
    print_subproject_table(entries)
    exit_pytexmk()
