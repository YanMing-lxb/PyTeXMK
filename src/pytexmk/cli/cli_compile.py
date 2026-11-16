"""PyTeXMK CLI 常规编译流程：清理、修复、编译与收尾。"""

from pathlib import Path

from ..aux_repair import repair_auxiliary_files
from ..build_state import BuildState
from ..compile_engine import RUN, _build_key
from ..diagnostics import report_success
from ..language import set_language
from ..timing import time_count, time_print
from ..ui_messages import print_message
from ..ui_theme import console
from .check_version import UpdateChecker
from .cli_state import WorkflowState

_ = set_language("cli_workflow")


def handle_clean_any(args, state: WorkflowState) -> bool:
    """处理 -ca / -Ca（清理所有带辅助文件后缀的文件）。

    返回 True 表示本次运行已结束，调用方应直接收工。
    """
    if not (args.clean_any or args.Clean_any):
        return False

    if getattr(args, "clean_dry_run", False):
        console.print("[yellow]" + _("试运行：以下文件将被删除（-ca/-Ca）") + "[/yellow]")
        import re as _re

        patterns = [_re.compile(p) for p in state.aux_regex_files]
        for path in Path(".").rglob("*"):
            if not path.is_file():
                continue
            if any(part in {".git", ".github", "examples", "tests", "dist", "docs", ".venv"} for part in path.parts):
                continue
            if any(p.match(path.name) for p in patterns):
                console.print(f"  [dim]{path}[/dim]")
        return True

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
            state.pfo.pdf_repair, state.output_name, ".", state.outdir
        ).seconds
        state.runtime_dict[_("修复 PDF 文件")] = runtime_pdf_repair
    else:
        _compile(args, state)
        if getattr(args, "pdflatex_check", False):
            _pdflatex_check(state)
        elif getattr(args, "submission_pack", False):
            _submission_pack(args, state)


def _pdflatex_check(state: WorkflowState) -> None:
    """只体检：报告哪些字符/宏包会让 pdflatex 编译失败。"""
    from ..submission import scan_compat

    report = scan_compat(Path("."), state.project_name)
    if report.ok:
        console.print("[bold green]" + _("pdflatex 兼容性检查通过：未发现非 ASCII 字符或不兼容宏包") + "[/bold green]")
        return
    console.print("[bold yellow]" + _("pdflatex 兼容性检查发现问题") + "[/bold yellow]")
    for package, reason in report.incompatible_packages.items():
        console.print(f"  [yellow]宏包[/] {package}: {reason}")
    for char, count in sorted(report.unsupported_chars.items(), key=lambda kv: -kv[1])[:20]:
        console.print(f"  [yellow]字符[/] {char} (U+{ord(char):04X}) × {count}")
    console.print(
        _("可用 [bold cyan]pytexmk -sp[/bold cyan] 生成已转换 Unicode 的投稿包")
    )


