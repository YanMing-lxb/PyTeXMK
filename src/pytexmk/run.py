'''
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
LastEditTime : 2025-01-29 22:01:43 +0800
Github       : https://github.com/YanMing-lxb/
FilePath     : /PyTeXMK/src/pytexmk/run_module.py
Description  : 
 -----------------------------------------------------------------------
'''

from rich import print

from pytexmk.compile import CompileLaTeX
from pytexmk.additional import MainFileOperation
from pytexmk.language import set_language
from pytexmk.info_print import time_count, print_message

_ = set_language('run')
MFO = MainFileOperation() # 实例化 MainFileOperation 类

# --------------------------------------------------------------------------------
# 整体进行编译
# --------------------------------------------------------------------------------
def RUN(runtime_dict, project_name, compiled_program, out_files, aux_files, outdir, auxdir, non_quiet, draft):
    # 草稿模式函数启用
    MFO.draft_model(project_name, draft, True)

    abbreviations_num = ('1st', '2nd', '3rd', '4th', '5th', '6th')
    # 编译前的准备工作
    compile_model = CompileLaTeX(project_name, compiled_program, out_files, aux_files, outdir, auxdir, non_quiet)

    # 检查并处理已存在的 LaTeX 输出文件
    print(_('检测识别已有辅助文件...'))
    runtime_read, return_read = time_count(compile_model.prepare_LaTeX_output_files, ) # 读取 LaTeX 文件
    cite_counter, toc_file, index_aux_content_dict_old = return_read # 获取 read_LaTeX_files 函数得到的参数
    runtime_dict[_('检测辅助文件')] = runtime_read

    # 首次编译 LaTeX 文档
    print_message(_("1 次 %(args)s 编译") % {'args': compiled_program}, "running")
    runtime_Latex = time_count(compile_model.compile_tex, ) 
    runtime_dict[f'{compiled_program} {abbreviations_num[0]}'] = runtime_Latex

    # 读取日志文件
    with open(f'{project_name}.log', 'r', encoding='utf-8', errors='ignore') as fobj:
        log_content = fobj.read()
    compile_model.check_errors(log_content)

    # 编译参考文献
    runtime_bib_judgment, return_bib_judgment = time_count(compile_model.bib_judgment, cite_counter) # 判断是否需要编译参考文献
    runtime_dict[_('编译文献判定')] = runtime_bib_judgment

    bib_engine, Latex_compilation_times_bib, print_bib, name_target_bib = return_bib_judgment # 获取 bib_judgment 函数得到的参数
    if bib_engine:
        if Latex_compilation_times_bib != 0:
            print_message(_('%(args)s 编译文献') % {'args': bib_engine}, "running")
            runtime_bib = time_count(compile_model.compile_bib, bib_engine) # 编译参考文献
            runtime_dict[_('%(args)s 编译') % {'args': name_target_bib}] = runtime_bib

    # 编译索引
    runtime_makindex_judgment, return_index_judgment = time_count(compile_model.index_judgment, index_aux_content_dict_old) # 判断是否需要编译目录索引
    print_index, run_index_list_cmd = return_index_judgment
    runtime_dict[_('编译索引判定')] = runtime_makindex_judgment

    if run_index_list_cmd: # 存在目录索引编译命令
        for cmd in run_index_list_cmd:
            print_message(_('%(args)s 编译') % {'args': cmd[0]}, "running")
            Latex_compilation_times_index = 1
            runtime_index, return_index = time_count(compile_model.compile_index, cmd)
            name_target_index = return_index # 获取 compile_index 函数得到的参数
            runtime_dict[_('%(args)s 编译') % {'args': name_target_index}] = runtime_index
    else:
        Latex_compilation_times_index = 0

    # 编译目录
    if compile_model.toc_changed_judgment(toc_file): # 判断是否需要编译目录
        Latex_compilation_times_toc = 1
    else:
        Latex_compilation_times_toc = 0

    # 计算额外需要的 LaTeX 编译次数
    Latex_compilation_times = max(Latex_compilation_times_bib, Latex_compilation_times_index, Latex_compilation_times_toc) 

    # 进行额外的 LaTeX 编译
    for times in range(2, Latex_compilation_times+2):
        print_message(_("%(args1)s 次 %(args2)s 编译") % {'args1': str(times), 'args2': compiled_program}, "running")
        runtime_Latex = time_count(compile_model.compile_tex, )
        runtime_dict[f'{compiled_program} {abbreviations_num[times-1]}'] = runtime_Latex

    # 编译完成, 开始判断编译 XDV 文件
    if compiled_program == "XeLaTeX":  # 判断是否编译 xdv 文件
        print_message(_("DVIPDFMX 编译"), "running")
        runtime_xdv = time_count(compile_model.compile_xdv, ) # 编译 xdv 文件
        runtime_dict[_('DVIPDFMX 编译')] = runtime_xdv

    # 显示编译过程中关键信息
    print_message(_("完成所有编译"), "success")
    
    print(_("文档整体: %(args1)s 编译 %(args2)s 次") % {'args1': compiled_program, 'args2': str(Latex_compilation_times+1)})
    print(_("参考文献: ") + print_bib)
    print(_("目录索引: ") + print_index)

    # 结束草稿模式
    MFO.draft_model(project_name, draft, False)

    return runtime_dict



# --------------------------------------------------------------------------------
# LaTeX Diff 编译
# --------------------------------------------------------------------------------
def LaTeXDiffRUN(runtime_dict, project_name, compiled_program, out_files, aux_files, outdir, auxdir, non_quiet, draft):
    # 草稿模式函数启用
    MFO.draft_model(project_name, draft, True)

    abbreviations_num = ('1st', '2nd')
    # 编译前的准备工作
    compile_model = CompileLaTeX(project_name, compiled_program, out_files, aux_files, outdir, auxdir, non_quiet)


    # 首次编译 LaTeX 文档
    print_message(_("1 次 %(args)s 编译") % {'args': compiled_program}, "running")
    runtime_Latex = time_count(compile_model.compile_tex, ) 
    runtime_dict[f'{compiled_program} {abbreviations_num[0]}'] = runtime_Latex

    print_message(_("2 次 %(args1)s 编译") % {'args1': compiled_program}, "running")
    runtime_Latex = time_count(compile_model.compile_tex, )
    runtime_dict[f'{compiled_program} {abbreviations_num[1]}'] = runtime_Latex

    # 编译完成, 开始判断编译 XDV 文件
    if compiled_program == "XeLaTeX":  # 判断是否编译 xdv 文件
        print_message(_("DVIPDFMX 编译"), "running")
        runtime_xdv = time_count(compile_model.compile_xdv, ) # 编译 xdv 文件
        runtime_dict[_('DVIPDFMX 编译')] = runtime_xdv

    # 显示编译过程中关键信息
    print_message(_("完成所有编译"), "success")
    
    print(_("文档整体: %(args1)s 编译 %(args2)s 次") % {'args1': compiled_program, 'args2': str(2)})

    # 结束草稿模式
    MFO.draft_model(project_name, draft, False)

    return runtime_dict

