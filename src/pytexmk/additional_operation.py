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
LastEditTime : 2024-03-01 12:50:42 +0800
Github       : https://github.com/YanMing-lxb/
FilePath     : \PyTeXMK\src\pytexmk\additional_operation.py
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
        f"{file_name}{ext}" for ext in [".pdf", ".synctex", ".aux", ".bbl", ".blg", ".log", ".out", ".toc", ".bcf",
                                        ".xml", ".synctex", ".nlo", ".nls", ".bak", ".ind", ".idx", ".ilg", ".lof",
                                        ".lot", ".ent-x", ".tmp", ".ltx", ".los", ".lol", ".loc", ".listing", ".gz",
                                        ".userbak", ".nav", ".snm", ".vrb", ".fls", ".xdv", ".fdb_latexmk", ".run.xml", ".ist", ".glo", ".gls"]
    ]
    for file in auxiliary_files:
        try:
            os.remove(file)
        except FileNotFoundError:
            pass
    print("已清除辅助文件")

# --------------------------------------------------------------------------------
# 定义清除已有结果文件
# --------------------------------------------------------------------------------
def remove_result(build_path):
    if os.path.exists(build_path):
        shutil.rmtree(build_path) # 删除整个文件夹
        print("删除上次生成的结果文件")
    os.mkdir(build_path) # 创建空的 build_path 文件夹
    
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

def time_count(fun):
    time_start = datetime.datetime.now()
    fun_return = fun
    time_end = datetime.datetime.now()
    time_run = time_end - time_start

    print_time = f'{round(time_run.total_seconds(), 6)} s'
    return time_run, print_time, fun_return
