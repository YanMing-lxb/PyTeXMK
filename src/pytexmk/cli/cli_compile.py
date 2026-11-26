"""PyTeXMK CLI 常规编译流程：清理、修复、编译与收尾。"""

import contextlib
import filecmp
from dataclasses import dataclass
from pathlib import Path

from .. import layout
from ..aux_repair import repair_auxiliary_files
from ..build_state import BuildState, _digest_file
from ..compile_engine import RUN, _build_key
from ..diagnostics import report_summary
from ..file_ops import iter_matched_files
from ..language import set_language
from ..lifecycle import EXIT_COMPILE_FAILED, EXIT_ERROR, exit_pytexmk
from ..pdf_tools import inspect_pdf
from ..timing import time_count, time_print
from ..ui_messages import print_message
from ..ui_theme import console
from .cli_state import WorkflowState

_ = set_language("cli_workflow")


def clean_main(args, state: WorkflowState) -> None:
    """处理 ``-c/-C``：清理当前主文件的辅助文件（-C 额外清理根目录与输出）。

    两个入口都需要唯一主文件（由 resolve_target 保证），只按 ``aux_files``
    静态清单工作，不做递归扫描。
    """
    cleaned, failed = _clean(args, state)
    if failed:
        console.print(
            "[yellow]"
            + _("有 %(n)s 个文件未能删除（可能被占用）：") % {"n": len(failed)}
            + "[/yellow]"
        )
        for path, reason in failed:
            console.print(f"  [dim]{path} --> {reason}[/dim]")
        exit_pytexmk(EXIT_ERROR)
    if state.runtime_dict:
        time_print(
            state.start_time,
            state.runtime_dict,
            program=state.compiled_program,
            start_perf=state.start_perf,
        )


def clean_recursive(args, state: WorkflowState) -> None:
    """处理 ``-ca/-Ca``：按后缀递归清理全项目辅助文件。

    ``-Ca`` 在能确定主文件时额外删除 ``Build/`` 里的 PDF/SyncTeX；``-ca``
    永远只删辅助文件。不再保留“可能属于作者”的文件清单。
    """
    targets = _recursive_clean_targets(args, state)
    removed, failed = state.mro.remove_paths(targets)
    state.runtime_dict["clear_all_aux_auxdir"] = 0

    if getattr(args, "clean_recursive_out", False):
        console.print(
            _("[bold green]已完成清除所有带辅助文件后缀的文件和主文件输出文件的指令[/bold green]")
        )
    else:
        console.print(
            _("[bold green]已完成清除所有带辅助文件后缀的文件的指令[/bold green]")
        )
    if failed:
        console.print(
            "[yellow]"
            + _("有 %(n)s 个文件未能删除（可能被占用）：") % {"n": len(failed)}
            + "[/yellow]"
        )
        for path, reason in failed:
            console.print(f"  [dim]{path} --> {reason}[/dim]")
        exit_pytexmk(EXIT_ERROR)

    if state.runtime_dict:
        time_print(
            state.start_time,
            state.runtime_dict,
            program=state.compiled_program,
            start_perf=state.start_perf,
        )


def _recursive_clean_targets(args, state: WorkflowState) -> list[Path]:
    """递归清理的实际目标清单（后缀匹配，无保护清单）。

    ``-Ca`` 额外把 outdir 里的主输出文件（PDF / SyncTeX）纳入同一清单；
    ``-ca`` 不删任何输出。主文件名未确定时 ``state.output_name`` 为空，
    此时不会加入 ``.pdf``/``.synctex.gz`` 这类无主名称。
    """
    targets: list[Path] = []
    for path in iter_matched_files(".", state.aux_regex_files):
        targets.append(path)

    if getattr(args, "clean_recursive_out", False) and state.output_name:
        outdir = Path(state.outdir)
        for name in state.out_files:
            candidate = outdir / name
            if candidate.exists() and candidate not in targets:
                targets.append(candidate)
    return targets


