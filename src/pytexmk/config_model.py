import toml
import os
import logging
from pathlib import Path

class ConfigParser:
    """
    用于解析配置文件的类
    """
    def __init__(self):
        self.logger = logging.getLogger(__name__)  # 加载日志记录器
        self.system_config_path = self._get_system_config_path()  # 获取系统配置文件路径
        self.local_config_path = Path.cwd() / 'config.toml'  # 获取本地配置文件路径
        self.default_config = {
            "main_file_name": "main",
            "compiler": "pdflatex",
            "quiet_mode": False,
            "index": {
                "ist_file_name": "index",
                "input_suffix": ".tex",
                "output_suffix": ".idx"
            },
            "pdf_preview": True,
            "pdf_viewer": "default",
            "aux_folder": "aux",
            "output_folder": "output",
            "latexdiff": {
                "old_tex_file": "old.tex",
                "new_tex_file": "new.tex",
                "diff_tex_file": "diff.tex"
            }
        }

    def _get_system_config_path(self):
        """
        根据操作系统获取系统配置文件路径
        """
        if os.name == 'nt':  # Windows系统
            return Path(os.getenv('APPDATA')) / 'PyTeXM' / 'config.toml'
        else:  # Linux或macOS系统
            return Path.home() / '.config' / 'PyTeXM' / 'config.toml'

    def load_config(self):
        """
        加载配置文件并返回解析后的配置字典
        """
        system_config = self._load_toml(self.system_config_path)  # 加载系统配置文件
        local_config = self._load_toml(self.local_config_path)  # 加载本地配置文件

        # 优先使用本地配置，如果本地配置不存在则使用系统配置
        final_config = {**system_config, **local_config}
        self.logger.info("配置文件加载完成")
        return final_config

    def _load_toml(self, path):
        """
        加载指定路径的toml文件并返回解析后的字典
        """
        if path.exists():
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    config = toml.load(f)
                self.logger.info(f"{path} 加载成功")
                return config
            except Exception as e:
                self.logger.error(f"加载 {path} 失败: {e}")
                return {}
        else:
            self.logger.warning(f"{path} 不存在")
            return {}

    def ensure_config_files(self):
        """
        确保系统配置文件和本地配置文件存在，如果不存在则创建默认配置文件
        """
        self._ensure_config_file(self.system_config_path)
        self._ensure_config_file(self.local_config_path)

    def _ensure_config_file(self, path):
        """
        确保指定路径的配置文件存在，如果不存在则创建默认配置文件
        """
        if not path.exists():
            path.parent.mkdir(parents=True, exist_ok=True)  # 创建父目录
            with open(path, 'w', encoding='utf-8') as f:
                toml.dump(self.default_config, f)
            self.logger.info(f"创建默认配置文件: {path}")

    def get_config(self):
        """
        获取解析后的配置字典
        """
        self.ensure_config_files()  # 确保配置文件存在
        return self.load_config()  # 加载并返回配置字典