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
Date         : 2024-08-07 20:16:03 +0800
LastEditTime : 2024-08-16 16:02:36 +0800
Github       : https://github.com/YanMing-lxb/
FilePath     : /PyTeXMK/src/pytexmk/get_main_file_module.py
Description  : 
 -----------------------------------------------------------------------
'''
import logging
from rich import print
from pathlib import Path

from .language_module import set_language
from .additional_module import MainFileJudgment, exit_pytexmk

_ = set_language('get_main_file')

MFJ = MainFileJudgment() # 实例化 MainFileJudgment 类

# 实例化 logger 类
logger = logging.getLogger(__name__)

def get_main_file(default_file, args_document, main_file_in_root, all_magic_comments):
    project_name = ''
    current_path = Path.cwd()  # 使用pathlib库获取当前工作目录的路径
    if args_document: # 当前目录下存在 tex 文件, 且命令行参数中指定了主文件
        project_name = args_document # 使用命令行参数指定主文件
        print(_("通过命令行命令指定待编译主文件为: ") + f"[bold cyan]{project_name}")
        return project_name
    if len(main_file_in_root) == 1: # 如果当前根目录下存在且只有一个主文件
        project_name = main_file_in_root[0] # 使用该文件作为待编译主文件
        print(_("通过根目录下唯一主文件指定待编译主文件为: ") + f"[bold cyan]{project_name}.tex")
        return project_name

    if 'root' in all_magic_comments: # 当前目录下存在多个主文件, 且存在 % TEX root 魔法注释
        logger.info(_("魔法注释 % !TEX root 在当前根目录下主文件中有被定义"))
        if len(all_magic_comments['root']) == 1: # 当前目录下存在多个主文件, 且只有一个存在 % TEX root 魔法注释
            logger.info(_("魔法注释 % !TEX root 只存在于: ") + f"{all_magic_comments['root'][0][0]}.tex")
            check_file = MFJ.check_project_name(main_file_in_root, all_magic_comments['root'][0][1], '.tex') # 检查 magic comments 中指定的 root 文件名是否正确
            if f"{all_magic_comments['root'][0][0]}" == f"{check_file}": # 如果 magic comments 中指定的 root 文件名与当前文件名相同
                project_name = check_file # 使用魔法注释 % !TEX root 指定的文件作为主文件
                print(_("通过魔法注释 % !TEX root 指定待编译主文件为: ") + f"[bold cyan]{project_name}.tex")
                return project_name
            else: # 如果 magic comments 中指定的 root 文件名与当前文件名不同
                logger.warning(_("魔法注释 % !TEX root 指定的文件名与当前文件名不同, 无法确定主文件: ") + f"[bold red]{check_file}.tex[/bold red], [bold green]{all_magic_comments['root'][0][0]}.tex[/bold green] ")
        if len(all_magic_comments['root']) > 1: # 当前目录下存在多个主文件, 且多个 tex 文件中同时存在 % TEX root 魔法注释
            logger.warning(_("魔法注释 % !TEX root 在当前根目录下的多个主文件中同时被定义, 无法根据魔法注释确定待编译主文件")) 

    if not project_name: # 如果当前根目录下存在多个主文件, 且不存在 % TEX root 魔法注释, 并且待编译主文件还没有找到
        logger.info(_("无法根据魔法注释判断出待编译主文件, 尝试根据默认主文件名指定待编译主文件"))
        for file in main_file_in_root:
            default_file = MFJ.check_project_name(main_file_in_root, default_file, '.tex') # 检查 default_file 是否正确
            if file == default_file: # 如果存在 default_file.tex 文件
                project_name = file # 使用 default_file.tex 文件作为待编译主文件名
                print(_("通过默认文件名 \"%(args)s.tex\" 指定待编译主文件为: ") % {"args": default_file} + f"[bold cyan]{project_name}.tex")
                return project_name
        if not project_name: # 如果不存在 main.tex 文件
            logger.info(_("当前根目录下不存在名为 \"%(args)s.tex\" 的文件") % {"args": default_file})

    if not project_name: # 如果当前根目录下不存在主文件且 -d 参数未指定
        logger.error(_("无法进行编译, 当前根目录下存在多个主文件: ") + ", ".join(main_file_in_root))
        logger.warning(_("请修改待编译主文件名为默认文件名 \"%(args)s.tex\" 或在文件中加入魔法注释 \"% !TEX root = [待编译主文件名]\" 或在终端输入 \"pytexmk [待编译主文件名]\" 进行编译, 或删除当前根目录下多余的 tex 文件") % {"args": default_file})
        logger.warning(_("当前根目录是: ") + str(current_path))
        exit_pytexmk()
    
    return project_name