def run(args, state: WorkflowState) -> None:
    """常规编译路径：修复 PDF / 完整编译二选一（清理在 workflow 中单独分派）。"""
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
    else:
        compiled = _compile(args, state)
        if compiled and getattr(args, "submission_pack", False):
            _submission_pack(args, state)


def _submission_pack(args, state: WorkflowState) -> None:
    """生成投稿 zip，并打印页数/体积/转换条数摘要。"""
    from ..submission import build_pack

    submit_dir = state.submission_output_dir
    result = build_pack(
        Path(),
        state.project_name,
        state.outdir,
        state.auxdir,
        pdf_name=state.output_name,
        submit_dir=submit_dir,
        # 开关全部来自配置文件 [submission]；命令行不再暴露 include-bib / pack-verify。
        convert_unicode=state.submission_unicode_to_latex,
        include_bbl=state.submission_include_bbl,
        sanitize=not state.submission_keep_preamble,
        reproducible=state.submission_reproducible,
    )
    size_mb = result.zip_path.stat().st_size / 1024 / 1024
    console.print(_("投稿包已生成") + ": " + str(result.zip_path), style="bold green")
    console.print(
        f"  {_('文件数')}: {len(result.files)} | {_('体积')}: {size_mb:.2f} MB | "
        f"PDF {_('页数')}: {result.pdf_pages if result.pdf_pages is not None else '?'} | "
        f"{_('编译轮数')}: {result.rounds if result.rounds is not None else '?'}"
    )
    if result.conversions:
        console.print(
            f"  [yellow]{_('Unicode 转换')}: {len(result.conversions)} 处"
            f"（清单见包内 pytexmk-submission-notes.txt）[/yellow]"
        )
    if result.sanitized:
        console.print(
            f"  [yellow]{_('导言区净化')}: {len(result.sanitized)} 项"
            f"（fontspec/unicode-math 等已在提交副本中注释）[/yellow]"
        )
    if result.remaining_chars:
        total = sum(result.remaining_chars.values())
        console.print(
            f"  [bold red]{_('仍有 ')}{total}{_(' 个非 ASCII 字符无法转换，pdflatex 会失败')}[/bold red]"
        )
        for char, count in list(result.remaining_chars.items())[:8]:
            console.print(f"    [red]{char} (U+{ord(char):04X}) × {count}[/red]")
        for location in result.remaining_locations[:5]:
            console.print(f"    [dim]{location}[/dim]")
        console.print("    [dim]" + _("中文/日文等正文需 ctex/xeCJK，pdflatex 无法处理") + "[/dim]")
    if not result.compat.ok:
        handled = bool(result.sanitized)
        if handled:
            console.print(
                "  [yellow]"
                + _("原稿使用了 Xe/Lua 专属宏包，提交副本中已自动处理（详见包内说明）")
                + "[/yellow]"
            )
        else:
            console.print("  [yellow]" + _("仍有 pdflatex 无法处理的项，请查看包内说明文件") + "[/yellow]")
        for package, reason in result.compat.incompatible_packages.items():
            console.print(f"    [yellow]{package}[/]: {reason}")
        for char, count in list(result.compat.unsupported_chars.items())[:10]:
            console.print(f"    [yellow]{char} (U+{ord(char):04X})[/] × {count}")
    if result.sha256:
        console.print(f"  [dim]sha256: {result.sha256}[/dim]")


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

    返回 ``(实际删除的路径, 删除失败列表)``；干跑返回空列表，因为没有任何
    文件被真正删除。
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
        state.runtime_dict["clear_out_outdir"] = timed_out.seconds
        console.print(
            _("[bold green]已完成清除所有主文件的辅助文件和输出文件的指令[/bold green]")
        )
    else:
        console.print(
            _("[bold green]已完成清除所有主文件的辅助文件的指令[/bold green]")
        )

    return removed, failed


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
