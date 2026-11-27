"""
 =======================================================================
 ····Y88b···d88P················888b·····d888·d8b·······················
 ·····Y88b·d88P·················8888b···d8888·Y8P·······················
 ······Y88o88P··················88888b·d88888···························
 ·······Y888P··8888b···88888b···888Y88888P888·888·88888b·····d88b·······
 ········888······"88b·888·"88b·888·Y888P·888·888·888·"88b·d88P"88b·····
 ········888···d888888·888··888·888··Y8P··888·888·888··888·888··888·····
 ········888··888··888·888··888·888···"···888·888·888··888·Y88b·888·····
 ········888··"Y888888·888··888·888·······888·888·888··888··"Y88888·····
 ·······························································888·····
 ··························································Y8b·d88P·····
 ···························································"Y88P"······
 =======================================================================

 -----------------------------------------------------------------------
Author       : 焱铭
Date         : 2024-08-06 22:17:51 +0800
LastEditTime : 2025-04-30 17:49:55 +0800
Github       : https://github.com/YanMing-lxb/
FilePath     : /PyTeXMK/src/pytexmk/compile_engine.py
Description  :
 -----------------------------------------------------------------------
模块职责边界（架构 FR-A3）：负责【主编译流程编排 + while 收敛调度】。
  具体职责：
    1. while 收敛循环的驱动、max_extra_compilations=10 安全上限、草稿模式开关。
    2. 子步骤时间统计：缩写序数 1st/2nd/... 对应 runtime_dict 写入。
    3. XeLaTeX 专属 dvipdfmx 后置调度；最终「完成所有编译」Banner 打印。
  调用依赖关系拓扑：
    cli.cli_workflow.run_workflow 通过 `from ..compile_engine import RUN` 作为唯一入口调用；
    compile_engine.py 实例化 compile.CompileLaTeX 执行实际编译 + 检测编排。
  下游依赖：
    compile / compile_report / tex_project / timing / ui_messages / language。
"""

import contextlib
import hashlib
import json
import re
from pathlib import Path

from pytexmk.build_state import BuildState
from pytexmk.compile import (
    CompileLaTeX,
    detect_shell_escape,
    effective_interaction,
    normalize_shell_escape_flag,
)
from pytexmk.compile_report import print_compile_report, print_compile_separator
from pytexmk.detection import BIBTEX_STYLE_PATTERN
from pytexmk.fls import iter_fls_records
from pytexmk.language import set_language
from pytexmk.layout import DEPENDENCY_SUFFIXES, GENERATED_DIRS
from pytexmk.tex_project import MainFileOperation, standardize_name
from pytexmk.timing import ordinal, time_count
from pytexmk.ui_messages import print_message
from pytexmk.version import __version__

_ = set_language("compile_engine")
MFO = MainFileOperation()  # 实例化 MainFileOperation 类

# 变更类维度：只有这些维度非零，才代表"再编译一次可能改变结果"。
# log 维度只是警告信号，它本身无法被继续编译消除，因此不参与推进判断。
ACTIONABLE_DIMS = ("bib", "idx", "toc", "aux", "out")


def _accumulate_tool_time(
    runtime_dict: dict[str, float],
    prefix: str,
    tool: str,
    seconds: float,
    round_no: int,
) -> None:
    """累加同类工具的总时长，并按轮次留一条明细键供调用次数统计。

    旧实现用同一个键反复赋值：第二遍 ``bibtex`` 直接覆盖第一遍，表里只
    剩一轮耗时，差额被总时长减法的残差算进 “Python 时长”。现在合计键
    保留（兼容 ``--json``），``bib_bibtex_1`` / ``bib_bibtex_2`` 明细键
    给出真实调用次数。
    """
    total_key = f"{prefix}_{tool}"
    runtime_dict[total_key] = round(runtime_dict.get(total_key, 0.0) + seconds, 4)
    runtime_dict[f"{total_key}_{round_no}"] = seconds

# 额外编译次数的安全上限（总编译次数 = 1 + 该值）。
# 正常情况下不动点检测会在 3~4 轮内收敛，上限仅用于防御"每轮都产生新指纹"的
# 病态项目（例如某宏包把时间戳写进 .aux），把最坏情况限制在 9 次以内。
#: 额外编译轮次的安全上限默认值。每轮编译都通过 ``RUN(max_extra=...)``
#: 解析成局部值传进编译主体：0.5 把它当模块级全局并在 RUN 里改写，``-ap`` 多
#: 子项目 / ``--watch`` 多轮之间会互相串味，且不是线程安全的。
DEFAULT_MAX_EXTRA_COMPILATIONS = 8

