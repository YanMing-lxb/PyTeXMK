import toml
import logging
from pathlib import Path

from .language_module import set_language

_ = set_language('config')

# 默认配置文件
default_system_config = """
default_files = "main" # 主文件名
compiled_program = "XeLaTeX" # 编译器
quiet_mode = true # 静默模式

[pdf]
pdf_preview = true # PDF预览，指编译结束后是否打开PDF文件
pdf_viewer = "default" # PDF查看器

[folder]
aux_folder = "Auxiliary" # 辅助文件夹
output_folder = "Build" # 输出文件夹

# 索引配置
[index]
ist_file_name = "nomencl.ist"  # 如果是文件名则输入文件名，否则输入文件后缀
input_suffix = ".nlo"  # 输入文件后缀
output_suffix = ".nls"  # 输出文件后缀

# LaTeX差异配置
[latexdiff]
old_tex_file = "old.tex"  # 旧TeX文件
new_tex_file = "new.tex"  # 新TeX文件
diff_tex_file = "diff.tex"  # 差异TeX文件
"""
        
default_local_config = """
default_files = "main" # 主文件名
compiled_program = "XeLaTeX" # 编译器
quiet_mode = true # 静默模式

[pdf]
pdf_preview = true # PDF预览，指编译结束后是否打开PDF文件
pdf_viewer = "default" # PDF查看器

[folder]
aux_folder = "Auxiliary" # 辅助文件夹
output_folder = "Build" # 输出文件夹

# 索引配置
[index]
ist_file_name = "nomencl.ist"  # 如果是文件名则输入文件名，否则输入文件后缀
input_suffix = ".nlo"  # 输入文件后缀
output_suffix = ".nls"  # 输出文件后缀

# LaTeX差异配置
[latexdiff]
old_tex_file = "old.tex"  # 旧TeX文件
new_tex_file = "new.tex"  # 新TeX文件
diff_tex_file = "diff.tex"  # 差异TeX文件
"""

class ConfigParser:
    """
    用于解析配置文件的类
    """
    def __init__(self):
        self.logger = logging.getLogger(__name__)  # 加载日志记录器
        self.system_config_path = self._get_system_config_path()  # 获取系统配置文件路径
        self.local_config_path = Path.cwd() / '.pytexmkrc'  # 获取本地配置文件路径
        self.logger.info(_("PyTeXMK 配置模块初始化完成"))

    def _get_system_config_path(self):
        """
        获取系统配置文件路径
        """
        try:
            home_path = Path.home()  # 获取用户主目录
            self.logger.info(_("用户主目录: ") + str(home_path))
            return home_path / '.pytexmkrc'
        except Exception as e:
            self.logger.error(_("获取用户主目录失败: ") + str(e))
            return None


    def load_config(self):
        """
        加载配置文件并返回解析后的配置字典
        """
        system_config = self._load_toml(self.system_config_path)  # 加载系统配置文件
        local_config = self._load_toml(self.local_config_path)  # 加载本地配置文件

        # 优先使用本地配置，如果本地配置不存在则使用系统配置
        final_config = system_config.copy() if system_config else {}
        if local_config:
            final_config.update(local_config)
        else:
            self.logger.info(_("未找到本地配置文件，使用系统配置"))

        self.logger.info(_("配置文件加载完成"))
        return final_config


    def _load_toml(self, path):
        """
        加载指定路径的toml文件并返回解析后的字典
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


    def generate_default_config_file(self, path, config):
        """
        确保指定路径的配置文件存在，如果不存在则创建默认配置文件
        将默认配置写入toml文件，并包含注释
        """
        if not path.exists():
            try:
                self.logger.info(_("创建默认配置文件: ") + str(path))
                path.parent.mkdir(parents=True, exist_ok=True)  # 创建父目录
                with open(path, 'w', encoding='utf-8') as f:
                    f.write(config)
            except Exception as e:
                self.logger.error(_("创建默认配置文件失败: ") + f"{path} --> {e}")
