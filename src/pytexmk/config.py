import toml
import copy
import logging
from pathlib import Path
from typing import Optional, Dict, Any, List

from pytexmk.language import set_language
from pytexmk.auxiliary_fun import get_app_path

_ = set_language("config")


class ConfigParser(dict):
    """
    配置解析器类, 用于处理用户配置和项目配置文件的加载和生成。

    支持点号分隔的键访问，如 config.get("engine.default")，同时保持向后兼容
    的 dict 式访问（config["key"]）。
    """

    VALID_ENGINES = {"xelatex", "lualatex", "pdflatex"}
    VALID_BIB_TOOLS = {"auto", "bibtex", "biber"}
    VALID_INDEX_TOOLS = {"auto", "makeindex", "xindy"}

    def __init__(self, interactive: bool = True):
        """
        初始化配置解析器, 设置日志记录器, 获取用户配置文件和项目配置文件路径。

        Parameters
        ----------
        interactive : bool
            是否使用交互模式。非交互模式（CI/CD、脚本调用）下不会调用 input()，
            自动补全缺失配置项并删除多余项。默认为 True。
        """
        super().__init__()
        self.interactive = interactive
        self.logger = logging.getLogger(__name__)
        self.user_config_path = self._get_user_config_path()
        self.project_config_path = Path.cwd() / ".pytexmkrc"
        self.data_dir = get_app_path() / "data"
        self.logger.info(_("PyTeXMK 配置模块已初始化"))

    def __getitem__(self, key: str) -> Any:
        """重写 __getitem__，保持与原 defaultdict 行为兼容：顶级键不存在时返回 None。

        Parameters
        ----------
        key : str
            配置键。

        Returns
        -------
        Any
            配置值，键不存在时返回 None。
        """
        try:
            return super().__getitem__(key)
        except KeyError:
            return None

    def _get_user_config_path(self) -> Optional[Path]:
        """获取用户配置文件路径。

        Returns
        -------
        Optional[Path]
            用户配置文件路径，如果获取失败则返回 None。
        """
        try:
            user_home_path = Path.home()
            self.logger.info(_("用户主目录路径: ") + str(user_home_path))
            return user_home_path / ".pytexmkrc"
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
            with open(path, "r", encoding="utf-8") as f:
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
                path.parent.mkdir(parents=True, exist_ok=True)
                with open(self.data_dir / config_file, "r", encoding="utf-8") as f:
                    default_config = f.read()
                with open(path, "w", encoding="utf-8") as f:
                    f.write(default_config)
            except Exception as e:
                self.logger.error(_("创建默认配置文件失败: ") + f"{path} --> {e}")
        else:
            self._check_and_correct_config(path, config_file)

    def _deep_update(self, base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
        """递归更新嵌套字典。

        Parameters
        ----------
        base : Dict[str, Any]
            基础字典。
        override : Dict[str, Any]
            覆盖字典。

        Returns
        -------
        Dict[str, Any]
            更新后的字典。
        """
        result = copy.deepcopy(base)
        for key, value in override.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = self._deep_update(result[key], value)
            else:
                result[key] = copy.deepcopy(value)
        return result

    def _get_missing_and_extra_keys(
        self, existing: Dict[str, Any], default: Dict[str, Any], prefix: str = ""
    ) -> tuple[Dict[str, Any], Dict[str, Any]]:
        """递归查找缺失和多余的配置键。

        Parameters
        ----------
        existing : Dict[str, Any]
            现有配置。
        default : Dict[str, Any]
            默认配置。
        prefix : str
            键前缀，用于嵌套配置节。

        Returns
        -------
        tuple[Dict[str, Any], Dict[str, Any]]
            (缺失键字典, 多余键字典)
        """
        missing = {}
        extra = {}

        for key, default_value in default.items():
            full_key = f"{prefix}.{key}" if prefix else key
            if key not in existing:
                missing[full_key] = default_value
            elif isinstance(default_value, dict) and isinstance(existing.get(key), dict):
                sub_missing, sub_extra = self._get_missing_and_extra_keys(existing[key], default_value, full_key)
                missing.update(sub_missing)
                extra.update(sub_extra)

        for key, value in existing.items():
            full_key = f"{prefix}.{key}" if prefix else key
            if key not in default:
                extra[full_key] = value

        return missing, extra

    def _apply_config_updates(self, existing: Dict[str, Any], default: Dict[str, Any]) -> Dict[str, Any]:
        """递归应用配置更新：补全缺失项，保持默认顺序。

        Parameters
        ----------
        existing : Dict[str, Any]
            现有配置。
        default : Dict[str, Any]
            默认配置。

        Returns
        -------
        Dict[str, Any]
            更新后的配置。
        """
        result = {}
        for key, default_value in default.items():
            if key in existing:
                if isinstance(default_value, dict) and isinstance(existing[key], dict):
                    result[key] = self._apply_config_updates(existing[key], default_value)
                else:
                    result[key] = existing[key]
            else:
                result[key] = copy.deepcopy(default_value)
        return result

    def _check_and_correct_config(self, path: Path, config_file: str):
        """检查并修正配置文件。

        在交互模式下会询问用户是否修复；在非交互模式下自动修复并输出日志。

        Parameters
        ----------
        path : Path
            配置文件路径。
        config_file : str
            默认配置文件名。
        """
        try:
            with open(path, "r", encoding="utf-8") as f:
                existing_config = toml.load(f)
        except Exception as e:
            self.logger.error(_("加载配置文件失败: ") + f"{path} --> {e}")
            return

        with open(self.data_dir / config_file, "r", encoding="utf-8") as f:
            default_config_dict = toml.load(f)

        missing_keys, extra_keys = self._get_missing_and_extra_keys(existing_config, default_config_dict)

        if not missing_keys and not extra_keys:
            return

        self.logger.warning(_("配置文件存在以下问题:"))
        if extra_keys:
            self.logger.warning(_("多余配置项: "))
            for key, value in extra_keys.items():
                self.logger.warning(f"  {key}: {value}")
        if missing_keys:
            self.logger.warning(_("缺少配置项: "))
            for key, value in missing_keys.items():
                self.logger.warning(f"  {key}: {value}")

        should_fix = False
        if self.interactive:
            try:
                choice = input(_("是否要补全缺少的配置项并删除多余的配置项？(yes/no 或 y/n): ")).strip().lower()
                if choice in ["yes", "y"]:
                    should_fix = True
                elif choice in ["no", "n"]:
                    self.logger.info(_("请稍后手动修改配置文件"))
                    return
                else:
                    self.logger.error(_("无效输入，请输入如下选项: yes/no 或 y/n"))
                    return
            except (EOFError, OSError):
                self.logger.warning(_("无法读取用户输入，将自动修复配置"))
                should_fix = True
        else:
            self.logger.info(_("非交互模式，自动补全/清理配置项"))
            should_fix = True

        if should_fix:
            for key in missing_keys:
                self.logger.info(_("已补全配置项: ") + f"{key}")
            for key in extra_keys:
                self.logger.info(_("已删除配置项: ") + f"{key}")

            ordered_config = self._apply_config_updates(existing_config, default_config_dict)
            try:
                with open(path, "w", encoding="utf-8") as f:
                    toml.dump(ordered_config, f)
                self.logger.info(_("配置文件更新成功: ") + str(path))
            except Exception as e:
                self.logger.error(_("配置文件更新失败: ") + f"{path} --> {e}")

    def _convert_config_value(self, key: str, value: Any, default_value: Any) -> Any:
        """将配置值转换为正确的类型，基于默认值的类型。

        Parameters
        ----------
        key : str
            配置键名（用于日志）。
        value : Any
            待转换的值。
        default_value : Any
            默认值，用于确定目标类型。

        Returns
        -------
        Any
            转换后的值。
        """
        if value is None:
            return copy.deepcopy(default_value)

        target_type = type(default_value)

        if isinstance(value, target_type):
            return value

        try:
            if target_type is bool:
                if isinstance(value, str):
                    return value.lower() in ("true", "1", "yes", "y", "on")
                return bool(value)
            elif target_type is int:
                return int(value)
            elif target_type is float:
                return float(value)
            elif target_type is str:
                return str(value)
            elif target_type is list:
                if isinstance(value, str):
                    return [v.strip() for v in value.split(",") if v.strip()]
                return list(value)
            else:
                return value
        except (ValueError, TypeError) as e:
            self.logger.warning(_("配置值类型转换失败: ") + f"{key}={value}, 期望类型 {target_type.__name__}: {e}")
            return copy.deepcopy(default_value)

    def _convert_config_types(
        self, config: Dict[str, Any], default: Dict[str, Any], prefix: str = ""
    ) -> Dict[str, Any]:
        """递归转换配置值类型。

        Parameters
        ----------
        config : Dict[str, Any]
            待转换的配置。
        default : Dict[str, Any]
            默认配置（提供类型信息）。
        prefix : str
            键前缀。

        Returns
        -------
        Dict[str, Any]
            类型转换后的配置。
        """
        result = {}
        for key, default_value in default.items():
            full_key = f"{prefix}.{key}" if prefix else key
            if key in config:
                if isinstance(default_value, dict) and isinstance(config[key], dict):
                    result[key] = self._convert_config_types(config[key], default_value, full_key)
                else:
                    result[key] = self._convert_config_value(full_key, config[key], default_value)
            else:
                result[key] = copy.deepcopy(default_value)
        return result

    def _validate_config(self, config: Dict[str, Any]) -> List[str]:
        """验证配置值是否合法。

        Parameters
        ----------
        config : Dict[str, Any]
            待验证的配置。

        Returns
        -------
        List[str]
            警告/错误信息列表。
        """
        warnings = []

        engine_config = config.get("engine", {})
        engine_default = engine_config.get("default", "xelatex")
        if engine_default not in self.VALID_ENGINES:
            warnings.append(_("未知的默认引擎: ") + f"{engine_default}, 有效值: {self.VALID_ENGINES}")

        fallback_order = engine_config.get("fallback_order", [])
        for eng in fallback_order:
            if eng not in self.VALID_ENGINES:
                warnings.append(_("降级顺序中包含未知引擎: ") + f"{eng}, 有效值: {self.VALID_ENGINES}")

        timeout = engine_config.get("timeout", 300)
        if not isinstance(timeout, (int, float)) or timeout <= 0:
            warnings.append(_("编译超时必须是正数: ") + str(timeout))

        bib_config = config.get("bib", {})
        bib_tool = bib_config.get("default_tool", "auto")
        if bib_tool not in self.VALID_BIB_TOOLS:
            warnings.append(_("未知的参考文献工具: ") + f"{bib_tool}, 有效值: {self.VALID_BIB_TOOLS}")

        index_config = config.get("index", {})
        index_tool = index_config.get("default_tool", "auto")
        if index_tool not in self.VALID_INDEX_TOOLS:
            warnings.append(_("未知的索引工具: ") + f"{index_tool}, 有效值: {self.VALID_INDEX_TOOLS}")

        compilation_config = config.get("compilation", {})
        max_extra_passes = compilation_config.get("max_extra_passes", 2)
        if not isinstance(max_extra_passes, int) or max_extra_passes < 0:
            warnings.append(_("智能补编最大次数必须是非负整数: ") + str(max_extra_passes))

        default_run_count = compilation_config.get("default_run_count", 2)
        if not isinstance(default_run_count, int) or default_run_count < 1:
            warnings.append(_("默认编译次数必须是正整数: ") + str(default_run_count))

        pvc_config = config.get("pvc", {})
        debounce = pvc_config.get("debounce", 1.0)
        if not isinstance(debounce, (int, float)) or debounce < 0:
            warnings.append(_("防抖时间必须是非负数: ") + str(debounce))

        return warnings

    def get(self, key: str, default: Any = None) -> Any:
        """支持点号分隔的键访问。

        Parameters
        ----------
        key : str
            点号分隔的键路径，如 "engine.default"。
        default : Any
            键不存在时返回的默认值。

        Returns
        -------
        Any
            配置值。
        """
        parts = key.split(".")
        value = self
        for part in parts:
            if isinstance(value, dict) and part in value:
                value = value[part]
            else:
                return default
        return value

    def get_engine_config(self) -> Dict[str, Any]:
        """返回 engine 配置节的字典。

        Returns
        -------
        Dict[str, Any]
            引擎配置。
        """
        return dict(self.get("engine", {}))

    def get_pvc_config(self) -> Dict[str, Any]:
        """返回 pvc 配置节的字典。

        Returns
        -------
        Dict[str, Any]
            PVC 模式配置。
        """
        return dict(self.get("pvc", {}))

    def get_compilation_config(self) -> Dict[str, Any]:
        """返回 compilation 配置节的字典。

        Returns
        -------
        Dict[str, Any]
            编译配置。
        """
        return dict(self.get("compilation", {}))

    def get_bib_config(self) -> Dict[str, Any]:
        """返回 bib 配置节的字典。

        Returns
        -------
        Dict[str, Any]
            参考文献配置。
        """
        return dict(self.get("bib", {}))

    def get_index_config(self) -> Dict[str, Any]:
        """返回 index 配置节的字典。

        Returns
        -------
        Dict[str, Any]
            索引配置。
        """
        return dict(self.get("index", {}))

    def get_output_config(self) -> Dict[str, Any]:
        """返回 output 配置节的字典。

        Returns
        -------
        Dict[str, Any]
            输出配置。
        """
        return dict(self.get("output", {}))

    def get_diff_config(self) -> Dict[str, Any]:
        """返回 diff 配置节的字典。

        Returns
        -------
        Dict[str, Any]
            LaTeXDiff 配置。
        """
        return dict(self.get("diff", {}))

    def init_config_file(self) -> "ConfigParser":
        """初始化配置文件。
        加载用户配置和项目配置文件, 优先使用项目配置（递归合并）。

        Returns
        -------
        ConfigParser
            返回自身，支持链式调用，同时保持 dict 接口。
        """
        self._init_default_config(self.user_config_path, "default_user_config.toml")
        user_config = self._load_toml(self.user_config_path)

        with open(self.data_dir / "default_user_config.toml", "r", encoding="utf-8") as f:
            default_user_config = toml.load(f)

        if user_config is None:
            user_config = {}

        user_config = self._convert_config_types(user_config, default_user_config)

        project_config = None
        if user_config.get("project_config_auto_init", True):
            self._init_default_config(self.project_config_path, "default_project_config.toml")
            project_config = self._load_toml(self.project_config_path)

        final_config = user_config

        if project_config:
            with open(self.data_dir / "default_project_config.toml", "r", encoding="utf-8") as f:
                default_project_config = toml.load(f)
            project_config = self._convert_config_types(project_config, default_project_config)
            final_config = self._deep_update(final_config, project_config)
        else:
            self.logger.info(_("未找到项目配置文件, 使用用户配置"))

        warnings = self._validate_config(final_config)
        for warning in warnings:
            self.logger.warning(warning)

        # 向后兼容：处理 quiet_mode 和 non_quiet 的互转
        if "quiet_mode" in final_config and "non_quiet" not in final_config:
            final_config["non_quiet"] = not final_config["quiet_mode"]
        elif "non_quiet" in final_config and "quiet_mode" not in final_config:
            final_config["quiet_mode"] = not final_config["non_quiet"]

        self.clear()
        self.update(final_config)

        self.logger.info(_("配置文件加载完成"))

        return self
