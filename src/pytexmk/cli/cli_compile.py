"""PyTeXMK CLI 常规编译流程：清理、修复、编译与收尾。"""

import contextlib
import filecmp
import time
from dataclasses import dataclass
from pathlib import Path

from rich.text import Text

from .. import layout
from ..aux_repair import repair_auxiliary_files
from ..build_state import BuildState, _digest_file
from ..compile_engine import RUN, _build_key
from ..diagnostics import report_summary
from ..file_ops import iter_matched_files
from ..language import set_language
from ..lifecycle import EXIT_COMPILE_FAILED, EXIT_ERROR, exit_pytexmk
from ..pdf_tools import inspect_pdf
from ..timing import get_text_len, time_count, time_print, total_len
from ..ui_messages import print_message
from ..ui_theme import console
from .cli_state import WorkflowState

_ = set_language("cli_workflow")


@dataclass
class _CleanResult:
    """清理结果：仍可按 ``removed, failed = ...`` 解包，另带分组计数。"""

    removed: list[Path]
    failed: list[tuple[Path, str]]
    source_count: int
    build_count: int
    build_paths: list[Path]
    folder_count: int = 0

    def __iter__(self):
        yield self.removed
        yield self.failed


def _clean_elapsed(state: WorkflowState) -> float:
    """清理动作的墙钟耗时：优先单调时钟，退化为开始时间戳。"""
    if state.start_perf is not None:
        return max(time.perf_counter() - state.start_perf, 0.0)
    return max((time.time() - state.start_time.timestamp()), 0.0)


def _clean_mode_label(args) -> str:
    """四个清理开关对应的“方式”文案。"""
    recursive = getattr(args, "clean_recursive", False) or getattr(
        args, "clean_recursive_out", False
    )
    with_output = getattr(args, "clean_out", False) or getattr(
        args, "clean_recursive_out", False
    )
    if recursive:
        return _("全项目辅助文件 + 输出") if with_output else _("全项目辅助文件")
    return _("辅助文件 + 输出") if with_output else _("辅助文件")


def _clean_reason(path: Path, reason: str) -> str:
    """把删除失败原因压成一行，并去掉 Windows 消息尾部重复的路径。"""
    text = " ".join(str(reason).split()).replace("\\\\", "\\")
    for tail in (f": '{path}'", f': "{path}"', f": {path}"):
        if text.endswith(tail):
            text = text[: -len(tail)]
            break
    return text


def _print_clean_failure(path: Path, reason: str) -> None:
    """一条删除失败：``路径 --> 原因``，超宽时换行并对齐到原因列。

    原因列深（路径过长）时退化为 8 空格续行，避免首行只剩几个字符。
    """
    head = f"{path} --> "
    indent = 4 + get_text_len(head)
    if indent > 40:
        indent = 8
    rows = _wrap_display(_clean_reason(path, reason), total_len - indent)
    console.print(Text("    " + head + rows[0], style="red"))
    for row in rows[1:]:
        console.print(Text(" " * indent + row, style="red"))


def _print_clean_report(args, result: _CleanResult, *, state: WorkflowState) -> None:
    """清理完成面板：数量、分组、用时；失败逐条列出（只在有失败时出现）。

    清理与编译互斥，原来那张“运行时长统计表”只剩下 0.0009 s 的删除步骤，
    对用户没有信息量，因此不再打印；耗时压成一行 ``用时``。
    """
    print_message(_("清理完成"), "success")

    _panel_kv(_("方式"), _clean_mode_label(args))
    _panel_kv(_("已删除文件"), _("%(n)s 个") % {"n": len(result.removed)})
    with_output = getattr(args, "clean_out", False) or getattr(
        args, "clean_recursive_out", False
    )
    recursive = getattr(args, "clean_recursive", False) or getattr(
        args, "clean_recursive_out", False
    )
    # 递归清理会横跨多个目录，才需要“命中几个文件夹”；-c/-C 的范围是固定的。
    if recursive:
        _panel_kv(_("对应文件夹"), _("%(n)s 个") % {"n": result.folder_count})
    if with_output:
        # 没有输出可删时只报数量，不要留下 `0 个（）` 这种空括号。
        names = "、".join(sorted({path.name for path in result.build_paths}))
        if len(names) > 40:
            names = names[:37] + "…"
        detail = _("%(n)s 个") % {"n": result.build_count}
        if names:
            detail = _("%(n)s 个（%(names)s）") % {
                "n": result.build_count,
                "names": names,
            }
        _panel_kv("Build", detail)
    _panel_kv(_("用时"), f"{_clean_elapsed(state):.2f} s")

    if result.failed:
        console.print()
        _category_header(_("失败"), f"{len(result.failed)}")
        for path, reason in result.failed:
            _print_clean_failure(path, reason)
    _panel_rule("=", style="white")


def clean_main(args, state: WorkflowState) -> None:
    """处理 ``-c/-C``：清理当前主文件的辅助文件（-C 额外清理根目录与输出）。

    两个入口都需要唯一主文件（由 resolve_target 保证），只按 ``aux_files``
    静态清单工作，不做递归扫描。
    """
    result = _clean(args, state)
    _print_clean_report(args, result, state=state)
    if result.failed:
        exit_pytexmk(EXIT_ERROR)


def clean_recursive(args, state: WorkflowState) -> None:
    """处理 ``-ca/-Ca``：按后缀递归清理全项目辅助文件。

    ``-Ca`` 在能确定主文件时额外删除 ``Build/`` 里的 PDF/SyncTeX；``-ca``
    永远只删辅助文件。不再保留“可能属于作者”的文件清单。
    """
    targets = _recursive_clean_targets(args, state)
    build_paths = _recursive_build_targets(args, state)
    build_set = set(build_paths)
    removed, failed = state.mro.remove_paths(targets)
    state.runtime_dict["clear_all_aux_auxdir"] = 0

    # Build 行是“实际删掉了哪些输出”：删失败的 PDF 只能留在失败块里，
    # 不能再算进 Build 的数量与文件名，否则与 `已删除文件` 自相矛盾。
    removed_set = set(removed)
    deleted_build = [path for path in build_paths if path in removed_set]

    result = _CleanResult(
        removed=removed,
        failed=failed,
        source_count=len([path for path in removed if path not in build_set]),
        build_count=len(deleted_build),
        build_paths=deleted_build,
        folder_count=len({path.parent for path in removed if path not in build_set}),
    )
    _print_clean_report(args, result, state=state)
    if failed:
        exit_pytexmk(EXIT_ERROR)


