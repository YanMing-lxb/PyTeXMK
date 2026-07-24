"""
工作流处理模块
"""

import sys
from pathlib import Path

from rich import print

from pytexmk.info_print import print_message, time_count, time_print
from pytexmk.language import set_language
from pytexmk.latexdiff import LaTeXDiffTool
from pytexmk.run import RUN, LaTeXDiffRUN

_ = set_language("workflow")


def is_tty() -> bool:
    """检测是否在交互式终端中运行"""
    return sys.stdin.isatty() and sys.stdout.isatty()


def standardize_name(compiled_program):
    standard_names = {"xelatex": "XeLaTeX", "pdflatex": "PdfLaTeX", "lualatex": "LuaLaTeX"}
    return standard_names.get(compiled_program.lower(), compiled_program)


def setup_pdf_preview(compiler, args, project_name, outdir, PFO):
    """PDF 预览处理"""
    if args.open_pdf or args.pdf_preview == "preview after compile":
        PFO.pdf_preview(project_name, outdir)


def handle_clean(
    args, compiler, MRO, project_name, outdir, auxdir, suffixes_out, suffixes_aux, start_time, runtime_dict
):
    """清洁命令处理"""
    out_files = [f"{project_name}{suffix}" for suffix in suffixes_out]
    aux_files = [f"{project_name}{suffix}" for suffix in suffixes_aux]
    aux_regex_files = [f".*\\{suffix}" for suffix in suffixes_aux]

    if args.clean_any:
        runtime_remove_aux_matched_auxdir = time_count(MRO.remove_matched_files, aux_regex_files, ".")
        runtime_dict[_("清除所有的辅助文件")] = runtime_remove_aux_matched_auxdir
        print(_("[bold green]已完成清除所有带辅助文件后缀的文件的指令"))
    elif args.Clean_any:
        runtime_remove_aux_matched_auxdir = time_count(MRO.remove_matched_files, aux_regex_files, ".")
        runtime_dict[_("清除所有的辅助文件")] = runtime_remove_aux_matched_auxdir
        runtime_remove_out_outdir = time_count(MRO.remove_specific_files, out_files, outdir)
        runtime_dict[_("清除文件夹内输出文件")] = runtime_remove_out_outdir
        print(_("[bold green]已完成清除所有带辅助文件后缀的文件和主文件输出文件的指令"))
    elif args.clean:
        runtime_remove_aux_auxdir = time_count(MRO.remove_specific_files, aux_files, auxdir)
        runtime_dict[_("清除文件夹内辅助文件")] = runtime_remove_aux_auxdir
        runtime_remove_aux_root = time_count(MRO.remove_specific_files, aux_files, ".")
        runtime_dict[_("清除根目录内辅助文件")] = runtime_remove_aux_root
        print(_("[bold green]已完成清除所有主文件的辅助文件的指令"))
    elif args.Clean:
        runtime_remove_aux_auxdir = time_count(MRO.remove_specific_files, aux_files, auxdir)
        runtime_dict[_("清除文件夹内辅助文件")] = runtime_remove_aux_auxdir
        runtime_remove_aux_root = time_count(MRO.remove_specific_files, aux_files, ".")
        runtime_dict[_("清除根目录内辅助文件")] = runtime_remove_aux_root
        runtime_remove_out_outdir = time_count(MRO.remove_specific_files, out_files, outdir)
        runtime_dict[_("清除文件夹内输出文件")] = runtime_remove_out_outdir
        print(_("[bold green]已完成清除所有主文件的辅助文件和输出文件的指令"))

    if runtime_dict:
        time_print(start_time, runtime_dict)


