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
LastEditTime : 2024-02-29 19:53:25 +0800
Github       : https://github.com/YanMing-lxb/
FilePath     : /PyTeXMK/src/pytexmk/__main__.py
Description  : 
 -----------------------------------------------------------------------
'''

import argparse
from datetime import datetime
from .version import script_name, version
from .compile_model import compile_tex, compile_bib, compile_index, compile_xdv
from .additional_operation import remove_aux, remove_result, move_result
# # 获取当前目录中所有以 .tex 结尾的文件列表
# files = [f for f in os.listdir() if f.endswith('.tex')]

# # 处理每个符合条件的文件名
# for file in files:
#     file_name += os.path.splitext(file)[0] + "\n"  # 使用 os.path.splitext 去掉后缀并添加到 file_name 中


# ================================================================================
# XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX 整体进行编译 XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX
# ================================================================================
def compile(tex_name, file_name, quiet, build_path):
    remove_aux(file_name) # 清除旧辅助文件

    compile_tex(tex_name, file_name, 1, quiet) # 首次编译 tex 文档
    bib_compile_return = compile_bib(file_name, quiet) # 编译参考文献
    index_compile_return = compile_index(file_name) # 编译索引

    extra_complie_times = max(bib_compile_return[0], index_compile_return[0]) # 额外编译 tex 文档
    for time in range(extra_complie_times):
        compile_tex(tex_name, file_name, time + 2, quiet)

    compile_xdv(tex_name, file_name) # 编译 xdv 文件

    print("\n\n" + "=" * 80 + "\n" +
          "▓" * 33 + " 完成所有编译 " + "▓" * 33 + "\n" +
          "=" * 80 + "\n")
    print(f"文档整体：{tex_name} 编译 {extra_complie_times+1} 次")
    print(f"参考文献：{bib_compile_return[1]}")
    print(f"目录索引：{index_compile_return[1]}")
    print("\n" + "=" * 80 + "\n" +
          "X" * 26 + " 开始执行编译以外的附加命令！" + "X" * 25 + "\n" +
          "=" * 80 + "\n")
    
    remove_result(build_path)
    move_result(file_name, build_path)
    remove_aux(file_name)


def main():
    # ▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓ 设置默认 ▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓
    file_name = "main"
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

    start_time = datetime.now() # 计算开始时间

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
        compile(tex_name, args.document if args.document else file_name, not args.no_quiet, build_path)

    # --------------------------------------------------------------------------------
    # 统计编译时长
    # --------------------------------------------------------------------------------
    end_time = datetime.now() # 计算开始时间
    run_time = end_time - start_time
    hours, remainder = divmod(run_time.seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    milliseconds = run_time.microseconds // 1000  # 获取毫秒部分
    print("\n" + "=" * 80)
    print(f"编译时长为：{hours} 小时 {minutes} 分 {seconds} 秒 {milliseconds} 毫秒 ({run_time.total_seconds():.3f} s total)\n")


if __name__ == "__main__":

    main()