def _recursive_clean_targets(args, state: WorkflowState) -> list[Path]:
    """递归清理的实际目标清单（后缀匹配，无保护清单）。

    ``-Ca`` 额外把 outdir 里的主输出文件（PDF / SyncTeX）纳入同一清单；
    ``-ca`` 不删任何输出。主文件名未确定时 ``state.output_name`` 为空，
    此时不会加入 ``.pdf``/``.synctex.gz`` 这类无主名称。
    """
    targets: list[Path] = []
    for path in iter_matched_files(".", state.aux_regex_files):
        targets.append(path)

    for candidate in _recursive_build_targets(args, state):
        if candidate not in targets:
            targets.append(candidate)
    return targets


def _recursive_build_targets(args, state: WorkflowState) -> list[Path]:
    """``-Ca`` 额外要删的输出文件（PDF/SyncTeX 等）；``-ca`` 返回空清单。"""
    if not getattr(args, "clean_recursive_out", False) or not state.output_name:
        return []
    outdir = Path(state.outdir)
    return [
        candidate
        for name in state.out_files
        if (candidate := outdir / name).exists()
    ]


def _pack_only(args) -> bool:
    """``-sp`` 单独使用时只打包，不进预处理/预检/编译/警告汇总。

    与 ``-f`` 或任一清理开关同时给出时仍先走完整编译：前者明确要求重编，
    后者清完辅助文件后直接打包只会得到一份缺 ``.fls`` 的兜底包。
    """
    if not getattr(args, "submission_pack", False):
        return False
    if getattr(args, "force_rebuild", False):
        return False
    return not (
        getattr(args, "clean", False)
        or getattr(args, "clean_out", False)
        or getattr(args, "clean_recursive", False)
        or getattr(args, "clean_recursive_out", False)
    )


def run(args, state: WorkflowState) -> None:
    """常规编译路径：修复 PDF / 只打包 / 完整编译（清理在 workflow 中单独分派）。"""
    if args.pdf_repair not in (None, False):
        repair = time_count(
            state.pfo.pdf_repair,
            state.output_name,
            ".",
            state.outdir,
            state.auxdir,
            list(args.pdf_repair) or None,
        )
        state.runtime_dict["repair_pdf"] = repair.seconds
        if not repair.value:
            exit_pytexmk(EXIT_ERROR)
        return
    if _pack_only(args):
        _submission_pack(args, state)
        return
    compiled = _compile(args, state)
    if compiled and getattr(args, "submission_pack", False):
        _submission_pack(args, state)


#: 投稿包摘要面板：标签列宽（按终端显示宽度，中文宽字符算 2）与值列起点。
#: 行式为 ``  <标签补空格> <三点> <值>``，值列起点 = 缩进 2 + 标签宽 + 两侧空格 + 三点。
_PANEL_LABEL_W = 14
_PANEL_DOTS = ":"
_PANEL_VALUE_COL = 2 + _PANEL_LABEL_W + 1 + len(_PANEL_DOTS) + 1


def _panel_rule(char: str = "=", *, style: str = "bold green") -> None:
    """打印满宽分隔线；宽度固定 ``total_len``，不跟随终端拉伸。"""
    console.print(char * total_len, style=style)


def _wrap_display(text: str, width: int) -> list[str]:
    """按终端显示宽度折行；``\\n`` 视为强制换行，长路径优先在 ``\\``/``/`` 处断。"""
    rows: list[str] = []
    for segment in text.split("\n"):
        rows.extend(_wrap_segment(segment, width))
    return rows


def _wrap_segment(text: str, width: int) -> list[str]:
    """单个段落的折行实现；调用方已处理 ``\\n`` 分段。"""
    rows: list[str] = []
    current = ""
    current_w = 0
    last_sep = -1
    for ch in text:
        ch_w = get_text_len(ch)
        if current and current_w + ch_w > width:
            if last_sep >= 0:
                rows.append(current[: last_sep + 1])
                current = current[last_sep + 1 :]
                current_w = get_text_len(current)
            else:
                rows.append(current)
                current = ""
                current_w = 0
            last_sep = -1
        current += ch
        current_w += ch_w
        if ch in "\\/，。；：、！？":
            last_sep = len(current) - 1
    rows.append(current)
    return rows


def _panel_kv(
    label: str,
    value: str,
    *,
    value_style: str = "",
    label_style: str = "bold cyan",
) -> None:
    """一行「标签 ······ 值」；值超宽时续行缩进到值列对齐。"""
    label_pad = " " * max(0, _PANEL_LABEL_W - get_text_len(label))
    value_width = total_len - _PANEL_VALUE_COL
    rows = _wrap_display(value, value_width)

    line = Text("  ")
    line.append(label + label_pad, style=label_style)
    line.append(" " + _PANEL_DOTS + " ", style="dim")
    line.append(rows[0], style=value_style or None)
    console.print(line)
    for cont in rows[1:]:
        console.print(Text(" " * _PANEL_VALUE_COL).append(cont, style=value_style or None))


def _relative(path: Path, root: Path) -> str:
    """面板里路径按项目根相对显示；不在项目内时退回原样。"""
    try:
        return path.resolve().relative_to(root).as_posix()
    except (OSError, ValueError):
        return str(path)


def _char_file_count(compat) -> int:
    """出现非 ASCII 字符的文件数（按 ``文件:行号`` 的冒号前一段去重）。"""
    files = {
        spot.rsplit(":", 1)[0]
        for spots in compat.char_locations.values()
        for spot in spots
        if spot
    }
    return len(files)


def _pack_issue_lines(compat, *, sanitize: bool, verbose: bool = False) -> list[str]:
    """把兼容性问题压成“一处一行”，供终端只显示最前面的几条。

    同一个 ``文件:行号`` 上的多个字符合并成一行（``文件:行号  字 字（N 种）``），
    只有重复出现才写 ``×N``；``verbose`` 改为逐字符一行并列出全部位置。
    ``sanitize=True`` 时不兼容宏包已被导言区净化注释，不算待办，不再进入错误清单。
    """
    issues: list[str] = []
    if not sanitize:
        for package, reason in compat.incompatible_packages.items():
            width = max(20, total_len - 6 - get_text_len(package) - 2)
            rows = _wrap_display(reason, width)
            text = f"{package}: {rows[0]}"
            issues.append(text + "…" if len(rows) > 1 else text)
    if verbose:
        for char, count in sorted(compat.non_ascii_chars.items(), key=lambda kv: (-kv[1], kv[0])):
            spots = compat.char_locations.get(char) or [""]
            suffix = f" ×{count}" if count > 1 else ""
            issues.append(f"{', '.join(spots)}  {char} (U+{ord(char):04X}){suffix}")
        return issues

    groups: dict[str, list[str]] = {}
    for char, count in sorted(compat.non_ascii_chars.items(), key=lambda kv: (-kv[1], kv[0])):
        spots = compat.char_locations.get(char) or []
        # 没有位置信息时不能拿空字符串当 key 合并，否则所有字符会挤成一行。
        key = spots[0] if spots else f"~{char}"
        groups.setdefault(key, []).append(f"{char}×{count}" if count > 1 else char)
    for key, tokens in groups.items():
        if key.startswith("~"):
            issues.append(" ".join(tokens))
        elif len(tokens) > 1:
            issues.append(
                f"{key}  {' '.join(tokens)}" + _("（%(n)s 种）") % {"n": len(tokens)}
            )
        else:
            issues.append(f"{key}  {tokens[0]}")
    return issues


