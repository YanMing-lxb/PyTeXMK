"""配置管理模块：纯读取合并用户配置与项目配置 TOML 文件，并支持手动初始化。"""
import logging
import tomllib
from copy import deepcopy
from pathlib import Path
from typing import Any

from pytexmk.language import set_language
from pytexmk.paths import get_app_path

_ = set_language("config")

# 内置默认配置：作为合并链的最终兜底（勿写盘，仅供运行时读取）。
DEFAULT_CONFIG: dict[str, Any] = {
    "default_file": "main",
    "compiled_program": "XeLaTeX",
    "quiet_mode": True,
    "pdf": {"pdf_preview_status": False, "pdf_viewer": "default"},
    "folder": {"auxdir": "./Auxiliary/", "outdir": "./Build/"},
    "index": {
        "index_style_file": "nomencl.ist",
        "input_suffix": ".nlo",
        "output_suffix": ".nls",
    },
    "latexdiff": {
        "old_tex_file": "old_file",
        "new_tex_file": "new_file",
        "diff_tex_file": "LaTeXDiff",
    },
    # 子项目发现规则：仅根配置生效，-ls/-s 不修改该段。
    "project_scan": {
        "depth": 3,
        "exclude": [],
    },
}


def _merge_dict(base: dict, override: dict) -> dict:
    """递归合并：override 中的键逐步覆盖 base；缺省用 base（默认值）兜底。"""
    result = deepcopy(base)
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(result.get(key), dict):
            result[key] = _merge_dict(result[key], value)
        else:
            result[key] = value
    return result


class ConfigParser:
    """
    配置解析器类，用于加载用户配置和项目配置文件。
    正常运行只读取合并，绝不自动生成文件、绝不调用 input()。
    """

    def __init__(self):
        """初始化配置解析器，获取用户配置文件路径与数据目录。"""
        self.logger = logging.getLogger(__name__)
        self.user_config_path = self._get_user_config_path()
        self.data_dir = get_app_path() / "data"
        self.logger.info(_("PyTeXMK 配置模块已初始化"))

    def _get_user_config_path(self) -> Path | None:
        """获取用户配置文件路径（~/.pytexmkrc），失败返回 None。"""
        try:
            return Path.home() / ".pytexmkrc"
        except Exception as e:  # noqa: BLE001
            self.logger.error(_("获取用户主目录路径失败: ") + str(e))
            return None

    def _load_toml(self, path: Path) -> dict[str, Any] | None:
        """读取 TOML 文件，不存在或解析失败返回 None（不抛异常、不写盘）。"""
        if path is None or not path.exists():
            return None
        try:
            with open(path, "rb") as f:
                config = tomllib.load(f)
            self.logger.info(_("成功加载配置文件: ") + str(path))
        except (OSError, tomllib.TOMLDecodeError) as e:
            self.logger.error(_("加载配置文件失败: ") + f"{path} --> {e}")
            return None
        else:
            return config

    def load_config(self, project_root: Path) -> dict[str, Any]:
        """纯读取合并：内置默认 <- 用户 rc <- 项目 rc（项目 root 权威）。

        注意：运行期不自动生成文件、不发起 input()；缺失配置用默认值
        静默运行，键不匹配仅记录日志警告，永不写盘。
        """
        final = deepcopy(DEFAULT_CONFIG)

        user_config = self._load_toml(self.user_config_path)
        if user_config:
            final = _merge_dict(final, user_config)

        project_path = project_root / ".pytexmkrc"
        project_config = self._load_toml(project_path)
        if project_config:
            final = _merge_dict(final, project_config)
            self.logger.info(_("已合并项目配置文件: ") + str(project_path))
        else:
            self.logger.info(_("未找到项目配置文件, 使用用户配置与默认配置"))

        self.logger.info(_("配置文件加载完成"))
        return final

    # 兼容别名：load_config(Path.cwd())，等价于加载当前目录项目配置。
    def init_config_file(self) -> dict[str, Any]:
        return self.load_config(Path.cwd())

    # ------------------------------------------------------------------
    # 手动初始化（-i / -iu，配合 -f 覆盖）
    # ------------------------------------------------------------------
    def _write_template(self, path: Path, template_name: str, force: bool) -> bool:
        """将内置模板写入 path；已存在且未加 force 时跳过不写入。"""
        if path.exists() and not force:
            self.logger.warning(
                _("配置文件已存在, 如需覆盖请添加 -f 参数: ") + str(path)
            )
            return False
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            template = (self.data_dir / template_name).read_text(
                encoding="utf-8"
            )
            path.write_text(template, encoding="utf-8")
            self.logger.info(_("已创建配置文件: ") + str(path))
            return True
        except OSError as e:
            self.logger.error(_("创建配置文件失败: ") + f"{path} --> {e}")
            return False

    def init_project_config(self, force: bool = False) -> bool:
        """生成根项目 .pytexmkrc。"""
        return self._write_template(
            Path.cwd() / ".pytexmkrc", "default_project_config.toml", force
        )

    def init_user_config(self, force: bool = False) -> bool:
        """生成用户级 ~/.pytexmkrc。"""
        if self.user_config_path is None:
            self.logger.error(_("无法确定用户主目录, 无法生成用户配置文件"))
            return False
        return self._write_template(
            self.user_config_path, "default_user_config.toml", force
        )