#: 源快照要跳过的目录（产物副本所在处，不是源）
_EXCLUDED_SOURCE_DIRS = GENERATED_DIRS


def _ordinal(n: int) -> str:
    """1 → "1st"、2 → "2nd"、11 → "11th"；实现见 ``timing.ordinal``。"""
    return ordinal(n)


def _has_actionable_work(dims: dict[str, int]) -> bool:
    """是否还存在"继续编译可能改变结果"的维度。"""
    return any(dims.get(key, -1) > 0 for key in ACTIONABLE_DIMS)


def _first_round_stop_reason(dims: dict[str, int], tools_pending: bool) -> str:
    """首轮能否直接判定 ``stable``。

    变更类维度全部归零只说明前一次留下的辅助文件已到不动点；若外部工具刚写出
    尚未被 TeX 消费的 ``.bbl/.ind``，必须再编一轮，不能提前收工。
    """
    if _has_actionable_work(dims) or tools_pending:
        return ""
    return "stable"


def _convergence_stop_reason(
    dims: dict[str, int],
    seen_fingerprints: list[str],
    current_fingerprint: str,
    signals: dict[str, list[str]] | None = None,
) -> str:
    """判断是否应当停止 while 收敛，返回停止原因（空串表示继续编译）。

    判定优先级（自上而下，命中即停）：

    1. ``fixed_point`` / ``cycle`` —— 本轮产物指纹已在历史中出现过。
       指纹相同意味着"再跑一次 LaTeX 会得到完全一样的结果"，继续编译纯属空转。
    2. ``stable`` —— 所有变更类维度归零（bib/idx/toc/aux/out 全为 0），
       即辅助文件已经不动了，说明上一轮写出的内容已被完整读回并固化。
    3. ``log_stalled`` —— 仍有变更类维度非零，但日志里只剩**永久性**信号
       （未定义引用 / 重复标签），且没有 `Label(s) may have changed` 这类
       跨轮引用警告。这些维度是被永久信号"连累"的：再编一轮也只会得到同样的
       警告，属于无效等待，直接停。

    第 3 条就是省掉"确认轮"的核心：当辅助文件还在动、但日志已明确告诉我们
    "剩下的问题改源码才能解决"时，不必真的再编一轮去验证。

    反过来，只要日志里存在 ``transient`` 信号（`Label(s) may have changed`、
    `Rerun to get cross-references right` 等），就必须再编一轮让 LaTeX 自己
    确认引用已收敛 —— 这类信号正是 LaTeX 内核给出的权威判断，可信度高于任何
    文件摘要比对。
    """
    if current_fingerprint in seen_fingerprints:
        previous = seen_fingerprints[-1] if seen_fingerprints else None
        return "fixed_point" if current_fingerprint == previous else "cycle"

    if not _has_actionable_work(dims):
        return "stable"

    if dims.get("log", -1) > 0 and signals is not None:
        transient = signals.get("transient") or []
        permanent = signals.get("permanent") or []
        # 只剩永久信号时，非零维度只是被它们拖着的"伪需求"
        if permanent and not transient:
            return "log_stalled"

    return ""


# --------------------------------------------------------------------------------
# 整体进行编译
# --------------------------------------------------------------------------------
def _run_xdv_if_needed(compiled_program, native, compile_model, runtime_dict) -> None:
    """XeLaTeX 传统两段式：**非 native** 时才需要 dvipdfmx 把 `.xdv` 转 PDF。

    判断集中在这一处：漏过 `not native` 时，native 构建（xelatex 直接输出 PDF、
    根本没有 `.xdv`）仍会调用 `dvipdfmx Auxiliary\\xxx.xdv`，得到“编译成功却以
    退出码 5 结束”。
    """
    if compiled_program != "XeLaTeX" or native:
        return
    print_message(_("DVIPDFMX 编译"), "running")
    runtime_dict["dvipdfmx"] = time_count(compile_model.compile_xdv).seconds