def _category_header(label: str, detail: str) -> None:
    """``+-- [分类] · 计数`` 分类头，配色与 ``警告汇总`` 的分类行一致。"""
    prefix = f"+-- [{label}] · {detail} "
    dashes = max(0, total_len - get_text_len(prefix))
    console.print(
        Text.assemble(
            ("+-- ", "bold #d79921"),
            (f"[{label}]", "bold"),
            (f" · {detail}", "dim"),
            (" " + "-" * dashes, "bold #d79921"),
        )
    )


def _submission_pack(args, state: WorkflowState) -> None:
    """生成投稿 zip，打印摘要；正文不做自动转换，问题在面板下方逐条报出。"""
    from ..submission import build_pack

    submit_dir = state.submission_output_dir
    sanitize = not state.submission_keep_preamble
    root = Path().resolve()
    verbose = bool(getattr(args, "verbose", False))
    started = time.perf_counter()
    result = build_pack(
        Path(),
        state.project_name,
        state.outdir,
        state.auxdir,
        pdf_name=state.output_name,
        submit_dir=submit_dir,
        # 开关全部来自配置文件 [submission]；命令行不再暴露 include-bib / pack-verify。
        sanitize=sanitize,
        reproducible=state.submission_reproducible,
    )
    elapsed = time.perf_counter() - started

    size_mb = result.zip_path.stat().st_size / 1024 / 1024

    # 标题沿用“开始预处理”的 X 底纹横幅与配色（红底字 + 蓝色粗分隔线）。
    print_message(_("投稿包已生成"), "additional")

    _panel_kv(_("包路径"), _relative(result.zip_path, root))

    # 体积/文件数/页数/轮数合成一行“包信息”，不再各占一行。
    parts = [_("%(n)s 个文件") % {"n": len(result.files)}]
    if result.pdf_pages is not None:
        parts.append(_("PDF %(n)s 页") % {"n": result.pdf_pages})
    if result.rounds is not None:
        parts.append(_("编译 %(n)s 轮") % {"n": result.rounds})
    _panel_kv(
        _("包信息"),
        _("体积 %(size)s MB (%(detail)s)")
        % {"size": f"{size_mb:.2f}", "detail": _("，").join(parts)},
    )
    if result.sanitized:
        _panel_kv(
            _("导言区"),
            _("%(n)s 项（已自动处理）") % {"n": len(result.sanitized)},
            value_style="yellow",
        )
    if result.log_path is not None:
        _panel_kv(_("诊断日志"), _relative(result.log_path, root), value_style="dim")
    if result.sha256:
        digest = result.sha256 if verbose else result.sha256[:16] + _("…（完整值见日志）")
        _panel_kv("SHA-256", digest, value_style="dim")
    if verbose:
        _panel_kv(_("打包耗时"), f"{elapsed:.2f} s", value_style="dim")

    # 产物检查只提示不拦截：缺 .fls 仍可打包，但包内容不再可信；PDF 旧于源码则
    # 用户核对的版式与包内源码不同版。告警都同步落诊断日志。
    console.print()
    dirty = False
    if not result.used_fls:
        where = "Auxiliary" if result.fls_path is None else result.fls_path.as_posix()
        _panel_kv(
            _("依赖清单"),
            _("缺少 %(p)s\n按后缀兜底收集（可能混入未引用文件），建议先编译一次")
            % {"p": where},
            value_style="yellow",
        )
        dirty = True
    if result.stale_sources:
        first = result.stale_sources[0]
        _panel_kv(
            _("PDF 一致性"),
            _("PDF 早于 %(n)s 个源文件（如 %(f)s），建议重编译后再重新打包。")
            % {"n": len(result.stale_sources), "f": first},
            value_style="yellow",
        )
        dirty = True
    if result.pdf_bytes is None:
        # 没有 PDF 就没有“PDF 不旧于源码”这回事：诊断日志已写“未找到构建 PDF”，
        # 面板不能再用绿色“通过”把这一项吞掉。
        pdf_rel = _relative(
            Path(state.outdir) / f"{state.output_name or state.project_name}.pdf",
            root,
        )
        _panel_kv(
            _("PDF 产物"),
            _("未找到 %(p)s，包内不带 PDF；建议先编译再打包") % {"p": pdf_rel},
            value_style="yellow",
        )
        dirty = True
    if not dirty:
        _panel_kv(
            _("产物检查"),
            _("通过：.fls 齐全，PDF 不旧于入包源码"),
            value_style="green",
        )

    if sanitize and result.compat.incompatible_packages:
        names = list(result.compat.incompatible_packages)
        shown = "、".join(names[:3]) + ("等" if len(names) > 3 else "")
        _panel_kv(
            _("宏包"),
            f"{shown}（已在提交副本中注释，无需手改）",
            value_style="yellow",
        )

    issues = _pack_issue_lines(result.compat, sanitize=sanitize, verbose=verbose)
    pkg_pending = 0 if sanitize else len(result.compat.incompatible_packages)

    # 问题块：分类头给出“字符数/文件数”，条目只列前 5 项（-vb 时全列），
    # 其余指向诊断日志；块内提示已并入标题，块尾用白线收尾。
    if issues:
        console.print()
        chars = len(result.compat.non_ascii_chars)
        counts = [f"{chars}c", f"{_char_file_count(result.compat)}f"]
        if pkg_pending:
            counts.append(f"{pkg_pending}p")
        counts = [item for item in counts if item[:-1] != "0"]
        _category_header(_("扫描解析"), "/".join(counts))
        if verbose:
            console.print(
                Text("  " + _("计数：c 字符 / f 文件 / p 宏包"), style="dim")
            )
        console.print(
            Text(
                "  " + _("pdflatex 无法处理以下内容（逐字位置与全部计数见诊断日志）"),
                style="bold red",
            )
        )
        limit = len(issues) if verbose else 5
        for line in issues[:limit]:
            console.print(Text("    " + line, style="red"))
        if len(issues) > limit:
            console.print(
                Text("    " + _("其余 %(n)s 项见诊断日志") % {"n": len(issues) - limit}, style="dim")
            )
    _panel_rule("=", style="white")


