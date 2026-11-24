"""配置查看 / 编译决策解释（U4）。

两个子命令分工：

* ``--show-config``：原样打印「默认 ← 用户 rc ← 项目 rc」合并后的完整配置；
* ``--explain``：解释“这次编译到底会用哪套参数”，不打印整份配置。
"""

from pathlib import Path
from typing import Any

from ..compile import effective_interaction
from ..config import DEFAULT_CONFIG
from ..language import set_language
from ..ui_theme import console

_ = set_language("cli_workflow")


def _walk(
    default: Any, current: Any, path: str, errors: list[str], *, strict: bool = True
) -> None:
    """递归对比默认配置，收集未知键与类型错误。"""
    if isinstance(default, dict) and isinstance(current, dict):
        for key, value in current.items():
            if key not in default:
                if strict:
                    errors.append(f"{path}.{key}: 未知配置项")
                continue
            _walk(
                default[key],
                value,
                f"{path}.{key}" if path else key,
                errors,
                strict=strict,
            )
        return
    if isinstance(default, bool) and not isinstance(current, bool):
        errors.append(f"{path}: 期望布尔值，实际 {type(current).__name__}")
    elif isinstance(default, dict) and not isinstance(current, dict):
        errors.append(f"{path}: 期望配置段（表），实际 {type(current).__name__}")
    elif (
        not isinstance(default, bool)
        and isinstance(default, (int, float))
        and (isinstance(current, bool) or not isinstance(current, (int, float)))
    ):
        # bool 是 int 的子类：默认值是数字时，`max_extra_compilations = true`
        # 这种"布尔冒充数字"必须报错，否则 int(True)=1 会静默改小轮次上限。
        errors.append(f"{path}: 期望数字，实际 {type(current).__name__}")
    elif isinstance(default, str) and not isinstance(current, str):
        errors.append(f"{path}: 期望字符串，实际 {type(current).__name__}")
    elif isinstance(default, list) and not isinstance(current, list):
        errors.append(f"{path}: 期望列表，实际 {type(current).__name__}")


def show_config(cp, project_root: Path = Path()) -> dict:
    """打印合并后的完整配置与来源路径，并返回该配置。"""
    config = cp.load_config(project_root)
    console.print("[bold]" + _("配置来源") + "[/bold]")
    if cp.user_config_path:
        console.print(f"  用户: {cp.user_config_path}")
    console.print(f"  项目: {(project_root / '.pytexmkrc').resolve()}")
    console.print("[bold]" + _("合并后的配置") + "[/bold]")
    import json

    console.print(json.dumps(config, ensure_ascii=False, indent=2, sort_keys=True))
    return config


def _semantic(config: dict, errors: list[str]) -> None:
    """检查字符串枚举类配置的合法取值。

    配置段本身类型错误时 ``_walk`` 已经记过错误；这里只跳过语义检查，
    不能让 ``build.get``/``index_cfg.get`` 抛 AttributeError 把校验流程打断。
    """
    build = config.get("build")
    if isinstance(build, dict):
        for key, allowed in (
            ("native", {"auto", "true", "false", "1", "0", "yes", "no", "on", "off"}),
            ("shell_escape", {"auto", "true", "false", "1", "0", "yes", "no", "on", "off"}),
            ("interaction", {"", "batchmode", "nonstopmode", "scrollmode", "errorstopmode"}),
        ):
            value = str(build.get(key, "")).lower()
            if value not in allowed:
                errors.append(f"build.{key}: 不支持取值 {build.get(key)!r}，可选 {sorted(allowed)}")
        extra = build.get("extra_args", [])
        if isinstance(extra, list) and any(not isinstance(item, str) for item in extra):
            errors.append("build.extra_args: 列表元素必须全部是字符串")
    # 段类型错误已由 _walk 报告；这里不再拿空字典补跑语义检查，避免同一个
    # 问题衍生出三条“不支持取值 None”的噪声。
    index_cfg = config.get("index")
    if isinstance(index_cfg, dict):
        tool = str(index_cfg.get("glossaries_tool", "makeindex")).lower()
        if tool not in {"makeindex", "makeglossaries"}:
            errors.append(
                f"index.glossaries_tool: 不支持取值 {index_cfg.get('glossaries_tool')!r}，"
                "可选 ['makeindex', 'makeglossaries']"
            )
    # [subprojects] 是动态清单，但每个值的类型仍是契约：字符串路径，或带
    # path/root/dir 的表；写成数字/布尔会在 -s 解析时静默失效，必须在这里拒绝。
    subprojects = config.get("subprojects")
    if subprojects is not None and not isinstance(subprojects, dict):
        errors.append(
            f"subprojects: 期望配置段（表），实际 {type(subprojects).__name__}"
        )
    elif isinstance(subprojects, dict):
        for name, value in subprojects.items():
            if isinstance(value, str):
                if not value.strip():
                    errors.append(f"subprojects.{name}: 路径不能为空")
                continue
            if isinstance(value, dict) and any(
                isinstance(value.get(key), str) and value.get(key)
                for key in ("path", "root", "dir")
            ):
                continue
            errors.append(
                f"subprojects.{name}: 期望相对路径字符串或带 path 的表，实际 {type(value).__name__}"
            )