def handle_diff(
    args,
    config,
    magic_comments,
    MFO,
    MRO,
    PFO,
    main_files_in_root,
    start_time,
    runtime_dict,
    suffixes_out,
    suffixes_aux,
    outdir,
    auxdir,
):
    """LaTeXDiff 处理（使用新 LaTeXDiffTool）"""
    old_tex_file = "old_file"
    new_tex_file = "new_file"
    diff_tex_file = "LaTeXDiff"

    if config and config.get("latexdiff"):
        latexdiff_config = config["latexdiff"]
        if latexdiff_config.get("old_tex_file"):
            old_tex_file = latexdiff_config["old_tex_file"]
        if latexdiff_config.get("new_tex_file"):
            new_tex_file = latexdiff_config["new_tex_file"]
        if latexdiff_config.get("diff_tex_file"):
            diff_tex_file = latexdiff_config["diff_tex_file"]

    if config and config.get("diff"):
        diff_config = config["diff"]
        if diff_config.get("output"):
            diff_tex_file = diff_config["output"]

    if args.diff_output:
        diff_tex_file = args.diff_output
        diff_tex_file = diff_tex_file.removesuffix(".tex")

    diff_mode = None
    if args.LaTeXDiff is not None or args.LaTeXDiff_compile is not None:
        if args.LaTeXDiff is not None:
            diff_mode = "generate_only"
            diff_args = args.LaTeXDiff
        else:
            diff_mode = "generate_and_compile"
            diff_args = args.LaTeXDiff_compile

        if diff_args and len(diff_args) == 2:
            old_tex_file, new_tex_file = diff_args
        elif diff_args and len(diff_args) == 0:
            pass
        else:
            print(_("[bold red]错误: LaTeXDiff 需要指定 0 或 2 个文件参数[/bold red]"))
            return False

    if not old_tex_file or not new_tex_file:
        print(_("[bold red]错误: 请在命令行或配置文件中指定 LaTeXDiff 的新旧 TeX 文件[/bold red]"))
        return False

    if old_tex_file == new_tex_file:
        print(_("[bold red]错误: 不能对同一个文件进行比较[/bold red]"))
        return False

    old_tex_file = MFO.check_project_name(main_files_in_root, old_tex_file, ".tex")
    new_tex_file = MFO.check_project_name(main_files_in_root, new_tex_file, ".tex")

    print_message(_("LaTeXDiff 预处理"), "additional")

    non_interactive = args.non_interactive or not is_tty()
    flatten = args.diff_flatten or (config.get("diff", {}).get("flatten", False) if config else False)
    fast = args.diff_fast or (config.get("diff", {}).get("fast", False) if config else False)

    if non_interactive:
        latex_diff_style = args.diff_style if args.diff_style is not None else 2
    else:
        if args.diff_style is not None:
            latex_diff_style = args.diff_style
        else:
            try:
                latex_diff_style = int(
                    input(
                        _(
                            "请输入 LaTeXDiff 的显示风格：\n"
                            "  1 - 显示参考文献/符号说明的修改\n"
                            "  2 - 不显示参考文献/符号说明的修改\n"
                            "请选择 (1 或者 2): "
                        )
                    )
                )
            except (EOFError, ValueError):
                latex_diff_style = 2

    diff_tool = LaTeXDiffTool()

    if not diff_tool.detect_available():
        print(_("[bold red]错误: 未检测到 latexdiff 命令，请先安装 LaTeXDiff[/bold red]"))
        return False

    try:
        print_message(_("LaTeXDiff 运行"), "running")

        if flatten:
            old_flat = f"{old_tex_file}-flatten"
            new_flat = f"{new_tex_file}-flatten"
            diff_tool.flatten_tex(f"{old_tex_file}.tex", f"{old_flat}.tex")
            diff_tool.flatten_tex(f"{new_tex_file}.tex", f"{new_flat}.tex")
            diff_tool.generate_diff(
                old_file=f"{old_flat}.tex",
                new_file=f"{new_flat}.tex",
                output_file=f"{diff_tex_file}.tex",
                fast=fast,
            )
            try:
                Path(f"{old_flat}.tex").unlink(missing_ok=True)
                Path(f"{new_flat}.tex").unlink(missing_ok=True)
            except Exception:
                pass
        else:
            diff_tool.generate_diff(
                old_file=f"{old_tex_file}.tex",
                new_file=f"{new_tex_file}.tex",
                output_file=f"{diff_tex_file}.tex",
                fast=fast,
            )

        runtime_dict[_("LaTeXDiff 运行")] = 0

        if diff_mode == "generate_and_compile":
            out_files = [f"{diff_tex_file}{suffix}" for suffix in suffixes_out]
            aux_files = [f"{diff_tex_file}{suffix}" for suffix in suffixes_aux]

            print_message(_("开始预处理命令"), "additional")
            print(_("检测并移动辅助文件到根目录..."))
            runtime_move_aux_root = time_count(MRO.move_specific_files, aux_files, auxdir, ".")
            runtime_dict[_("辅助文件->根目录")] = runtime_move_aux_root

            compiled_program = standardize_name(config.get("compiled_program", "xelatex")) if config else "XeLaTeX"
            non_quiet = args.non_quiet

            if latex_diff_style == 1:
                LaTeXDiffRUN(
                    runtime_dict,
                    diff_tex_file,
                    compiled_program,
                    out_files,
                    aux_files,
                    outdir,
                    auxdir,
                    non_quiet,
                    args.draft,
                )
            else:
                RUN(
                    runtime_dict,
                    diff_tex_file,
                    compiled_program,
                    out_files,
                    aux_files,
                    outdir,
                    auxdir,
                    non_quiet,
                    args.draft,
                )

            print_message(_("开始后处理"), "additional")
            print(_("移动结果文件到输出目录..."))
            runtime_move_out_outdir = time_count(MRO.move_specific_files, out_files, ".", outdir)
            runtime_dict[_("结果文件->输出目录")] = runtime_move_out_outdir
            print(_("移动辅助文件到辅助目录..."))
            runtime_move_aux_auxdir = time_count(MRO.move_specific_files, aux_files, ".", auxdir)
            runtime_dict[_("辅助文件->辅助目录")] = runtime_move_aux_auxdir

            if args.open_pdf or args.pdf_preview == "preview after compile":
                PFO.pdf_preview(diff_tex_file, outdir)

    except Exception as e:
        print(_("[bold red]LaTeXDiff 编译出错: ") + str(e))
        return False

    return True