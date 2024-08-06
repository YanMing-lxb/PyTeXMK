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
Date         : 2024-08-06 16:59:49 +0800
LastEditTime : 2024-08-06 21:39:49 +0800
Github       : https://github.com/YanMing-lxb/
FilePath     : /PyTeXMK/src/pytexmk/language_model.py
Description  : 
 -----------------------------------------------------------------------
'''

import locale

def check_language(info_strings_zh, info_strings_en):
    # 获取当前系统的默认区域设置
    current_locale = locale.getdefaultlocale()
    if current_locale[0].startswith('zh'):
        return info_strings_zh
    else:
        return info_strings_en

def info_desrption(info_list, key):
    return info_list[key]