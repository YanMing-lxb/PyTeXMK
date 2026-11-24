"""结构化子项目发现与写回：扫描主 .tex、构造清单并合并 [subprojects] 段。"""

import logging
import re
from pathlib import Path
from typing import Any

from rich.table import Table

from pytexmk.file_ops import atomic_write_text
from pytexmk.language import set_language
from pytexmk.layout import EXCLUDED_DIRS, GENERATED_DIRS
from pytexmk.ui_theme import console

_ = set_language("subproject")
logger = logging.getLogger(__name__)

# 一定会排除的目录名（含所有 `.` 开头目录）：VCS/虚拟环境 + 编译产物 + 素材目录
DEFAULT_EXCLUDE_DIRS = (
    EXCLUDED_DIRS
    | GENERATED_DIRS
    | {
        "temp", "tmp", "Pictures", "figures", "images",
        "assets", "RawData", "data", "schema",
    }
)

#: 托管段里由工具维护的表头。`-ls` 会写回本段并更新该表头。
_MANAGED_HEADER = "# 子项目清单（由 pytexmk -ls 维护）：名称 = 相对路径\n"
_MANAGED_HEADER_PREFIX = "# 子项目清单（由 pytexmk"
#: TOML 裸键允许的字符；中文/含斜杠的别名必须加引号。
_BARE_KEY_RE = re.compile(r"^[A-Za-z0-9_-]+$")
#: `[subprojects]` 表头允许行尾注释，避免同步时另起一个重名表。
_SUBPROJECTS_HEADER_RE = re.compile(r"^\s*\[subprojects\]\s*(#.*)?$")


def has_magic(tex: Path) -> bool:
    """字节级判定某 .tex 是否为主文件：前 16KB 内命中 \\documentclass 或 \\begin{document}。

    一次字节读取，避免 utf-8 全量解码与逐行迭代（发现器性能热点）。
    实践中 \\documentclass 不会出现在注释里，故无需跳过注释/空行。
    任何读取错误（OSError / UnicodeDecodeError / 空文件）均返回 False，不抛异常。
    """
    try:
        with tex.open("rb") as f:
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
        except TypeError, ValueError:
            continue
        blacklist.add(resolved)
    return blacklist


def discover_subprojects(root: Path, config: dict[str, Any]) -> list[tuple[str, str]]:
    """按根 [project_scan] 规则扫描子项目，返回排序后的 (名称, 相对路径)。

    判定：目录内存在主 .tex 即为一子项目；命中后不下钻。
    排除：`. 开头`、内置非法目录、根配置 outdir/auxdir 动态黑名单、用户 exclude。
    """
    depth, exclude_names = _scan_settings(config)
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
        dirnames[:] = [d for d in dirnames if not d.startswith(".") and d not in exclude_names]
        if not _contained_dir(base, root_resolved, dynamic):
            dirnames[:] = []
            continue
        # 根自身不判为子项目（原实现只判 root 的子孙目录）。
        if level == 0:
            continue
        rel = _subproject_rel(base, root_resolved, filenames)
        if rel is not None:
            found[rel] = rel
            dirnames[:] = []  # 命中后不下钻
        # 下钻受控：level>depth（即 level==depth+1）的目录已被检查，但不再继续下钻到
        # level=depth+2（超出检查范围）；level<=depth 的普通目录保留 dirnames 继续下钻。
        if level > depth:
            dirnames[:] = []
    return sorted(found.items(), key=lambda kv: kv[0])


def _scan_settings(config: dict[str, Any]) -> tuple[int, set[str]]:
    """读取 project_scan.depth / exclude，并规范化为目录名集合。"""
    scan = config.get("project_scan") or {}
    try:
        depth = int(scan.get("depth") or 3)
    except TypeError, ValueError:
        depth = 3
    user_exclude = scan.get("exclude") or []
    if not isinstance(user_exclude, list):
        user_exclude = []

    exclude_names = set(DEFAULT_EXCLUDE_DIRS)
    for item in user_exclude:
        item = str(item).strip()
        if not item:
            continue
        # 兼容 `*Build` / `.*Build` 这类 glob 写法：只取目录名本身。
        name = item.lstrip("*")
        if "/" in name or "\\" in name:
            logger.warning(_("project_scan.exclude 只接受目录名，已按 basename 处理: ") + item)
            name = Path(name).name
        name = name.lstrip(".")
        if name:
            exclude_names.add(name)
    return depth, exclude_names


def _contained_dir(base: Path, root: Path, dynamic: set[Path]) -> bool:
    """目录是否仍在 root 内且不在动态 outdir/auxdir 黑名单。"""
    try:
        base_resolved = base.resolve()
        base_resolved.relative_to(root)
    except OSError, ValueError:
        return False
    return base_resolved not in dynamic


def _subproject_rel(base: Path, root: Path, filenames: list[str]) -> str | None:
    """目录内有主 .tex 时返回相对路径，否则返回 None。"""
    for filename in filenames:
        if filename.lower().endswith(".tex") and has_magic(base / filename):
            return base.relative_to(root).as_posix()
    return None


