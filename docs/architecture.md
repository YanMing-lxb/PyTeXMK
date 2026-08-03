# PyTeXMK 架构设计文档

> 本文档描述 PyTeXMK v1.2.1 版本的分层架构、模块职责矩阵、新功能放置决策树以及 import 纪律。
> 本文档依据 `spec.md`（路径 A 推荐方案）编写，适用于当前 23 模块规模。

---

## 章节 1：分层依赖图（ASCII）

PyTeXMK 采用严格的 6 层向下依赖架构，Layer 0 为对外 API 顶层，Layer 5 为全局 I18N/UI 打印底层。
依赖方向**严格单向向下**，禁止任何跨层向上引用（即「底层不能 import 上层」）。

```
────────────────────────────────────────────────────────────────────
 Layer 0  对外 API（Public Surface）
────────────────────────────────────────────────────────────────────
          __init__.py  [__version__, __app_name__, main, __getattr__]
              │
              ▼ down
────────────────────────────────────────────────────────────────────
 Layer 1  CLI 子包（Command Line Interface）
────────────────────────────────────────────────────────────────────
  cli/__init__.py (空，占位)
  cli/__main__.py          cli/cli_args.py         cli/cli_workflow.py
  cli/check_version.py
              │
              ▼ down
────────────────────────────────────────────────────────────────────
 Layer 2  Core-Run（扁平，编译收敛核心）
────────────────────────────────────────────────────────────────────
 compile_engine.py     compile.py           detection.py          latexdiff.py
 [RUN / LaTeXDiffRUN] [CompileLaTeX]  [CompilationDetector]   [LaTeXDiff Runner]
              │
              ▼ down
────────────────────────────────────────────────────────────────────
 Layer 3  Domain-Ops（扁平，领域操作）
────────────────────────────────────────────────────────────────────
  tex_project.py      file_ops.py     subprocess_runner.py   pdf_tools.py   ui_theme.py
 [MainFileOperation] [FileMoveRemoveManager] [MySubProcess]    [PdfFileOp]    [custom_theme]
              │
              ▼ down
────────────────────────────────────────────────────────────────────
 Layer 4  Infra（扁平横切基础设施）
────────────────────────────────────────────────────────────────────
   version.py        paths.py       lifecycle.py      logger_config.py    config.py
 [__version__]   [get_app_path]   [exit_pytexmk]    [setup_logger]    [ConfigManager]
              │
              ▼ down
────────────────────────────────────────────────────────────────────
 Layer 5  I18N / UI 打印（全局 Hub，被所有上层依赖）
────────────────────────────────────────────────────────────────────
  language.py          timing.py       compile_report.py     ui_messages.py
 [set_language]   [time_count]   [print_compile_report]  [print_message]
────────────────────────────────────────────────────────────────────
```

**方向规则图示**：
```
L0  --down-->  L1  --down-->  L2  --down-->  L3  --down-->  L4  --down-->  L5
```

严格禁止向上箭头（Infra/I18N 不得 import CLI / Core-Run；Core-Run 不得 import CLI；只有 CLI 可以 import 所有下层）。

本架构对应的设计原则：
1. **下层稳定、上层变化**：Layer 5 I18N Hub 最稳定（language indegree = 19/23 = 82.6%），Layer 1 CLI 变化最频繁。
2. **依赖即信任**：上层可以信任下层实现；下层不得反向假设上层存在。
3. **唯一入口扇出**：`cli_workflow.py` outdegree = 14/23 = 60.9% 是调度根；其他模块不得做全局调度。

---

## 章节 2：23 模块职责矩阵（含 [cli 子包] 标签）

本矩阵列出 PyTeXMK 当前 23 个源模块（其中 4 个位于 `cli/` 子包内，标注 `[cli 子包]`），
行号、行数为 v1.2.1 锚点的近似值，「对外关键符号」按该模块被外部 import 频率排序（前 5）。

