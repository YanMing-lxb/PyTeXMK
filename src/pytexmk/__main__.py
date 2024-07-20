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
Date         : 2024-02-28 23:11:52 +0800
LastEditTime : 2024-07-20 09:39:21 +0800
Github       : https://github.com/YanMing-lxb/
FilePath     : \PyTeXMK\src\pytexmk\__main__.py
Description  : 
 -----------------------------------------------------------------------
'''
# -*- coding: utf-8 -*-
import os
import sys
import argparse
import datetime
import webbrowser
from .version import script_name, __version__
from .compile_model import CompileModel
from .additional_operation import MoveRemoveClean, MainFileJudgment
from .info_print import time_count, time_print, print_message

MFJ = MainFileJudgment() # 实例化 MainFileJudgment 类
MRC = MoveRemoveClean() # 实例化 MoveRemoveClean 类
# --------------------------------------------------------------------------------
# 整体进行编译
# --------------------------------------------------------------------------------
def RUN(start_time, compiler_engine, project_name, out_files, aux_files, outdir, auxdir, quiet, no_clean): # TODO: 完善整体编译函数
    name_target_list = []
    runtime_list = []
    abbreviations_num = ('1st', '2nd', '3rd', '4th', '5th', '6th')
    # 编译前的准备工作
    compile_model = CompileModel(compiler_engine, project_name, quiet)

    runtime_move_aux_root, _  = MRC.move_to_root(aux_files, auxdir) # 将辅助文件移动到根目录
    name_target_list.append('辅助文件-->根目录')
    runtime_list.append(runtime_move_aux_root)

    # 检查并处理已存在的 LaTeX 输出文件
    runtime_read, return_read = time_count(compile_model.prepare_latex_output_files, ) # 读取 latex 文件
    cite_counter, toc_file, index_aux_content_dict_old = return_read # 获取 read_latex_files 函数得到的参数
    name_target_list.append('预处理已有输出文件')
    runtime_list.append(runtime_read)


    # 首次编译 LaTeX 文档
    print_message(f"{abbreviations_num[0]} 次 {compiler_engine} 编译")
    runtime_Latex, try_bool_tex = time_count(compile_model.compile_tex, ) 
    if not try_bool_tex: print(f"{compiler_engine} 1st 编译失败，{'请用 -nq 模式运行以显示错误信息！' if quiet else '请检查上面的错误信息！'}"); return
    name_target_list.append(f'{compiler_engine} 1st') # 将获取到的编译项目名称 添加到对应的列表中
    runtime_list.append(runtime_Latex)


    # 编译参考文献
    runtime_bib_judgment, return_bib_judgment = time_count(compile_model.bib_judgment, cite_counter) # 判断是否需要编译参考文献
    name_target_list.append('文献引擎判定')
    runtime_list.append(runtime_bib_judgment)

    bib_engine, Latex_compilation_times_bib, print_bib, name_target_bib = return_bib_judgment # 获取 bib_judgment 函数得到的参数
    if bib_engine:
        print_message(f'{bib_engine} 文献编译')
        if Latex_compilation_times_bib != 0:
            runtime_bib, try_bool_bib = time_count(compile_model.compile_bib, bib_engine) # 编译参考文献
            name_target_list.append(name_target_bib)
            runtime_list.append(runtime_bib)
            if not try_bool_bib: print(f"{name_target_bib} 编译失败，{'请用 -nq 模式运行以显示错误信息！' if quiet else '请检查上面的错误信息！'}"); return
        else:
            print(f"{print_bib}")
        

    # 编译索引
    runtime_makindex_judgment, return_index_judgment = time_count(compile_model.index_judgment, index_aux_content_dict_old) # 判断是否需要编译目录索引
    print_index, run_index_list_cmd = return_index_judgment
    name_target_list.append('索引引擎判定')
    runtime_list.append(runtime_makindex_judgment)

    if run_index_list_cmd: # 存在目录索引编译命令
        for cmd in run_index_list_cmd:
            print_message(f"{cmd[0]} 编译")
            Latex_compilation_times_index = 1
            runtime_index, return_index = time_count(compile_model.compile_index, cmd)
            name_target_index, try_bool_index = return_index # 获取 compile_index 函数得到的参数
            name_target_list.append(name_target_index)
            runtime_list.append(runtime_index)
            if not try_bool_index: print(f"{name_target_index} 编译失败，{'请用 -nq 模式运行以显示错误信息！' if quiet else '请检查上面的错误信息！'}"); return
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
        print_message(f"{times} 次 {compiler_engine} 编译")
        runtime_Latex, try_bool_tex = time_count(compile_model.compile_tex, )
        if not try_bool_tex: print(f"{compiler_engine} {abbreviations_num[times-1]} 编译失败，{'请用 -nq 模式运行以显示错误信息！' if quiet else '请检查上面的错误信息！'}"); return
        name_target_list.append(f'{compiler_engine} {abbreviations_num[times-1]}')
        runtime_list.append(runtime_Latex)



    # 编译完成，开始判断编译 XDV 文件
    if compiler_engine == "xelatex":  # 判断是否编译 xdv 文件
        print_message("dvipdfmx 编译")
        runtime_xdv, try_bool_xdv = time_count(compile_model.compile_xdv, ) # 编译 xdv 文件
        if not try_bool_xdv: print("dvipdfmx 编译失败，{'请用 -nq 模式运行以显示错误信息！' if quiet else '请检查上面的错误信息！'}"); return
        name_target_list.append('dvipdfmx 编译')
        runtime_list.append(runtime_xdv)


    # 显示编译过程中关键信息
    print("\n\n" + "=" * 80 + "\n" +
          "▓" * 33 + " 完成所有编译 " + "▓" * 33 + "\n" +
          "=" * 80 + "\n")
    print(f"文档整体：{compiler_engine} 编译 {Latex_compilation_times+1} 次")
    print(f"参考文献：{print_bib}")
    print(f"目录索引：{print_index}")
    print_message("开始执行编译以外的附加命令！")
    
    runtime_move_out_outdir, _ = time_count(MRC.move_to_folder, out_files, outdir) # 将输出文件移动到指定目录
    name_target_list.append("结果文件-->输出目录")
    runtime_list.append(runtime_move_out_outdir)

    runtime_move_aux_auxdir, _ = time_count(MRC.move_to_folder, aux_files, auxdir) # 将辅助文件移动到指定目录
    name_target_list.append("辅助文件-->辅助目录")
    runtime_list.append(runtime_move_aux_auxdir)

    time_print(start_time, name_target_list, runtime_list) # 打印编译时长统计




def main():
    # ! ! ! ! ! ! ! ! ! ! ! ! ! ! ! ! ! ! ! 设置默认 ! ! ! ! ! ! ! ! ! ! ! ! ! ! ! ! ! !
    compiler_engine = "xelatex"
    outdir = "./Build/"
    auxdir = "./Auxiliary/"
    magic_comments_keys = ["program", "root", "outdir", "auxdir"]
    # ! ! ! ! ! ! ! ! ! ! ! ! ! ! ! ! ! ! ! ! ! ! ! ! ! ! ! ! ! ! ! ! ! ! ! ! ! ! ! ! !

    start_time = datetime.datetime.now() # 计算开始时间
    
    # --------------------------------------------------------------------------------
    # 定义命令行参数
    # --------------------------------------------------------------------------------
    parser = argparse.ArgumentParser(description="LaTeX 辅助编译程序，如欲获取详细说明信息请运行 [-r] 参数。")
    parser.add_argument('-v', '--version', action='version', version=f'{script_name}: {__version__}')
    parser.add_argument('-r', '--readme', action='store_true', help="显示README文件")
    parser.add_argument('-p', '--pdflatex', action='store_true', help="pdflatex 进行编译")
    parser.add_argument('-x', '--xelatex', action='store_true', help="xelatex 进行编译")
    parser.add_argument('-l', '--lualatex', action='store_true', help="lualatex 进行编译")
    parser.add_argument('-c', '--clean', action='store_true', help="清除所有辅助文件")
    parser.add_argument('-C', '--Clean', action='store_true', help="清除所有辅助文件和 pdf 文件")
    parser.add_argument('-nc', '--no-clean', action='store_true', help="保留已生成的辅助文件")
    parser.add_argument('-nq', '--no-quiet', action='store_true', help="非安静模式运行，此模式下显示编译过程")
    parser.add_argument('-cp', '--clean-pdf', action='store_true', help="尝试修复所有根目录以外的 pdf 文件，当 LaTeX 编译过程中警告 invalid X X R object 时，可使用此参数尝试修复所有 pdf 文件")
    
    parser.add_argument('document', nargs='?', help="要被编译的文件名")
    args = parser.parse_args()

    

    if args.readme: # 如果存在 readme 参数
        import pkg_resources
        readme_path = pkg_resources.resource_filename(__name__, "/data/README.html")
        print(f"正在打开 {readme_path} 文件！")
        webbrowser.open('file://' + os.path.abspath(readme_path))
        sys.exit()

    tex_files = MFJ.search_tex_file() # 运行 search_tex_file 函数搜索当前目录下所有 tex 文件
    magic_comments = MFJ.search_magic_comments(tex_files, magic_comments_keys) # 运行 search_magic_comments 函数搜索 tex_files 列表中是否存在 magic comments

    # --------------------------------------------------------------------------------
    # 输出文件路径判断
    # --------------------------------------------------------------------------------
    if magic_comments.get('outdir'): # 如果存在 magic comments 且 outdir 存在
        outdir = magic_comments['outdir'] # 使用 magic comments 中的 outdir 作为输出目录
        print(f"通过魔法注释找到输出目录为 {outdir}！")
    if magic_comments.get('auxdir'): # 如果存在 magic comments 且 auxdir 存在
        auxdir = magic_comments['auxdir'] # 使用 magic comments 中的 auxdir 作为辅助文件目录
        print(f"通过魔法注释找到辅助文件目录为 {auxdir}！")

    # --------------------------------------------------------------------------------
    # 主文件逻辑判断
    # --------------------------------------------------------------------------------
    if args.document: # pytexmk 指定 latex 文件
        project_name = MFJ.check_project_name(args.document) # check_project_name 函数检查 args.document 参数输入的文件名是否正确
    else: # pytexmk 未指定 latex 文件
        if magic_comments.get('root'): # 如果存在 magic comments 且 root 存在
            project_name = MFJ.check_project_name(magic_comments['root']) # 使用 magic comments 中的 root 作为文件名
            print(f"通过魔法注释找到 {project_name}.tex 文件！")
        else: # pytexmk 和魔法注释都不存在，使用search_main_file方法搜索主文件
            project_name = MFJ.search_main_file(tex_files)

    # --------------------------------------------------------------------------------
    # 编译类型判断
    # --------------------------------------------------------------------------------
    if args.xelatex:
        compiler_engine = "xelatex"
    elif args.pdflatex:
        compiler_engine = "pdflatex"
    elif args.lualatex:
        compiler_engine = "lualatex"
    elif magic_comments.get('program'): # 如果存在 magic comments 且 program 存在
        compiler_engine = magic_comments['program'] # 使用 magic comments 中的 program 作为编译器
        print(f"通过魔法注释设置编译器为 {compiler_engine}！")

    # --------------------------------------------------------------------------------
    # 编译程序运行
    # --------------------------------------------------------------------------------
    out_files = [f"{project_name}{ext}" for ext in [".pdf", ".synctex.gz"]]
    aux_files = [
        f"{project_name}{ext}" for ext in [".log", ".blg", ".ilg",  # 日志文件
                                           ".aux", ".bbl", ".xml",  # 参考文献辅助文件
                                           ".toc", ".lof", ".lot",  # 目录辅助文件
                                           ".out", ".bcf",
                                           ".idx", ".ind", ".nlo", ".nls", ".ist", ".glo", ".gls",  # 索引辅助文件
                                           ".bak", ".spl",
                                           ".ent-x", ".tmp", ".ltx", ".los", ".lol", ".loc", ".listing", ".gz",
                                           ".userbak", ".nav", ".snm", ".vrb", ".fls", ".xdv", ".fdb_latexmk", ".run.xml"]
    ]

    if project_name: # 如果存在 project_name
        if args.clean:
            MRC.remove_files(aux_files, auxdir)
        elif args.Clean:
            MRC.remove_files(aux_files, auxdir)
            MRC.remove_files(out_files, outdir)
            MRC.remove_files(aux_files, '.')
        elif args.clean_pdf:
            MRC.clean_pdf(project_name, '.', outdir)
        elif args.no_clean:
            RUN(start_time, compiler_engine, project_name, out_files, aux_files, outdir, auxdir, not args.no_quiet, True)
        else:
            RUN(start_time, compiler_engine, project_name, out_files, aux_files, outdir, auxdir, not args.no_quiet, False)

if __name__ == "__main__":

    main()
