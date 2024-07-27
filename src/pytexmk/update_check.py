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
Date         : 2024-07-26 20:22:15 +0800
LastEditTime : 2024-07-27 15:35:29 +0800
Github       : https://github.com/YanMing-lxb/
FilePath     : /PyTeXMK/src/pytexmk/update_check.py
Description  : 
 -----------------------------------------------------------------------
'''

import json
import urllib.request
import importlib.metadata
from rich import print
import logging

logger = logging.getLogger(__name__)  # 创建日志对象

# --------------------------------------------------------------------------------
# 定义版本更新检查函数
# --------------------------------------------------------------------------------
def check_for_updates():
    """
    检查当前安装的 pytexmk 版本是否为最新版本。如果不是，提示用户更新。
    """
    try:
        # 获取当前安装的 pytexmk 版本
        current_version = importlib.metadata.version("pytexmk")
         
        # 从 PyPI 获取最新的 pytexmk 版本信息
        url = r"https://pypi.org/pypi/pytexmk/json"
        with urllib.request.urlopen(url) as response:
            data = json.loads(response.read())
            latest_version = data['info']['version']
         
        # 比较版本
        if current_version < latest_version:
            print(f"有新版本可用: [bold green]{latest_version}[/bold green]。当前版本: [bold red]{current_version}[/bold red]")
            print("请运行 'pip install --upgrade pytexmk' 进行更新")
        else:
            print(f"当前已是最新版本: [bold green]{current_version}[/bold green]")
    except Exception as e:
        logger.error(f"检查更新时发生错误: {e}")