| No. | 文件名 | 行数（近似） | 对外关键符号（前 5） | 一句话职责 |
|-----|--------|-------------|----------------------|-----------|
| 01 | `__init__.py` | 12 | `__version__`, `__app_name__`, `main`, `__getattr__` | 包对外 API：导出版本号、懒加载转发 cli_args/cli_workflow/check_version/main |
| 02 | `__main__.py` | 4 | `main`（薄转发） | 根包主入口：3 行薄转发 `from .cli.__main__ import main`，使 `python -m pytexmk` 可用 |
| 03 | `cli/__main__.py [cli 子包]` | 34 | `main` | CLI 主骨架：set_language + parse_args + run_workflow + try/except 生命周期，副作用集中 |
| 04 | `cli/cli_args.py [cli 子包]` | 169 | `parse_args`, `CustomArgumentParser`, `CustomHelpFormatter` | 命令行参数解析：argparse 16 个参数定义、CustomHelpFormatter 等宽帮助、校验互斥组 |
| 05 | `cli/cli_workflow.py [cli 子包]` | 330 | `run_workflow`, `doctor_check`, `show_config_display` | CLI 工作流调度：按运行模式（RUN / LaTeXDiff / --doctor / --show-config）分发到 Core-Run |
| 06 | `cli/check_version.py [cli 子包]` | 203 | `UpdateChecker`, `check_pypi_update`, `get_cached_latest` | 版本检查：GitHub API 拉取最新版本号、本地文件缓存、~10 秒超时避免网络卡壳 |
| 07 | `compile_engine.py` | 279 | `RUN`, `LaTeXDiffRUN` | 对外运行函数：`RUN` 编排主编译收敛循环（最多 8 次）、`LaTeXDiffRUN` 封装 latexdiff 流程（v1.2.0 起 `run.py` 重命名为 `compile_engine.py`，旧名字无兼容层保留） |
| 08 | `compile.py` | 165 | `CompileLaTeX`, `aux_move_to_dir` | 编译调度：`CompileLaTeX.__call__` 单次执行子进程 + 拉 log + 触发 6 维检测 + 搬 aux 目录 |
| 09 | `detection.py` | 469 | `CompilationDetector`, `RERUN_LOG_PATTERNS`, `RERUN_AUX_PATTERNS` | 6 维检测策略：bib/toc/index/aux/out/log 六类正则 + 10 项检测方法，判断是否需要 rerun |
| 10 | `latexdiff.py` | 178 | `run_latexdiff`, `diff_tex_with_commit`, `diff_tex_with_file` | LaTeXDiff 差异：调用 latexdiff 命令行、支持 Git 历史 commit 与两个本地文件两种对比模式 |
| 11 | `tex_project.py` | 241 | `MainFileOperation`, `find_main_tex`, `parse_magic_comments`, `draft_mode_sanitize` | TeX 项目域：主文件检索（通配 main.tex + 魔法注释）、`% !TeX root` 解析、草稿模式安全过滤 |
| 12 | `file_ops.py` | 84 | `FileMoveRemoveManager`, `safe_move`, `safe_remove`, `clean_aux_files` | 纯文件操作：`FileMoveRemoveManager` 封装移动/删除、`shutil.move` / `unlink` 的安全封装（吞 FileNotFound、记录日志）、批量 aux 清理（v1.2.0 起 `MoveRemoveOperation` 重命名为 `FileMoveRemoveManager`） |
| 13 | `subprocess_runner.py` | 97 | `MySubProcess`, `SubprocessFailedError`, `run_command_capture`, `_format_duration` | 子进程执行：Popen 封装 stdout/stderr 捕获、自定义异常替代 `sys.exit`、耗时格式化 |
| 14 | `pdf_tools.py` | 55 | `PdfFileOperation`, `open_pdf_viewer`, `compare_pdf_pages` | PDF 工具：跨平台 PDF 预览启动（Windows `start` / macOS `open` / Linux `xdg-open`） |
| 15 | `ui_theme.py` | 13 | `custom_theme`, `console` | Rich UI 主题：`custom_theme` 三色常量（success=green/warning=yellow/error=red）、全局单例 `console` |
| 16 | `version.py` | 29 | `__version__`, `__app_name__`, `script_name` | 版本常量：`1.2.1` 硬编码 + `PyTeXMK` 应用名，所有其他模块的版本号唯一来源 |
| 17 | `paths.py` | 13 | `get_app_path`, `get_data_dir`, `get_config_dir` | 路径定位：`pkgutil.get_data` + 平台 `AppData`/`.config` 目录解析，locale/data/config 相对锚点 |
| 18 | `lifecycle.py` | 9 | `exit_pytexmk`, `ExitCode` 枚举 | 生命周期退出：统一退出钩子（打印再见横幅、写 logger、刷新缓冲、`sys.exit`），禁止零散 `sys.exit` |
| 19 | `logger_config.py` | 65 | `setup_logger`, `get_logger`, `LOG_FILE_PATH` | 日志配置：Rich 日志 handler + 文件 handler 双写、按日滚动、日志级别 CLI 参数切换 |
| 20 | `config.py` | 172 | `ConfigManager`, `load_user_config`, `merge_project_config`, `DEFAULT_CONFIG_TOML` | TOML 配置：三层合并（默认 default → 用户 `~/.config/pytexmk/` → 项目 `.pytexmk.toml`） + 键校验 |
| 21 | `language.py` | 49 | `set_language`, `gettext`, `_current_domain` | i18n Hub：`gettext.translation` 封装，所有模块调用 `set_language("<domain>")` 取翻译器 `_` |
| 22 | `timing.py` | 133 | `time_count`, `time_print`, `total_len`, `get_text_len` | 计时统计：装饰器式编译耗时累计、中英文双宽字符对齐 `get_text_len`、统计段格式化 |
| 23 | `compile_report.py` | 63 | `print_compile_report`, `print_compile_separator`, `DIVIDER_STYLE`, `WARNING_STYLE` | 编译检测报告：Rerun 原因 6 维汇总表 + 分隔线（-×80）+ 三色样式标签（warning/stable/conclusion） |
| 24 | `ui_messages.py` | 76 | `print_message`, `magic_comment_desc_table` | UI 通用横幅：启动 / 成功 / 失败 Rich 三色大横幅、`--help` 中魔法注释说明表文本 |