def RUN(
    runtime_dict,
    project_name,
    compiled_program,
    out_files,
    aux_files,
    outdir,
    auxdir,
    non_quiet,
    draft,
    *,
    shell_escape="true",
    synctex=True,
    native=False,
    extra_args=None,
    interaction=None,
    jobname=None,
    max_extra=None,
):
    # 草稿模式函数启用
    """主编译流程：草稿模式、多轮 LaTeX/Bib/Index 编译、统计时长。"""
    max_extra_value = (
        DEFAULT_MAX_EXTRA_COMPILATIONS if max_extra is None else int(max_extra)
    )

    if str(shell_escape).lower() == "auto":
        shell_escape = detect_shell_escape(_iter_tex_sources(project_name))
    else:
        shell_escape = normalize_shell_escape_flag(shell_escape)

    # draft=True：加 draft 并写跨进程标记；draft=False：消费上次崩溃留下的
    # 标记（没有标记就不碰作者的 documentclass）。
    MFO.draft_model(project_name, enabled=draft, auxdir=auxdir)

    # 编译前的准备工作
    compile_model = CompileLaTeX(
        project_name, compiled_program, out_files, aux_files, outdir, auxdir,
        non_quiet=non_quiet,
        shell_escape=shell_escape, synctex=synctex, native=native, extra_args=extra_args,
        interaction=interaction, jobname=jobname,
    )
    detector = compile_model.detector

    try:
        return _run_impl(
            runtime_dict, project_name, compiled_program, compile_model, detector,
            outdir, auxdir,
            draft=draft, shell_escape=shell_escape, native=native, interaction=interaction,
            max_extra=max_extra_value,
        )
    finally:
        # C3：草稿模式必须自愈。无论是正常结束、编译失败调用 exit_pytexmk，
        # 还是 Ctrl+C，源文件都要恢复原样，绝不能把 draft 选项留在用户仓库里。
        MFO.restore_draft()


def _run_pythontex_if_present(compile_model, runtime_dict, compiled_program) -> bool:
    """若首轮 LaTeX 生成了 ``.pytxcode``，先跑 pythontex，再补一轮 LaTeX。

    pythontex 是「LaTeX → pythontex → LaTeX」的三段式流程；不补最后一轮
    LaTeX，用户只会看到代码块未展开的 PDF。这里不新增收敛维度，补跑后
    仍交给正常检测循环判断是否还需要更多轮。
    """
    if not compile_model.has_pythontex_code():
        return False
    print_message(_("pythontex 处理代码块"), "running")
    runtime_dict["pythontex"] = time_count(compile_model.compile_pythontex).seconds
    print_message(_("pythontex 后重新编译 LaTeX"), "running")
    runtime_dict["latex_after_pythontex"] = time_count(
        compile_model.compile_tex
    ).seconds
    return True


