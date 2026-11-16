"""`pytexmk --doctor`：本机 TeX 工具链与配置体检（U4）。

只做“能不能跑起来”的检查，不尝试编译，避免在用户机器上留下任何产物。
退出码：0 全部通过（允许可选组件缺失）；1 关键组件缺失。
"""

from __future__ import annotations

import shutil
from pathlib import Path

from ..config import ConfigParser
from ..language import set_language
from ..lifecycle import EXIT_ERROR, exit_pytexmk
from ..ui_theme import console

_ = set_language("cli_workflow")

#: (命令, 说明, 是否关键)
_CHECKS = (
    ("xelatex", "XeLaTeX（默认引擎）", True),
    ("pdflatex", "pdfLaTeX（投稿兼容检查）", False),
    ("lualatex", "LuaLaTeX", False),
    ("biber", "biber 参考文献", False),
    ("bibtex", "bibtex 参考文献", False),
    ("makeindex", "makeindex 索引", False),
    ("xindy", "xindy 索引（多语言排序）", False),
    ("latexdiff", "LaTeXDiff 差异对比", False),
    ("qpdf", "qpdf（PDF 修复优先路径）", False),
)


def run(args, cp: ConfigParser, logger) -> None:
    """打印体检表；有关键组件缺失时以退出码 1 结束。"""
    console.print("[bold]" + _("PyTeXMK 环境体检") + "[/bold]")
    failures = 0
    for command, label, critical in _CHECKS:
        path = shutil.which(command)
        if path:
            console.print(f"  [green]✓[/green] {label:<28} [dim]{path}[/dim]")
        else:
            marker = "red ✗" if critical else "yellow !"
            console.print(f"  [{marker}] {label:<28} [dim]{_('未找到')}[/dim]")
            if critical:
                failures += 1

    _check_pytexlogs()
    _check_config(cp, logger)
    _check_state()

    if failures:
        console.print(
            "[bold red]"
            + _("缺少关键引擎，请先安装 TeX 发行版（MiKTeX / TeX Live）")
            + "[/bold red]"
        )
        exit_pytexmk(EXIT_ERROR)
    console.print("[bold green]" + _("体检通过：可以直接编译") + "[/bold green]")


def _check_pytexlogs() -> None:
    """检查 PyTeXLogs 版本（0.5.0 起依赖保证含可执行建议）。"""
    try:
        import pytexlogs
    except ImportError:
        console.print("  [yellow]![/yellow] PyTeXLogs                [dim]未安装（诊断功能不可用）[/dim]")
        return
    version = getattr(pytexlogs, "__version__", "unknown")
    console.print(f"  [green]✓[/green] PyTeXLogs {version:<17} [dim]含可执行建议[/dim]")


def _check_config(cp: ConfigParser, logger) -> None:
    """检查项目/用户配置文件能否解析。"""
    for label, path in (("项目配置", Path.cwd() / ".pytexmkrc"), ("用户配置", Path.home() / ".pytexmkrc")):
        if not path.exists():
            console.print(f"  [dim]-[/dim] {label:<28} [dim]{_('未配置（使用默认值）')}[/dim]")
            continue
        try:
            cp.load_config(path.parent)
        except Exception as exc:  # noqa: BLE001
            logger.debug("配置解析失败", exc_info=True)
            console.print(f"  [red]✗[/red] {label:<28} [red]{exc}[/red]")
        else:
            console.print(f"  [green]✓[/green] {label:<28} [dim]{path}[/dim]")


def _check_state() -> None:
    """检查状态文件能否读取（损坏时只提示，不影响编译）。"""
    candidates = [Path.cwd() / ".pytexmk_refcache.json", Path.cwd() / "Auxiliary" / ".pytexmk_refcache.json"]
    for path in candidates:
        if not path.exists():
            continue
        try:
            import json

            json.loads(path.read_text(encoding="utf-8"))
        except Exception:  # noqa: BLE001
            console.print(f"  [yellow]![/yellow] {'状态文件':<26} [yellow]{path} 无法解析（会自动重建）[/yellow]")
        else:
            console.print(f"  [green]✓[/green] {'状态文件':<26} [dim]{path}[/dim]")
        return
