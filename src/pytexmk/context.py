"""项目上下文与解析：承载工作根目录、配置来源与子项目映射，路径一律 pathlib。"""

from dataclasses import dataclass, field
from pathlib import Path

from pytexmk.language import set_language

_ = set_language("context")


class ProjectNotFoundError(Exception):
    """子项目名称未命中根配置 [subprojects] 时抛出。

    参数:
        name: 用户输入的错误别名
        available: 当前可用的别名 / 路径列表（大写不敏感匹配）
    """

    def __init__(self, name: str, available: list[str] | None = None):
        self.name = name
        self.available = available or []
        suggestions = ""
        if self.available:
            suggestions = _("，可用别名: %(s)s") % {"s": ", ".join(sorted(self.available))}
        super().__init__(_("未找到子项目: %(name)s") % {"name": name} + suggestions)


class AmbiguousProjectError(ProjectNotFoundError):
    """子项目简称命中了多个不同目标。"""

    def __init__(self, name: str, matches: list[str]):
        self.name = name
        self.available = matches
        Exception.__init__(
            self,
            _("子项目 %(name)s 匹配多个目标，请指定完整别名: %(matches)s")
            % {"name": name, "matches": ", ".join(sorted(matches))},
        )


@dataclass
class ProjectContext:
    """一次 PyTeXMK 运行所需的统一上下文。

    字段说明：
        root       : 项目根目录（即用户终端当前目录），用 resolve() 归一化。
        work_root  : 实际工作目录（一定是目录）。普通编译 == root；
                     `-s` 子项目编译或命令行指定子目录主文件时为该文件所在目录。
        work_file  : `-s` 条目直接指向某个 .tex 文件、或命令行给出带子目录的
                     主文件名时为该文件绝对路径，否则 None。
        config     : 纯读取合并后的原始配置 dict（优先级 默认<-用户rc<-项目rc）。
        subprojects: 子项目别名 -> 绝对 Path 映射（来自根 [subprojects]）。
        subproject : 本次 `-s` 选中的别名，None 表示根项目编译。
    """

    root: Path
    work_root: Path
    config: dict = field(default_factory=dict)
    subprojects: dict[str, Path] = field(default_factory=dict)
    subproject: str | None = None
    work_file: Path | None = None


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
        root_resolved = root.resolve()
        for name, value in raw.items():
            rel = _extract_path(value)
            if not rel:
                continue
            # 仅允许相对路径；绝对路径或越界相对路径一律忽略
            candidate = (root_resolved / rel).resolve()
            try:
                candidate.relative_to(root_resolved)
            except ValueError:
                continue
            subprojects[str(name)] = candidate
        return subprojects

    def discover_subprojects(self, config, root: Path) -> dict[str, Path]:
        """扫描目录树得到 别名->路径 映射（不依赖根配置是否已写入 [subprojects]）。

        这是 `-s` 的兜底路径：用户直接敲 `pytexmk -s Review -l` 而不先跑
        `-ls` 时，仍然应该能找到子项目，而不是报"未找到子项目"。
        """
        from pytexmk.subproject_scanner import discover_subprojects

        root_resolved = root.resolve()
        discovered: dict[str, Path] = {}
        try:
            entries = discover_subprojects(root_resolved, config)
        except OSError:
            return discovered
        for name, rel in entries:
            candidate = (root_resolved / rel).resolve()
            try:
                candidate.relative_to(root_resolved)
            except ValueError:
                continue
            discovered.setdefault(str(name), candidate)
        return discovered

    @staticmethod
    def _match(name: str, candidates: dict[str, Path]) -> tuple[str, Path] | None:
        """按 精确别名 → 大小写不敏感别名 → 相对路径后缀 → 叶子目录名 的顺序匹配。

        最后两级匹配是必要的：扫描同步把深层子项目的别名记成完整相对路径
        （如 `Section/en02`），用户更可能直接写 `-s en02`。
        """
        if name in candidates:
            return name, candidates[name]

        lowered = name.lower().replace("\\", "/")
        normalized = {
            alias: alias.lower().replace("\\", "/") for alias in candidates
        }
        matches = [alias for alias, rel in normalized.items() if rel == lowered]
        if not matches:
            matches = [
                alias for alias, rel in normalized.items()
                if rel.endswith("/" + lowered) or candidates[alias].name.lower() == lowered
            ]
        if not matches:
            return None
        if len({candidates[alias] for alias in matches}) > 1:
            raise AmbiguousProjectError(name, matches)
        return matches[0], candidates[matches[0]]

    def resolve(self, args, cwd: Path | None = None) -> ProjectContext:
        """解析运行上下文，未命中 `-s` 别名时抛出 ProjectNotFoundError。"""
        root = (Path.cwd() if cwd is None else cwd).resolve()
        config = self.loader.load_config(root)
        subprojects = self.build_subprojects(config, root)

        subproject: str | None = None
        work_root = root
        work_file: Path | None = None

        requested = getattr(args, "subproject", None)
        document = getattr(args, "document", None)
        if requested:
            candidates = dict(subprojects)
            matched = self._match(requested, candidates)
            if matched is None:
                # 根配置里没有（或没有这一项）时退回目录扫描，
                # 让 `-s` 不依赖用户先手动运行 `-ls`
                discovered = self.discover_subprojects(config, root)
                for alias, path in discovered.items():
                    candidates.setdefault(alias, path)
                matched = self._match(requested, candidates)

            if matched is None:
                raise ProjectNotFoundError(requested, list(candidates.keys()))

            alias, target = matched
            subproject = alias
            if target.is_file():
                # 条目直接指向 .tex：工作目录取它的父目录，并记下该主文件
                work_file = target
                work_root = target.parent
            elif target.is_dir():
                work_root = target
            else:
                # 文件型别名指向不存在的文件：必须报“项目未找到”，不能落到
                # 一个不存在的目录里继续扫描（那样会选错主文件或报无关错误）。
                raise ProjectNotFoundError(requested, list(candidates.keys()))

            # `-s Review ./Review/main.tex` 这类重复指定：只有该文件确实落在
            # -s 已选定的目录内才接管，否则视为与 -s 冲突，交给后续流程报错
            if work_file is None:
                nested = self._resolve_nested_document(document, root)
                if nested is not None and nested[1] == work_root:
                    work_file = nested[0]
        else:
            # 命令行直接给出带子目录的主文件（如 `pytexmk -l ./Review/main.tex`）：
            # 与 `-s` 指向文件同一套语义——进入该文件所在目录编译，
            # 让 project_name 保持为短名（无目录成分）。
            nested = self._resolve_nested_document(document, root)
            if nested is not None:
                work_file, work_root = nested

        return ProjectContext(
            root=root,
            work_root=work_root,
            config=config,
            subprojects=subprojects,
            subproject=subproject,
            work_file=work_file,
        )

    @staticmethod
    def _resolve_nested_document(document, root: Path) -> tuple[Path, Path] | None:
        """把命令行里指向子目录的主文件解析为 (文件绝对路径, 文件父目录)。

        仅在满足下列全部条件时生效，否则返回 None（走原有流程）：
          1. document 非空且不含目录成分——同目录主文件交给原有逻辑处理；
          2. 不是绝对路径、不含 `..`——与 check_project_name 的约束保持一致；
          3. `root/<document>.tex` 或 `root/<document>` 确实是一个已存在的文件。
        返回的父目录一定是 root 的后代（条件 2 + 存在性已保证），不会越出项目。
        """
        if not document:
            return None

        candidate = Path(str(document).replace("\\", "/"))
        if candidate.is_absolute() or ".." in candidate.parts:
            return None
        if len(candidate.parts) < 2:
            return None

        probe = candidate.with_suffix(".tex")
        if not probe.exists():
            if candidate.suffix:
                return None
            # 允许省略 .tex 后缀：`pytexmk Review/main`
            probe = candidate.with_name(candidate.name + ".tex")
            if not probe.exists():
                return None

        try:
            resolved = probe.resolve()
            resolved.relative_to(root)
        except OSError, ValueError:
            return None
        if resolved == root:
            return None

        return resolved, resolved.parent