def _run_impl(
    runtime_dict,
    project_name,
    compiled_program,
    compile_model,
    detector,
    outdir,
    auxdir,
    draft,
    shell_escape,
    native,
    interaction,
    *,
    max_extra,
):
    """RUN 的实际主体（拆出来才能用 try/finally 包住草稿模式自愈）。"""
    build_options = _build_options(
        compiled_program,
        compile_model,
        outdir,
        auxdir,
        draft,
        shell_escape,
        native,
        interaction,
        max_extra,
    )

    runtime_read, return_read, _err = time_count(
        detector.prepare_LaTeX_output_files,
    )  # 读取 LaTeX 文件
    # time_count 返回 Timed(seconds, value, error)，这里只关心耗时与返回值
    cite_counter, toc_file, index_aux_content_dict_old = return_read  # 获取 read_LaTeX_files 函数得到的参数
    runtime_dict["detect_aux"] = runtime_read

    aux_content_old, out_content_old = detector.prepare_aux_out_snapshots()

    # 构建基线：上次编译落盘在共享状态文件里的产物摘要与收敛标记。
    # 它在进程重启后依然有效，因此冷启动时不必靠"多编一轮"重新观察。
    build_state = BuildState(auxdir, compile_model.jobname)

    # 首次编译 LaTeX 文档
    print_message(_("1 次 %(args)s 编译") % {"args": compiled_program}, "running")
    runtime_Latex = time_count(
        compile_model.compile_tex,
    ).seconds
    runtime_dict["latex_1"] = runtime_Latex

    # PythonTeX 的中间代码只会在首轮 LaTeX 后出现；先处理并补一轮 LaTeX，
    # 再进入常规六维检测，避免用户拿到代码块未展开的 PDF。
    _run_pythontex_if_present(compile_model, runtime_dict, compiled_program)

    # 首次编译后：run_full_detection 聚合 6 维检测 + 返回子步骤 schedule 所需值
    runtime_detect, return_detect, _err = time_count(
        detector.run_full_detection,
        cite_counter_old=cite_counter,
        toc_file_old=toc_file,
        index_aux_content_old=index_aux_content_dict_old,
        aux_content_old=aux_content_old,
        out_content_old=out_content_old,
    )
    detection = return_detect
    dims = detection.dims
    latex_compilation_times = detection.latex_compilation_times
    runtime_dict["detect_state"] = runtime_detect

    # 记录已经跑过的文献/索引任务，避免同一状态下重复调用外部工具
    bib_signature_done: str | None = None
    bib2gls_done = False
    index_signature_done: str | None = None
    #: 当前 LaTeX 轮次（1 = 首轮）；closure 在首轮工具调用前就要读到它。
    current_times = 1
    total_compilations = 1
    #: 外部工具（bibtex/biber/bib2gls/makeindex）是否在最近一轮 TeX 之后写出了
    #: 尚未被 TeX 消费的新产物。此时不能把构建标成“稳定”——否则下一轮会跳过
    #: 编译，PDF 里永远是旧参考文献/旧索引。
    tools_pending = False

    def _record_tool_time(prefix: str, tool: str, seconds: float) -> None:
        _accumulate_tool_time(runtime_dict, prefix, tool, seconds, current_times)

    def _run_bib_if_needed(det) -> None:
        """按需执行 bibtex/biber（以及 glossaries-extra 的 bib2gls）。

        同一 ``.aux`` 状态只跑一次外部工具。bib2gls 分支的开关必须从
        ``detector.bib2gls_mode`` 读：``det`` 是 ``DetectionResult``，它只带
        dims/次数/bib_engine 等聚合结果，从来没有 ``bib2gls_mode`` 字段，
        早期用 ``getattr(det, "bib2gls_mode", False)`` 求值恒为 False，
        导致 bib2gls 项目既不跑索引工具、也不跑 bib2gls，术语表静默为空。

        另外 bib2gls 与文献引擎解耦：只用 ``\\gls`` 而不 ``\\cite`` 的文档
        ``bib_engine`` 可能为空，但术语表仍然要由 bib2gls 生成。
        """
        nonlocal bib_signature_done, bib2gls_done, tools_pending
        needs_bib = bool(det.bib_engine) and det.latex_compilation_times_bib != 0
        needs_bib2gls = bool(getattr(detector, "bib2gls_mode", False)) and not bib2gls_done
        if not needs_bib and not needs_bib2gls:
            return
        signature = detector.aux_signature()
        if signature == bib_signature_done and not needs_bib2gls:
            return
        if needs_bib:
            print_message(_("%(args)s 编译文献") % {"args": det.bib_engine}, "running")
            runtime_bib = time_count(compile_model.compile_bib, det.bib_engine).seconds
            _record_tool_time("bib", det.bib_engine, runtime_bib)
            tools_pending = True
        if needs_bib2gls:
            print_message(_("bib2gls 编译术语表"), "running")
            runtime_b2g = time_count(compile_model.compile_bib2gls).seconds
            runtime_dict["bib2gls"] = round(runtime_dict.get("bib2gls", 0.0) + runtime_b2g, 4)
            bib2gls_done = True
            tools_pending = True
        bib_signature_done = signature

    def _run_index_if_needed(det) -> None:
        """按需执行 makeindex/xindy；同一索引输入状态只跑一次。"""
        nonlocal index_signature_done, tools_pending
        if not det.index_run_cmds:
            return
        signature = detector.index_signature()
        if signature == index_signature_done:
            return
        for cmd in det.index_run_cmds:
            print_message(_("%(args)s 编译") % {"args": cmd[0]}, "running")
            runtime_index = time_count(compile_model.compile_index, cmd).seconds
            _record_tool_time("index", cmd[0], runtime_index)
            tools_pending = True
        index_signature_done = signature

    # 编译参考文献 / 索引（首轮）
    _run_bib_if_needed(detection)
    _run_index_if_needed(detection)

    seen_fingerprints: list[str] = [detector.state_fingerprint()]
    stop_reason = ""
    signals: dict[str, list[str]] = detector.classify_signals()

    # 首轮就可能已收敛：若首轮后所有变更维度归零，说明前一次编译留下的辅助
    # 文件已经把结果带到了不动点，无需再编。但如果外部工具刚写出尚未消费的
    # .bbl/.ind，就不能算稳定——必须再跑一轮 LaTeX 把它读进来。
    stop_reason = _first_round_stop_reason(dims, tools_pending)

    print_compile_separator()
    print_compile_report(
        round_index=1,
        next_extra_compilations=latex_compilation_times,
        total_compilations=1,
        dims=dims,
        compiled_program=standardize_name(compiled_program),
        reached_limit=False,
        stop_reason=stop_reason,
        max_extra=max_extra,
    )

    # 进行额外的 LaTeX 编译（迭代收敛直到状态不再变化，或达到安全上限）
    while not stop_reason and latex_compilation_times > 0 and (current_times - 1) < max_extra:
        current_times += 1
        total_compilations += 1

        # 本轮编译前：更新基线并保存快照（与首轮同样计时，避免“有时计、有时不计”）
        runtime_prep, return_prep, _err = time_count(detector.prepare_LaTeX_output_files)
        cite_counter, toc_file, index_aux_content_dict_old = return_prep
        runtime_dict["detect_aux"] = round(runtime_dict.get("detect_aux", 0.0) + runtime_prep, 4)
        runtime_snap, snapshots, _err = time_count(detector.prepare_aux_out_snapshots)
        aux_content_old, out_content_old = snapshots
        runtime_dict["detect_aux"] = round(runtime_dict.get("detect_aux", 0.0) + runtime_snap, 4)

        # 执行本轮 LaTeX 编译
        print_message(
            _("%(args1)s 次 %(args2)s 编译") % {"args1": str(current_times), "args2": compiled_program},
            "running",
        )
        tools_pending = False  # 本轮 TeX 会消费掉上一轮工具写出的产物
        runtime_Latex = time_count(
            compile_model.compile_tex,
        ).seconds
        runtime_dict[f"latex_{current_times}"] = runtime_Latex

        runtime_detect, return_detect, _err = time_count(
            detector.run_full_detection,
            cite_counter_old=cite_counter,
            toc_file_old=toc_file,
            index_aux_content_old=index_aux_content_dict_old,
            aux_content_old=aux_content_old,
            out_content_old=out_content_old,
        )
        detection = return_detect
        runtime_dict["detect_state"] = round(
            runtime_dict.get("detect_state", 0.0) + runtime_detect, 4
        )
        dims = detection.dims
        latex_compilation_times = detection.latex_compilation_times

        # 本轮若仍需要文献/索引处理，就地补跑（历史实现只在循环外跑一次，
        # 导致 idx/bib 维度永远非零、循环空转到上限）
        _run_bib_if_needed(detection)
        _run_index_if_needed(detection)

        current_fingerprint = detector.state_fingerprint()
        signals = detector.classify_signals()
        stop_reason = _convergence_stop_reason(dims, seen_fingerprints, current_fingerprint, signals)
        seen_fingerprints.append(current_fingerprint)

        reached_limit = (current_times - 1) >= max_extra and latex_compilation_times > 0
        if stop_reason and tools_pending:
            # 外部工具刚写出新 .bbl/.ind：即使辅助文件指纹已稳定，也还要一轮
            # LaTeX 才能把它们读进 PDF。预算耗尽时单独记为 tool-pending。
            stop_reason = "tool-pending" if reached_limit else ""
        if not stop_reason and reached_limit:
            stop_reason = "limit"

        print_compile_separator()
        print_compile_report(
            round_index=current_times,
            next_extra_compilations=latex_compilation_times,
            total_compilations=total_compilations,
            dims=dims,
            compiled_program=standardize_name(compiled_program),
            reached_limit=reached_limit,
            stop_reason=stop_reason,
            max_extra=max_extra,
        )
        if stop_reason:
            break

    # 编译完成, 开始判断编译 XDV 文件
    _run_xdv_if_needed(compiled_program, native, compile_model, runtime_dict)

    # 停止原因的最终归一化：空串绝不能落到“stable”。
    # - `tool-pending`：外部工具产物尚未被 TeX 消费（预算耗尽时）；
    # - `limit`：LaTeX 仍要求再跑，但额外轮次预算用完；
    # - `stable`：确实没有变更类工作。
    if not stop_reason:
        if tools_pending:
            stop_reason = "tool-pending"
        elif latex_compilation_times > 0:
            stop_reason = "limit"
        else:
            stop_reason = "stable"
    elif stop_reason == "stable" and tools_pending:
        stop_reason = "tool-pending"

    if not compile_model.verify_pdf_exists():
        print_message(_("未检测到编译输出的 PDF，请检查日志"), "warning")

    # 显示编译过程中关键信息
    print_message(_("完成所有编译"), "success")

    # 收尾提示：把"再编译也消不掉"的警告明确告诉用户，避免用户以为是编译流程的问题
    residual_notes = detector.residual_warnings()
    if residual_notes:
        for note in residual_notes:
            print_message(_("未能消除：%(args)s") % {"args": note}, "additional")

    # 落盘构建基线：产物摘要 + 收敛标记 + 源快照 + 构建参数指纹。
    # 有了它，下次运行时"源文件是否变过"无需再编一轮就能判断。
    _persist_build_state(
        build_state,
        round_no=total_compilations,
        fingerprint=detector.state_fingerprint(),
        dims=dims,
        signals=signals,
        stop_reason=stop_reason,
        project_name=project_name,
        build_key=_build_key(build_options),
    )

    return runtime_dict


