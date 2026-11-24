'''
 =======================================================================
 ·······································································
 ·······································································
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
 ·······································································
 =======================================================================

 -----------------------------------------------------------------------
Author       : 焱铭
Date         : 2026-09-25 17:13:51 +0800
LastEditTime : 2026-09-25 18:56:55 +0800
Github       : https://github.com/YanMing-lxb/
FilePath     : /PyTeXMK/src/pytexmk/cli/cli_latexdiff.py
Description  :
 -----------------------------------------------------------------------
'''

"""PyTeXMK CLI LaTeXDiff 流程：新旧 TeX 文件对比与差异编译。"""


from .. import layout  # noqa: E402
from ..compile_engine import RUN, LaTeXDiffRUN  # noqa: E402
from ..language import set_language  # noqa: E402
from ..latexdiff import LaTeXDiff_Aux  # noqa: E402
from ..lifecycle import EXIT_COMPILE_FAILED, EXIT_ERROR, exit_pytexmk  # noqa: E402
from ..timing import time_count  # noqa: E402
from ..ui_messages import print_message  # noqa: E402
from ..ui_theme import console  # noqa: E402
from .cli_state import SUFFIXES_AUX, SUFFIXES_OUT, WorkflowState  # noqa: E402

_ = set_language("cli_workflow")

# LaTeXDiff 风格 1 下需要单独比对差异的辅助文件后缀
_DIFF_AUX_SUFFIXES = layout.DIFF_AUX_SUFFIXES


def run(args, state: WorkflowState) -> None:
    """执行 LaTeXDiff：校验 → 辅助文件检查 → flatten → 风格选择 → 差异编译 → 后处理。

    无论差异编译成功与否，finally 都会把根目录的辅助文件归还到 auxdir。
    """
    logger = state.logger

    if not state.old_tex_file or not state.new_tex_file:
        logger.error(_("请在命令行或配置文件中指定新旧两个 TeX 文件"))
        exit_pytexmk(EXIT_ERROR)

    if state.old_tex_file == state.new_tex_file:
        logger.error(_("不能对同一个文件进行比较, 请检查文件名是否正确"))
        exit_pytexmk(EXIT_ERROR)

    print_message(_("LaTeXDiff 预处理"), "additional")

    # 命令行构建参数（--pass-arg 等）必须在 latexdiff 分支同样生效；
    # 旧实现直接读配置层 state，命令行覆盖被吞掉。
    # side_effects=False：不在这里删除主工程的旧 SyncTeX（output_name 仍是
    # 被比较的主文件，不是 LaTeXDiff 的 jobname）。
    from .cli_compile import _apply_build_overrides, capture_engine_outputs, publish_compiled_outputs

    _apply_build_overrides(args, state, side_effects=False)

    lda = LaTeXDiff_Aux(state.outdir, SUFFIXES_OUT, SUFFIXES_AUX, state.auxdir)
    _require_aux_files(lda, state.old_tex_file, logger)
    _require_aux_files(lda, state.new_tex_file, logger)

    old_tex_file_flatten = lda.flatten_Latex(state.old_tex_file)
    new_tex_file_flatten = lda.flatten_Latex(state.new_tex_file)
    runtime_move_matched_files = time_count(
        state.mro.move_matched_files, state.aux_regex_files, state.auxdir, "."
    ).seconds
    state.runtime_dict["move_all_root"] = runtime_move_matched_files
    latex_diff_style = _resolve_style(args, logger)

    try:
        print_message(_("LaTeXDiff 运行"), "running")
        aux_suffixes_exit: list[str] = []
        if latex_diff_style == "1":
            for aux_suffix in _DIFF_AUX_SUFFIXES:
                aux_file_exit = lda.aux_files_both_exist(
                    state.old_tex_file, state.new_tex_file, aux_suffix
                )
                if aux_file_exit is not None:
                    aux_suffixes_exit.append(aux_file_exit)
            for aux_suffix in aux_suffixes_exit:
                runtime_compile_LaTeXDiff = time_count(
                    lda.compile_LaTeXDiff,
                    state.old_tex_file,
                    state.new_tex_file,
                    state.diff_tex_file,
                    aux_suffix,
                ).seconds
        runtime_compile_LaTeXDiff = time_count(
            lda.compile_LaTeXDiff,
            old_tex_file_flatten,
            new_tex_file_flatten,
            state.diff_tex_file,
            ".tex",
        ).seconds
        state.runtime_dict["latexdiff"] = runtime_compile_LaTeXDiff

        print_message(_("LaTeXDiff 后处理"), "additional")
        console.print(_("清理压平临时文件..."))
        # 压平文件现在写在独占临时目录，不再需要（也不应该）按相对路径删根目录。
        lda.cleanup()
        state.runtime_dict["clear_out_outdir"] = 0.0

        if args.LaTeXDiff_compile is not None:
            # 差异文档以 state.diff_tex_file 为 jobname：0.5 这里是空字符串，
            # 于是 state.aux_files 变成 "".join 出来的 ".log"/".aux" 这类无主文件名，
            # 编译参数里就会出现裸 ".log"，既定位不到文件也会污染根目录。
            state.output_name = state.diff_tex_file
            # aux_files 在 cli_context 里就已按 output_name 拼好，这里必须一并重算，
            # 否则传给编译器的仍是 ".aux"/".log"（输出名被 latexdiff 分支吃空）。
            state.refresh_file_lists(state.diff_tex_file)
            out_files = state.out_files
            build_options = {
                "shell_escape": state.shell_escape,
                "synctex": state.synctex,
                "native": state.native_build,
                "extra_args": state.extra_args,
                "interaction": state.interaction or None,
                "jobname": state.diff_tex_file,
            }
            before = capture_engine_outputs(state)
            print_message(_("开始预处理命令"), "additional")
            if latex_diff_style == "1":
                LaTeXDiffRUN(
                    state.runtime_dict,
                    state.diff_tex_file,
                    state.compiled_program,
                    out_files,
                    state.aux_files,
                    state.outdir,
                    state.auxdir,
                    non_quiet=state.non_quiet,
                    draft=args.draft,
                    **build_options,
                )
            elif latex_diff_style == "2":
                RUN(
                    state.runtime_dict,
                    state.diff_tex_file,
                    state.compiled_program,
                    out_files,
                    state.aux_files,
                    state.outdir,
                    state.auxdir,
                    non_quiet=state.non_quiet,
                    draft=args.draft,
                    max_extra=state.max_extra_compilations,
                    **build_options,
                )
            else:
                logger.error(
                    _(
                        "请输入正确的选项 (1 或者 2)\n"
                        "  1 - 显示参考文献/符号说明的修改\n"
                        "  2 - 不显示参考文献/符号说明的修改"
                    )
                )
            print_message(_("开始后处理"), "additional")

            publish_compiled_outputs(state, before, archive_aux=False)
    except Exception as e:
        logger.error(_("LaTeXDiff 编译出错: ") + str(e))
        exit_pytexmk(EXIT_COMPILE_FAILED)
    finally:
        lda.cleanup()
        runtime_move_matched_files = time_count(
            state.mro.move_matched_files, state.aux_regex_files, ".", state.auxdir
        ).seconds
        state.runtime_dict["move_aux_auxdir"] = runtime_move_matched_files


