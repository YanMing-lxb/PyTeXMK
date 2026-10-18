"""PyTeXMK CLI 常规编译流程：清理、修复、编译与收尾。"""

from pathlib import Path

from pytexlogs import run_pipeline as _run_log_pipeline

from ..aux_repair import repair_auxiliary_files
from ..build_state import BuildState
from ..compile_engine import RUN
from ..language import set_language
from ..lifecycle import exit_pytexmk
from ..timing import time_count, time_print
from ..ui_messages import print_message
from ..ui_theme import console
from ..version import __version__
from .check_version import UpdateChecker
from .cli_state import WorkflowState

_ = set_language("cli_workflow")


def handle_clean_any(args, state: WorkflowState) -> bool:
    """处理 -ca / -Ca（清理所有带辅助文件后缀的文件）。

    返回 True 表示本次运行已结束，调用方应直接收工。
    """
    if not (args.clean_any or args.Clean_any):
        return False

    runtime_remove_aux_matched_auxdir = time_count(
        state.mro.remove_matched_files, state.aux_regex_files, "."

    ).seconds
    state.runtime_dict[_("清除所有的辅助文件")] = runtime_remove_aux_matched_auxdir

    if args.Clean_any:
        runtime_remove_out_outdir = time_count(
            state.mro.remove_specific_files, state.out_files, state.outdir
        ).seconds
        state.runtime_dict[_("清除文件夹内输出文件")] = runtime_remove_out_outdir
        console.print(
            _("[bold green]已完成清除所有带辅助文件后缀的文件和主文件输出文件的指令[/bold green]")
        )
    else:
        console.print(
            _("[bold green]已完成清除所有带辅助文件后缀的文件的指令[/bold green]")
        )

    if state.runtime_dict:
        time_print(state.start_time, state.runtime_dict)
    return True


def run(args, state: WorkflowState) -> None:
    """常规编译路径：清理 / 修复 PDF / 完整编译三选一。"""
    if args.clean or args.Clean:
        _clean(args, state)
    elif args.pdf_repair:
        runtime_pdf_repair = time_count(
            state.pfo.pdf_repair, state.project_name, ".", state.outdir
        ).seconds
        state.runtime_dict[_("修复 PDF 文件")] = runtime_pdf_repair
    else:
        _compile(args, state)


def finalize(state: WorkflowState) -> None:
    """全部流程收尾：编译后 PDF 预览、耗时统计与版本更新检查。"""
    if state.preview_after_compile and state.project_name:
        state.pfo.pdf_preview(state.project_name, state.outdir)
        exit_pytexmk()

    if state.runtime_dict:
        time_print(state.start_time, state.runtime_dict)

    UpdateChecker(1, 6).check_for_updates()


def _clean(args, state: WorkflowState) -> None:
    """-c / -C：清理主文件的辅助文件（-C 额外清理输出文件）。"""
    runtime_remove_aux_auxdir = time_count(
        state.mro.remove_specific_files, state.aux_files, state.auxdir
    ).seconds
    state.runtime_dict[_("清除文件夹内辅助文件")] = runtime_remove_aux_auxdir
    runtime_remove_aux_root = time_count(
        state.mro.remove_specific_files, state.aux_files, "."
    ).seconds
    state.runtime_dict[_("清除根目录内辅助文件")] = runtime_remove_aux_root

    # 构建基线必须同步作废：否则下次编译会把"已删除的产物"误判为"未变动"
    _discard_build_state(state)

    if args.Clean:
        runtime_remove_out_outdir = time_count(
            state.mro.remove_specific_files, state.out_files, state.outdir
        ).seconds
        state.runtime_dict[_("清除文件夹内输出文件")] = runtime_remove_out_outdir
        console.print(
            _("[bold green]已完成清除所有主文件的辅助文件和输出文件的指令[/bold green]")
        )
    else:
        console.print(
            _("[bold green]已完成清除所有主文件的辅助文件的指令[/bold green]")
        )