> 备注：矩阵中 No.1~24 中，`cli/__init__.py [cli 子包]`（0 行空文件）是子包存在标志但无对外符号，
> 因此计入子包但不计入 23 模块统计，23 模块指上表 No.1~24 中去掉 `cli/__init__.py`（因为是子包占位），
> 恰好 23 行数据（No.1 根包 `__init__` + No.2 根包 `__main__` + No.3~6 的 4 个 cli 子包模块 + No.7~24 的 18 个根包扁平模块）。

---

## 章节 3：新功能放哪的决策树（含 5 号规则阈值）

当新增一个功能或一个源文件时，按以下 5 条规则依次判断归属位置。
**规则 1~4 优先级高于规则 5**；规则 1~4 命中即停止，否则进入规则 5。
规则 5 内含「子包拆分硬阈值」，**禁止为拆而拆**。

### 决策流程（自上而下判定）

```
新功能 / 新模块需求
        │
        ▼
┌──────────────────────────────────────────────────────────┐
│ Q1：与 CLI 入口直接相关？                                   │
│    - 新增 argparse 参数（比如 -p bibtex-extra）           │
│    - 新增子命令（--doctor / --show-config / --migrate）   │
│    - 新增版本检查逻辑（非 RUN 流程）                       │
│    ├─ YES → 放 Layer 1 `src/pytexmk/cli/` 子包           │
│    └─ NO  → 继续 Q2                                        │
└──────────────────────────────────────────────────────────┘
        │ (NO)
        ▼
┌──────────────────────────────────────────────────────────┐
│ Q2：与多次编译收敛 / RUN 主循环 / CompileLaTeX / latexdiff 相关？ │
│    - RUN 最大次数、收敛判断策略改动                       │
│    - CompileLaTeX 单次调度、子进程参数封装               │
│    - detection 检测维度新增 / latexdiff 预处理           │
│    ├─ YES → 放 Layer 2 Core-Run 扁平组（compile_engine.py / compile.py │
│    │        / detection.py / latexdiff.py 同级目录旁）     │
│    └─ NO  → 继续 Q3                                        │
└──────────────────────────────────────────────────────────┘
        │ (NO)
        ▼
┌──────────────────────────────────────────────────────────┐
│ Q3：横切基础设施？                                          │
│    - 路径定位（get_app_path / 用户目录 / 项目目录）        │
│    - 退出钩子（sys.exit 集中处理）                        │
│    - TOML 配置读写 / 校验                                  │
│    - 日志 handler、级别配置                                 │
│    - 版本号 / 应用名常量                                   │
│    ├─ YES → 放 Layer 4 Infra 扁平组（version.py / paths.py │
│    │        / lifecycle.py / logger_config.py / config.py 旁）│
│    └─ NO  → 继续 Q4                                        │
└──────────────────────────────────────────────────────────┘
        │ (NO)
        ▼
┌──────────────────────────────────────────────────────────┐
│ Q4：i18n 翻译域相关输出？                                    │
│    - 新增 Rich 三色横幅（启动 / 总结 / 失败）             │
│    - 新增编译报告（比如 -p bibtex-extra 的 report 段）    │
│    - 新增计时统计维度（阶段耗时 / 分引擎耗时）             │
│    ├─ YES → 放 Layer 5 I18N/UI 扁平组（language.py / timing.py │
│    │        / compile_report.py / ui_messages.py 旁）      │
│    └─ NO  → 进入 Q5（兜底规则 + 子包拆分阈值）             │
└──────────────────────────────────────────────────────────┘
        │ (NO)
        ▼
┌───────────────────────────────────────────────────────────────────────┐
│ Q5 / 规则 5：兜底到 Layer 3 Domain-Ops 扁平组 + 子包拆分硬阈值          │
│                                                                           │
│ Step 1：先放 Layer 3 Domain-Ops 扁平组（tex_project.py / file_ops.py      │
│         / subprocess_runner.py / pdf_tools.py / ui_theme.py 同级）；      │
│                                                                           │
│ Step 2：当候选域（例如未来要新增的「bib 管理」域）规模增长后，若以下        │
│         **三条件同时成立**（AND 关系，缺一不可），才允许把该域从扁平组    │
│         独立成子包 `src/pytexmk/<new_subpkg>/`：                           │
│                                                                           │
│   条件 ① 同域模块数 ≥ 4                                                    │
│           （例：bib_fetch.py / bib_clean.py / bib_compare.py               │
│                  / bib_dedupe.py = 4，满足）                               │
│                                                                           │
│   条件 ② 同域内部 import 边数 ≥ 3                                          │
│           （即这 4 个模块之间互相 import 的边数 ≥ 3；若都是                  │
│            单向只被外部引、内部无交互 → 不满足）                            │
│                                                                           │
│   条件 ③ 耦合系数 ≥ 0.7                                                    │
│           （耦合系数定义：                                                 │
│              外部 import 边数  out                                       │
│            ──────────────────────────────────  ≥ 0.7                     │
│              内部 import 边数 in + 外部 import 边数 out                   │
│            即 ≥70% 的引用都来自域外部，说明该域对外服务稳定、是黑盒）        │
│                                                                           │
│ Step 3：三条件**全满足**后才允许独立子包；否则继续扁平留在根包。             │
│ 此为子包拆分硬阈值，禁止为拆而拆。                                           │
└───────────────────────────────────────────────────────────────────────┘
```

