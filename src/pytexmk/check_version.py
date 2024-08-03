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
LastEditTime : 2024-08-03 12:10:19 +0800
Github       : https://github.com/YanMing-lxb/
FilePath     : /PyTeXMK/src/pytexmk/check_version.py
Description  : 
 -----------------------------------------------------------------------
'''
import re
import time
import toml
import logging
import urllib.request
from rich import print
from pathlib import Path
import importlib.metadata
import importlib.resources
from packaging import version


class UpdateChecker():

    def __init__(self, time_out, cache_time):
        self.logger = logging.getLogger(__name__)  # 创建日志对象

        data_path = Path(importlib.resources.files('pytexmk')) / 'data'  # 获取 pytexmk 安装路径并拼接 data 子路径
        data_path.mkdir(exist_ok=True)  # 创建 data 目录，如果已存在则不报错
        self.cache_file = data_path / "pytexmk_version_cache.toml"  # 创建缓存文件路径

        self.cache_time = cache_time * 3600 # 缓存有效期，6小时
        self.time_out = time_out

        self.versions = []

    def _load_cached_version(self):
        try:
            cache_path = Path(self.cache_file)
            if cache_path.exists() and (time.time() - cache_path.stat().st_mtime < self.cache_time):
                with cache_path.open('r') as f:
                    data = toml.load(f)
                    self.logger.info(f'读取 PyTeXMK 版本缓存文件中的版本号')
                    self.logger.info(f'PyTeXMK 版本缓存文件路径: {self.cache_file}')
                    return data.get("latest_version")
        except Exception as e:
            self.logger.error(f"加载缓存版本时出错: {e}")
        return None

    def _update_pytexmk_version_cache(self, latest_version):
        try:
            with open(self.cache_file, 'w') as f:
                toml.dump({"latest_version": latest_version}, f)
        except Exception as e:
            self.logger.error(f"更新版本缓存时出错: {e}")

    def _get_latest_version(self, package_name):
        start_time = time.time()
        mirror_url = "https://mirrors.aliyun.com/pypi/simple/"
        url = f"{mirror_url}{package_name}"

        try:
            response = urllib.request.urlopen(url)
            html_content = response.read().decode('utf-8')
            pattern = re.compile(r'<a\s+href="[^"]+/pytexmk-([\d\.]+)-py3-none-any\.whl[^"]*"\s+data-requires-python="[^"]+">.*?</a>', re.DOTALL)
            matches = pattern.findall(html_content)

            for version in matches:
                self.versions.append(version)

            if self.versions:
                latest_version = max(self.versions)
                self.logger.info(f"获取 {package_name} 最新版本号成功: [bold green]{latest_version}[/bold green]")
                return latest_version
            else:
                self.logger.error(f"获取 {package_name} 最新版本号失败: 未找到版本号")
                return None

        except Exception as e:
            self.logger.error(f"获取 {package_name} 最新版本号出错: {e}")
            return None
        finally:
            end_time = time.time()
            elapsed_time = round(end_time - start_time, 4)
            self.logger.info(f"获取最新版本号耗时: {elapsed_time} 秒")


    def check_for_updates(self):
        latest_version = self._load_cached_version()
        if not latest_version:
            latest_version = self._get_latest_version("pytexmk")
            if latest_version:
                self._update_pytexmk_version_cache(latest_version)
            else:
                return

        current_version = importlib.metadata.version("pytexmk")

        if version.parse(current_version) < version.parse(latest_version):
            print(f"有新版本可用: [bold green]{latest_version}[/bold green] 当前版本: [bold red]{current_version}[/bold red]")
            print("请运行 [bold green]'pip install --upgrade pytexmk'[/bold green] 进行更新")
        else:
            print(f"当前版本: [bold green]{current_version}[/bold green]")