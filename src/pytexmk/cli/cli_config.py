"""配置查看 / 校验 / 编译决策解释（U4）。

三个子命令分工：

* ``--show-config``：原样打印「默认 ← 用户 rc ← 项目 rc」合并后的完整配置；
* ``--validate-config``：对照内置默认配置检查未知键与类型错误，CI 可用来挡住坏配置；
* ``--explain``：解释“这次编译到底会用哪套参数”，不打印整份配置。
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from ..config import DEFAULT_CONFIG
from ..language import set_language
from ..ui_theme import console

_ = set_language("cli_workflow")


def _walk(default: Any, current: Any, path: str, errors: list[str]) -> None:
    """递归对比默认配置，收集未知键与类型错误。"""
    if isinstance(default, dict) and isinstance(current, dict):
        for key, value in current.items():
            if key not in default:
                errors.append(f"{path}.{key}: 未知配置项")
                continue
            _walk(default[key], value, f"{path}.{key}" if path else key, errors)
        return
    if isinstance(default, bool) and not isinstance(current, bool):
        errors.append(f"{path}: 期望布尔值，实际 {type(current).__name__}")
    elif isinstance(default, dict) and not isinstance(current, dict):
        errors.append(f"{path}: 期望配置段（表），实际 {type(current).__name__}")
    elif isinstance(default, (int, float)) and not isinstance(current, (int, float)):
        errors.append(f"{path}: 期望数字，实际 {type(current).__name__}")
    elif isinstance(default, str) and not isinstance(current, str):
        errors.append(f"{path}: 期望字符串，实际 {type(current).__name__}")
    elif isinstance(default, list) and not isinstance(current, list):
        errors.append(f"{path}: 期望列表，实际 {type(current).__name__}")


def show_config(cp, project_root: Path = Path(".")) -> None:
    """打印合并后的完整配置与来源路径。"""
    config = cp.load_config(project_root)
    console.print("[bold]" + _("配置来源") + "[/bold]")
    if cp.user_config_path:
        console.print(f"  用户: {cp.user_config_path}")
    console.print(f"  项目: {(project_root / '.pytexmkrc').resolve()}")
    console.print("[bold]" + _("合并后的配置") + "[/bold]")
    import json

    console.print(json.dumps(config, ensure_ascii=False, indent=2, sort_keys=True))


def _semantic(config: dict, errors: list[str]) -> None:
    """检查字符串枚举类配置的合法取值。"""
    build = config.get("build") or {}
    for key, allowed in (
        ("native", {"auto", "true", "false", "1", "0", "yes", "no", "on", "off"}),
        ("shell_escape", {"auto", "true", "false", "1", "0", "yes", "no", "on", "off"}),
        ("interaction", {"", "batchmode", "nonstopmode", "errorstopmode"}),
    ):
        value = str(build.get(key, "")).lower()
        if value not in allowed:
            errors.append(f"build.{key}: 不支持取值 {build.get(key)!r}，可选 {sorted(allowed)}")
    index_cfg = config.get("index") or {}
    tool = str(index_cfg.get("glossaries_tool", "makeindex")).lower()
    if tool not in {"makeindex", "makeglossaries"}:
        errors.append(
            f"index.glossaries_tool: 不支持取值 {index_cfg.get('glossaries_tool')!r}，"
            "可选 ['makeindex', 'makeglossaries']"
        )


def validate_config(cp, project_root: Path = Path(".")) -> bool:
    """返回 True 表示配置合法；错误逐条打印。"""
    config = cp.load_config(project_root)
    errors: list[str] = []
    # [subprojects] 是动态清单（由 -ls / 手写维护），不属于固定配置 schema
    stable = {key: value for key, value in config.items() if key != "subprojects"}
    _walk(DEFAULT_CONFIG, stable, "", errors)
    _semantic(stable, errors)
    if not errors:
        console.print("[green]" + _("配置校验通过") + "[/green]")
        return True
    console.print("[bold red]" + _("配置校验失败") + "[/bold red]")
    for error in errors:
        console.print(f"  [red]{error}[/red]")
    return False


def explain(state) -> None:
    """解释本次编译的有效参数，不产生任何编译动作。"""
    from rich.table import Table

    table = Table(title=_("本次编译的有效配置"))
    table.add_column(_("项目"), style="cyan")
    table.add_column(_("取值"))
    rows = [
        (_("主文件"), f"{state.project_name}.tex"),
        (_("输出文件名"), state.output_name or state.project_name),
        (_("编译器"), state.compiled_program),
        (_("构建模式"), _("原生目录构建") if state.native_build else _("两段式搬运")),
        (_("输出目录"), state.outdir),
        (_("辅助目录"), state.auxdir),
        (_("shell-escape"), state.shell_escape),
        (_("交互模式"), state.interaction or "nonstopmode"),
        (_("额外参数"), " ".join(state.extra_args) or "-"),
        (_("最大编译轮次"), str(state.max_extra_compilations)),
        (_("草稿模式"), _("是") if getattr(state.args, "draft", False) else _("否")),
        (_("编译后预览"), _("是") if state.preview_after_compile else _("否")),
        (_("安静模式"), _("是") if not state.non_quiet else _("否")),
    ]
    for name, value in rows:
        table.add_row(name, str(value))
    console.print(table)
    console.print(
        "[dim]"
        + _("参数优先级：命令行 > 项目 .pytexmkrc > 用户 ~/.pytexmkrc > 内置默认；主文件魔法注释仅覆盖引擎等少数项")
        + "[/dim]"
    )
