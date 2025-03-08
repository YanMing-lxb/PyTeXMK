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
LastEditTime : 2025-01-29 22:00:42 +0800
Github       : https://github.com/YanMing-lxb/
FilePath     : /PyTeXMK/src/pytexmk/check_version_module.py
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
from datetime import timedelta

from pytexmk.language import set_language

_ = set_language('check_version')


class UpdateChecker():

    def __init__(self, time_out, cache_time):
        """
        初始化 CheckVersion 类的实例。

        参数:
        time_out (int): 超时时间，单位为秒。
        cache_time (int): 缓存时间，单位为小时。

        行为逻辑:
        1. 创建日志对象。
        2. 初始化版本列表。
        3. 将缓存时间转换为秒并存储。
        4. 存储超时时间。
        5. 获取 pytexmk 安装路径并拼接 data 子路径，创建 data 目录（如果已存在则不报错）。
        6. 创建缓存文件路径。
        """
        self.logger = logging.getLogger(__name__)  # 创建日志对象

        self.versions = []  # 初始化版本列表

        self.cache_time = cache_time * 3600  # 将缓存时间转换为秒并存储
        self.time_out = time_out  # 存储超时时间

        data_path = Path(importlib.resources.files('pytexmk')) / 'data'  # 获取 pytexmk 安装路径并拼接 data 子路径
        self.cache_file = data_path / "pytexmk_version_cache.toml"  # 创建缓存文件路径

    # --------------------------------------------------------------------------------
    # 定义 缓存文件读取函数
    # --------------------------------------------------------------------------------
    def _load_cached_version(self):
        """
        从缓存文件中加载最新版本号.

        行为逻辑说明:
        - 尝试读取缓存文件路径.
        - 检查缓存文件是否存在且未过期(根据缓存时间判断).
        - 如果缓存文件有效,读取文件内容并返回最新版本号.
        - 如果发生任何异常,记录错误信息并返回 None.

        返回说明:
        - 返回缓存文件中的最新版本号,如果加载失败或缓存文件无效,则返回 None.
        """
        try:
            cache_path = Path(self.cache_file)  # 获取缓存文件路径
            if not cache_path.exists():
                return None  # 如果缓存文件不存在,返回 None

            # 使用timedelta来转换秒数
            cache_time_remaining = round(self.cache_time - (time.time() - cache_path.stat().st_mtime), 4)  # 计算缓存剩余时间
            delta = timedelta(seconds=cache_time_remaining)
            # 计算小时、分钟和秒
            total_seconds = delta.total_seconds()  # 将timedelta转换为总秒数
            hours, remainder = divmod(int(total_seconds), 3600)  # 计算小时数
            minutes, seconds = divmod(remainder, 60)  # 计算分钟数和秒数

            if cache_path.exists() and (cache_time_remaining > 0):  # 检查缓存文件是否存在且未过期
                with cache_path.open('r') as f:  # 打开缓存文件
                    data = toml.load(f)  # 加载缓存文件内容
                    self.logger.info(_("读取 PyTeXMK 版本缓存文件中的版本号，缓存有效期: ") + f'{int(hours):02} h {int(minutes):02} min {int(seconds):02} s')  # 记录日志信息
                    self.logger.info(_("PyTeXMK 版本缓存文件路径: ") + str(self.cache_file))  # 记录日志信息
                    return data.get("latest_version")  # 返回最新版本号
        except Exception as e:
            self.logger.error(_("加载缓存版本时出错: ") + str(e))  # 记录错误信息
        return None  # 如果加载失败或缓存文件无效,返回 None

    # --------------------------------------------------------------------------------
    # 定义 缓存文件写入函数
    # --------------------------------------------------------------------------------
    def _update_pytexmk_version_cache(self, latest_version):
        """
        更新PyTeXMK版本缓存文件.

        参数:
        latest_version (str): 最新的PyTeXMK版本号.

        行为逻辑:
        尝试打开缓存文件并以写模式写入最新的版本号.如果操作失败,记录错误日志.
        """
        try:
            # 尝试以写模式打开缓存文件
            with open(self.cache_file, 'w') as f:
                # 使用toml库将最新的版本号写入文件
                toml.dump({"latest_version": latest_version}, f)
        except Exception as e:
            # 如果更新缓存时出错,记录错误日志
            self.logger.error(_("更新版本缓存时出错: ") + str(e))

    # --------------------------------------------------------------------------------
    # 定义 网络获取版本信息函数
    # --------------------------------------------------------------------------------
    def _get_latest_version(self, package_name): # TODO 将该函数放到线程中执行,获取线程信息,保存,并且在下次运行时检查这个显示是否已经执行结束,如果结束则不再执行,否则执行
        """
        获取指定包的最新版本号.

        参数:
        package_name (str): 包的名称.

        返回:
        str: 最新版本号,如果获取失败则返回 None.

        行为逻辑:
        1. 记录开始时间.
        2. 构建包的镜像URL.
        3. 尝试打开URL并读取HTML内容.
        4. 使用正则表达式匹配HTML内容中的版本号.
        5. 将匹配到的版本号添加到版本列表中.
        6. 如果版本列表不为空,返回最大版本号;否则记录错误并返回 None.
        7. 捕获所有异常并记录错误信息,返回 None.
        8. 记录获取版本号的耗时.
        """
        start_time = time.time()  # 记录开始时间
        mirror_url = "https://mirrors.aliyun.com/pypi/simple/"  # 设置镜像URL #TODO 添加多个镜像源,进行循环尝试
        url = f"{mirror_url}{package_name}"  # 构建包的URL

        try:
            response = urllib.request.urlopen(url)  # 尝试打开URL
            html_content = response.read().decode('utf-8')  # 读取并解码HTML内容
            pattern = re.compile(r'<a\s+href="[^"]+/pytexmk-([\d\.]+)-py3-none-any\.whl[^"]*"\s+data-requires-python="[^"]+">.*?</a>', re.DOTALL)  # 定义正则表达式模式
            matches = pattern.findall(html_content)  # 使用正则表达式匹配版本号

            for ver in matches:  # 遍历匹配到的版本号
                self.versions.append(ver)  # 将版本号添加到版本列表中
            
            if self.versions:  # 如果版本列表不为空
                # 使用列表推导式和parse函数将字符串转换为版本对象
                version_objects = [version.parse(ver) for ver in self.versions]

                # 使用max函数和key参数找到最新版本
                latest_version = max(version_objects)

                self.logger.info(_("获取 %(args)s 最新版本号成功: ") % {"args": package_name} + f"[bold green]{latest_version}[/bold green]")  # 记录成功信息
                return latest_version  # 返回最新版本号
            else:
                self.logger.error(_("获取 %(args)s 最新版本号失败: 未找到版本号") % {"args": package_name})  # 记录错误信息
                return None  # 返回 None

        except Exception as e:  # 捕获所有异常
            self.logger.error(_("获取 %(args)s 最新版本号出错: ") % {"args": package_name} + str(e))  # 记录错误信息
            return None  # 返回 None
        finally:
            end_time = time.time()  # 记录结束时间
            elapsed_time = round(end_time - start_time, 4)  # 计算耗时
            self.logger.info(_("获取最新版本号耗时: ") + f"{elapsed_time} s")  # 记录耗时信息

    # --------------------------------------------------------------------------------
    # 定义 更新检查主函数
    # --------------------------------------------------------------------------------
    def check_for_updates(self):
        """
        检查是否有新版本可用,并提示用户更新.

        行为逻辑说明:
        1. 从缓存中加载最新版本信息.
        2. 如果缓存中没有最新版本信息,则从远程获取最新版本信息并更新缓存.
        3. 获取当前安装的版本信息.
        4. 比较当前版本和最新版本,如果当前版本较旧,则提示用户更新.
        5. 如果当前版本是最新的,则提示当前版本信息.
        """
        latest_version = self._load_cached_version()  # 从缓存中加载最新版本信息
        
        if latest_version:
            latest_version = version.parse(latest_version)  # 将字符串转换为版本对象
        else:
            latest_version = self._get_latest_version("pytexmk")
            if latest_version:
                self._update_pytexmk_version_cache(str(latest_version))
            else:
                return

        # 获取当前安装的版本信息
        current_version = version.parse(importlib.metadata.version("pytexmk"))

        if current_version < latest_version:
            print(_("有新版本可用: ") + f"[bold green]{latest_version}[/bold green] " + _("当前版本: ") + f"[bold red]{current_version}[/bold red]")
            print(_("请运行 [bold green]'pip install --upgrade pytexmk'[/bold green] 进行更新"))
        else:
            print(_("当前版本: ") + f"[bold green]{current_version}[/bold green]")