def _submission_pack(args, state: WorkflowState) -> None:
    """生成投稿 zip，并打印页数/体积/转换条数摘要。"""
    from ..submission import build_pack

    submit_dir = getattr(args, "submit_dir", None) or "./Submission"
    result = build_pack(
        Path("."),
        state.project_name,
        state.outdir,
        state.auxdir,
        pdf_name=state.output_name,
        submit_dir=submit_dir,
        convert_unicode=True,
        include_bbl=True,
        include_bib=bool(getattr(args, "include_bib", False)),
        sanitize=not getattr(args, "keep_preamble", False),
        verify=bool(getattr(args, "pack_verify", False)),
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
    if result.verify_ok is not None:
        style = "green" if result.verify_ok else "red"
        console.print(
            f"  [{style}]pdflatex 验证: {'通过' if result.verify_ok else '失败'}[/{style}]"
        )
        if not result.verify_ok:
            for line in result.verify_tail[-5:]:
                console.print(f"    [dim]{line}[/dim]")
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
    if result.verify_ok is False:
        from ..lifecycle import EXIT_PACK_VERIFY, exit_pytexmk

        console.print(
            "  [dim]"
            + _("投稿包已生成，但 pdflatex 验证未通过；请先修复残留项再投稿")
            + "[/dim]"
        )
        exit_pytexmk(EXIT_PACK_VERIFY)


def finalize(state: WorkflowState) -> None:
    """全部流程收尾：编译后 PDF 预览、耗时统计与版本更新检查。"""
    if state.preview_after_compile and state.output_name:
        state.pfo.pdf_preview(state.output_name, state.outdir)
        # 不再在这里 exit：耗时统计与成功摘要还没打印（U3）

    if state.runtime_dict:
        time_print(state.start_time, state.runtime_dict)

    UpdateChecker(1, 6).check_for_updates()


def _clean(args, state: WorkflowState) -> None:
    """-c / -C：清理主文件的辅助文件（-C 额外清理输出文件）。"""
    if getattr(args, "clean_dry_run", False):
        console.print("[yellow]" + _("试运行：以下文件将被删除") + "[/yellow]")
        for folder in (state.auxdir, "."):
            for name in state.aux_files:
                candidate = Path(folder) / name
                if candidate.exists():
                    console.print(f"  [dim]{candidate}[/dim]")
        if args.Clean:
            for name in state.out_files:
                candidate = Path(state.outdir) / name
                if candidate.exists():
                    console.print(f"  [dim]{candidate}[/dim]")
        return

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
    """执行一次完整编译：原生目录构建 → 编译 → 归档结果 → 诊断摘要。"""
    _apply_build_overrides(args, state)
    print_message(_("开始预处理"), "additional")

    if not getattr(args, "no_preflight", False) and not _run_preflight(state):
        return

    if _can_skip_compile(args, state):
        _report_skipped_compile(state)
        return

    if state.native_build:
        # 原生目录构建：辅助文件直接由 TeX 写进 auxdir，不再往返搬运（3.7）
        Path(state.auxdir).mkdir(parents=True, exist_ok=True)
        Path(state.outdir).mkdir(parents=True, exist_ok=True)
        console.print("[green]" + _("原生目录构建：辅助文件直接写入 %(d)s") % {"d": state.auxdir} + "[/green]")
        _repair_truncated_aux_files(state)
        _warn_if_last_compile_interrupted(state)
    else:
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

    report_write = bool(getattr(args, "report", False))
    report_path = args.report if isinstance(getattr(args, "report", None), str) else None

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
        shell_escape=state.shell_escape,
        native=state.native_build,
        extra_args=state.extra_args,
        interaction=state.interaction or None,
        jobname=state.output_name,
        max_extra=state.max_extra_compilations,
        write_report=report_write,
        report_path=report_path,
        include_only=getattr(args, "includeonly", None),
    )

    print_message(_("开始后处理"), "additional")

    if state.native_build:
        # 只把最终产物搬到 outdir；辅助文件原地留在 auxdir（不会再有搬运失败风险）
        console.print("[yellow]" + _("归档 PDF / synctex 到输出目录...") + "[/yellow]")
        runtime_move_out_outdir = time_count(
            state.mro.move_specific_files, state.out_files, state.auxdir, state.outdir
        ).seconds
        state.runtime_dict[_("结果文件->输出目录")] = runtime_move_out_outdir
    else:
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

    warning_count = report_success(
        state.output_name,
        state.auxdir,
        root_file=f"{state.project_name}.tex",
        translate_fn=set_language("log_parser"),
        write_report=report_write,
        report_path=report_path,
    )
    if report_write:
        destination = report_path or str(
            Path(state.auxdir) / f"{state.output_name}.pytexmk-report.json"
        )
        console.print("[dim]" + _("诊断报告: ") + destination + "[/dim]")
    if getattr(args, "fail_on", "none") == "warning" and warning_count:
        console.print(
            "[bold red]"
            + _("--fail-on warning：出现 %(n)s 个警告，按失败退出") % {"n": warning_count}
            + "[/bold red]"
        )
        from ..lifecycle import EXIT_WARNING_POLICY, exit_pytexmk

        exit_pytexmk(EXIT_WARNING_POLICY)

    if getattr(args, "synctex_check", False):
        _check_synctex(state)


def _check_synctex(state: WorkflowState) -> None:
    """编译成功后校验 SyncTeX 正/反向定位；失败以专用错误码退出。"""
    from ..lifecycle import EXIT_SYNCTEX_CHECK, exit_pytexmk
    from ..synctex import check

    report = check(
        Path(state.outdir) / f"{state.output_name}.pdf",
        Path(f"{state.project_name}.tex"),
        root=".",
    )
    if report.ok:
        console.print("[green]" + report.summary() + "[/green]")
        return
    console.print("[bold red]" + _("SyncTeX 校验失败") + "[/bold red]")
    for error in report.errors:
        console.print(f"  [red]{error}[/red]")
    for line in report.raw_tail:
        console.print(f"  [dim]{line}[/dim]")
    console.print(
        "  [dim]"
        + _("编辑器的“跳到 PDF/跳到源码”会失效；检查 .synctex.gz 是否与 PDF 同目录同名")
        + "[/dim]"
    )
    exit_pytexmk(EXIT_SYNCTEX_CHECK)


def _run_preflight(state: WorkflowState) -> bool:
    """返回 True 表示可以继续编译；False 表示有致命问题。"""
    from ..preflight import check_project, format_report

    report = check_project(state.project_name, Path("."))
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
            + _("确认无误时可加 --no-preflight 跳过检查")
            + "[/dim]"
        )
        return False
    return True


