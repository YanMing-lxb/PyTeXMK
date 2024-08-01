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
LastEditTime : 2024-07-29 21:50:18 +0800
Github       : https://github.com/YanMing-lxb/
FilePath     : /PyTeXMK/src/pytexmk/check_version.py
Description  : 
 -----------------------------------------------------------------------
'''
import time
import json
import socket
import logging
import urllib.request
from rich import print
from pathlib import Path
import importlib.metadata
import importlib.resources
from packaging import version

class UpdateChecker:
    """
    UpdateChecker 类用于检查 pytexmk 第三方库的版本更新。

    成员变量：
    - logger: 日志对象，用于记录日志信息。
    - cache_file: 缓存文件路径，存储最新版本信息。
    - cache_lifetime: 缓存有效期（秒），超出有效期将重新获取最新版本信息。
    """

    def __init__(self):
        """
        初始化 UpdateChecker 对象，设置日志，获取 pytexmk 安装路径，
        并创建缓存文件路径。
        """
        self.logger = logging.getLogger(__name__)  # 创建日志对象
 
        data_path = Path(importlib.resources.files('pytexmk')) / 'data'  # 获取 pytexmk 安装路径并拼接 data 子路径
        data_path.mkdir(exist_ok=True)  # 创建 data 目录，如果已存在则不报错
        self.cache_file = data_path / "pytexmk_version_cache.json"  # 创建缓存文件路径
 
        self.cache_lifetime = 43200  # 缓存有效期，12小时
 
    def load_cached_version(self):
        """
        从缓存文件中加载最新版本信息。
 
        返回：
        - 若缓存存在且未过期，返回缓存中的最新版本号。
        - 否则返回 None。
        """
        try:
            # 使用Path对象替代os.path
            cache_path = Path(self.cache_file)
            # 检查缓存文件是否存在且未过期
            if cache_path.exists() and (time.time() - cache_path.stat().st_mtime < self.cache_lifetime):
                # 打开缓存文件并加载数据
                with cache_path.open('r') as f:
                    data = json.load(f)
                    self.logger.info(f'PyTeXMK 版本缓存文件路径: {self.cache_file}')
                    return data.get("latest_version")
        except Exception as e:
            self.logger.error(f"加载缓存版本时出错: {e}")
        return None
 
    def update_pytexmk_version_cache(self, latest_version):
        """
        更新缓存文件中的最新版本信息。

        参数：
        - latest_version: 最新的版本号。
        """
        try:
            with open(self.cache_file, 'w') as f:
                json.dump({"latest_version": latest_version}, f)
        except Exception as e:
            self.logger.error(f"更新版本缓存时出错: {e}")
 
    def check_for_updates(self):
        """
        检查 pytexmk 版本更新：
        - 首先尝试从缓存加载最新版本信息。
        - 若缓存未命中或已过期，则从 PyPI 服务器获取最新版本信息并更新缓存。
        - 比较当前版本和最新版本，提示用户是否有新版本可更新。
        """
        latest_version = self.load_cached_version()
            
        if not latest_version:
            url = "https://pypi.org/pypi/pytexmk/json"
            try:
                with urllib.request.urlopen(url, timeout=30) as response:
                    data = json.loads(response.read())
                    latest_version = data['info']['version']
                    self.update_pytexmk_version_cache(latest_version)
            except urllib.error.URLError as e:
                self.logger.error(f"无法连接到更新服务器，请检查您的网络连接: {e}")
                return
            except socket.timeout:
                self.logger.error("连接更新服务器超时，请稍后再试")
                return
        current_version = importlib.metadata.version("pytexmk")

        if version.parse(current_version) < version.parse(latest_version):
            print(f"有新版本可用: [bold green]{latest_version}[/bold green]。当前版本: [bold red]{current_version}[/bold red]")
            print("请运行 [bold green]'pip install --upgrade pytexmk'[/bold green] 进行更新")
        else:
            print(f"当前已是最新版本: [bold green]{current_version}[/bold green]")