def _persist_build_state(
    build_state: BuildState,
    *,
    round_no: int,
    fingerprint: str,
    dims: dict[str, int],
    signals: dict[str, list[str]],
    stop_reason: str,
    project_name: str,
    build_key: str = "",
) -> None:
    """把本轮结束时的状态写进共享状态文件（失败绝不阻断编译结果）。

    注意：**只有收敛的构建才标记 ``converged``**。若停在 ``limit``（安全上限
    用尽）或 ``tool-pending``（外部工具产物尚未被 TeX 消费），结果可能并未稳定，
    此时绝不能写入收敛标记，否则下一次运行会误判"源未变可跳过"。
    """
    converged = stop_reason in {"stable", "converged", "fixed_point", "log_stalled"}
    with contextlib.suppress(Exception):  # 状态文件问题不影响编译成功
        build_state.save_round(
            round_no=round_no,
            fingerprint=fingerprint,
            dims=dims,
            signals=signals,
            stop_reason=stop_reason,
            converged=converged,
            sources=build_state.source_snapshot(
                _iter_source_files(
                    project_name,
                    str(build_state.auxdir),
                    fls_name=build_state.project_name,
                )
            ),
            build_key=build_key,
            # 记录日志摘要：缓存命中时必须能证明“复用到的诊断”就是这一轮的日志，
            # 而不是被删除/替换过的旧文件。
            diagnostics=build_state.log_record(),
        )


