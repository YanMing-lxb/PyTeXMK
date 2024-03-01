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
Date         : 2024-03-01 16:14:14 +0800
LastEditTime : 2024-03-01 16:54:24 +0800
Github       : https://github.com/YanMing-lxb/
FilePath     : /PyTeXMK/src/pytexmk/test.py
Description  : 
 -----------------------------------------------------------------------
'''

# from additional_operation import search_tex

# if search_tex() :
#     print(1)
import os

def check_tex_extension(file_name):
    base_name, file_extension = os.path.splitext(os.path.basename(file_name))
    if file_extension == '.tex':
        file_name_return = base_name
    elif '.' not in file_name:
        if '/' in file_name or '\\' in file_name:
            file_name_return = None
            print("错误：文件路径无效")
        else:
            file_name_return = file_name
    else:
        file_name_return = None
        print("提示：文件后缀不是.tex")
    
    return file_name_return

# 测试
file1 = "/se/se/example.te"
file2 = "example"
check_tex_extension(file1)  # 输出: 提示：文件后缀不是.tex
check_tex_extension(file2)  # 输出: example