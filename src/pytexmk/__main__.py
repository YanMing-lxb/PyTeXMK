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
LastEditTime : 2024-03-01 17:05:53 +0800
Github       : https://github.com/YanMing-lxb/
FilePath     : /PyTeXMK/src/pytexmk/__main__.py
Description  : 
 -----------------------------------------------------------------------
'''

import argparse
import datetime
from .version import script_name, version
from .compile_model import compile_tex, compile_bib, compile_index, compile_xdv
from .additional_operation import remove_aux, remove_result, move_result, time_count, search_file, check_file_name
# # 获取当前目录中所有以 .tex 结尾的文件列表
# files = [f for f in os.listdir() if f.endswith('.tex')]

# # 处理每个符合条件的文件名
# for file in files:
#     file_name += os.path.splitext(file)[0] + "\n"  # 使用 os.path.splitext 去掉后缀并添加到 file_name 中


# ================================================================================
# XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX 整体进行编译 XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX
# ================================================================================
def compile(tex_name, file_name, quiet, build_path):
    name_target_list = []
    time_com_list = []
    print_time_list = []

    time_com_remove_aux, print_time_remove_aux, _ = time_count(remove_aux, file_name) # 清除已有辅助文件
    name_target_list.append("清除辅助文件")
    time_com_list.append(time_com_remove_aux)
    print_time_list.append(print_time_remove_aux)

    time_com_tex, print_time_com_tex, _ = time_count(compile_tex, tex_name, file_name, 1, quiet) # 首次编译 tex 文档
    time_com_bib, print_time_com_bib, return_com_bib = time_count(compile_bib, file_name, quiet) # 编译参考文献
    time_com_index, print_time_com_index, return_com_index = time_count(compile_index, file_name) # 编译目录索引
    
    times_compile_tex_bib, print_bib, name_target_bib = return_com_bib # 获取 compile_bib 函数得到的参数
    times_compile_tex_index, print_index, name_target_index = return_com_index # 获取 compile_index 函数得到的参数
    times_extra_complie = max(times_compile_tex_bib, times_compile_tex_index) # 计算额外编译 tex 文档次数

    # 将获取到的编译项目名称 添加到对应的列表中
    name_target_list.append(f'{tex_name} 1')
    time_com_list.append(time_com_tex)
    print_time_list.append(print_time_com_tex)
    if times_compile_tex_bib != 0: # 存在参考文献编译过程
        name_target_list.append(name_target_bib)
        time_com_list.append(time_com_bib)
        print_time_list.append(print_time_com_bib)
    if times_compile_tex_index != 0: # 存在目录索引编译过程
        name_target_list.append(name_target_index)
        time_com_list.append(time_com_index)
        print_time_list.append(print_time_com_index)

    for i in range(times_extra_complie): # 进行额外编译 tex
        time_com_tex, print_time_com_tex, _ = time_count(compile_tex, tex_name, file_name, i + 2, quiet)
        name_target_list.append(f'{tex_name} {i+2}')
        time_com_list.append(time_com_tex)
        print_time_list.append(print_time_com_tex)

    if tex_name == "xelatex":  # 判断是否编译 xdv 文件
        time_com_xdv, print_time_com_xdv, _ = time_count(compile_xdv, file_name) # 编译 xdv 文件
        name_target_list.append('xdvipdfmx')
        time_com_list.append(time_com_xdv)
        print_time_list.append(print_time_com_xdv)

    print("\n\n" + "=" * 80 + "\n" +
          "▓" * 33 + " 完成所有编译 " + "▓" * 33 + "\n" +
          "=" * 80 + "\n")
    print(f"文档整体：{tex_name} 编译 {times_extra_complie+1} 次")
    print(f"参考文献：{print_bib}")
    print(f"目录索引：{print_index}")
    print("\n" + "=" * 80 + "\n" +
          "X" * 26 + " 开始执行编译以外的附加命令！" + "X" * 25 + "\n" +
          "=" * 80 + "\n")
    
    time_com_remove_res, print_time_remove_res, _ = time_count(remove_result, build_path) # 清除已有结果文件
    name_target_list.append("清除旧结果文件")
    time_com_list.append(time_com_remove_res)
    print_time_list.append(print_time_remove_res)
    time_com_move_res, print_time_move_res, _ = time_count(move_result, file_name, build_path) # 移动生成结果文件
    name_target_list.append("移动结果文件")
    time_com_list.append(time_com_move_res)
    print_time_list.append(print_time_move_res)
    time_com_remove_aux, print_time_remove_aux, _ = time_count(remove_aux, file_name) # 清除生成辅助文件
    name_target_list.append("清除辅助文件")
    time_com_list.append(time_com_remove_aux)
    print_time_list.append(print_time_remove_aux)


def main():
    # ▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓ 设置默认 ▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓
    tex_name = "xelatex"
    build_path = "./Build/"
    # ▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓

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

    start_time = datetime.datetime.now() # 计算开始时间

    if args.xelatex:
        tex_name = "xelatex"
    if args.pdflatex:
        tex_name = "pdflatex"
    if args.lualatex:
        tex_name = "lualatex"

    if args.clean:
        remove_aux(file_name)
    elif args.Clean:
        remove_aux(file_name)
        remove_result(build_path)
    else:
        if args.document: # 指定 latex 文件
            file_name = check_file_name(args.document) # check_file_name 函数检查 args.document 参数输入的文件名是否正确
        else: # 未指定 latex 文件
            file_name = search_file() # 运行 search_file 函数判断
        if file_name: # 如果存在 file_name
            compile(tex_name, file_name, not args.no_quiet, build_path)

    # --------------------------------------------------------------------------------
    # 统计编译时长
    # --------------------------------------------------------------------------------
    end_time = datetime.datetime.now() # 计算开始时间
    run_time = end_time - start_time
    hours, remainder = divmod(run_time.seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    milliseconds = run_time.microseconds // 1000  # 获取毫秒部分
    print("\n" + "=" * 80)
    print(f"编译时长为：{hours} 小时 {minutes} 分 {seconds} 秒 {milliseconds} 毫秒 ({run_time.total_seconds():.3f} s total)\n")

if __name__ == "__main__":

    main()

# 总时长
# 调用程序时长
# 其他操作时长
# pytexmk运行时长
# 运行规则数目