def finalize(state: WorkflowState) -> None:
    """全部流程收尾：编译后 PDF 预览与耗时统计。"""
    if state.preview_after_compile and state.output_name:
        state.pfo.pdf_preview(state.output_name, state.outdir)
        # 不再在这里 exit：耗时统计与成功摘要还没打印（U3）

    if state.runtime_dict:
        time_print(
            state.start_time,
            state.runtime_dict,
            program=state.compiled_program,
            start_perf=state.start_perf,
        )


def _clean(args, state: WorkflowState) -> tuple[list[Path], list[tuple[Path, str]]]:
    """-c / -C：清理主文件的辅助文件（-C 额外清理输出文件）。

    返回 ``_CleanResult``（可按 ``removed, failed = ...`` 解包）；干跑不删除
    任何文件，计数因此为 0。
    """
    # 命名索引（author.idx/ind）与多套 glossary 产物不在静态列表里，先补齐
    _collect_named_index_aux(state)

    # -c 只看辅助目录；-C 再连同项目根目录里的同名副本一起清理。
    folders = [state.auxdir]
    if args.clean_out and not _same_directory(state.auxdir, "."):
        folders.append(".")

    targets: list[Path] = []
    for folder in folders:
        for name in state.aux_files:
            candidate = Path(folder) / name
            if candidate.exists() and candidate not in targets:
                targets.append(candidate)

    # 每个目录单独计时，但仍然只删一次；旧实现先 remove_specific_files 再取
    # JSON 清单，删除结果与清单来自两套调用，无法证明“cleaned 真的删掉了”。
    removed: list[Path] = []
    failed: list[tuple[Path, str]] = []
    for folder in folders:
        folder_targets = [path for path in targets if path.parent == Path(folder)]
        timed = time_count(state.mro.remove_paths, folder_targets)
        removed.extend(timed.value[0])
        failed.extend(timed.value[1])
        key = "clear_aux_auxdir" if folder == state.auxdir else "clear_aux_root"
        state.runtime_dict[key] = timed.seconds

    # 构建基线必须同步作废：否则下次编译会把"已删除的产物"误判为"未变动"
    _discard_build_state(state)

    build_paths: list[Path] = []
    if args.clean_out:
        out_targets: list[Path] = []
        if state.output_name:
            for name in state.out_files:
                candidate = Path(state.outdir) / name
                if candidate.exists() and candidate not in targets:
                    out_targets.append(candidate)
        timed_out = time_count(state.mro.remove_paths, out_targets)
        removed.extend(timed_out.value[0])
        failed.extend(timed_out.value[1])
        build_paths = list(timed_out.value[0])
        state.runtime_dict["clear_out_outdir"] = timed_out.seconds

    in_build = set(build_paths)
    return _CleanResult(
        removed=removed,
        failed=failed,
        source_count=len([path for path in removed if path not in in_build]),
        build_count=len(build_paths),
        build_paths=build_paths,
        folder_count=len({path.parent for path in removed if path not in in_build}),
    )


def _compile(args, state: WorkflowState) -> bool:
    """执行一次完整编译：原生目录构建 → 编译 → 归档结果 → 诊断摘要。

    返回 True 表示当前 ``outdir`` 里有一对可用的 PDF/SyncTeX（无论是本次新编出来的，
    还是因为“源文件未变”复用的上次产物）。预检阻断会在本函数内直接以非零码退出，
    不再返回一个被调用方忽略的 False。
    """
    _apply_build_overrides(args, state)
    print_message(_("开始预处理"), "additional")

    if state.preflight_enabled:
        preflight_report = _run_preflight(state)
        if preflight_report is not None:
            # 预检阻断不是“可以继续的提示”：必须让调用方看到非零退出码。
            exit_pytexmk(EXIT_COMPILE_FAILED)

    if _can_skip_compile(args, state):
        _report_skipped_compile(state)
        # 跳过编译不等于跳过诊断：日志分析照常执行，终端仍显示警告 / 错误。
        _finish_compile(state, status="skipped")
        return True

    _prepare_project_state(state)
    before = capture_engine_outputs(state)
    _run_latex(state, args)

    print_message(_("开始后处理"), "additional")
    publish_compiled_outputs(state, before)
    _finish_compile(state)
    return True


def _prepare_project_state(state: WorkflowState) -> None:
    """编译前整理辅助文件：原生目录直接写 auxdir，传统模式先搬到根目录。"""
    # imakeidx 的命名索引（\makeindex[name=author] → author.idx/ind）主干不是
    # jobname，静态 aux_files 覆盖不到；补进列表后搬运/清理才认得它们。
    _collect_named_index_aux(state)

    if state.native_build:
        # 原生目录构建：辅助文件直接由 TeX 写进 auxdir，不再往返搬运（3.7）
        Path(state.auxdir).mkdir(parents=True, exist_ok=True)
        Path(state.outdir).mkdir(parents=True, exist_ok=True)
        console.print(
            "[green]"
            + _("原生目录构建：辅助文件直接写入 %(d)s") % {"d": state.auxdir}
            + "[/green]"
        )
        # 切换过 --no-native 的项目根目录会残留同名辅助文件，而 TeX 找输入时
        # 根目录优先于 auxdir —— 不清掉它们，`\printindex` 读到的就是旧 .ind。
        _sweep_stale_root_aux(state)
        _repair_truncated_aux_files(state)
        _warn_if_last_compile_interrupted(state)
        return

    runtime_move_aux_root, aux_moved_count, _err = time_count(
        state.mro.move_specific_files, state.aux_files, state.auxdir, "."
    )
    state.runtime_dict["move_aux_root"] = runtime_move_aux_root

    aux_exist_count = sum(1 for f in state.aux_files if Path(f).exists())
    if aux_exist_count == 0:
        console.print("[green]" + _("未检测到已有辅助文件，进行初始化") + "[/green]")
    else:
        console.print(
            "[green]"
            + _("已检测到 %(n)s 个已有辅助文件") % {"n": aux_exist_count}
            + "[/green]"
        )
        # 中断自愈：截断的辅助文件会让后续每次编译都在同一处失败，必须先清掉
        _repair_truncated_aux_files(state)
        # .log 缺失完成标记 ⇒ 提示用户辅助文件可能不完整
        _warn_if_last_compile_interrupted(state)

    if aux_moved_count == 0:
        console.print("[green]" + _("没有检测到可迁移的辅助文件") + "[/green]")
    else:
        console.print(
            "[yellow]"
            + _("已移动 %(n)s 个辅助文件到项目根目录") % {"n": aux_moved_count}
            + "[/yellow]"
        )


