"""项目上下文与解析：承载工作根目录、配置来源与子项目映射，路径一律 pathlib。"""

from dataclasses import dataclass, field
from pathlib import Path

from pytexmk.language import set_language

_ = set_language("context")


class ProjectNotFoundError(Exception):
    """子项目名称未命中根配置 [subprojects] 时抛出。

    参数:
        name: 用户输入的错误别名
        available: 当前 [subprojects] 中已存在的可用别名列表（大写不敏感匹配）
    """

    def __init__(self, name: str, available: list[str] | None = None):
        self.name = name
        self.available = available or []
        suggestions = ""
        if self.available:
            suggestions = _("，可用别名: %(s)s") % {"s": ", ".join(sorted(self.available))}
        super().__init__(_("未找到子项目: %(name)s") % {"name": name} + suggestions)


@dataclass
class ProjectContext:
    """一次 PyTeXMK 运行所需的统一上下文。

    字段说明：
        root       : 项目根目录（即用户终端当前目录），用 resolve() 归一化。
        work_root  : 实际工作根目录。普通编译 == root；`-s` 子项目编译时为该子项目目录。
        config     : 纯读取合并后的原始配置 dict（优先级 默认<-用户rc<-项目rc）。
        subprojects: 子项目别名 -> 绝对 Path 映射（来自根 [subprojects]）。
        subproject : 本次 `-s` 选中的别名，None 表示桌面/根项目编译。
    """

    root: Path
    work_root: Path
    config: dict = field(default_factory=dict)
    subprojects: dict[str, Path] = field(default_factory=dict)
    subproject: str | None = None


def _extract_path(value) -> str:
    """解析子项目条目的路径：支持 `name = "path"` 与 `[subprojects.x] path = "..."`。"""
    if isinstance(value, str):
        return value
    if isinstance(value, dict):
        for key in ("path", "root", "dir"):
            v = value.get(key)
            if isinstance(v, str) and v:
                return v
    return ""


class ContextResolver:
    """根据命令行参数与根配置解析出本次运行的 ProjectContext。"""

    def __init__(self, config_loader):
        self.loader = config_loader

    def build_subprojects(self, config, root: Path) -> dict[str, Path]:
        """从根配置 [subprojects] 构造 别名->绝对路径 映射；Windows 去重大写不敏感。"""
        subprojects: dict[str, Path] = {}
        raw = config.get("subprojects") or {}
        if not isinstance(raw, dict):
            return subprojects
        for name, value in raw.items():
            rel = _extract_path(value)
            if not rel:
                continue
            # 仅允许相对路径；绝对路径或越界相对路径一律忽略
            candidate = (root / rel).resolve()
            try:
                candidate.relative_to(root.resolve())
            except ValueError:
                continue
            subprojects[str(name)] = candidate
        return subprojects

    def resolve(self, args, cwd: Path | None = None) -> ProjectContext:
        """解析运行上下文，未命中 `-s` 别名时抛出 ProjectNotFoundError。"""
        root = (Path.cwd() if cwd is None else cwd).resolve()
        config = self.loader.load_config(root)
        subprojects = self.build_subprojects(config, root)

        subproject: str | None = None
        work_root = root
        if getattr(args, "subproject", None):
            name = args.subproject
            target = subprojects.get(name)
            if target is None:
                raise ProjectNotFoundError(name, list(subprojects.keys()))
            subproject = name
            work_root = target

        return ProjectContext(
            root=root,
            work_root=work_root,
            config=config,
            subprojects=subprojects,
            subproject=subproject,
        )