def entries_to_subprojects(entries: list[tuple[str, str]]) -> dict[str, str]:
    """扫描结果 -> [subprojects] flat 映射（名称 -> 相对路径）。"""
    return {name: rel for name, rel in entries}


def _escape_toml(text: str) -> str:
    return text.replace("\\", "\\\\").replace('"', '\\"')


def _unquote_toml(token: str) -> str:
    token = token.strip()
    if len(token) >= 2 and token[0] == '"' and token[-1] == '"':
        return token[1:-1].replace('\\"', '"').replace("\\\\", "\\")
    return token


def _format_key(name: str) -> str:
    """只给 TOML 裸键不接受的别名加引号（`alias` 保持 `alias`，不再变 `"alias"`）。"""
    return name if _BARE_KEY_RE.fullmatch(name) else f'"{_escape_toml(name)}"'


def _format_entry(
    name: str, path: str, raw_key: str | None = None, comment: str = ""
) -> str:
    key = raw_key or _format_key(name)
    line = f'{key} = "{_escape_toml(path)}"'
    if comment:
        line += "  " + comment
    return line + "\n"


def _split_toml_comment(raw: str) -> tuple[str, str]:
    """拆出行尾注释：引号内的 ``#`` 不算注释，返回 ``(正文, #注释)``。"""
    body = raw.rstrip("\r\n")
    in_quote = False
    escaped = False
    for index, char in enumerate(body):
        if escaped:
            escaped = False
            continue
        if char == "\\" and in_quote:
            escaped = True
            continue
        if char == '"':
            in_quote = not in_quote
            continue
        if char == "#" and not in_quote:
            return body[:index], body[index:]
    return body, ""


def _split_key_value(text: str) -> tuple[str, str] | None:
    """在引号外找第一个 ``=``，避免把别名里的等号当成赋值符。"""
    in_quote = False
    escaped = False
    for index, char in enumerate(text):
        if escaped:
            escaped = False
            continue
        if char == "\\" and in_quote:
            escaped = True
            continue
        if char == '"':
            in_quote = not in_quote
            continue
        if char == "=" and not in_quote:
            return text[:index], text[index + 1 :]
    return None


def _parse_entry(raw: str) -> tuple[str, str, str, str] | None:
    """解析 `[subprojects]` 里的一行 `键 = "值"`；注释/空行/表头返回 None。

    返回 ``(名称, 路径, 原始键写法, 行尾注释)``。行尾注释单独保存，路径没变时
    仍整行原样写回；路径变了也不丢用户注释。
    """
    body, comment = _split_toml_comment(raw)
    line = body.strip()
    if not line or line.startswith(("#", ";")) or "=" not in line:
        return None
    pair = _split_key_value(line)
    if pair is None:
        return None
    key_part, value_part = pair
    raw_key = key_part.strip()
    if not raw_key:
        return None
    name = _unquote_toml(raw_key)
    path = _unquote_toml(value_part.strip())
    if not name or not path:
        return None
    return name, path, raw_key, comment


def _read_section(rc_path: Path) -> tuple[list[str], int | None, int]:
    """读出整个文件的行，以及 `[subprojects]` 段的起止下标。"""
    lines = rc_path.read_text(encoding="utf-8").splitlines(keepends=True)
    header_idx = None
    for i, line in enumerate(lines):
        if _SUBPROJECTS_HEADER_RE.match(line.rstrip("\r\n")):
            header_idx = i
            break
    if header_idx is None:
        return lines, None, len(lines)

    end = len(lines)
    for i in range(header_idx + 1, len(lines)):
        if lines[i].strip().startswith("["):
            end = i
            break
    return lines, header_idx, end


def _collect_entries(section_lines: list[str]) -> list[dict[str, Any]]:
    """按出现次序收集段内条目，保留原始行与原始键写法。"""
    result: list[dict[str, Any]] = []
    for index, raw in enumerate(section_lines):
        parsed = _parse_entry(raw)
        if parsed is None:
            continue
        name, path, raw_key, comment = parsed
        result.append(
            {
                "name": name,
                "path": path,
                "orig_path": path,
                "raw_key": raw_key,
                "raw_line": raw,
                "comment": comment,
                "index": index,
            }
        )
    return result


def _path_key(root: Path, path: str) -> Path:
    """把配置里的相对路径归一化为可比较的绝对路径。

    仅用于去重，不改变写回文本：`./chap1`、`chap1/` 与扫描得到的 `chap1`
    必须视为同一目录，否则会同时保留两条、让 `-A` 编译两次。
    """
    candidate = root / path
    try:
        return candidate.resolve()
    except OSError, RuntimeError:
        return candidate.absolute()