def _run_latex(state: WorkflowState, args) -> None:
    """调用主编译入口 RUN。"""
    RUN(
        state.runtime_dict,
        state.project_name,
        state.compiled_program,
        state.out_files,
        state.aux_files,
        state.outdir,
        state.auxdir,
        non_quiet=state.non_quiet,
        draft=args.draft,
        shell_escape=state.shell_escape,
        synctex=state.synctex,
        native=state.native_build,
        extra_args=state.extra_args,
        interaction=state.interaction or None,
        jobname=state.output_name,
        max_extra=state.max_extra_compilations,
    )


@dataclass(slots=True)
class ArchiveResult:
    """一次归档的可核对结果。

    ``had_pdf``     归档前编译落点是否有本轮产生的 PDF；
    ``moved``       实际搬动的文件个数（PDF + SyncTeX）；
    ``source_pdf``  归档后编译落点仍残留的 PDF；非空说明搬移没有真正完成。
    """

    had_pdf: bool
    moved: int
    source_pdf: Path | None


def capture_engine_outputs(state: WorkflowState) -> dict[str, tuple]:
    """记录编译落点的同名产物，供归档识别本轮新文件。"""
    source = Path(state.auxdir if state.native_build else ".")
    try:
        return {
            name: signature for name in state.out_files
            if (signature := _output_signature(source / name)) is not None
        }
    except OSError as exc:
        _fail_compile(state, _("无法读取编译产物: ") + str(exc))


def publish_compiled_outputs(
    state: WorkflowState, before: dict[str, tuple], *, archive_aux: bool = True,
) -> None:
    """归档本轮写入的 PDF/SyncTeX，并校验可交付结果。"""
    after = capture_engine_outputs(state)
    produced = [name for name, signature in after.items() if signature != before.get(name)]
    if _engine_reported_no_pages(state):
        produced.clear()
    archive = _archive_outputs(state, produced, archive_aux=archive_aux)
    _validate_archive(state, archive)


def _engine_reported_no_pages(state: WorkflowState) -> bool:
    """最后一轮没有页面时，即使前一轮生成过 PDF 也不能交付。"""
    folder = Path(state.auxdir if state.native_build else ".")
    try:
        with (folder / f"{state.output_name}.log").open("rb") as log:
            log.seek(max(0, log.seek(0, 2) - 8192))
            tail = b"\n" + log.read()
    except OSError:
        return False
    return tail.rfind(b"\nNo pages of output.") > tail.rfind(b"\nOutput written on ")


def _output_signature(path: Path) -> tuple[int, int, int, int, int, str | None] | None:
    """区分本轮写入和原地残留的产物，兼容时间戳精度较低的文件系统。"""
    try:
        stamp = path.stat()
    except FileNotFoundError:
        return None
    return (
        stamp.st_dev, stamp.st_ino, stamp.st_size, stamp.st_mtime_ns,
        stamp.st_ctime_ns, _digest_file(path),
    )


def _archive_outputs(
    state: WorkflowState, produced: list[str] | None = None, *, archive_aux: bool = True,
) -> ArchiveResult:
    """把 PDF / SyncTeX 从编译落点搬到 outdir，返回可核对的归档结果。"""
    # 若 outdir 与源目录是同一个目录，跳过搬移 —— 否则 src 与 dest 是同一文件，
    # 旧实现会“先删 dest 再 move”，等于把刚编译出来的 PDF/SyncTeX 直接删掉。
    archive_src = state.auxdir if state.native_build else "."
    pdf_in_src = Path(archive_src) / f"{state.output_name}.pdf"
    if produced is None:
        produced = [name for name in state.out_files if (Path(archive_src) / name).is_file()]
    had_pdf = pdf_in_src.name in produced
    delivered = produced if had_pdf else []
    archived = _("PDF / synctex") if state.synctex else "PDF"
    moved = 0
    pdf_published = False
    same_directory = _same_directory(archive_src, state.outdir)
    if same_directory:
        console.print(
            "[yellow]"
            + _("输出目录与辅助目录相同，%(p)s 已在目标位置，跳过归档") % {"p": archived}
            + "[/yellow]"
        )
    elif had_pdf:
        console.print("[yellow]" + _("归档 %(p)s 到输出目录...") % {"p": archived} + "[/yellow]")
        pdf_move = time_count(
            state.mro.move_specific_files, [pdf_in_src.name], archive_src, state.outdir
        )
        moved = pdf_move.value
        elapsed = pdf_move.seconds
        sidecars = [name for name in delivered if name != pdf_in_src.name]
        pdf_published = moved == 1
        if pdf_published and sidecars:
            sync_move = time_count(
                state.mro.move_specific_files, sidecars, archive_src, state.outdir
            )
            moved += sync_move.value
            elapsed += sync_move.seconds
        state.runtime_dict["move_out_outdir"] = round(elapsed, 4)

    if archive_aux and not state.native_build:
        # 本轮新建的命名索引（首次出现的主干）只有编译后才在磁盘上看到
        _collect_named_index_aux(state)
        console.print("[yellow]" + _("移动辅助文件到辅助目录...") + "[/yellow]")
        runtime_move_aux_auxdir = time_count(
            state.mro.move_specific_files, state.aux_files, ".", state.auxdir
        ).seconds
        state.runtime_dict["move_aux_auxdir"] = runtime_move_aux_auxdir

    # 只有真的尝试过搬移，才把“源目录仍残留 PDF”当作归档失败；
    # outdir 与 auxdir 相同（如 `-o .`）时 PDF 本来就在目标位置，不能误判。
    leftover = pdf_in_src if had_pdf and not same_directory and pdf_in_src.exists() else None
    if had_pdf and not same_directory and moved != len(delivered) and leftover is None:
        if pdf_published:
            _discard_stale_synctex(state)
        _fail_compile(state, _("编译产物未能完整归档: ") + str(state.outdir))
    if had_pdf and leftover is None:
        _discard_stale_synctex(state, keep=tuple(delivered))
    return ArchiveResult(had_pdf=had_pdf, moved=moved, source_pdf=leftover)


