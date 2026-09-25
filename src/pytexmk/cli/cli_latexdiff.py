"""PyTeXMK CLI LaTeXDiff 流程：新旧 TeX 文件对比与差异编译。"""

from rich import print

from ..compile_engine import RUN, LaTeXDiffRUN
from ..language import set_language
from ..latexdiff import LaTeXDiff_Aux
from ..lifecycle import exit_pytexmk
from ..timing import time_count
from ..ui_messages import print_message
from .cli_state import SUFFIXES_AUX, SUFFIXES_OUT, WorkflowState

_ = set_language("cli_workflow")

# LaTeXDiff 风格 1 下需要单独比对差异的辅助文件后缀
_DIFF_AUX_SUFFIXES = [".bbl", ".nls", ".gls", ".idx"]


def run(args, state: WorkflowState) -> None:
    """执行 LaTeXDiff：校验 → 辅助文件检查 → flatten → 风格选择 → 差异编译 → 后处理。

    无论差异编译成功与否，finally 都会把根目录的辅助文件归还到 auxdir。
    """
    logger = state.logger

    if not state.old_tex_file or not state.new_tex_file:
        logger.error(_("请指定在命令行或配置文件中指定两个新旧 TeX 文件"))
        exit_pytexmk()

    if state.old_tex_file == state.new_tex_file:
        logger.error(_("不能对同一个文件进行比较, 请检查文件名是否正确"))
        exit_pytexmk()

    print_message(_("LaTeXDiff 预处理"), "additional")

    lda = LaTeXDiff_Aux(state.outdir, SUFFIXES_OUT, SUFFIXES_AUX, state.auxdir)
    _require_aux_files(lda, state.old_tex_file, logger)
    _require_aux_files(lda, state.new_tex_file, logger)

    old_tex_file_flatten = lda.flatten_Latex(state.old_tex_file)
    new_tex_file_flatten = lda.flatten_Latex(state.new_tex_file)
    runtime_move_matched_files, _ret = time_count(
        state.mro.move_matched_files, state.aux_regex_files, state.auxdir, "."
    )
    state.runtime_dict[_("全辅助文件->根目录")] = runtime_move_matched_files
    latex_diff_style = input(
        _(
            "请输入 LaTeXDiff 的显示风格：\n"
            "  1 - 显示参考文献/符号说明的修改\n"
            "  2 - 不显示参考文献/符号说明的修改\n"
            "请选择 (1 或者 2): "
        )
    )

    try:
        print_message(_("LaTeXDiff 运行"), "running")
        aux_suffixes_exit = []
        if latex_diff_style == "1":
            for aux_suffix in _DIFF_AUX_SUFFIXES:
                aux_file_exit = lda.aux_files_both_exist(state.old_tex_file, state.new_tex_file, aux_suffix)
                aux_suffixes_exit.append(aux_file_exit) if aux_file_exit else None
            for aux_suffix in aux_suffixes_exit:
                runtime_compile_LaTeXDiff, _ret = time_count(
                    lda.compile_LaTeXDiff, state.old_tex_file, state.new_tex_file, state.diff_tex_file, aux_suffix
                )

        runtime_compile_LaTeXDiff, _ret = time_count(
            lda.compile_LaTeXDiff, old_tex_file_flatten, new_tex_file_flatten, state.diff_tex_file, ".tex"
        )
        state.runtime_dict[_("LaTeXDiff 运行")] = runtime_compile_LaTeXDiff

        print_message(_("LaTeXDiff 后处理"), "additional")
        print(_("删除 Flatten 后的文件..."))
        runtime_remove_flatten_root, _ret = time_count(
            state.mro.remove_specific_files, [f"{old_tex_file_flatten}.tex", f"{new_tex_file_flatten}.tex"], "."
        )
        state.runtime_dict[_("清除文件夹内输出文件")] = runtime_remove_flatten_root

        if args.LaTeXDiff_compile or args.LaTeXDiff_compile == []:
            out_files = [f"{state.diff_tex_file}{suffix}" for suffix in SUFFIXES_OUT]
            print_message(_("开始预处理命令"), "additional")
            if latex_diff_style == "1":
                LaTeXDiffRUN(
                    state.runtime_dict, state.diff_tex_file, state.compiled_program, out_files, state.aux_files,
                    state.outdir, state.auxdir, state.non_quiet, args.draft,
                )
            elif latex_diff_style == "2":
                RUN(
                    state.runtime_dict, state.diff_tex_file, state.compiled_program, out_files, state.aux_files,
                    state.outdir, state.auxdir, state.non_quiet, args.draft,
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

            print(_("移动结果文件到输出目录..."))
            runtime_move_out_outdir, _ret = time_count(state.mro.move_specific_files, out_files, ".", state.outdir)
            state.runtime_dict[_("结果文件->输出目录")] = runtime_move_out_outdir
    except Exception as e:  # noqa: BLE001
        logger.error(_("LaTeXDiff 编译出错: ") + str(e))
        exit_pytexmk()
    finally:
        runtime_move_matched_files, _ret = time_count(
            state.mro.move_matched_files, state.aux_regex_files, ".", state.auxdir
        )
        state.runtime_dict[_("辅助文件->辅助目录")] = runtime_move_matched_files


def _require_aux_files(lda: LaTeXDiff_Aux, tex_file: str, logger) -> None:
    """校验指定 TeX 文件的辅助文件是否就位，缺失则直接退出。"""
    if lda.check_aux_files(tex_file):
        logger.info(_("%(args)s 的辅助文件存在") % {"args": tex_file})
    else:
        logger.error(_("%(args)s 的辅助文件不存在, 请检查编译") % {"args": tex_file})
        exit_pytexmk()