def _resolve_style(args, logger) -> str:
    """决定 latexdiff 风格：命令行 > 配置 > 默认 2；无 TTY 时不再阻塞等待输入。"""
    style = getattr(args, "diff_style", None)
    if style:
        return str(style)
    import sys

    if not sys.stdin or not sys.stdin.isatty():
        logger.info(_("非交互环境，LaTeXDiff 使用默认风格 2"))
        return "2"
    try:
        answer = input(
            _(
                "请输入 LaTeXDiff 的显示风格：\n"
                "  1 - 显示参考文献/符号说明的修改\n"
                "  2 - 不显示参考文献/符号说明的修改\n"
                "请选择 (1 或者 2，直接回车默认 2): "
            )
        ).strip()
    except EOFError, KeyboardInterrupt:
        logger.info(_("未读取到输入，使用默认风格 2"))
        return "2"
    if not answer:
        return "2"
    if answer not in ("1", "2"):
        logger.error(_("风格只能是 1 或 2，收到: ") + answer)
        exit_pytexmk(EXIT_ERROR)
    return answer


def _require_aux_files(lda: LaTeXDiff_Aux, tex_file: str, logger) -> None:
    """检查辅助文件；缺失只警告，不直接退出。

    旧版本在旧文件没有编译产物时直接拒绝运行，但 latexdiff 对纯文本
    源文件同样能生成差异（只是参考文献编号不如带 .bbl 精确）。这里降级为
    警告，让用户能先看到差异再决定要不要补编译。
    """
    if lda.check_aux_files(tex_file):
        logger.info(_("%(args)s 的辅助文件存在") % {"args": tex_file})
    else:
        logger.warning(
            _("%(args)s 的辅助文件不存在，差异结果可能缺少参考文献/索引内容") % {"args": tex_file}
        )