def _validate_archive(
    state: WorkflowState,
    archive: ArchiveResult,
) -> None:
    """归档后的硬校验：产物必须是**本轮的、完整的、有页面的** PDF。

    旧实现只查 outdir 里“有没有同名文件”。于是：搬移失败时看的是旧 PDF；
    编译没产出 PDF 时看的是上一轮 PDF；被覆盖成文本的文件也照样算成功。
    归档结果必须包含本轮写入的 PDF，且文件可解析并至少有一页。
    """
    out_pdf = Path(state.outdir) / f"{state.output_name}.pdf"
    if archive.source_pdf is not None:
        _fail_compile(
            state,
            _("编译产物归档失败：%(p)s 仍留在 %(s)s（可能被占用或目录不可写）")
            % {"p": out_pdf, "s": archive.source_pdf.parent},
        )

    if not archive.had_pdf:
        _fail_compile(state, _("本轮编译没有生成新 PDF: ") + str(out_pdf))
    status = inspect_pdf(out_pdf)
    if not status.ok:
        reason_text = {
            "missing": _("输出目录里没有 PDF（编译可能未产出页面）"),
            "empty": _("PDF 是空文件"),
            "not-pdf": _("PDF 文件内容不是有效的 PDF（可能被其他程序覆盖）"),
            "no-pages": _("PDF 没有页面（文档为空或只含不可排版内容）"),
            "corrupt": _("PDF 结构损坏，无法解析"),
            "unreadable": _("PDF 无法读取（可能被占用）"),
        }.get(status.reason, _("PDF 校验失败"))
        _fail_compile(
            state,
            _("编译产物校验失败: %(p)s（%(r)s）") % {"p": out_pdf, "r": reason_text},
        )

    out_sync = _find_synctex_sidecar(state.outdir, state.output_name)
    if state.synctex and out_sync is None:
        console.print(
            "[yellow]"
            + _("提示：输出目录里缺少 SyncTeX 定位文件（%(n)s.synctex 或 .synctex.gz），编辑器将无法反向跳转")
            % {"n": state.output_name}
            + "[/yellow]"
        )


def _find_synctex_sidecar(outdir: str | Path, jobname: str) -> Path | None:
    """按 jobname 找实际存在的 SyncTeX 文件（压缩格式优先）。"""
    for suffix in layout.SYNCTEX_SUFFIXES:
        candidate = Path(outdir) / f"{jobname}{suffix}"
        if candidate.exists():
            return candidate
    return None


def _fail_compile(state: WorkflowState, message: str) -> None:
    """产物不可交付时统一以 ``EXIT_COMPILE_FAILED`` 退出。"""
    _discard_build_state(state)
    console.print("[bold red]" + message + "[/bold red]")
    exit_pytexmk(EXIT_COMPILE_FAILED)


def _finish_compile(state: WorkflowState, *, status: str = "ok") -> None:
    """编译结束后的日志分析：保持终端警告 / 错误展示，不自动写报告。

    ``status="skipped"`` 用于“源文件未变、复用上次产物”的路径：仍要读取
    现有 .log 并按原格式展示警告 / 错误。末尾的下一步提示由 pytexlogs
    摘要的页脚统一给出，这里不再自己拼计数或第二个出口。
    """
    summary = report_summary(
        state.output_name,
        state.auxdir,
        root_file=f"{state.project_name}.tex",
        translate_fn=set_language("diagnostics"),
    )
    if status != "skipped":
        _record_output_digests(state)
    if not summary.available:
        return
    if summary.errors:
        # 错误分组只在上面的失败摘要里展开；成功路径也必须让计数可见，
        # 否则“0 退出码 + 有错误”会被当成完全没问题。
        console.print(
            "[dim]" + _("检测到 %(e)s 个错误，详见编译日志中的 ERROR 条目。") % {"e": summary.errors} + "[/dim]"
        )


def _record_output_digests(state: WorkflowState) -> None:
    """把本轮 PDF/SyncTeX 的摘要写进构建基线（配对校验的依据）。"""
    with contextlib.suppress(Exception):
        outdir = Path(state.outdir)
        pdf = outdir / f"{state.output_name}.pdf"
        sync: Path | None = None
        if getattr(state, "synctex", True):
            sync = _find_synctex_sidecar(outdir, state.output_name)
        BuildState(state.auxdir, state.output_name).record_outputs(pdf, sync)


def _same_directory(left: str | Path, right: str | Path) -> bool:
    """两个目录路径是否指向同一位置（用于避免“自己搬给自己”）。"""
    try:
        return Path(left).resolve() == Path(right).resolve()
    except OSError:
        return str(left) == str(right)


def _run_preflight(state: WorkflowState):
    """返回阻断性的 preflight 报告；通过时返回 None。"""
    from ..preflight import check_project, format_report

    report = check_project(state.project_name, Path())
    if report.warnings:
        console.print("[yellow]" + _("编译前检查提示") + "[/yellow]")
        for line in format_report(report, limit=5):
            console.print(f"  {line}")
    if report.errors:
        console.print("[bold red]" + _("编译前检查发现阻断性问题，已停止编译") + "[/bold red]")
        for line in format_report(report, limit=8):
            console.print(f"  [red]{line}[/red]")
        console.print(
            "[dim]"
            + _("确认无误时可在配置中设 [preflight] enabled = false 跳过检查")
            + "[/dim]"
        )
        return report
    return None


def apply_effective_build_plan(args, state: WorkflowState) -> None:
    """把命令行构建参数合进 state，供 ``--explain`` 等只读动作使用。

    与真正编译共用同一套合并逻辑，但不删除旧 SyncTeX、不打印执行期提示，
    保证解释命令零副作用。
    """
    _apply_build_overrides(args, state, side_effects=False)


def _apply_build_overrides(
    args, state: WorkflowState, *, side_effects: bool = True
) -> None:
    """把命令行构建参数合进 state（命令行优先级最高）。

    构建类开关（native / shell_escape / synctex / interaction / 轮次上限）只由
    配置文件驱动；命令行只剩 ``-pa/--pass-arg`` 一项。

    side_effects=False 供只读入口使用。旧 SyncTeX 由归档流程在新 PDF 发布后清理。
    """
    if getattr(args, "extra_args", None):
        state.extra_args.extend(str(a) for a in args.extra_args)
    if not state.synctex and side_effects:
        console.print(
            "[yellow]"
            + _("SyncTeX 已关闭：本次不生成 .synctex.gz，编辑器将无法正/反向跳转")
            + "[/yellow]"
        )


