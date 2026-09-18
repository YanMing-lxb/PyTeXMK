"""结构化子项目发现与写回：扫描主 .tex、构造清单并整体替换 [subprojects] 段。"""
from __future__ import annotations

from pathlib import Path
from typing import Any

from rich.console import Console
from rich.table import Table

from pytexmk.language import set_language

_ = set_language("subproject")

# 一定会排除的目录名（含所有 `.` 开头目录）。
DEFAULT_EXCLUDE_DIRS = {
    "Auxiliary", "Build", "build", "dist", "out", "output", "temp", "tmp",
    "__pycache__", "node_modules", "venv", "env", "site-packages",
    "Pictures", "figures", "images", "assets", "RawData", "data", "schema",
}
# 一定会排除的文件名（_检查主文件时不涉及，备用兜底）。
DEFAULT_EXCLUDE_FILES = {
    ".DS_Store", "Thumbs.db",
}
DEFAULT_EXCLUDE_FILE_SUFFIXES = {
    ".pdf", ".log", ".aux", ".csv", ".vsz", ".drawio", ".xlsx",
    ".png", ".svg", ".md", ".bak", ".tmp",
}


def has_magic(tex: Path) -> bool:
    """字节级判定某 .tex 是否为主文件：前 16KB 内命中 \\documentclass 或 \\begin{document}。

    一次字节读取，避免 utf-8 全量解码与逐行迭代（发现器性能热点）。
    实践中 \\documentclass 不会出现在注释里，故无需跳过注释/空行。
    任何读取错误（OSError / UnicodeDecodeError / 空文件）均返回 False，不抛异常。
    """
    try:
        with open(tex, "rb") as f:
            buf = f.read(16 * 1024)
    except OSError:
        return False
    return b"\\documentclass" in buf or b"\\begin{document}" in buf


def _dynamic_blacklist(root: Path, config: dict[str, Any]) -> set[Path]:
    """根配置实际 outdir/auxdir 的绝对路径黑名单，防止把输出目录扫成子项目。"""
    blacklist: set[Path] = set()
    folder = config.get("folder") or {}
    for key in ("outdir", "auxdir"):
        target = folder.get(key)
        if not target:
            continue
        try:
            resolved = (root / target).resolve()
            resolved.relative_to(root.resolve())
        except (TypeError, ValueError):
            continue
        blacklist.add(resolved)
    return blacklist


