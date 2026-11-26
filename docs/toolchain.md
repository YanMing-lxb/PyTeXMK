# 工具链地图

本文件记录 PyTeXMK 当前生效的工具链分工、入口命令与易错项，供 AI 与贡献者判断
“该用哪个工具”。配置事实以 `pyproject.toml`、`Makefile`、`.github/workflows/` 为准；
本文件只做索引与约束说明，不复制长配置。

## 总览

| 环节 | 工具 | 配置 / 入口 | 常用命令 |
| --- | --- | --- | --- |
| 依赖与环境 | **uv**（唯一） | `pyproject.toml`、`uv.lock`、`.venv` | `uv sync --all-extras --dev`、`uv run …` |
| Python 版本 | ≥ 3.15（开发 venv 3.15.2） | `requires-python = ">=3.15"` | 见下“环境事实” |
| 代码检查 | ruff | `[tool.ruff]`（target py315，行宽 120） | `uv run ruff check src tools tests` |
| 测试 | pytest ≥ 9.2 | `[tool.pytest.ini_options]`，`tests/` | `uv run pytest -q tests` |
| 国际化 | Babel / pybabel | `tools/i18n/babel.py`、`babel.cfg` | `make pot/add-lang/update/mo` |
| 二进制打包 | PyInstaller onedir | `tools/build/pack_binary.py` | `make build` |
| 分发包 | uv build（setuptools 后端） | `pyproject.toml` build-system | `uv build` |
| 平台 zip / 水位门禁 | `tools/build/pack_zip.py`、`tools/build/check_glibc.py` | 打包后处理 | 见打包一节 |
| 发布 / CI 辅助 | `tools/release/upload.py`、`tools/release/ci_dryrun.py`、`tools/release/check_actions.py` | 标准库脚本 | 见发布一节 |

## tools 目录分组

| 分组 | 目录 | 脚本职责 |
| --- | --- | --- |
| 共享（非 CLI 入口） | `tools/shared/` | `config.py`（路径/版本常量）、`utils.py`（跨脚本复用辅助） |
| 构建产物 | `tools/build/` | `pack_binary.py`（onedir 打包/清理）、`pack_zip.py`（平台 zip）、`check_glibc.py`（glibc 门禁）、`generate_icon.py`（图标生成） |
| 国际化 | `tools/i18n/` | `babel.py`（pybabel 四命令封装） |
| 发布与 CI 辅助 | `tools/release/` | `upload.py`（打 tag 推送）、`ci_dryrun.py`（触发 dry_run）、`check_actions.py`（action 版本检查） |

命名规则：入口脚本 `动词_名词.py`；检查/门禁脚本 `check_<对象>.py`；`shared/` 内模块不做
CLI 入口。各脚本先把 tools 根目录加入 `sys.path`，再 `from shared.config import …` /
`from shared.utils import …` 引用共享模块。

## 依赖与环境（uv）

- **开发环境与依赖一律用 uv 管理**：锁文件是 `uv.lock`，虚拟环境是 `.venv`；不要用
  pip、conda、poetry 建环境或往环境里装依赖。
- 首次拉取后：`uv sync --all-extras --dev`；日常跑命令走 `uv run …`。
- 镜像源：默认清华 PyPI 镜像；直接依赖 `pytexlogs` 显式走官方 pypi.org
  （见 `[tool.uv.index]` 与 `[tool.uv.sources]`），不要整体切换默认源。
- **dev 依赖必须写两处且逐条一致**（`tests/unit/test_packaging.py` 会校验）：
  - `[project.optional-dependencies].dev`：给 `pip install pytexmk[dev]` 的下游；
  - `[dependency-groups].dev`：给 `uv sync`（PEP 735，不进 wheel METADATA）。
- 环境事实：编译/测试必须用 `.venv`（Python 3.15.2）；系统 Python 3.13 无法解析
  PEP 758 逗号 `except A, B:`，不要拿系统解释器跑测试或编译。

## 代码检查（ruff）

- 配置在 `[tool.ruff]`：`target-version = "py315"`，`line-length = 120`；
  规则集 `E4/E7/E9/F/W/I/UP/B`，忽略 `E501`（行宽交给 formatter）。
- 检查命令：`uv run ruff check src tools tests`。
- 格式化：`uv run ruff format src tools tests`（本项目不强制在每次改动后跑，
  但不要引入与 formatter 冲突的手写格式）。

