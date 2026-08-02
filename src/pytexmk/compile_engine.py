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

from pytexmk.compile import CompileLaTeX
from pytexmk.compile_report import print_compile_report, print_compile_separator
from pytexmk.language import set_language
from pytexmk.tex_project import MainFileOperation
from pytexmk.timing import time_count
from pytexmk.ui_messages import print_message

_ = set_language("compile_engine")
MFO = MainFileOperation()  # 实例化 MainFileOperation 类


def standardize_name(compiled_program):
    standard_names = {
        "xelatex": "XeLaTeX",
        "pdflatex": "PdfLaTeX",
        "lualatex": "LuaLaTeX",
    }
    return standard_names.get(compiled_program.lower(), compiled_program)


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

    abbreviations_num = (
        "1st", "2nd", "3rd", "4th", "5th", "6th",
        "7th", "8th", "9th", "10th", "11th", "12th", "13th",
    )
    # 编译前的准备工作
    compile_model = CompileLaTeX(
        project_name, compiled_program, out_files, aux_files, outdir, auxdir, non_quiet
    )

    runtime_read, return_read = time_count(
        compile_model.detector.prepare_LaTeX_output_files,
    )  # 读取 LaTeX 文件
    cite_counter, toc_file, index_aux_content_dict_old = (
        return_read  # 获取 read_LaTeX_files 函数得到的参数
    )
    runtime_dict[_("检测辅助文件")] = runtime_read

    aux_content_old, out_content_old = compile_model.detector.prepare_aux_out_snapshots()

    # 首次编译 LaTeX 文档
    print_message(_("1 次 %(args)s 编译") % {"args": compiled_program}, "running")
    runtime_Latex, _ret = time_count(
        compile_model.compile_tex,
    )
    runtime_dict[f"{compiled_program} {abbreviations_num[0]}"] = runtime_Latex

    # 首次编译后：run_full_detection 聚合 6 维检测 + 返回子步骤 schedule 所需值
    runtime_detect, return_detect = time_count(
        compile_model.detector.run_full_detection,
        cite_counter_old=cite_counter,
        toc_file_old=toc_file,
        index_aux_content_old=index_aux_content_dict_old,
        aux_content_old=aux_content_old,
        out_content_old=out_content_old,
    )
    dims, Latex_compilation_times, bib_engine, index_run_cmds, Latex_compilation_times_bib = return_detect
    runtime_dict[_("编译文献判定")] = runtime_detect
    runtime_dict[_("编译索引判定")] = runtime_detect

    # 编译参考文献
    if bib_engine and Latex_compilation_times_bib != 0:
        print_message(_("%(args)s 编译文献") % {"args": bib_engine}, "running")
        runtime_bib, _ret = time_count(
            compile_model.compile_bib, bib_engine
        )  # 编译参考文献
        name_target_bib = bib_engine
        runtime_dict[_("%(args)s 编译") % {"args": name_target_bib}] = runtime_bib

    # 编译索引
    if index_run_cmds:  # 存在目录索引编译命令
        for cmd in index_run_cmds:
            print_message(_("%(args)s 编译") % {"args": cmd[0]}, "running")
            runtime_index, return_index = time_count(compile_model.compile_index, cmd)
            name_target_index = return_index  # 获取 compile_index 函数得到的参数
            runtime_dict[_("%(args)s 编译") % {"args": name_target_index}] = (
                runtime_index
            )

    total_compilations = 1
    current_times = 1
    max_extra_compilations = 10  # 最大额外编译次数上限，防止死循环

    print_compile_separator()
    print_compile_report(
        round_index=1,
        next_extra_compilations=Latex_compilation_times,
        total_compilations=1,
        dims=dims,
        compiled_program=standardize_name(compiled_program),
        reached_limit=False,
        max_extra=max_extra_compilations,
    )

    # 进行额外的 LaTeX 编译（迭代收敛直到所有维度均返回 0，或达到安全上限）
    while Latex_compilation_times > 0 and (current_times - 1) < max_extra_compilations:
        current_times += 1
        total_compilations += 1

        # 本轮编译前：更新基线并保存快照
        cite_counter, toc_file, index_aux_content_dict_old = (
            compile_model.detector.prepare_LaTeX_output_files()
        )
        aux_content_old, out_content_old = compile_model.detector.prepare_aux_out_snapshots()

        # 执行本轮 LaTeX 编译
        print_message(
            _("%(args1)s 次 %(args2)s 编译")
            % {"args1": str(current_times), "args2": compiled_program},
            "running",
        )
        runtime_Latex, _ret = time_count(
            compile_model.compile_tex,
        )
        runtime_dict[f"{compiled_program} {abbreviations_num[current_times - 1]}"] = (
            runtime_Latex
        )

        # 本轮编译后：run_full_detection 聚合 6 维检测
        dims, Latex_compilation_times, _bib_eng, index_run_cmds, _tbib = (
            compile_model.detector.run_full_detection(
                cite_counter_old=cite_counter,
                toc_file_old=toc_file,
                index_aux_content_old=index_aux_content_dict_old,
                aux_content_old=aux_content_old,
                out_content_old=out_content_old,
            )
        )

        reached_limit = (
            (current_times - 1) >= max_extra_compilations
            and Latex_compilation_times > 0
        )
        print_compile_separator()
        print_compile_report(
            round_index=current_times,
            next_extra_compilations=Latex_compilation_times,
            total_compilations=total_compilations,
            dims=dims,
            compiled_program=standardize_name(compiled_program),
            reached_limit=reached_limit,
            max_extra=max_extra_compilations,
        )

    # 编译完成, 开始判断编译 XDV 文件
    if compiled_program == "XeLaTeX":  # 判断是否编译 xdv 文件
        print_message(_("DVIPDFMX 编译"), "running")
        runtime_xdv, _ret = time_count(
            compile_model.compile_xdv,
        )  # 编译 xdv 文件
        runtime_dict[_("DVIPDFMX 编译")] = runtime_xdv

    # 显示编译过程中关键信息
    print_message(_("完成所有编译"), "success")

    # 结束草稿模式
    MFO.draft_model(project_name, draft, False)

    return runtime_dict


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
    compile_model = CompileLaTeX(
        project_name, compiled_program, out_files, aux_files, outdir, auxdir, non_quiet
    )

    # 首次编译 LaTeX 文档
    print_message(_("1 次 %(args)s 编译") % {"args": compiled_program}, "running")
    runtime_Latex, _ret = time_count(
        compile_model.compile_tex,
    )
    runtime_dict[f"{compiled_program} {abbreviations_num[0]}"] = runtime_Latex

    print_message(_("2 次 %(args1)s 编译") % {"args1": compiled_program}, "running")
    runtime_Latex, _ret = time_count(
        compile_model.compile_tex,
    )
    runtime_dict[f"{compiled_program} {abbreviations_num[1]}"] = runtime_Latex

    # 编译完成, 开始判断编译 XDV 文件
    if compiled_program == "XeLaTeX":  # 判断是否编译 xdv 文件
        print_message(_("DVIPDFMX 编译"), "running")
        runtime_xdv, _ret = time_count(
            compile_model.compile_xdv,
        )  # 编译 xdv 文件
        runtime_dict[_("DVIPDFMX 编译")] = runtime_xdv

    # 显示编译过程中关键信息
    print_message(_("完成所有编译"), "success")

    # 结束草稿模式
    MFO.draft_model(project_name, draft, False)

    return runtime_dict
