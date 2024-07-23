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
Date         : 2024-07-23 20:20:00 +0800
LastEditTime : 2024-07-23 22:43:57 +0800
Github       : https://github.com/YanMing-lxb/
FilePath     : \PyTeXMKd:\Application\miniconda3\envs\yanming\Lib\site-packages\pytexmk\logger_config.py
Description  : 
 -----------------------------------------------------------------------
'''

import logging
import logging.config
from rich.logging import RichHandler  # 导入rich库的日志处理模块


# --------------------------------------------------------------------------------
# 定义日志记录器
# --------------------------------------------------------------------------------
def setup_logger(verbose): # TODO 全局都采用日志记录器，并丰富日志信息
    '''设置日志记录器。'''
    FORMAT = "%(message)s"
    
    # 如果设置了verbose 选项，则将日志级别设置为INFO，以便输出更多信息
    if verbose:
        print("启用 PyTeXMK 详细日志输出...")
        logging.basicConfig(
            level="INFO",
            format=FORMAT,
            datefmt="[%X]",
            handlers=[RichHandler(show_level=True, show_time=False, markup=True, show_path=False)]
        )
    else:
        logging.basicConfig(
            level="WARNING",
            format=FORMAT,
            datefmt="[%X]",
            handlers=[RichHandler(show_level=True, show_time=False, markup=True, show_path=False)]
        )

    # 获取名为'pytexmk.py'的日志记录器实例
    logger = logging.getLogger('pytexmk.py')

    return logger