def _build_options(
    compiled_program,
    compile_model,
    outdir,
    auxdir,
    draft,
    shell_escape,
    native,
    interaction,
    max_extra,
) -> dict:
    """收集参与构建指纹的参数；改这里必须同步 ``tests/unit/test_build_key.py``。"""
    return {
        "engine": compiled_program,
        "interaction": effective_interaction(interaction),
        "shell_escape": bool(shell_escape),
        "synctex": bool(compile_model.synctex),
        "draft": bool(draft),
        "native": bool(native),
        "outdir": str(outdir),
        "auxdir": str(auxdir),
        "jobname": compile_model.jobname,
        "extra_args": list(compile_model.extra_args),
        # 轮次预算也是构建参数：0 与 8 得到的收敛程度完全不同，不能共用同一份
        # 复用基线（旧实现漏了它，改预算后仍会跳过编译）。
        "max_extra": int(max_extra),
        "version": __version__,
    }


def _build_key(options: dict) -> str:
    """构建参数指纹：任何一项变化都必须让"源未变可跳过"失效。"""
    payload = json.dumps(options, sort_keys=True, ensure_ascii=False, default=str)
    return "sha256:" + hashlib.sha256(payload.encode("utf-8")).hexdigest()


#: 依赖快照要覆盖的源/资源后缀（定义见 pytexmk.layout）
_SOURCE_SUFFIXES = DEPENDENCY_SUFFIXES

#: 外部文献/索引工具真正读取的输入后缀。`.fls` 不一定记录它们
#: （实测 MiKTeX 的 recorder 会漏掉 bib），必须单独纳入依赖快照，
#: 否则“只改 references.bib”永远触发不了重编。
_TOOL_INPUT_SUFFIXES = frozenset({".bib", ".bst", ".ist", ".xdy"})

_BIBDATA_RE = re.compile(r"\\bibdata\{([^}]*)\}")
_BCF_DATASOURCE_RE = re.compile(
    r"<bcf:datasource[^>]*>([^<]+)</bcf:datasource>", re.IGNORECASE
)


def _read_text(path: Path) -> str:
    """读文本，失败返回空串（依赖解析永不阻断编译）。"""
    try:
        return path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""


