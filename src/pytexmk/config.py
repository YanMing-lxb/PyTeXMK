import toml
import logging
from pathlib import Path
from collections import defaultdict

from pytexmk.language import set_language

_ = set_language('config')
# TODO : 创建三套配置文件模板，分别为用户配置、本地配置、默认配置
# 用户配置：一般为系统管理员配置，存放位置为：用户主目录下。
# 本地配置：一般为项目专用配置，存放位置为：当前工作目录下。
# 默认配置：将 __main__.py 中的默认配置移至此处，方便用户修改, 存放位置为：pytexmk目录下。
# 默认配置文件
default_system_config = """
default_file = "main" # 主文件名
compiled_program = "XeLaTeX" # 编译器
non_quiet = false # 非静默模式
local_config_auto_init = true # 是否自动创建本地配置文件

[pdf]
pdf_preview_status = true # PDF预览, 指编译结束后是否打开PDF文件
pdf_viewer = "default" # PDF查看器: default为默认PDF查看器

[folder]
auxdir = "./Auxiliary/" # 辅助文件夹
outdir = "./Build/" # 输出文件夹

# 索引配置
[index]
index_style_file = "nomencl.ist"  # 输入样式文件：如果是文件名则输入文件名, 否则输入文件后缀 (例如：glossaries 宏包需要输入 .ist; nomencl 宏包则需要输入nomencl.ist)
input_suffix = ".nlo"  # 输入文件后缀
output_suffix = ".nls"  # 输出文件后缀
# glossaries 宏包和 nomencl 宏包无需配置 [index]

# LaTeX差异配置
[latexdiff]
old_tex_file = "old_file"  # 旧TeX文件
new_tex_file = "new_file"  # 新TeX文件
diff_tex_file = "LaTeXDiff"  # 差异TeX文件
"""
        
default_local_config = """
default_file = "main" # 主文件名
compiled_program = "XeLaTeX" # 编译器
quiet_mode = true # 静默模式

[pdf]
pdf_preview_status = false # PDF预览, 指编译结束后是否打开PDF文件
pdf_viewer = "default" # PDF查看器: default为默认PDF查看器

[folder]
auxdir = "./Auxiliary/" # 辅助文件夹
outdir = "./Build/" # 输出文件夹

# 索引配置
[index]
index_style_file = "nomencl.ist"  # 输入样式文件：如果是文件名则输入文件名, 否则输入文件后缀 (例如：glossaries 宏包需要输入 .ist; nomencl 宏包则需要输入nomencl.ist)
input_suffix = ".nlo"  # 输入文件后缀
output_suffix = ".nls"  # 输出文件后缀
# glossaries 宏包和 nomencl 宏包无需配置 [index]

# LaTeX差异配置
[latexdiff]
old_tex_file = "old_file"  # 旧TeX文件
new_tex_file = "new_file"  # 新TeX文件
diff_tex_file = "LaTeXDiff"  # 差异TeX文件
"""

class ConfigParser:
    """
    配置解析器类, 用于处理系统配置和本地配置文件的加载和生成。
    """
    def __init__(self):
        """
        初始化配置解析器, 设置日志记录器, 获取系统配置文件路径和本地配置文件路径。
        """
        self.logger = logging.getLogger(__name__)  # 加载日志记录器
        self.system_config_path = self._get_system_config_path()  # 获取系统配置文件路径
        self.local_config_path = Path.cwd() / '.pytexmkrc'  # 获取本地配置文件路径
        self.logger.info(_("PyTeXMK 配置模块初始化完成"))

    def _get_system_config_path(self):
        """
        获取系统配置文件路径。
        返回:
            Path: 系统配置文件路径。
        """
        try:
            home_path = Path.home()  # 获取用户主目录
            self.logger.info(_("用户主目录: ") + str(home_path))
            return home_path / '.pytexmkrc'
        except Exception as e:
            self.logger.error(_("获取用户主目录失败: ") + str(e))
            return None

    def _load_toml(self, path):
        """
        加载指定路径的 TOML 配置文件。
        参数:
            path (Path): 配置文件路径。
        返回:
            dict: 配置字典。
        """
        if not path.exists():
            self.logger.warning(_("配置文件不存在: ") + str(path))
            return None

        try:
            with open(path, 'r', encoding='utf-8') as f:
                config = toml.load(f)
            self.logger.info(_("配置文件加载成功: ") + str(path))
            return config
        except Exception as e:
            self.logger.error(_("配置文件加载失败: ") + f"{path} --> {e}")
            return None

    def init_default_config(self, path, config):
        """
        生成默认配置文件。
        参数:
            path (Path): 配置文件路径。
            config (str): 配置内容。
        """
        if not path.exists():
            try:
                self.logger.info(_("创建默认配置文件: ") + str(path))
                path.parent.mkdir(parents=True, exist_ok=True)  # 创建父目录
                with open(path, 'w', encoding='utf-8') as f:
                    f.write(config)
            except Exception as e:
                self.logger.error(_("创建默认配置文件失败: ") + f"{path} --> {e}")
    
    def init_config_file(self):
        """
        初始化配置文件。
        加载系统配置和本地配置文件, 优先使用本地配置。
        返回:
            dict: 最终的配置字典。
        """
        self.init_default_config(self.system_config_path, default_system_config)
        system_config = defaultdict(lambda: None, self._load_toml(self.system_config_path))  # 加载系统配置文件
        if system_config["local_config_auto_init"]:
            self.init_default_config(self.local_config_path, default_local_config)
            local_config = self._load_toml(self.local_config_path)  # 加载本地配置文件
        
        final_config = system_config if system_config else {}

        if local_config:
            final_config.update(local_config)
        else:
            self.logger.info(_("未找到本地配置文件, 使用系统配置"))

        self.logger.info(_("配置文件加载完成"))

        # 转换为 defaultdict 来避免KeyError，默认值为None
        final_config = defaultdict(lambda: None, final_config)

        # TODO: 校验配置项中default_file是否正确
        # default_file = self.check_project_name(main_files_in_root, default_file, '.tex') # 检查 default_file 是否正确，主要是检查配置文件中的默认文件名是否正确


        return final_config