def config_errors(
    config: dict, load_errors: dict | None = None, *, strict: bool = True
) -> list[str]:
    """返回配置错误清单；不打印、不重载配置。

    编译路径用 ``strict=False`` 只检查会让运行期崩溃的结构/类型问题，未知键
    （例如旧版遗留的 ``[main]`` 段）不阻断编译。
    """
    errors: list[str] = []
    for path, reason in (load_errors or {}).items():
        errors.append(f"{path}: 配置无法解析（{reason}）")
    # [subprojects] 是动态清单（由 -ls / 手写维护），不属于固定配置 schema
    stable = {key: value for key, value in config.items() if key != "subprojects"}
    _walk(DEFAULT_CONFIG, stable, "", errors, strict=strict)
    _semantic(config, errors)
    return errors


def print_config_errors(errors: list[str], title: str | None = None) -> None:
    """按统一格式打印配置错误。"""
    console.print("[bold red]" + (title or _("配置校验失败")) + "[/bold red]")
    for error in errors:
        console.print(f"  [red]{error}[/red]")


def explain(state) -> None:
    """解释本次编译的有效参数，不产生任何编译动作。"""
    from rich.table import Table

    output_name = state.output_name or state.project_name
    pdf_path = (Path(state.outdir) / f"{output_name}.pdf").resolve()

    table = Table(title=_("本次编译的有效配置"))
    table.add_column(_("项目"), style="cyan")
    table.add_column(_("取值"))
    rows = [
        (_("主文件"), f"{state.project_name}.tex"),
        (_("输出文件名"), output_name),
        (_("编译器"), state.compiled_program),
        (_("构建模式"), _("原生目录构建") if state.native_build else _("两段式搬运")),
        (_("输出目录"), state.outdir),
        (_("辅助目录"), state.auxdir),
        (_("shell-escape"), state.shell_escape),
        (_("SyncTeX"), _("开启") if state.synctex else _("关闭")),
        (_("交互模式"), effective_interaction(state.interaction)),
        (_("额外参数"), " ".join(state.extra_args) or "-"),
        (_("最大编译轮次"), str(state.max_extra_compilations)),
        (_("编译前检查"), _("开启") if state.preflight_enabled else _("关闭")),
        (_("投稿目录"), state.submission_output_dir),
        (_("草稿模式"), _("是") if getattr(state.args, "draft", False) else _("否")),
        (_("编译后预览"), _("是") if state.preview_after_compile else _("否")),
        (_("安静模式"), _("是") if not state.non_quiet else _("否")),
    ]
    for name, value in rows:
        table.add_row(name, str(value))
    console.print(table)
    # 绝对路径单独一行并禁止折行：放进表格会被 Rich 按终端宽度截断，
    # 集成方/编辑器复制时拿到的是半条路径。
    console.print(_("最终 PDF: ") + str(pdf_path), soft_wrap=True)
    console.print(
        "[dim]"
        + _("参数优先级：命令行 > 项目 .pytexmkrc > 用户 ~/.pytexmkrc > 内置默认；主文件魔法注释仅覆盖引擎等少数项")        + "[/dim]"
    )
