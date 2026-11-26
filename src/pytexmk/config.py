"""配置管理模块：纯读取合并用户配置与项目配置 TOML 文件，并支持手动初始化。"""
import logging
import tomllib
from copy import deepcopy
from pathlib import Path
from typing import Any

from pytexmk.file_ops import atomic_write_text
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
    # 构建行为：原生目录构建 / shell-escape / SyncTeX / 轮次上限 / 引擎参数
    "build": {
        "native": "auto",
        "shell_escape": "auto",
        "synctex": True,          # 是否让引擎写 .synctex.gz（投稿版可关掉省体积）
        "interaction": "",
        "extra_args": [],
        "max_extra_compilations": 8,
    },
    # 投稿打包：按 .fls 收依赖；遇到 pdflatex 不兼容的 Unicode 时生成转换副本
    "submission": {
        "unicode_to_latex": True,
        "include_bbl": False,     # 默认只带 .bib；期刊要求预编译 .bbl 时再开
        "reproducible": True,
        "output_dir": "./Submission/",
        "keep_preamble": False,
    },
    # 编译前静态检查（缺失的 \end{document}/.bib/图片等）
    "preflight": {
        "enabled": True,
    },
    "index": {
        # 输入/输出后缀由 detection 的索引注册表按索引包决定（makeidx/nomencl/
        # imakeidx/glossaries 各不相同），配置层面只保留样式文件与工具选择。
        "index_style_file": "nomencl.ist",
        "glossaries_tool": "makeindex",
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

    常规流程（``load_config``）只读取并合并用户级与项目级配置，绝不自动生成文件、
    绝不调用 ``input()``。唯一的例外是显式的写盘入口：``-i`` / ``-iu`` 初始化，
    两者都由用户命令直接触发，并默认覆盖已有文件。
    """

    def __init__(self):
        """初始化配置解析器，获取用户配置文件路径与数据目录。"""
        self.logger = logging.getLogger(__name__)
        self.user_config_path = self._get_user_config_path()
        self.data_dir = get_app_path() / "data"
        #: 最近一次 load_config 里读取/解析失败的配置文件 → 失败原因
        self.load_errors: dict[Path, str] = {}
        self.logger.info(_("PyTeXMK 配置模块已初始化"))

    def _get_user_config_path(self) -> Path | None:
        """获取用户配置文件路径（~/.pytexmkrc），失败返回 None。"""
        try:
            return Path.home() / ".pytexmkrc"
        except Exception as e:
            self.logger.error(_("获取用户主目录路径失败: ") + str(e))
            return None

    def _load_toml(self, path: Path) -> dict[str, Any] | None:
        """读取 TOML 文件，不存在或解析失败返回 None（不抛异常、不写盘）。

        解析/读取失败的原因会记入 ``load_errors[path]``：运行期只记日志不影响
        编译，但 ``--doctor`` 需要据此把结果判成失败（否则配置写坏了也显示 ✓）。
        """
        if path is None or not path.exists():
            return None
        try:
            with path.open("rb") as f:
                config = tomllib.load(f)
            self.logger.info(_("成功加载配置文件: ") + str(path))
        except (OSError, UnicodeDecodeError, tomllib.TOMLDecodeError) as e:
            self.logger.error(_("加载配置文件失败: ") + f"{path} --> {e}")
            self.load_errors[path] = f"{path} --> {e}"
            return None
        else:
            return config

    def load_config(self, project_root: Path) -> dict[str, Any]:
        """纯读取合并：内置默认 <- 用户 rc <- 项目 rc（项目 root 权威）。

        注意：运行期不自动生成文件、不发起 input()；缺失配置用默认值
        静默运行，键不匹配仅记录日志警告，永不写盘。
        """
        self.load_errors.clear()
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

    # ------------------------------------------------------------------
    # 手动初始化（-i / -iu，默认覆盖已有文件）
    # ------------------------------------------------------------------
    def _write_template(self, path: Path, template_name: str) -> bool:
        """将内置模板写入 path，已有文件直接覆盖（不备份）。"""
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            template = (self.data_dir / template_name).read_text(
                encoding="utf-8"
            )
            atomic_write_text(path, template)
            self.logger.info(_("已创建配置文件: ") + str(path))
            return True
        except OSError as e:
            self.logger.error(_("创建配置文件失败: ") + f"{path} --> {e}")
            return False

    def init_project_config(self) -> bool:
        """生成根项目 .pytexmkrc（覆盖已有文件）。"""
        return self._write_template(
            Path.cwd() / ".pytexmkrc", "default_project_config.toml"
        )

    def init_user_config(self) -> bool:
        """生成用户级 ~/.pytexmkrc（覆盖已有文件）。"""
        if self.user_config_path is None:
            self.logger.error(_("无法确定用户主目录, 无法生成用户配置文件"))
            return False
        return self._write_template(
            self.user_config_path, "default_user_config.toml"
        )