def discover_subprojects(root: Path, config: dict[str, Any]) -> list[tuple[str, str]]:
    """按根 [project_scan] 规则扫描子项目，返回排序后的 (名称, 相对路径)。

    判定：目录内存在主 .tex 即为一子项目；命中后不下钻。
    排除：`. 开头`、内置非法目录、根配置 outdir/auxdir 动态黑名单、用户 exclude。
    """
    scan = config.get("project_scan") or {}
    try:
        depth = int(scan.get("depth") or 3)
    except (TypeError, ValueError):
        depth = 3
    user_exclude = scan.get("exclude") or []
    if not isinstance(user_exclude, list):
        user_exclude = []

    exclude_names = set(DEFAULT_EXCLUDE_DIRS)
    for item in user_exclude:
        item = str(item).strip()
        if not item:
            continue
        exclude_names.add(item.lstrip("*").lstrip(".").strip())

    dynamic = _dynamic_blacklist(root, config)
    root_resolved = root.resolve()
    found: dict[str, str] = {}

    # 原递归语义映射到 Path.walk(top_down=True) 的 depth（"剩余下钻层数"）：
    # 原实现 walk(start, depth_left) 先 if depth_left<0: return，再遍历子目录并对其
    # 调 _dir_is_subproject，非命中下钻一层（depth_left-1）。目录在父目录那次 walk 里
    # 被检查：父目录 level=L-1 的 walk 传入 depth_left = depth-(L-1)，能枚举 child 当且
    # 仅当 depth-(L-1) >= 0 即 level=L <= depth+1。故 level 1..depth+1 的目录都要被检查
    # 是否子项目（depth=3 时检查到 level4）。而下钻仅当 level=L <= depth（walk(level L)
    # 需 depth-L>=0），故 level=depth+1 的目录只检查、不继续下钻到 level=depth+2。
    # 因此：level>depth+1 的目录既不检查也不下钻；level<=depth+1 检查子项目；下钻
    # 不超过 level=depth。
    for base, dirnames, filenames in root.walk(top_down=True):
        level = len(base.relative_to(root).parts)
        # 深度剪枝：level>depth+1 的目录不检查也不再下钻（正常下钻不会到达，兜底）。
        if level > depth + 1:
            dirnames[:] = []
            continue
        # 排除剪枝：原地过滤掉 `. 开头` 及内置/用户 exclude 目录，不再被下钻。
        dirnames[:] = [
            d for d in dirnames
            if not d.startswith(".") and d not in exclude_names
        ]
        # 动态黑名单剪枝：仅 root 内含且 resolve 后仍 contained 的目录落黑名单。
        try:
            base_resolved = base.resolve()
            base_resolved.relative_to(root_resolved)
        except (OSError, ValueError):
            dirnames[:] = []
            continue
        if base_resolved in dynamic:
            dirnames[:] = []
            continue
        # 根自身不判为子项目（原实现只判 root 的子孙目录）。
        if level == 0:
            continue
        for filename in filenames:
            if filename.lower().endswith(".tex") and has_magic(base / filename):
                rel = base.relative_to(root_resolved).as_posix()
                found[rel] = rel
                dirnames[:] = []  # 命中后不下钻
                break
        # 下钻受控：level>depth（即 level==depth+1）的目录已被检查，但不再继续下钻到
        # level=depth+2（超出检查范围）；level<=depth 的普通目录保留 dirnames 继续下钻。
        if level > depth:
            dirnames[:] = []
    return sorted(found.items(), key=lambda kv: kv[0])


def entries_to_subprojects(entries: list[tuple[str, str]]) -> dict[str, str]:
    """扫描结果 -> [subprojects] flat 映射（名称 -> 相对路径）。"""
    return {name: rel for name, rel in entries}


def _build_block(entries: list[tuple[str, str]]) -> list[str]:
    block = ["[subprojects]\n"]
    block.append("# 子项目清单（由 pytexmk -ls 自动托管）：名称 = 相对路径\n")
    for name, rel in entries:
        name_esc = name.replace("\\", "\\\\").replace('"', '\\"')
        rel_esc = rel.replace("\\", "\\\\").replace('"', '\\"')
        block.append(f'"{name_esc}" = "{rel_esc}"\n')
    return block


def write_subprojects_to_rc(rc_path: Path, entries: list[tuple[str, str]]) -> bool:
    """整体替换根 .pytexmkrc 的 [subprojects] 段（含手写内容与注释一并覆盖）。

    仅替换该段；段外内容逐字节保留；`[project_scan]` 等其它段不受影响。
    rc 不存在时返回 False（不写盘）。
    """
    if not rc_path.exists():
        return False
    lines = rc_path.read_text(encoding="utf-8").splitlines(keepends=True)
    block = _build_block(entries)

    header_idx = None
    for i, line in enumerate(lines):
        if line.strip() == "[subprojects]":
            header_idx = i
            break

    if header_idx is None:
        # 追加到文件末尾
        if lines and not lines[-1].endswith("\n"):
            lines.append("\n")
        lines.append("\n")
        lines.extend(block)
    else:
        end = len(lines)
        for i in range(header_idx + 1, len(lines)):
            stripped = lines[i].strip()
            if stripped.startswith("["):
                # [subprojects.x] 仍属本段；其它顶层表为段边界
                if stripped == "[subprojects]":
                    continue
                if stripped.startswith("[subprojects") and stripped.endswith("]"):
                    continue
                end = i
                break
        lines[header_idx:end] = block

    rc_path.write_text("".join(lines), encoding="utf-8")
    return True


def print_subproject_table(entries: list[tuple[str, str]]) -> None:
    console = Console()
    table = Table(title=_("扫描到的子项目清单"))
    table.add_column(_("名称"))
    table.add_column(_("相对路径"))
    for name, rel in entries:
        table.add_row(name, rel)
    console.print(table)