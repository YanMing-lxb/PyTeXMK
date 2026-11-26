# AGENTS.md

## 开始前

1. 先跑基线：`ruff check --config pyproject.toml src tests` 与相关 `pytest`；不要凭记忆判断。
2. 确认本次只做哪一类：行为修复 / Python 3.15 迁移 / pathlib 现代化 / 纯风格清理。

## 环境事实

- **依赖与环境由 uv 唯一管理**：锁文件 `uv.lock`、环境 `.venv`；`uv sync --all-extras --dev`
  装依赖，`uv run …` 跑命令；不要用 pip / conda / poetry 建环境或往环境里装依赖。
- 编译/测试必须用 `.venv` 解释器（Python 3.15.2）；系统 Python 3.13 无法解析 PEP 758
  逗号 `except A, B:`。
- `PATH` 缺 `xelatex` 时先判断是否为测试环境缺 TeX，不要把环境失败写成代码回归。
- 不修改系统环境变量或 MiKTeX 本体，不联网，不提交，除非用户明确要求。

## 硬约束

- **不要混轮**：行为修复不要夹带语法或风格清理；纯风格轮次不要改变行为。
- **保留契约**：`file_ops._replace` 的临时文件 + `Path.replace` + 失败回滚；native biber 的
  `--input-directory` 必须指向 `auxdir`；`--version` 不经过惰性导入开关。
- **不要为清单造使用点**：`Path.info` 已因缓存语义否决，`uuid.uuid7` 当前无场景。
- **PEP 758** 只用于不带 `as` 的处理器；`except A, B as e` 仍非法。
- **i18n 工具链是 Babel，不是 gettext**：`.pot/.po/.mo` 的抽取、init、update、编译均走
  `pybabel`（封装在 `tools/i18n/babel.py`，配置 `babel.cfg`，依赖 `babel>=2.18.0`）；只有
  **运行时加载** `.mo` 才用 Python 标准库 `gettext`（`language.py`）。文档、注释、对外表述
  不要把整套 i18n 笼统称作 gettext 工具链；提到 gettext 时仅限运行时加载器。
- **CI 的 TeX 环境**：`tex-e2e` 用 `zauguin/install-texlive` action，`packages` 为 tlmgr
  包名最小集合；需要额外宏包时往该清单补 tlmgr 名，不要回退到手动 `apt-get` 装 TeX。
  包名必须用 tlmgr 名（Latin Modern 是 `lm`，不是 Debian 的 `lmodern`；`textcomp` 已并入
  LaTeX 内核，无独立 tlmgr 包）；未知包名会让 `tlmgr install` 整体返回非零而失败。

## 架构与文档指针

- 分层依赖与 import 纪律（6 层单向向下，底层不得 import 上层）：`docs/architecture.md`。
- 工具链分工、命令入口与易错项总览：`docs/toolchain.md`。
- 测试命名、目录索引与单测命令：`docs/测试索引与修改指南.md`。
- 发布流程与 winget 排障：`docs/winget_publish.md`。

## 常用工具入口

- i18n 语言包：`tools/i18n/babel.py`（`make pot/add-lang/update/mo`）。
- CI action 版本检查：`tools/release/check_actions.py`（`make actions`；`ARGS=--apply` 升级 semver 引用，
  主版本浮动标签保持不动）。

## 验证

以下命令在 `.venv` 解释器下执行（等价 `uv run …`），不要用系统 Python：

```powershell
ruff check --config pyproject.toml src tests
python -m compileall -q src\pytexmk
python -m pytest -q tests
python -m pytexmk.cli --version
```

单测单个：`python -m pytest -q tests/unit/test_compile_engine.py -k stop_reason`