def _discard_stale_synctex(state: WorkflowState, *, keep: tuple[str, ...] = ()) -> None:
    """新 PDF 已归档，清掉未随它生成的同名 SyncTeX。"""
    name = getattr(state, "output_name", None)
    if not name:
        return
    for suffix in layout.SYNCTEX_SUFFIXES:
        filename = f"{name}{suffix}"
        if filename in keep:
            continue
        path = Path(state.outdir) / filename
        try:
            path.unlink(missing_ok=True)
        except OSError as exc:
            _fail_compile(state, _("无法清除旧 SyncTeX: ") + f"{path}: {exc}")


#: 命名索引（imakeidx）的产物后缀：主干不是 jobname，静态 aux_files 覆盖不到
NAMED_INDEX_SUFFIXES = layout.NAMED_INDEX_SUFFIXES

#: 只由索引工具生成的辅助后缀。native 构建前清理根目录残留时只动这些，
#: 避免把用户手放的 .bbl / .aux 之类一并处理。
#: 这里**不含** `.ist`：makeindex 的样式文件是用户输入，删掉就等于静默删源码。
INDEX_ARTIFACT_SUFFIXES = layout.INDEX_ARTIFACT_SUFFIXES

#: 可能由用户手写、不能无条件删除的索引类后缀：即使 auxdir 已有同名文件，
#: 也要先确认两份内容一致（即根目录只是同一产物的旧副本）才删。
_USER_EDITABLE_INDEX_SUFFIXES = layout.INDEX_USER_EDITABLE_SUFFIXES


def _same_bytes(left: Path, right: Path) -> bool:
    """两份文件内容是否完全相同；读不了就当不同（保守，宁可保留）。"""
    try:
        return filecmp.cmp(left, right, shallow=False)
    except OSError:
        return False


def _collect_named_index_aux(state: WorkflowState) -> None:
    """把命名索引的产物补进 ``state.aux_files``。

    根目录与 auxdir 都会被扫描，主干取自磁盘上真实存在的 ``*.idx``；与 jobname
    同名的那份已在静态列表里，跳过。补进列表后，非 native 的“辅助文件→auxdir”、
    ``-ca`` 清理、``-C`` 递归清理才会认得 ``author.idx`` / ``author.ind``。
    """
    for base in (Path(), Path(state.auxdir)):
        for idx_file in base.glob("*.idx"):
            stem = idx_file.stem
            if stem == state.output_name:
                continue
            for suffix in NAMED_INDEX_SUFFIXES:
                name = f"{stem}{suffix}"
                if name not in state.aux_files:
                    state.aux_files.append(name)


def _sweep_stale_root_aux(state: WorkflowState) -> None:
    """native 构建前清掉根目录里残留的索引类辅助文件。

    TeX 找输入文件时根目录优先于 ``-output-directory``：如果之前用过
    ``--no-native``（文件留在根目录），本次 native 构建新生成的 ``auxdir/main.ind``
    会被根目录那份旧 ``main.ind`` 遮住，``\\printindex`` 打出来的是旧索引。
    这里对索引类后缀做一次清理：auxdir 已有同名文件就删根目录的旧副本，
    auxdir 还没有就把它挪进去。
    """
    auxdir = Path(state.auxdir)
    # `auxdir = "."`（或等价路径）时，根目录副本与辅助目录里的就是同一批文件：
    # 旧实现把 main.ind 移进 "."（自己搬给自己）后又被删除，有效索引直接消失。
    if _same_directory(auxdir, "."):
        return
    for name in state.aux_files:
        suffix = Path(name).suffix
        if suffix not in INDEX_ARTIFACT_SUFFIXES:
            continue
        root_copy = Path(name)
        aux_copy = auxdir / name
        if not root_copy.exists():
            continue
        try:
            if root_copy.resolve() == aux_copy.resolve():
                continue
            if aux_copy.exists():
                if suffix in _USER_EDITABLE_INDEX_SUFFIXES and not _same_bytes(
                    root_copy, aux_copy
                ):
                    # 同名但内容不同：根目录这份可能是用户手写的样式文件，
                    # 删掉就再也回不来了。保留并明确告知，让用户自己决定。
                    console.print(
                        "[yellow]"
                        + _(
                            "根目录 %(f)s 与辅助目录同名但内容不同，已保留（疑似手写样式文件）"
                        )
                        % {"f": name}
                        + "[/yellow]"
                    )
                    continue
                root_copy.unlink()
                console.print(
                    "[dim]" + _("清理根目录残留的辅助文件: %(f)s") % {"f": name} + "[/dim]"
                )
            else:
                auxdir.mkdir(parents=True, exist_ok=True)
                root_copy.replace(aux_copy)
        except OSError:
            # 文件被占用（编辑器/预览器）时保持原样，不能因此让编译失败
            continue


def _repair_truncated_aux_files(state: WorkflowState) -> None:
    """删除被中断的编译留下的截断辅助文件（.aux/.toc/.out/... ）。

    辅助文件刚被搬回项目根目录，此时若某个文件是"写到一半"的状态，
    下一次 LaTeX 会以 ``File ended while scanning use of \\@writefile``
    失败，而且此后每次都会失败 —— 因为坏文件还在原处。这里直接删除，
    让本轮编译完整重建它们。
    """
    repaired = repair_auxiliary_files(
        [Path(), Path(state.auxdir)],
        project_name=state.output_name,
        logger=state.logger,
    )
    if repaired:
        console.print(
            "[yellow]"
            + _("检测到 %(n)s 个被中断的编译留下的损坏辅助文件，已删除并将在本次编译中重建。") % {"n": len(repaired)}
            + "[/yellow]"
        )


def _can_skip_compile(args, state: WorkflowState) -> bool:
    """判断本次是否可以整次跳过编译（源文件与产物都和上次一致）。

    四个必要条件缺一不可：
      1. 上次编译判定为收敛（存在无法消除的残留警告时也照样算收敛，
         因为再编译也改变不了它们）；
      2. 所有 ``.tex`` 源文件的 ``(size, mtime_ns)`` 与上次快照一致；
      3. 构建产物摘要与上次基线一致；
      4. PDF **与 .synctex.gz 都在** outdir 里 —— 只查 PDF 会漏掉“编辑器清理脚本
         删了 synctex.gz”的情形，那样跳过后永远不会自愈，跳转一直是死的。
    用户显式指定 ``-f/--force-rebuild`` 或 ``-d/--draft`` 时永不跳过。
    """
    if getattr(args, "force_rebuild", False) or getattr(args, "draft", False):
        return False

    try:
        tracker = BuildState(state.auxdir, state.output_name)
        if not tracker.was_converged():
            return False
        if not tracker.baseline_matches_current():
            return False
        if not _outputs_present(state):
            return False
        # 复用产物必须同时能复用**诊断**：日志被删除/清空/替换后，PyTeXLogs
        # 只会返回全零摘要，终端会漏报真实的警告 / 错误。
        if not _diagnostics_reusable(tracker):
            return False
        # PDF 与 SyncTeX 必须仍是上次一起产出的那一对；外部替换任意一份都重编。
        if not _outputs_match_record(tracker, state):
            return False
        if not tracker.sources_unchanged(_iter_source_files_for_state(state)):
            return False
        # C2：构建参数变了（换引擎/换目录/开关 shell-escape/轮次预算）必须重编，
        # 否则"源文件没动"会把两个不可比的 PDF 当成同一个。
        previous_key = tracker.build_key()
        return bool(previous_key) and previous_key == _current_build_key(state)
    except Exception:  # 状态文件不可用就老老实实编译
        return False


