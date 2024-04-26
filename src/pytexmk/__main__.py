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
LastEditTime : 2024-04-26 22:43:47 +0800
Github       : https://github.com/YanMing-lxb/
FilePath     : /PyTeXMK/src/pytexmk/__main__.py
Description  : 
 -----------------------------------------------------------------------
'''
# -*- coding: utf-8 -*-
import argparse
import datetime
from .version import script_name, __version__
from .compile_model import compile_tex, compile_bib, compile_index, compile_xdv
from .additional_operation import *
from .info_print import time_count, time_print, print_message

# ================================================================================
# XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX 整体进行编译 XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX
# ================================================================================
def compile(start_time,tex_name, file_name, quiet, outdir):
    name_target_list = []
    time_run_list = []

    time_run_remove_aux, _ = time_count(remove_aux, file_name) # 清除已有辅助文件
    name_target_list.append("清除旧辅助文件")
    time_run_list.append(time_run_remove_aux)

    time_run_tex, try_bool_tex = time_count(compile_tex, tex_name, file_name, 1, quiet) # 首次编译 tex 文档
    if not try_bool_tex: print(f"{tex_name} 1st 编译失败，{'请用 -nq 模式运行以显示错误信息！' if quiet else '请检查上面的错误信息！'}"); return
    time_run_bib, return_com_bib = time_count(compile_bib, file_name, quiet) # 编译参考文献
    times_compile_tex_bib, print_bib, name_target_bib, try_bool_bib = return_com_bib # 获取 compile_bib 函数得到的参数
    if not try_bool_bib: print(f"{name_target_bib} 编译失败，{'请用 -nq 模式运行以显示错误信息！' if quiet else '请检查上面的错误信息！'}"); return
    time_run_index, return_com_index = time_count(compile_index, file_name) # 编译目录索引
    times_compile_tex_index, print_index, name_target_index, try_bool_index = return_com_index # 获取 compile_index 函数得到的参数
    if not try_bool_index: print(f"{name_target_bib} 编译失败，{'请用 -nq 模式运行以显示错误信息！' if quiet else '请检查上面的错误信息！'}"); return
    
    times_extra_complie = max(times_compile_tex_bib, times_compile_tex_index) # 计算额外编译 tex 文档次数

    # 将获取到的编译项目名称 添加到对应的列表中
    name_target_list.append(f'{tex_name} 1st')
    time_run_list.append(time_run_tex)
    
    if times_compile_tex_bib != 0: # 存在参考文献编译过程
        if name_target_bib:
            name_target_list.append(name_target_bib)
            time_run_list.append(time_run_bib)
    if times_compile_tex_index != 0: # 存在目录索引编译过程
        if name_target_index:
            name_target_list.append(name_target_index)
            time_run_list.append(time_run_index)

    for i in range(times_extra_complie): # 进行额外编译 tex
        time_run_tex, try_bool_tex = time_count(compile_tex, tex_name, file_name, i + 2, quiet)
        if i+2 == 2: 
            if not try_bool_tex: print(f"{tex_name} {i+2}nd 编译失败，{'请用 -nq 模式运行以显示错误信息！' if quiet else '请检查上面的错误信息！'}"); return
            name_target_list.append(f'{tex_name} {i+2}nd')
        if i+2 == 3:
            if not try_bool_tex: print(f"{tex_name} {i+2}rd 编译失败，{'请用 -nq 模式运行以显示错误信息！' if quiet else '请检查上面的错误信息！'}"); return
            name_target_list.append(f'{tex_name} {i+2}rd')
            
        time_run_list.append(time_run_tex)

    if tex_name == "xelatex":  # 判断是否编译 xdv 文件
        time_run_xdv, try_bool_xdv = time_count(compile_xdv, file_name, quiet) # 编译 xdv 文件
        if not try_bool_xdv: print("dvipdfmx 编译失败，{'请用 -nq 模式运行以显示错误信息！' if quiet else '请检查上面的错误信息！'}"); return
        name_target_list.append('dvipdfmx 编译')
        time_run_list.append(time_run_xdv)

    print("\n\n" + "=" * 80 + "\n" +
          "▓" * 33 + " 完成所有编译 " + "▓" * 33 + "\n" +
          "=" * 80 + "\n")
    print(f"文档整体：{tex_name} 编译 {times_extra_complie+1} 次")
    print(f"参考文献：{print_bib}")
    print(f"目录索引：{print_index}")
    print_message("开始执行编译以外的附加命令！")
    
    time_run_remove_res, _ = time_count(remove_result, outdir) # 清除已有结果文件
    name_target_list.append("清除旧结果文件")
    time_run_list.append(time_run_remove_res)
    time_run_move_res, _ = time_count(move_result, file_name, outdir) # 移动生成结果文件
    name_target_list.append("移动结果文件")
    time_run_list.append(time_run_move_res)
    time_run_remove_aux, _ = time_count(remove_aux, file_name) # 清除生成辅助文件
    name_target_list.append("清除辅助文件")
    time_run_list.append(time_run_remove_aux)

    time_print(start_time, name_target_list, time_run_list) # 打印编译时长统计

def main():
    # ▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓ 设置默认 ▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓
    tex_name = "xelatex"
    outdir = "./Build/"
    magic_comments_keys = ["program", "root", "outdir"]
    # ▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓

    start_time = datetime.datetime.now() # 计算开始时间
    
    # --------------------------------------------------------------------------------
    # 定义命令行参数
    # --------------------------------------------------------------------------------
    parser = argparse.ArgumentParser(description="LaTeX 辅助编译程序.")
    parser.add_argument('-v', '--version', action='version', version=f'{script_name}: {__version__}')
    parser.add_argument('-p', '--pdflatex', action='store_true', help="pdflatex 进行编译")
    parser.add_argument('-x', '--xelatex', action='store_true', help="xelatex 进行编译")
    parser.add_argument('-l', '--lualatex', action='store_true', help="lualatex 进行编译")
    parser.add_argument('-c', '--clean', action='store_true', help="清除所有辅助文件")
    parser.add_argument('-C', '--Clean', action='store_true', help="清除所有辅助文件和 pdf 文件")
    parser.add_argument('-nq', '--no-quiet', action='store_true', help="非安静模式运行，此模式下显示编译过程")
    parser.add_argument('-cp', '--clean-pdf', action='store_true', help="清理 pdf 文件，当 LaTeX 编译过程中警告 invalid X X R object 时，可使用此参数清理所有 pdf 文件")
    
    parser.add_argument('document', nargs='?', help="要被编译的文件名")
    args = parser.parse_args()

    tex_files = search_tex_file # 运行 search_tex_file 函数搜索当前目录下所有 tex 文件
    magic_comments = search_magic_comments(tex_files, magic_comments_keys) # 运行 search_magic_comments 函数搜索 tex_files 列表中是否存在 magic comments

    # --------------------------------------------------------------------------------
    # 输出文件路径判断
    # --------------------------------------------------------------------------------
    if magic_comments['outdir']: # 如果存在 magic comments 且 outdir 存在
        outdir = magic_comments['outdir'] # 使用 magic comments 中的 outdir 作为输出目录
        print(f"通过魔法注释找到输出目录为 {outdir}！")

    # --------------------------------------------------------------------------------
    # 主文件逻辑判断
    # --------------------------------------------------------------------------------
    if args.document: # pytexmk 指定 latex 文件
        file_name = check_file_name(args.document) # check_file_name 函数检查 args.document 参数输入的文件名是否正确
    else: # pytexmk 未指定 latex 文件
        if magic_comments['root']: # 如果存在 magic comments 且 root 存在
            file_name = check_file_name(magic_comments['root']) # 使用 magic comments 中的 root 作为文件名
            print(f"通过魔法注释找到 {file_name}.tex 文件！")
        else: # pytexmk 和魔法注释都不存在，使用search_main_file方法搜索主文件
            file_name = search_main_file(tex_files)
    # --------------------------------------------------------------------------------
    # 编译类型判断
    # --------------------------------------------------------------------------------
    if args.xelatex:
        tex_name = "xelatex"
    elif args.pdflatex:
        tex_name = "pdflatex"
    elif args.lualatex:
        tex_name = "lualatex"
    elif magic_comments['program']: # 如果存在 magic comments 且 program 存在
        tex_name = magic_comments['program'] # 使用 magic comments 中的 program 作为编译器
        print(f"通过魔法注释设置编译器为 {tex_name}！")

    # --------------------------------------------------------------------------------
    # 编译程序运行
    # --------------------------------------------------------------------------------

    if file_name: # 如果存在 file_name
        if args.clean:
            remove_aux(file_name)
        elif args.Clean:
            remove_aux(file_name)
            remove_result(outdir)
            remove_result_in_root(file_name)
        elif args.clean_pdf:
            clean_all_pdf('.', outdir, file_name)
        else:
            compile(start_time, tex_name, file_name, not args.no_quiet, outdir)
            
    

if __name__ == "__main__":

    main()