def _compile(args, state: WorkflowState) -> None:
    """执行一次完整编译：辅助文件就位 → 编译 → 结果与辅助文件归档 → 日志解析。"""
    print_message(_("开始预处理"), "additional")

    if _can_skip_compile(args, state):
        _report_skipped_compile(state)
        return

    runtime_move_aux_root, aux_moved_count, _err = time_count(
        state.mro.move_specific_files, state.aux_files, state.auxdir, "."
    )
    state.runtime_dict[_("辅助文件->根目录")] = runtime_move_aux_root

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

    RUN(
        state.runtime_dict,
        state.project_name,
        state.compiled_program,
        state.out_files,
        state.aux_files,
        state.outdir,
        state.auxdir,
        state.non_quiet,
        args.draft,
    )

    print_message(_("开始后处理"), "additional")

    console.print("[yellow]" + _("移动结果文件到输出目录...") + "[/yellow]")
    runtime_move_out_outdir = time_count(
        state.mro.move_specific_files, state.out_files, ".", state.outdir
    ).seconds
    state.runtime_dict[_("结果文件->输出目录")] = runtime_move_out_outdir

    console.print("[yellow]" + _("移动辅助文件到辅助目录...") + "[/yellow]")
    runtime_move_aux_auxdir = time_count(
        state.mro.move_specific_files, state.aux_files, ".", state.auxdir
    ).seconds
    state.runtime_dict[_("辅助文件->辅助目录")] = runtime_move_aux_auxdir

    _run_log_pipeline(
        state.project_name,
        state.auxdir,
        root_file=state.project_name,
        pytexmk_version=__version__,
        ref_tracker_translate_fn=set_language("log_parser"),
    )


def _repair_truncated_aux_files(state: WorkflowState) -> None:
    """删除被中断的编译留下的截断辅助文件（.aux/.toc/.out/... ）。

    辅助文件刚被搬回项目根目录，此时若某个文件是"写到一半"的状态，
    下一次 LaTeX 会以 ``File ended while scanning use of \\@writefile``
    失败，而且此后每次都会失败 —— 因为坏文件还在原处。这里直接删除，
    让本轮编译完整重建它们。
    """
    repaired = repair_auxiliary_files(
        [Path("."), Path(state.auxdir)],
        project_name=state.project_name,
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

    三个必要条件缺一不可：
      1. 上次编译判定为收敛（存在无法消除的残留警告时也照样算收敛，
         因为再编译也改变不了它们）；
      2. 所有 ``.tex`` 源文件的 ``(size, mtime_ns)`` 与上次快照一致；
      3. 构建产物摘要与上次基线一致，且 PDF 确实存在。
    用户显式指定 ``-fr/--force-rebuild`` 或 ``-dr/--draft`` 时永不跳过。
    """
    if getattr(args, "force_rebuild", False) or getattr(args, "draft", False):
        return False

    try:
        tracker = BuildState(state.auxdir, state.project_name)
        if not tracker.was_converged():
            return False
        if not tracker.baseline_matches_current():
            return False
        if not Path(state.outdir, f"{state.project_name}.pdf").exists():
            return False
        return tracker.sources_unchanged(_iter_tex_sources(state))
    except Exception:  # 状态文件不可用就老老实实编译
        return False


def _iter_tex_sources(state: WorkflowState):
    """枚举参与编译的 ``.tex`` 源文件（与 compile_engine 的快照口径保持一致）。"""
    from ..compile_engine import _iter_tex_sources as _engine_sources

    yield from _engine_sources(state.project_name)


def _report_skipped_compile(state: WorkflowState) -> None:
    """源文件未改动时给出明确提示，让用户知道"没编译"是刻意为之。"""
    console.print(
        "[bold green]"
        + _("源文件与上次编译一致，已跳过编译（如需强制重新编译请加 [bold cyan]-fr[/bold cyan]）。")
        + "[/bold green]"
    )
    pdf_path = Path(state.outdir) / f"{state.project_name}.pdf"
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
    try:
        BuildState(state.auxdir, state.project_name).discard()
    except Exception:  # 状态文件问题绝不阻断清理流程
        pass


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
    log_path = Path(state.auxdir) / f"{state.project_name}.log"
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
            + _("建议先运行 [bold cyan]pytexmk -c[/bold cyan] 清理后再重试。[/yellow]")
        )