def _aux_chain(main_aux: Path) -> list[Path]:
    """主 .aux 及其 ``\\@input{...}`` 引用到的章节 .aux（去重、保序）。"""
    result: list[Path] = []
    seen: set[str] = set()

    def add(path: Path) -> None:
        try:
            key = str(path.resolve())
        except OSError:
            key = path.as_posix()
        if key not in seen and path.is_file():
            seen.add(key)
            result.append(path)

    add(main_aux)
    if not main_aux.is_file():
        return result
    for name in re.findall(r"\\@input\{([^}]*)\}", _read_text(main_aux)):
        target = Path(name.strip())
        if not target.is_absolute():
            target = main_aux.parent / target
        add(target)
    return result


def _resolve_tool_input(raw: str, root: Path) -> Path | None:
    """把一个工具输入名解析成真实存在的文件（相对引擎工作目录）。"""
    name = raw.strip()
    if not name:
        return None
    candidate = Path(name.replace("\\", "/"))
    if candidate.is_absolute():
        return candidate if candidate.is_file() else None
    probes = [root / candidate]
    if not candidate.suffix:
        probes.extend(root / f"{candidate}{suffix}" for suffix in (".bib", ".bst"))
    for probe in probes:
        if probe.is_file():
            return probe
    return None


def _tool_input_files(project_name: str, auxdir: str, jobname: str) -> list[Path]:
    """从 ``.aux`` / ``.bcf`` 解析 BibTeX/Biber 的数据库与样式输入。

    解析不完整（没有 ``\\bibdata``/``datasource``）时返回空列表，由调用方按
    后缀做保守兜底扫描：宁可多编译一次，也不能漏掉作者改过的文献。
    """
    root = Path.cwd()
    names: list[str] = []
    main_aux = Path(auxdir) / f"{jobname}.aux"
    if not main_aux.is_file():
        main_aux = Path(f"{jobname}.aux")
    for aux_path in _aux_chain(main_aux):
        text = _read_text(aux_path)
        for match in _BIBDATA_RE.finditer(text):
            names.extend(part for part in match.group(1).split(","))
        for match in BIBTEX_STYLE_PATTERN.finditer(text):
            names.append(match.group(1))

    bcf_candidates = [Path(auxdir) / f"{jobname}.bcf", Path(f"{jobname}.bcf")]
    for bcf in bcf_candidates:
        if bcf.is_file():
            names.extend(_BCF_DATASOURCE_RE.findall(_read_text(bcf)))
            break

    paths: list[Path] = []
    seen: set[str] = set()
    for raw in names:
        resolved = _resolve_tool_input(raw, root)
        if resolved is None:
            continue
        key = str(resolved.resolve())
        if key not in seen:
            seen.add(key)
            paths.append(resolved)
    return paths


def _scan_tool_inputs() -> list[Path]:
    """没有可信解析结果时的兜底：扫描项目内常见的工具输入文件。"""
    root = Path.cwd()
    found: list[Path] = []
    for path in root.rglob("*"):
        if not path.is_file() or path.suffix.lower() not in _TOOL_INPUT_SUFFIXES:
            continue
        parts = path.relative_to(root).parts[:-1]
        if any(part.startswith(".") or part in _EXCLUDED_SOURCE_DIRS for part in parts):
            continue
        found.append(path)
    return found


def _fls_inputs(project_name: str, auxdir: str) -> list[Path]:
    """解析 ``-recorder`` 生成的 .fls 中的 INPUT 行（真实参与编译的文件）。"""
    for candidate in (Path(auxdir) / f"{project_name}.fls", Path(f"{project_name}.fls")):
        if not candidate.exists():
            continue
        workdir = Path.cwd()
        inputs: dict[Path, None] = {}
        outputs: set[Path] = set()
        for kind, raw in iter_fls_records(candidate):
            try:
                path = (workdir / raw).resolve()
                if kind == "PWD":
                    workdir = path
                elif kind == "OUTPUT":
                    outputs.add(path)
                elif path.is_file():
                    inputs[path] = None
            except (OSError, ValueError):
                continue
        return [path for path in inputs if path not in outputs]
    return []


