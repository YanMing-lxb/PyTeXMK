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
Date         : 2024-02-29 16:02:37 +0800
LastEditTime : 2024-03-01 20:43:13 +0800
Github       : https://github.com/YanMing-lxb/
FilePath     : /PyTeXMK/src/pytexmk/additional_operation.py
Description  : 
 -----------------------------------------------------------------------
'''

import os
import datetime
import shutil

# --------------------------------------------------------------------------------
# 定义清除辅助文件命令
# --------------------------------------------------------------------------------
def remove_aux(file_name):
    auxiliary_files = [
        f"{file_name}{ext}" for ext in [".aux", ".bbl", ".blg", ".log", ".out", ".toc", ".bcf",
                                        ".xml", ".nlo", ".nls", ".bak", ".ind", ".idx", ".ilg", ".lof",
                                        ".lot", ".ent-x", ".tmp", ".ltx", ".los", ".lol", ".loc", ".listing", ".gz",
                                        ".userbak", ".nav", ".snm", ".vrb", ".fls", ".xdv", ".fdb_latexmk", ".run.xml", ".ist", ".glo", ".gls"]
    ]
    file_exists = False
    for file in auxiliary_files:
        if os.path.exists(file):
            try:
                os.remove(file)
                file_exists = True
            except FileNotFoundError:
                pass
    if file_exists:
        print("已清除辅助文件")
    else:
        print("未找到辅助文件")

# --------------------------------------------------------------------------------
# 定义清除已有结果文件
# --------------------------------------------------------------------------------
def remove_result(build_path):
    if os.path.exists(build_path):
        shutil.rmtree(build_path)  # 删除整个文件夹
        print("删除上次生成的结果文件")
    os.mkdir(build_path)  # 创建空的 build_path 文件夹

# --------------------------------------------------------------------------------
# 定义移动生成文件
# --------------------------------------------------------------------------------
def move_result(file_name, build_path):
    result_files = [f"{file_name}{ext}" for ext in [".pdf", ".synctex.gz"]]
    for file in result_files:
        if os.path.exists(file):
            shutil.move(file, build_path)
        else:
            print(f'{file} 不存在！')
    print(f"移动结果文件到 {build_path}")

# --------------------------------------------------------------------------------
# 定义时间统计函数
# --------------------------------------------------------------------------------
def time_count(fun, *args):
    time_start = datetime.datetime.now()
    fun_return = fun(*args)
    time_end = datetime.datetime.now()
    time_run = time_end - time_start

    print_time = f'{round(time_run.total_seconds(), 6)} s'
    return time_run, print_time, fun_return

# --------------------------------------------------------------------------------
# 定义输入检查函数
# --------------------------------------------------------------------------------
def check_file_name(file_name):
    base_name, file_extension = os.path.splitext(
        os.path.basename(file_name))  # 去掉路径，提取文件名和后缀
    if file_extension == '.tex':  # 判断后缀是否是 .tex
        file_name_return = base_name
    elif '.' not in file_name:  # 判断输入 file_name 中没有 后缀
        if '/' in file_name or '\\' in file_name:  # 判断是否是没有后缀的路径
            file_name_return = None
            print("错误：文件路径无效")
        else:
            file_name_return = file_name
    else:
        file_name_return = None
        print("提示：文件后缀不是.tex")

    return file_name_return

# --------------------------------------------------------------------------------
# 定义 tex 文件检索函数
# --------------------------------------------------------------------------------
def search_file():
    # 获取当前路径
    current_path = os.getcwd()
    # 遍历当前路径下的所有文件
    tex_files = [file for file in os.listdir(
        current_path) if file.endswith('.tex')]

    if tex_files:
        # 如果只有一个.tex文件，则直接提取文件名并打印
        if len(tex_files) == 1:
            tex_name = os.path.splitext(tex_files[0])[0]
            print(f"编译 {tex_name}.tex 文件:")
        else:
            # 如果存在多个.tex文件
            if 'main.tex' in tex_files:
                # 存在名为main.tex的文件，打印'main'
                tex_name = 'main'
                print("编译 'main.tex' 文件")
            else:
                # 不存在名为main.tex的文件，打印所有找到的.tex文件
                tex_name = None
                print("存在多个 .tex 文件，请添加 main.tex 文件或终端输入：pytexmk <主文件名> 名进行编译")
    else:
        # 不存在.tex文件，打印当前路径并提示
        tex_name = None
        print("在当前终端路径下不存在 .tex 文件，请检查终端显示路径是否是项目路径:", current_path)

    return tex_name