## 测试（pytest）

- 配置在 `[tool.pytest.ini_options]`：`testpaths = ["tests"]`，`pythonpath = ["src"]`，
  标记 `unit / cli / integration / regression`。
- 全量：`uv run pytest -q tests`；单个用例：`uv run pytest -q tests/unit/test_x.py -k 关键词`。
- 自家代码的 `DeprecationWarning` 与 `SyntaxWarning` 按配置视为失败，不要在测试里
  用 `-W ignore` 绕过。

## 国际化（Babel，不是 gettext 工具链）

- 抽取 / 初始化 / 合并 / 编译全部走 **Babel 的 `pybabel`**，封装在 `tools/i18n/babel.py`，
  配置 `babel.cfg`；依赖 `babel>=2.18.0`。
- 工作流：`make pot`（extract）→ `make add-lang`（init，新增语言）→
  `make update`（合并新 msgid）→ `make mo`（compile 成 `.mo`）。
- **只有运行时加载 `.mo` 才用 Python 标准库 `gettext`**（`language.py`）；
  不要把整套 i18n 工具链笼统称作 gettext。
- 不要手改 `.mo`（二进制产物）；改完 `.po` 必须跑 `make mo` 重新编译。

## 打包

- **二进制（onedir）**：`tools/build/pack_binary.py` 调 PyInstaller，产物 `dist/pytexmk/`；
  入口 `make build`（先 `make mo` 保证打进的是最新译文）。
- **分发包（sdist + wheel）**：`uv build`，产物 `dist/`；不要用 `setup.py bdist_wheel`
  或手动 setuptools 命令。
- **平台 zip**：`tools/build/pack_zip.py` 把 onedir 压成
  `pytexmk-<ver>-<platform>-<arch>.zip`；Linux 产物另由
  `tools/build/check_glibc.py` 断言 glibc 水位 ≤ 2.28。
- **图标**：`tools/build/generate_icon.py`（Pillow，dev 依赖），`make icon`。

## 发布与 CI 辅助

- `tools/release/upload.py upload`：打 tag 并推送到远端（`make upload`）。
- `tools/release/ci_dryrun.py`：触发 Release 工作流 dry_run，只构建不发布；纯标准库，
  经 `uv run --no-project` 调用（`make dryrun`）。
- `tools/release/check_actions.py`：扫描 workflow / composite 里的 `uses:`，对比上游最新
  release；`--apply` 只升级 semver 引用，主版本浮动标签不动（`make actions`）。
- winget 发布没有本地 / Make 入口：完全在 `Release.yml` 的 `publish-to-winget` job
  内用官方 `wingetcreate` 完成，不要在本地脚本里重复打包。

## Makefile 目标

| 目标 | 作用 |
| --- | --- |
| `make build` | PyInstaller onedir 二进制（先编译 `.mo`） |
| `make icon` | 生成各平台图标 |
| `make whl` | 清理后 `uv build` 出 wheel + sdist（先编译 `.mo`） |
| `make inswhl` | 本地安装编译出的 wheel（外层调 `uv tool`，不在 `uv run` 内嵌套） |
| `make clean` | 清理 build/dist/staging 与 `.spec` |
| `make pot / add-lang / update / mo` | i18n 四步流程 |
| `make dryrun` | 触发 CI dry_run（`ARGS` 透传给 `release/ci_dryrun.py`） |
| `make actions` | 检查 action 版本（`ARGS=--apply` 升级 semver 引用） |
| `make upload` | 上传 PyPI |

## 易错项（不要用错工具）

- 不要用 pip / conda / poetry 建环境或装依赖；开发环境只走 uv。
- 不要在 `uv run` 里嵌套 `uv tool`：父 uv 持有工具目录锁，Windows 上子 uv 会因
  `.lock` 拒绝访问；`inswhl` 这类工具安装必须在 Makefile 外层执行。
- 不要直接用系统 Python 跑测试 / 编译；用 `.venv` 或 `uv run`。
- 不要手改 `.mo`；改 `.po` 后走 `make mo`。
- 不要手动跑 `setup.py bdist_wheel` 等旧 setuptools 命令；分发包走 `uv build`。
- 加 dev 依赖时两处（extras.dev 与 dependency-groups.dev）必须同步。
- 不修改系统环境变量或 MiKTeX 本体，不联网，不提交，除非用户明确要求。