def _iter_source_files(project_name: str, auxdir: str | None = None, fls_name: str | None = None):
    """参与"源是否变过"判断的文件集合（C1）。

    组合三类来源，去重后逐个产出：
      1. 任意深度的 ``.tex``（与 ``_iter_tex_sources`` 相同的排除规则）；
      2. ``-recorder`` 的 ``.fls`` 里 INPUT 记录的真实依赖（图片、宏包、bib…）；
      3. 没有 .fls（首次编译/被清理）时，按后缀兜底扫描常见资源类型。

    ``fls_name`` 是 TeX jobname（``--jobname`` 时 ``<jobname>.fls``），
    源文件枚举仍以 ``project_name`` 为准。
    """
    seen: set[str] = set()

    def _key(path: Path) -> str:
        try:
            return str(path.resolve())
        except OSError:
            return path.as_posix()

    for path in _iter_tex_sources(project_name):
        key = _key(path)
        if key not in seen:
            seen.add(key)
            yield path

    fls_paths: list[Path] = []
    stem = fls_name or project_name
    for candidate in (Path(auxdir or ".") / f"{stem}.fls", Path(f"{stem}.fls")):
        if candidate.exists():
            fls_paths = _fls_inputs(stem, auxdir or ".")
            break
    for path in fls_paths:
        key = _key(path)
        if key not in seen:
            seen.add(key)
            yield path

    # 外部工具的实际输入独立于 .fls：BibTeX 从 .aux 的 \bibdata/\bibstyle，
    # Biber 从 .bcf 的 datasource 读取。解析不到时按后缀保守兜底。
    tool_inputs = _tool_input_files(project_name, auxdir or ".", stem)
    if not tool_inputs:
        tool_inputs = _scan_tool_inputs()
    for path in tool_inputs:
        key = _key(path)
        if key not in seen:
            seen.add(key)
            yield path

    if fls_paths:
        return  # .fls 已经给出真实依赖清单，无需再做后缀兜底扫描

    cwd = Path.cwd()
    # 主输出 PDF 也是 .pdf，但它不是“输入依赖”；只按路径身份排除根目录的
    # <jobname>.pdf，不能按后缀把 \includegraphics 引用的 PDF 图片一并跳过。
    output_pdf_names = {f"{project_name}.pdf", f"{stem}.pdf"}
    for path in cwd.rglob("*"):
        if not path.is_file() or path.suffix.lower() not in _SOURCE_SUFFIXES:
            continue
        if path.parent == cwd and path.name in output_pdf_names:
            continue
        parts = path.relative_to(cwd).parts[:-1]
        if any(part.startswith(".") or part in _EXCLUDED_SOURCE_DIRS for part in parts):
            continue
        key = _key(path)
        if key in seen:
            continue
        seen.add(key)
        yield path


def _iter_tex_sources(project_name: str):
    """枚举参与编译的 ``.tex`` 源文件。

    只看**当前工作目录**（``pytexmk -s`` 会先 chdir 到子项目目录）：
      * 主文件 ``<project>.tex``
      * 任意深度的 ``*.tex``，但跳过隐藏目录、输出/辅助目录，
        以及**带独立 ``.pytexmkrc`` 的子项目目录**

    为什么排除子项目：论文仓库里往往还躺着 ``Cover/``、``Review/`` 这类
    各自带主文件和配置的独立项目，它们编译出的是另一个 PDF，改动它们不该
    触发本项目重编译。判定依据是"该目录有自己的 ``.pytexmkrc``"——这比硬编码
    目录名可靠，用户自定义的子项目也能被正确识别。
    """
    main_tex = Path(f"{project_name}.tex")
    seen: set[str] = set()

    if main_tex.exists():
        seen.add(main_tex.as_posix())
        yield main_tex

    cwd = Path.cwd()
    for path in Path().rglob("*.tex"):
        posix = path.as_posix()
        if posix in seen:
            continue
        parts = path.parts[:-1]
        if any(part.startswith(".") for part in parts):
            continue
        # 输出/辅助目录里的 .tex 是产物副本，不是源
        if any(part in _EXCLUDED_SOURCE_DIRS for part in parts):
            continue
        # 子项目（自带 .pytexmkrc）及其内部文件不属于本项目
        if _belongs_to_subproject(path.parent, cwd):
            continue
        seen.add(posix)
        yield path


def _belongs_to_subproject(directory: Path, stop: Path) -> bool:
    """判断 directory 是否位于某个子项目目录之内（含其本身）。

    从该目录逐级向上查找，直到当前工作目录为止；一旦遇到 ``.pytexmkrc``
    就说明它属于另一个独立项目。脚本工作目录本身的 ``.pytexmkrc`` 不算
    （那是本项目自己的配置）。
    """
    current = directory.resolve()
    while current != stop and stop in current.parents:
        if (current / ".pytexmkrc").exists():
            return True
        current = current.parent
    return False
