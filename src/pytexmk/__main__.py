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
LastEditTime : 2024-03-03 15:37:58 +0800
Github       : https://github.com/YanMing-lxb/
FilePath     : \PyTeXMK\src\pytexmk\__main__.py
Description  : 
 -----------------------------------------------------------------------
'''
# -*- coding: utf-8 -*-
import argparse
import datetime
from .version import script_name, version
from .compile_model import compile_tex, compile_bib, compile_index, compile_xdv
from .additional_operation import remove_aux, remove_result, remove_result_in_root, move_result, search_file, check_file_name
from info_print import time_count, time_print, print_message
# ================================================================================
# XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX 整体进行编译 XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX
# ================================================================================
def compile(tex_name, file_name, quiet, build_path):
    name_target_list = []
    time_run_list = []

    time_run_remove_aux, _ = time_count(remove_aux, file_name) # 清除已有辅助文件
    name_target_list.append("清除辅助文件")
    time_run_list.append(time_run_remove_aux)

    time_run_tex, _ = time_count(compile_tex, tex_name, file_name, 1, quiet) # 首次编译 tex 文档
    time_run_bib, return_com_bib = time_count(compile_bib, file_name, quiet) # 编译参考文献
    time_run_index, return_com_index = time_count(compile_index, file_name) # 编译目录索引
    
    times_compile_tex_bib, print_bib, name_target_bib = return_com_bib # 获取 compile_bib 函数得到的参数
    times_compile_tex_index, print_index, name_target_index = return_com_index # 获取 compile_index 函数得到的参数
    times_extra_complie = max(times_compile_tex_bib, times_compile_tex_index) # 计算额外编译 tex 文档次数

    # 将获取到的编译项目名称 添加到对应的列表中
    name_target_list.append(f'{tex_name} 1 次')
    time_run_list.append(time_run_tex)
    if times_compile_tex_bib != 0: # 存在参考文献编译过程
        name_target_list.append(name_target_bib)
        time_run_list.append(time_run_bib)
    if times_compile_tex_index != 0: # 存在目录索引编译过程
        name_target_list.append(name_target_index)
        time_run_list.append(time_run_index)

    for i in range(times_extra_complie): # 进行额外编译 tex
        time_run_tex, _ = time_count(compile_tex, tex_name, file_name, i + 2, quiet)
        name_target_list.append(f'{tex_name} {i+2} 次')
        time_run_list.append(time_run_tex)

    if tex_name == "xelatex":  # 判断是否编译 xdv 文件
        time_run_xdv, _ = time_count(compile_xdv, file_name, quiet) # 编译 xdv 文件
        name_target_list.append('xdvipdfmx')
        time_run_list.append(time_run_xdv)

    print("\n\n" + "=" * 80 + "\n" +
          "▓" * 33 + " 完成所有编译 " + "▓" * 33 + "\n" +
          "=" * 80 + "\n")
    print(f"文档整体：{tex_name} 编译 {times_extra_complie+1} 次")
    print(f"参考文献：{print_bib}")
    print(f"目录索引：{print_index}")
    print_message("开始执行编译以外的附加命令！")
    
    time_run_remove_res, _ = time_count(remove_result, build_path) # 清除已有结果文件
    name_target_list.append("清除旧结果文件")
    time_run_list.append(time_run_remove_res)
    time_run_move_res, _ = time_count(move_result, file_name, build_path) # 移动生成结果文件
    name_target_list.append("移动结果文件")
    time_run_list.append(time_run_move_res)
    time_run_remove_aux, _ = time_count(remove_aux, file_name) # 清除生成辅助文件
    name_target_list.append("清除辅助文件")
    time_run_list.append(time_run_remove_aux)

    return name_target_list, time_run_list

def main():
    # ▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓ 设置默认 ▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓
    tex_name = "xelatex"
    build_path = "./Build/"
    # ▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓

    start_time = datetime.datetime.now() # 计算开始时间
    
    # --------------------------------------------------------------------------------
    # 定义命令行参数
    # --------------------------------------------------------------------------------
    parser = argparse.ArgumentParser(description="LaTeX 辅助编译程序.")
    parser.add_argument('-v', '--version', action='version', version=f'{script_name}: {version}')
    parser.add_argument('-c', '--clean', action='store_true', help="清除所有辅助文件")
    parser.add_argument('-C', '--Clean', action='store_true', help="清除所有辅助文件和 pdf 文件")
    parser.add_argument('-nq', '--no-quiet', action='store_true', help="非安静模式运行，此模式下显示编译过程")
    parser.add_argument('-p', '--pdflatex', action='store_true', help="pdflatex 进行编译")
    parser.add_argument('-x', '--xelatex', action='store_true', help="xelatex 进行编译")
    parser.add_argument('-l', '--lualatex', action='store_true', help="lualatex 进行编译")
    parser.add_argument('document', nargs='?', help="要被编译的文件名")
    args = parser.parse_args()

    if args.xelatex:
        tex_name = "xelatex"
    if args.pdflatex:
        tex_name = "pdflatex"
    if args.lualatex:
        tex_name = "lualatex"

    if args.document: # 指定 latex 文件
        file_name = check_file_name(args.document) # check_file_name 函数检查 args.document 参数输入的文件名是否正确
    else: # 未指定 latex 文件
        file_name = search_file() # 运行 search_file 函数判断

    if file_name: # 如果存在 file_name
        if args.clean:
            remove_aux(file_name)
        elif args.Clean:
            remove_aux(file_name)
            remove_result(build_path)
            remove_result_in_root(file_name)
        else:
            name_target_list, time_run_list = compile(tex_name, file_name, not args.no_quiet, build_path)
            time_print(start_time, name_target_list, time_run_list) # 打印编译时长统计

if __name__ == "__main__":

    main()