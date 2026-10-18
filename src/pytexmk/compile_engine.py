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
    cli.cli_workflow.run_workflow 通过 `from ..compile_engine import RUN, LaTeXDiffRUN` 作为唯一入口调用；
    compile_engine.py 实例化 compile.CompileLaTeX 执行实际编译 + 检测编排。
  下游依赖：
    compile / compile_report / tex_project / timing / ui_messages / language。
"""

from pathlib import Path

from pytexmk.build_state import BuildState
from pytexmk.compile import CompileLaTeX
from pytexmk.compile_report import print_compile_report, print_compile_separator
from pytexmk.language import set_language
from pytexmk.tex_project import MainFileOperation, standardize_name
from pytexmk.timing import time_count
from pytexmk.ui_messages import print_message

_ = set_language("compile_engine")
MFO = MainFileOperation()  # 实例化 MainFileOperation 类

# 变更类维度：只有这些维度非零，才代表"再编译一次可能改变结果"。
# log 维度只是警告信号，它本身无法被继续编译消除，因此不参与推进判断。
ACTIONABLE_DIMS = ("bib", "idx", "toc", "aux", "out")

# 额外编译次数的安全上限（总编译次数 = 1 + 该值）。
# 正常情况下不动点检测会在 3~4 轮内收敛，上限仅用于防御"每轮都产生新指纹"的
# 病态项目（例如某宏包把时间戳写进 .aux），把最坏情况限制在 9 次以内。
MAX_EXTRA_COMPILATIONS = 8

#: 源快照要跳过的目录（产物副本所在处，不是源）
_EXCLUDED_SOURCE_DIRS = frozenset({"Build", "Auxiliary", "build", "out", "output", "dist"})


def _ordinal(n: int) -> str:
    """把 1 → "1st"、2 → "2nd"、11 → "11th" 这样的序数词。

    历史实现用固定的 13 元组，编译次数一旦超过 13 就会抛 IndexError；
    改为按需生成后，上限调整不会再引入越界风险。
    """
    if 10 <= n % 100 <= 20:
        suffix = "th"
    else:
        suffix = {1: "st", 2: "nd", 3: "rd"}.get(n % 10, "th")
    return f"{n}{suffix}"


def _has_actionable_work(dims: dict[str, int]) -> bool:
    """是否还存在"继续编译可能改变结果"的维度。"""
    return any(dims.get(key, -1) > 0 for key in ACTIONABLE_DIMS)


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
):
    # 草稿模式函数启用
    """主编译流程：草稿模式、多轮 LaTeX/Bib/Index 编译、统计时长。"""
    MFO.draft_model(project_name, draft, True)

    # 编译前的准备工作
    compile_model = CompileLaTeX(project_name, compiled_program, out_files, aux_files, outdir, auxdir, non_quiet)
    detector = compile_model.detector

    runtime_read, return_read, _err = time_count(
        detector.prepare_LaTeX_output_files,
    )  # 读取 LaTeX 文件
    # PEP 758（3.15）：从左值链里直接取出三个返回值，无需括号
    cite_counter, toc_file, index_aux_content_dict_old = return_read  # 获取 read_LaTeX_files 函数得到的参数
    runtime_dict[_("检测辅助文件")] = runtime_read

    aux_content_old, out_content_old = detector.prepare_aux_out_snapshots()

    # 构建基线：上次编译落盘在共享状态文件里的产物摘要与收敛标记。
    # 它在进程重启后依然有效，因此冷启动时不必靠"多编一轮"重新观察。
    build_state = BuildState(auxdir, project_name)

    # 首次编译 LaTeX 文档
    print_message(_("1 次 %(args)s 编译") % {"args": compiled_program}, "running")
    runtime_Latex = time_count(
        compile_model.compile_tex,
    ).seconds
    runtime_dict[f"{compiled_program} {_ordinal(1)}"] = runtime_Latex

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
    runtime_dict[_("编译状态检测")] = runtime_detect

    # 记录已经跑过的文献/索引任务，避免同一状态下重复调用外部工具
    bib_signature_done: str | None = None
    index_signature_done: str | None = None

    def _run_bib_if_needed(det) -> None:
        """按需执行 bibtex/biber；同一 .aux 状态只跑一次。"""
        nonlocal bib_signature_done
        if not det.bib_engine or det.latex_compilation_times_bib == 0:
            return
        signature = detector.aux_signature()
        if signature == bib_signature_done:
            return
        print_message(_("%(args)s 编译文献") % {"args": det.bib_engine}, "running")
        runtime_bib = time_count(compile_model.compile_bib, det.bib_engine).seconds
        runtime_dict[_("%(args)s 编译") % {"args": det.bib_engine}] = runtime_bib
        bib_signature_done = signature

    def _run_index_if_needed(det) -> None:
        """按需执行 makeindex/xindy；同一索引输入状态只跑一次。"""
        nonlocal index_signature_done
        if not det.index_run_cmds:
            return
        signature = detector.index_signature()
        if signature == index_signature_done:
            return
        for cmd in det.index_run_cmds:
            print_message(_("%(args)s 编译") % {"args": cmd[0]}, "running")
            runtime_index = time_count(compile_model.compile_index, cmd).seconds
            runtime_dict[_("%(args)s 编译") % {"args": cmd[0]}] = runtime_index
        index_signature_done = signature

    # 编译参考文献 / 索引（首轮）
    _run_bib_if_needed(detection)
    _run_index_if_needed(detection)

    total_compilations = 1
    current_times = 1
    seen_fingerprints: list[str] = [detector.state_fingerprint()]
    stop_reason = ""
    signals: dict[str, list[str]] = detector.classify_signals()

    # 首轮就可能已收敛：若首轮后所有变更维度归零，说明前一次编译留下的辅助
    # 文件已经把结果带到了不动点，无需再编。
    if not _has_actionable_work(dims):
        stop_reason = "stable"

    print_compile_separator()
    print_compile_report(
        round_index=1,
        next_extra_compilations=latex_compilation_times,
        total_compilations=1,
        dims=dims,
        compiled_program=standardize_name(compiled_program),
        reached_limit=False,
        stop_reason=stop_reason,
        max_extra=MAX_EXTRA_COMPILATIONS,
    )

    # 进行额外的 LaTeX 编译（迭代收敛直到状态不再变化，或达到安全上限）
    while not stop_reason and latex_compilation_times > 0 and (current_times - 1) < MAX_EXTRA_COMPILATIONS:
        current_times += 1
        total_compilations += 1

        # 本轮编译前：更新基线并保存快照
        cite_counter, toc_file, index_aux_content_dict_old = detector.prepare_LaTeX_output_files()
        aux_content_old, out_content_old = detector.prepare_aux_out_snapshots()

        # 执行本轮 LaTeX 编译
        print_message(
            _("%(args1)s 次 %(args2)s 编译") % {"args1": str(current_times), "args2": compiled_program},
            "running",
        )
        runtime_Latex = time_count(
            compile_model.compile_tex,
        ).seconds
        runtime_dict[f"{compiled_program} {_ordinal(current_times)}"] = runtime_Latex

        detection = detector.run_full_detection(
            cite_counter_old=cite_counter,
            toc_file_old=toc_file,
            index_aux_content_old=index_aux_content_dict_old,
            aux_content_old=aux_content_old,
            out_content_old=out_content_old,
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

        reached_limit = (current_times - 1) >= MAX_EXTRA_COMPILATIONS and latex_compilation_times > 0
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
            max_extra=MAX_EXTRA_COMPILATIONS,
        )
        if stop_reason:
            break

    # 编译完成, 开始判断编译 XDV 文件
    if compiled_program == "XeLaTeX":  # 判断是否编译 xdv 文件
        print_message(_("DVIPDFMX 编译"), "running")
        runtime_xdv = time_count(
            compile_model.compile_xdv,
        ).seconds  # 编译 xdv 文件
        runtime_dict[_("DVIPDFMX 编译")] = runtime_xdv

    # 显示编译过程中关键信息
    print_message(_("完成所有编译"), "success")

    # 收尾提示：把"再编译也消不掉"的警告明确告诉用户，避免用户以为是编译流程的问题
    residual_notes = detector.residual_warnings()
    if residual_notes:
        for note in residual_notes:
            print_message(_("未能消除：%(args)s") % {"args": note}, "additional")

    # 结束草稿模式
    MFO.draft_model(project_name, draft, False)

    # 落盘构建基线：产物摘要 + 收敛标记 + 源快照。
    # 有了它，下次运行时"源文件是否变过"无需再编一轮就能判断。
    _persist_build_state(
        build_state,
        round_no=total_compilations,
        fingerprint=detector.state_fingerprint(),
        dims=dims,
        signals=signals,
        stop_reason=stop_reason or "stable",
        project_name=project_name,
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
) -> None:
    """把本轮结束时的状态写进共享状态文件（失败绝不阻断编译结果）。

    注意：**只有收敛的构建才标记 ``converged``**。若停在 ``limit``（安全上限
    用尽）说明结果可能并未稳定，此时绝不能写入收敛标记，否则下一次运行会
    误判"源未变可跳过"，把一个未收敛的 PDF 当成成品。
    """
    converged = stop_reason in {"stable", "converged", "fixed_point", "log_stalled"}
    try:
        build_state.save_round(
            round_no=round_no,
            fingerprint=fingerprint,
            dims=dims,
            signals=signals,
            stop_reason=stop_reason,
            converged=converged,
            sources=build_state.source_snapshot(_iter_tex_sources(project_name)),
        )
    except Exception:  # 状态文件问题不影响编译成功
        pass


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

    cwd = Path().resolve()
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


# --------------------------------------------------------------------------------
# LaTeX Diff 编译
# --------------------------------------------------------------------------------
def LaTeXDiffRUN(
    runtime_dict,
    project_name,
    compiled_program,
    out_files,
    aux_files,
    outdir,
    auxdir,
    non_quiet,
    draft,
):
    # 草稿模式函数启用
    """LaTeXDiff 差异文档编译流程：两轮 LaTeX 编译以稳定目录引用。"""
    MFO.draft_model(project_name, draft, True)

    abbreviations_num = ("1st", "2nd")
    # 编译前的准备工作
    compile_model = CompileLaTeX(project_name, compiled_program, out_files, aux_files, outdir, auxdir, non_quiet)

    # 首次编译 LaTeX 文档
    print_message(_("1 次 %(args)s 编译") % {"args": compiled_program}, "running")
    runtime_Latex = time_count(
        compile_model.compile_tex,
    ).seconds
    runtime_dict[f"{compiled_program} {abbreviations_num[0]}"] = runtime_Latex

    print_message(_("2 次 %(args1)s 编译") % {"args1": compiled_program}, "running")
    runtime_Latex = time_count(
        compile_model.compile_tex,
    ).seconds
    runtime_dict[f"{compiled_program} {abbreviations_num[1]}"] = runtime_Latex

    # 编译完成, 开始判断编译 XDV 文件
    if compiled_program == "XeLaTeX":  # 判断是否编译 xdv 文件
        print_message(_("DVIPDFMX 编译"), "running")
        runtime_xdv = time_count(
            compile_model.compile_xdv,
        ).seconds  # 编译 xdv 文件
        runtime_dict[_("DVIPDFMX 编译")] = runtime_xdv

    # 显示编译过程中关键信息
    print_message(_("完成所有编译"), "success")

    # 结束草稿模式
    MFO.draft_model(project_name, draft, False)

    return runtime_dict