def _outputs_match_record(tracker: BuildState, state: WorkflowState) -> bool:
    """outdir 的 PDF/SyncTeX 是否与上次记录的摘要一致。"""
    record = tracker.output_record()
    if not record:
        return False
    outdir = Path(state.outdir)
    pdf = outdir / f"{state.output_name}.pdf"
    if record.get("pdf") != _digest_file(pdf):
        return False
    if not getattr(state, "synctex", True):
        return record.get("synctex") is None and _find_synctex_sidecar(outdir, state.output_name) is None
    synced = [
        outdir / f"{state.output_name}{suffix}" for suffix in layout.SYNCTEX_SUFFIXES
        if (outdir / f"{state.output_name}{suffix}").is_file()
    ]
    return len(synced) == 1 and record.get("synctex") == _digest_file(synced[0])


def _diagnostics_reusable(tracker: BuildState) -> bool:
    """上一轮记录的日志摘要是否仍与磁盘上的 ``.log`` 一致。"""
    record = tracker.diagnostics_record()
    if not record.get("available"):
        return False
    log_path = tracker.log_path()
    if not log_path.is_file():
        return False
    return record.get("digest") == _digest_file(log_path)


def _outputs_present(state: WorkflowState) -> bool:
    """outdir 里是否同时有**可交付**的 PDF 与 SyncTeX（缺任一都必须重编）。

    PDF 不能只查存在：被覆盖成文本、解析失败或零页的旧文件同样会让缓存跳过，
    用户拿到的就是一份坏产物。
    """
    outdir = Path(state.outdir)
    pdf = outdir / f"{state.output_name}.pdf"
    if not inspect_pdf(pdf).ok:
        return False
    if not getattr(state, "synctex", True):
        return True
    return _find_synctex_sidecar(outdir, state.output_name) is not None


def _current_build_key(state: WorkflowState) -> str:
    """按当前 state 计算构建参数指纹（与 compile_engine 落盘时同口径）。"""
    from ..compile import (
        detect_shell_escape,
        effective_interaction,
        normalize_shell_escape_flag,
    )
    from ..version import __version__

    if str(state.shell_escape).lower() == "auto":
        from ..compile_engine import _iter_tex_sources

        shell_escape = detect_shell_escape(_iter_tex_sources(state.project_name))
    else:
        shell_escape = normalize_shell_escape_flag(state.shell_escape)

    return _build_key({
        "engine": state.compiled_program,
        "interaction": effective_interaction(state.interaction),
        "shell_escape": bool(shell_escape),
        "synctex": bool(state.synctex),
        "draft": bool(getattr(state.args, "draft", False)),
        "native": bool(state.native_build),
        "outdir": str(state.outdir),
        "auxdir": str(state.auxdir),
        "extra_args": list(state.extra_args),
        "jobname": state.output_name,
        # 轮次预算必须进复用键：`--max-runs 0` 与默认 8 的收敛程度不同，
        # 旧实现漏了它，改预算后仍会复用上一轮 PDF。
        "max_extra": int(getattr(state, "max_extra_compilations", 8)),
        "version": __version__,
    })


def _iter_source_files_for_state(state: WorkflowState):
    """C1：源快照覆盖 .tex + .fls 依赖（图片/宏包/bib）。"""
    from ..compile_engine import _iter_source_files

    yield from _iter_source_files(state.project_name, state.auxdir, fls_name=state.output_name)


def _report_skipped_compile(state: WorkflowState) -> None:
    """源文件未改动时给出明确提示，让用户知道"没编译"是刻意为之。"""
    console.print(
        "[bold green]"
        + _("源文件与上次编译一致，已跳过编译（如需强制重新编译请加 [bold cyan]-f[/bold cyan]）。")
        + "[/bold green]"
    )
    pdf_path = Path(state.outdir) / f"{state.output_name}.pdf"
    if pdf_path.exists():
        console.print(
            "[green]"
            + _("当前 PDF：%(p)s") % {"p": str(pdf_path)}
            + "[/green]"
        )


def _discard_build_state(state: WorkflowState) -> None:
    """清理构建基线（只删 ``pytexmk.build``，保留 ``pytexlogs.refs``）。

    引用缓存归 pytexlogs 所有，清理辅助文件时不该连带丢掉它。
    """
    with contextlib.suppress(Exception):  # 状态文件问题绝不阻断清理流程
        BuildState(state.auxdir, state.output_name).discard()


def _warn_if_last_compile_interrupted(state: WorkflowState) -> None:
    """检测上次 LaTeX 编译是否被中断，若有则给出黄色警告。

    检测逻辑：
      1. auxdir 里 .log 文件存在（说明有过编译）
      2. 取 .log 最后 3 行，检查是否包含正常完成标记
         - "Output written on ..." (pdf)
         - "No pages of output." (正常无输出也算完成)
         - "Transcript written on ..." (latexmk 等包装的收尾)
      3. 若没有完成标记 ⇒ 上次编译被 Ctrl+C / 崩溃中断
    """
    log_path = Path(state.auxdir) / f"{state.output_name}.log"
    if not log_path.exists():
        return

    try:
        # 读最后 2KB（足以覆盖结尾标记），避免整文件加载大 log
        with log_path.open("rb") as fh:
            fh.seek(0, 2)  # 移到末尾
            size = fh.tell()
            tail_size = min(2048, size)
            fh.seek(size - tail_size)
            tail_bytes = fh.read()
        tail_text = tail_bytes.decode("utf-8", errors="replace")
    except OSError:
        return

    completion_markers = (
        "Output written on",
        "No pages of output",
        "Transcript written on",
        )
    if not any(marker in tail_text for marker in completion_markers):
        console.print(
            "[yellow]"
            + _("警告：检测到上次编译可能被中断，辅助文件可能不完整。")
            + _("建议先运行 [bold cyan]pytexmk -c[/bold cyan] 清理后再重试。")
            + "[/yellow]"
        )