### 规则 5 阈值三条件（全称重申）

> **子包拆分硬阈值**：同域模块数 ≥ 4 **AND** 同域内部 import 边数 ≥ 3 **AND**
> 耦合系数（外部 import 边数 / (内部 import 边数 + 外部 import 边数)）≥ 0.7，
> 三者缺一不可。

本阈值的背景来源：spec.md 静态调查 6 候选域（cli/core_run/domain_ops/infra/i18n/api），
**仅 cli 域**（4 模块 / 内引 4 / 耦合 0.826）同时满足三条件，
其他 5 个候选域至少不满足 1~2 条，因此 19 个非 cli 模块保持扁平。
未来新域的拆分必须使用同样的三个阈值进行客观判定，禁止主观「看起来应该拆」。

---

## 章节 4：import 纪律（3 条）

PyTeXMK 的 import 规则与分层架构严格对应。违反以下 3 条会直接导致：
- 循环依赖（ModuleNotFoundError 或运行期 ImportError）
- 相对 import 点数错误
- 跨子包 API 暴露不一致

### 纪律（a）：禁止跨层向上 import

依据分层依赖图（章节 1）的 `L0 → L1 → L2 → L3 → L4 → L5` 方向，
**只允许上层 import 下层，禁止下层 import 上层**（即方向只能是向下箭头）。

具体允许矩阵：

| 所在层 | 允许 import 的层 | 禁止 import 的层 | 示例 |
|--------|-----------------|-----------------|------|
| **CLI（L1）** | L2 / L3 / L4 / L5（所有下层） | 无（L0 是自己的 API 壳） | `cli_workflow.py` 可以 `from ..compile_engine import RUN`（L1→L2） |
| **Core-Run（L2）** | L3 / L4 / L5 | L0 / L1（禁止引 CLI） | `compile_engine.py` 可以 `from .language import set_language`（L2→L5），但不得 `from .cli.cli_workflow import X`（L2→L1 ❌） |
| **Domain-Ops（L3）** | L4 / L5 | L0 / L1 / L2 | `tex_project.py` 可以 `from .config import ConfigManager`（L3→L4），但不得引 L2 run/compile |
| **Infra（L4）** | 仅允许 L5 | L0 / L1 / L2 / L3（禁止引任何上层/业务层） | `paths.py` 可以 `from .language import _`（L4→L5），但不得 `from .config import X`（L4→L4 允许同层，L4→L3 ❌） |
| **I18N/UI（L5）** | 无（除 language 自己） | L0/L1/L2/L3/L4（最底层） | `language.py` 只依赖标准库 gettext，不得 import 任何业务层；`timing.py` 可引同层 L5 `language.py`（同层允许） |