def _merge_manual_entries(
    root: Path, entries: list[tuple[str, str]], existing: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    """合并扫描结果与现有条目：保留手写条目与原有次序，新条目追加在末尾。

    规则：
    * 同名条目以本次扫描路径为准，但保留原行位置与键写法；
    * 不同名的手写别名优先保留，即使它指向的目录也被自动扫描到；
    * 同一路径只保留最先出现的一条，避免 `-A` 把同一项目编译两次；
    * 路径失效的旧条目自然淘汰。
    """
    discovered_map = dict(entries)
    merged: list[dict[str, Any]] = []
    seen_names: set[str] = set()
    seen_paths: set[Path] = set()

    for item in existing:
        name = item["name"]
        path = discovered_map.get(name, item["path"])
        key = _path_key(root, path)
        if name in seen_names or key in seen_paths:
            continue
        if name not in discovered_map:
            # 手写别名即使指向自动发现的目录也要保留：它是用户选择的调用名，
            # 不能因为扫描器也看到了同一目录就被改写成目录名。
            if not ((root / path).exists() or (root / f"{path}.tex").exists()):
                continue
        seen_names.add(name)
        seen_paths.add(key)
        merged.append({**item, "path": path})

    for name, path in entries:
        key = _path_key(root, path)
        if name in seen_names or key in seen_paths:
            continue
        seen_names.add(name)
        seen_paths.add(key)
        merged.append(
            {
                "name": name,
                "path": path,
                "orig_path": path,
                "raw_key": None,
                "raw_line": None,
                "comment": "",
                "index": None,
            }
        )
    return merged


def _render_entry(item: dict[str, Any]) -> str:
    """路径没变时原样保留手写行（含键引号与空格）；变了才重写值。"""
    raw_line = item.get("raw_line")
    if raw_line and item["path"] == item["orig_path"]:
        return raw_line if raw_line.endswith("\n") else raw_line + "\n"
    return _format_entry(
        item["name"], item["path"], item.get("raw_key"), item.get("comment", "")
    )


def _build_block(
    merged: list[dict[str, Any]],
    section_lines: list[str],
    header_comment: str = "",
) -> list[str]:
    """重建 `[subprojects]` 段：旧注释保留，旧条目按原次序写回，新条目追加。"""
    header = "[subprojects]"
    if header_comment:
        header += "  " + header_comment
    block = [header + "\n", _MANAGED_HEADER]
    kept_by_index = {
        item["index"]: item for item in merged if item.get("index") is not None
    }
    for index, raw in enumerate(section_lines):
        stripped = raw.strip()
        if stripped.startswith(_MANAGED_HEADER_PREFIX):
            continue
        item = kept_by_index.get(index)
        if item is not None:
            block.append(_render_entry(item))
            continue
        if _parse_entry(raw) is not None:
            continue  # 已失效/重复的旧条目
        block.append(raw if raw.endswith("\n") else raw + "\n")
    for item in merged:
        if item.get("index") is None:
            block.append(_render_entry(item))
    return block


def write_subprojects_to_rc(rc_path: Path, entries: list[tuple[str, str]]) -> bool:
    """更新根 .pytexmkrc 的 `[subprojects]` 段（由 `-ls` 调用）。

    与旧实现的关键差别：
    * 保留仍指向真实路径的手写别名，不再整段清空重排；
    * 保留手写条目与自动条目的原有次序，`-A` 不会因为一次同步换编译顺序；
    * 路径没变的条目原样保留整行（`alias = "x"` 不会变成 `"alias" = "x"`）；
    * 段内注释保留，只替换工具自己的托管表头。

    rc 不存在时返回 False（不写盘）。
    """
    if not rc_path.exists():
        return False
    lines, header_idx, end = _read_section(rc_path)
    section_lines = [] if header_idx is None else lines[header_idx + 1 : end]
    existing = _collect_entries(section_lines)
    merged = _merge_manual_entries(rc_path.parent, entries, existing)
    header_comment = ""
    if header_idx is not None:
        match = _SUBPROJECTS_HEADER_RE.match(lines[header_idx].rstrip("\r\n"))
        if match and match.group(1):
            header_comment = match.group(1)
    block = _build_block(merged, section_lines, header_comment=header_comment)
    # 段与下一个表之间留一个空行；第二次同步会从旧段原样保留这个空行，
    # 这里只在“旧段末尾没有空行且后面紧跟表头”时补一次，保持幂等。
    if (
        end < len(lines)
        and block
        and block[-1].strip()
        and lines[end].strip().startswith("[")
    ):
        block.append("\n")

    if header_idx is None:
        if lines and not lines[-1].endswith("\n"):
            lines.append("\n")
        lines.append("\n")
        lines.extend(block)
    else:
        lines[header_idx:end] = block

    try:
        atomic_write_text(rc_path, "".join(lines))
    except OSError as exc:
        # 没有权限、目标被占用、只读属性等：让调用方按"写回失败"处理，
        # 不能把 OSError 直接抛成 CLI traceback。
        logger.error(_("写入子项目清单失败: ") + str(exc))
        return False
    return True


def print_subproject_table(entries: list[tuple[str, str]]) -> None:
    table = Table(title=_("扫描到的子项目清单"))
    table.add_column(_("名称"))
    table.add_column(_("相对路径"))
    for name, rel in entries:
        table.add_row(name, rel)
    console.print(table)
