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
LastEditTime : 2025-04-30 20:02:15 +0800
Github       : https://github.com/YanMing-lxb/
FilePath     : /PyTeXMK/src/pytexmk/check_version.py
Description  : 
 -----------------------------------------------------------------------
'''
import time
import toml
import json
import logging
import urllib.request
from rich import print
from pathlib import Path
from packaging import version
from datetime import timedelta
from platformdirs import user_cache_dir

from pytexmk.language import set_language
from pytexmk.version import script_name, __version__

_ = set_language('check_version')

API_URL = f"https://api.github.com/repos/YanMing-lxb/{script_name}/releases/latest"

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
        5. 获取安装路径并拼接 data 子路径，创建 data 目录（如果已存在则不报错）。
        6. 创建缓存文件路径。
        """
        self.logger = logging.getLogger(__name__)  # 创建日志对象

        self.versions = []  # 初始化版本列表

        self.cache_time = cache_time * 3600  # 将缓存时间转换为秒并存储
        self.time_out = time_out  # 存储超时时间

        cache_path = Path(user_cache_dir(script_name, ensure_exists=True))
        self.cache_file = cache_path / f"{script_name}_version_cache.toml"

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
                    self.logger.info(_(f"读取版本缓存文件中的版本号，缓存有效期: ") + f'{int(hours):02} h {int(minutes):02} min {int(seconds):02} s')  # 记录日志信息
                    self.logger.info(_("版本缓存文件路径: ") + str(self.cache_file))  # 记录日志信息
                    return data.get("latest_version")  # 返回最新版本号
        except Exception as e:
            self.logger.error(_("加载缓存版本时出错: ") + str(e))  # 记录错误信息
        return None  # 如果加载失败或缓存文件无效,返回 None

    # --------------------------------------------------------------------------------
    # 定义 缓存文件写入函数
    # --------------------------------------------------------------------------------
    def _update_version_cache(self, latest_version):
        """
        更新版本缓存文件.

        参数:
        latest_version (str): 最新的版本号.

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
    def _get_latest_version(self):  # TODO 将该函数放到线程中执行,获取线程信息,保存,并且在下次运行时检查这个显示是否已经执行结束,如果结束则不再执行,否则执行

        start_time = time.time()
        
        try:
            headers = {
                'User-Agent': f'{script_name} Update Checker',  # GitHub要求明确User-Agent
                'Accept': 'application/vnd.github.v3+json'
            }
            req = urllib.request.Request(API_URL, headers=headers)
            
            with urllib.request.urlopen(req, timeout=self.time_out) as response:
                # 添加编码处理
                data = json.loads(response.read().decode('utf-8'))
                
                # 增加版本号格式校验
                if 'tag_name' not in data:
                    raise ValueError("Invalid GitHub API response")
                    
                latest_version = data['tag_name'].lstrip('v')  # 去除可能存在的v前缀
                parsed_version = version.parse(latest_version)
                
                self.logger.info(_("通过 GitHub API 获取最新版本成功"))
                return parsed_version
                
        except urllib.error.HTTPError as e:
            # 处理API速率限制
            if e.code == 403 and 'X-RateLimit-Remaining' in e.headers:
                reset_time = time.strftime("%Y-%m-%d %H:%M:%S", 
                    time.localtime(int(e.headers['X-RateLimit-Reset'])))
                self.logger.error(_("API速率限制，重置时间：%s") % reset_time)
            else:
                self.logger.error(_("请求失败，状态码：%d") % e.code)
        except json.JSONDecodeError:
            self.logger.error(_("响应数据解析失败"))
        except KeyError:
            self.logger.error(_("响应中缺少版本信息"))
        except Exception as e:
            self.logger.error(_("获取GitHub版本失败：") + str(e))
        finally:
            self.logger.info(_("请求耗时：%.2f秒") % (time.time()-start_time))
        
        return None   

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
            latest_version = self._get_latest_version()
            if latest_version:
                self._update_version_cache(str(latest_version))
            else:
                return

        # 获取当前安装的版本信息
        current_version = version.parse(__version__)

        if current_version < latest_version:
            print(_("有新版本可用: ") + f"[bold green]{latest_version}[/bold green] " + _("当前版本: ") + f"[bold red]{current_version}[/bold red]")
            print(_("请运行 [bold green]'pip install --upgrade %(args)s'[/bold green] 进行更新") % {'args': script_name})
        else:
            print(_("当前版本: ") + f"[bold green]{current_version}[/bold green]")