def _apply_build_overrides(args, state: WorkflowState) -> None:
    """把命令行构建参数合进 state（命令行优先级最高）。"""
    if getattr(args, "native_build", None) is not None:
        state.native_build = bool(args.native_build)
    if getattr(args, "shell_escape", None) is not None:
        state.shell_escape = "true" if args.shell_escape else "false"
    if getattr(args, "interaction", None):
        state.interaction = args.interaction
    if getattr(args, "extra_args", None):
        state.extra_args.extend(str(a) for a in args.extra_args)
    if getattr(args, "max_runs", None) is not None:
        state.max_extra_compilations = max(1, int(args.max_runs))
    if getattr(args, "includeonly", None):
        # 用户常写成 sec1.tex / 带空格；TeX 的 \includeonly 只接受不带扩展名的名字。
        args.includeonly = ",".join(
            part.strip().removesuffix(".tex")
            for part in str(args.includeonly).split(",")
            if part.strip()
        )
        # 部分编译必须隔离：否则会覆盖完整构建的 PDF/aux，破坏增量基线。
        state.outdir = str(Path(state.outdir) / "partial")
        state.auxdir = str(Path(state.auxdir) / "partial")
        state.preview_after_compile = False
        console.print(
            "[yellow]"
            + _("部分编译模式：仅输出到 %(o)s，不会覆盖完整构建")
            % {"o": state.outdir}
            + "[/yellow]"
        )
    if getattr(args, "quiet", False):
        state.non_quiet = False


def _repair_truncated_aux_files(state: WorkflowState) -> None:
    """删除被中断的编译留下的截断辅助文件（.aux/.toc/.out/... ）。

    辅助文件刚被搬回项目根目录，此时若某个文件是"写到一半"的状态，
    下一次 LaTeX 会以 ``File ended while scanning use of \\@writefile``
    失败，而且此后每次都会失败 —— 因为坏文件还在原处。这里直接删除，
    让本轮编译完整重建它们。
    """
    repaired = repair_auxiliary_files(
        [Path("."), Path(state.auxdir)],
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

    三个必要条件缺一不可：
      1. 上次编译判定为收敛（存在无法消除的残留警告时也照样算收敛，
         因为再编译也改变不了它们）；
      2. 所有 ``.tex`` 源文件的 ``(size, mtime_ns)`` 与上次快照一致；
      3. 构建产物摘要与上次基线一致，且 PDF 确实存在。
    用户显式指定 ``-fr/--force-rebuild`` 或 ``-dr/--draft`` 时永不跳过。
    """
    if getattr(args, "force_rebuild", False) or getattr(args, "draft", False):
        return False
    if getattr(args, "includeonly", None):
        return False

    try:
        tracker = BuildState(state.auxdir, state.output_name)
        if not tracker.was_converged():
            return False
        if not tracker.baseline_matches_current():
            return False
        if not Path(state.outdir, f"{state.output_name}.pdf").exists():
            return False
        if not tracker.sources_unchanged(_iter_source_files_for_state(state)):
            return False
        # C2：构建参数变了（换引擎/换目录/开关 shell-escape）必须重编，
        # 否则"源文件没动"会把两个不可比的 PDF 当成同一个。
        previous_key = tracker.build_key()
        return bool(previous_key) and previous_key == _current_build_key(state)
    except Exception:  # 状态文件不可用就老老实实编译
        return False


def _current_build_key(state: WorkflowState) -> str:
    """按当前 state 计算构建参数指纹（与 compile_engine 落盘时同口径）。"""
    from ..compile import detect_shell_escape
    from ..version import __version__

    if str(state.shell_escape).lower() == "auto":
        from ..compile_engine import _iter_tex_sources

        shell_escape = detect_shell_escape(_iter_tex_sources(state.project_name))
    else:
        shell_escape = state.shell_escape not in ("false", "0", "no", "off")

    return _build_key({
        "engine": state.compiled_program,
        "interaction": state.interaction or ("nonstopmode" if state.non_quiet else "batchmode"),
        "shell_escape": bool(shell_escape),
        "draft": bool(getattr(state.args, "draft", False)),
        "native": bool(state.native_build),
        "outdir": str(state.outdir),
        "auxdir": str(state.auxdir),
        "extra_args": list(state.extra_args),
        "jobname": state.output_name,
        "version": __version__,
    })


def _iter_source_files_for_state(state: WorkflowState):
    """C1：源快照覆盖 .tex + .fls 依赖（图片/宏包/bib）。"""
    from ..compile_engine import _iter_source_files

    yield from _iter_source_files(state.project_name, state.auxdir, fls_name=state.output_name)


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
    try:
        BuildState(state.auxdir, state.output_name).discard()
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
            + _("建议先运行 [bold cyan]pytexmk -c[/bold cyan] 清理后再重试。[/yellow]")
        )