> 同层 import 允许（例如 `compile.py` L2 可以引 `detection.py` L2），不违反纪律（a）。

### 纪律（b）：禁止跨子包同层相对 import 点数错误

相对 import 的点数量必须与「源模块所在位置 → 目标模块所在位置」的目录层级严格对应。
点数错误会导致 `ModuleNotFoundError: No module named 'pytexmk.xxx'`，
每次移动或新增模块后必须烟检。

具体点数规则：

| 源位置 | 目标位置 | 正确点数 | 正确写法 | 错误写法（举例） |
|--------|---------|---------|---------|----------------|
| `cli/__main__.py`（cli 子包内） | `cli/cli_args.py`（同子包内） | `.` = 1 点 | `from .cli_args import parse_args` | `from cli_args import ...`（0 点绝对 ❌）<br>`from ..cli_args import ...`（2 点多了 ❌） |
| `cli/cli_workflow.py`（cli 子包内） | `compile_engine.py`（根包扁平） | `..` = 2 点 | `from ..compile_engine import RUN` | `from .compile_engine import ...`（1 点少了 ❌）<br>`from pytexmk.compile_engine import ...`（绝对路径允许，但本项目推荐相对） |
| `cli/check_version.py`（cli 子包内） | `language.py`（根包扁平） | `..` = 2 点 | `from ..language import set_language` | `from .language import ...`（1 点少了 ❌） |
| 根包扁平 `compile_engine.py`（src/pytexmk/） | `cli/cli_workflow.py`（cli 子包） | `.cli.X` = 1 点进子包 | `from .cli.cli_workflow import run_workflow` | `from .cli_workflow import ...`（0 点子包不存在 ❌）<br>`from ..pytexmk.cli.cli_workflow import ...`（3 点升出去又回来 ❌） |

烟检命令（修改 import 后必须执行，保证点数无误）：
```bash
uv run python -c 'import pytexmk.cli.__main__, pytexmk.cli.cli_args, pytexmk.cli.cli_workflow, pytexmk.cli.check_version; print("import 点数 OK")'
```

### 纪律（c）：子包对外 API 必须经子包 `__init__.py` 显式 re-export

任何对外暴露的跨子包 API（即外部代码需要 `from pytexmk.<subpkg> import <symbol>`）
必须在 `<subpkg>/__init__.py` 中**显式 re-export**，不能让外部代码
「跳过子包 `__init__`」直接访问 `<subpkg>` 内的模块。

#### 当前 cli 子包状态

`src/pytexmk/cli/__init__.py` 当前**故意留空（0 行）**。
原因：当前 4 个 cli 模块（`__main__` / `cli_args` / `cli_workflow` / `check_version`）
没有需要对外暴露的**聚合公共 API**。所有使用方要么：
1. 通过根包 `__init__.py.__getattr__` 懒加载（如 `from pytexmk import cli_args` 兼容写法）；或
2. 直接写全路径 `from pytexmk.cli.cli_args import parse_args`（这是直接 import 模块对象，不是跨子包 API 符号暴露，不违反本纪律）。

#### 未来若要聚合 API 的正确做法

若未来要支持：
```python
from pytexmk.cli import run_workflow, parse_args  # 期望：一次 import 拿多个符号
```
则必须在 `src/pytexmk/cli/__init__.py` 中**显式 re-export**：

```python
from .cli_workflow import run_workflow
from .cli_args import parse_args

__all__ = ["run_workflow", "parse_args"]
```

**禁止跳过 `__init__`**：即禁止外部直接写
`from pytexmk.cli.cli_workflow import run_workflow` 作为「公共 API」
（内部模块自用可以，但一旦要成为公共 API，必须经 `cli/__init__.py` 中转），
否则未来重构内部模块拆分/合并时，外部 import 路径全部破碎，破坏语义化版本。
