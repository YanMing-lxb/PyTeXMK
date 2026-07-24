import toml
import logging
from pathlib import Path
from collections import defaultdict
from typing import Optional, Dict, Any

from pytexmk.language import set_language
from pytexmk.auxiliary_fun import get_app_path

_ = set_language('config')

class ConfigParser:
    """
    配置解析器类, 用于处理用户配置和项目配置文件的加载和生成。
    """

    def __init__(self):
        """
        初始化配置解析器, 设置日志记录器, 获取用户配置文件和项目配置文件路径。
        """
        self.logger = logging.getLogger(__name__)  # 初始化日志记录器
        self.user_config_path = self._get_user_config_path()  # 获取用户配置文件路径
        self.project_config_path = Path.cwd() / '.pytexmkrc'  # 获取项目配置文件路径
        self.data_dir = get_app_path() / 'data'  # 获取data文件夹路径
        self.logger.info(_("PyTeXMK 配置模块已初始化"))

    def _get_user_config_path(self) -> Optional[Path]:
        """获取用户配置文件路径。

        Returns
        -------
        Optional[Path]
            用户配置文件路径，如果获取失败则返回 None。
        """
        try:
            user_home_path = Path.home()  # 获取用户主目录
            self.logger.info(_("用户主目录路径: ") + str(user_home_path))
            return user_home_path / '.pytexmkrc'
        except Exception as e:
            self.logger.error(_("获取用户主目录路径失败: ") + str(e))
            return None

    def _load_toml(self, path: Path) -> Optional[Dict[str, Any]]:
        """加载指定路径的 TOML 配置文件。

        Parameters
        ----------
        path : Path
            配置文件路径。

        Returns
        -------
        Optional[Dict[str, Any]]
            配置字典。
        """
        if not path.exists():
            self.logger.warning(_("配置文件不存在: ") + str(path))
            return None

        try:
            with open(path, 'r', encoding='utf-8') as f:
                config = toml.load(f)
            self.logger.info(_("成功加载配置文件: ") + str(path))
            return config
        except Exception as e:
            self.logger.error(_("加载配置文件失败: ") + f"{path} --> {e}")
            return None

    def _init_default_config(self, path: Path, config_file: str):
        """生成默认配置文件。

        Parameters
        ----------
        path : Path
            配置文件路径。
        config_file : str
            默认配置文件名。
        """
        if not path.exists():
            try:
                self.logger.info(_("正在创建默认配置文件: ") + str(path))
                path.parent.mkdir(parents=True, exist_ok=True)  # 创建父目录
                with open(self.data_dir / config_file, 'r', encoding='utf-8') as f:
                    default_config = f.read()
                with open(path, 'w', encoding='utf-8') as f:
                    f.write(default_config)
            except Exception as e:
                self.logger.error(_("创建默认配置文件失败: ") + f"{path} --> {e}")
        else:
            self._check_and_correct_config(path, config_file)

    def _check_and_correct_config(self, path: Path, config_file: str):
        """检查并修正配置文件。

        Parameters
        ----------
        path : Path
            配置文件路径。
        config_file : str
            默认配置文件名。
        """
        try:
            with open(path, 'r', encoding='utf-8') as f:
                existing_config = toml.load(f)
        except Exception as e:
            self.logger.error(_("加载配置文件失败: ") + f"{path} --> {e}")
            return

        # 加载默认配置文件
        with open(self.data_dir / config_file, 'r', encoding='utf-8') as f:
            default_config_dict = toml.load(f)

        # 获取所有key的集合
        existing_keys = set(existing_config.keys())
        default_keys = set(default_config_dict.keys())

        # 找出多余和缺少的key
        extra_keys = existing_keys - default_keys
        missing_keys = default_keys - existing_keys

        if extra_keys or missing_keys:
            self.logger.warning(_("配置文件存在以下问题:"))
            if extra_keys:
                self.logger.warning(_("多余配置项: "))
                for key in extra_keys:
                    self.logger.warning(f"  {key}: {existing_config[key]}")
            if missing_keys:
                self.logger.warning(_("缺少配置项: "))
                for key in missing_keys:
                    self.logger.warning(f"  {key}: {default_config_dict[key]}")

            choice = input(_("是否要补全缺少的配置项并删除多余的配置项？(yes/no 或 y/n): ")).strip().lower()
            if choice in ['yes', 'y']:
                # 补全缺少的key
                for key in missing_keys:
                    existing_config[key] = default_config_dict[key]
                    self.logger.info(_("已补全配置项: ") + f"{key}: {default_config_dict[key]}")

                # 删除多余的key
                for key in extra_keys:
                    value = existing_config[key]
                    del existing_config[key]
                    self.logger.info(_("已删除配置项: ") + f"{key}: {value}")

                # 写回配置文件，保持默认配置的顺序
                ordered_config = {k: existing_config[k] for k in default_config_dict}
                try:
                    with open(path, 'w', encoding='utf-8') as f:
                        toml.dump(ordered_config, f)
                    self.logger.info(_("配置文件更新成功: ") + str(path))
                except Exception as e:
                    self.logger.error(_("配置文件更新失败: ") + f"{path} --> {e}")
            elif choice in ['no', 'n']:
                self.logger.info(_("请稍后手动修改配置文件"))
            else:
                self.logger.error(_("无效输入，请输入如下选项: yes/no 或 y/n"))

    def init_config_file(self) -> Dict[str, Any]:
        """初始化配置文件。
        加载用户配置和项目配置文件, 优先使用项目配置。

        Returns
        -------
        Dict[str, Any]
            最终的配置字典。
        """
        self._init_default_config(self.user_config_path, 'default_user_config.toml')
        user_config = defaultdict(lambda: None, self._load_toml(self.user_config_path))  # 加载用户配置文件
        project_config = None  # 初始化 project_config
        if user_config["project_config_auto_init"]:
            self._init_default_config(self.project_config_path, 'default_project_config.toml')
            project_config = self._load_toml(self.project_config_path)  # 加载项目配置文件

        final_config = user_config if user_config else {}

        if project_config:
            final_config.update(project_config)
        else:
            self.logger.info(_("未找到项目配置文件, 使用用户配置"))

        self.logger.info(_("配置文件加载完成"))

        # 转换为 defaultdict 来避免KeyError，默认值为None
        final_config = defaultdict(lambda: None, final_config)

        return final_config