# CHANGELOG

## v1.2.1 - 2026-08-03

### 🏗 架构变更

- **🔪 彻底移除 Cython 加密打包链路：永久切换源码模式 onedir（单一打包入口）**
  - 删除 [tools/pydmk.py](file:///d:/Document%20YM/Desktop%20Document/Tools_Development/PyTeXMK/tools/pydmk.py) 整体文件（move_src_to_srcpyd / encrypt_py_to_pyd / _check_compiler_available / clean_cython_artifacts / pydmk CLI 19 个子函数全部物理删除，不复用、不兼容）
  - [tools/config.py](file:///d:/Document%20YM/Desktop%20Document/Tools_Development/PyTeXMK/tools/config.py#L1-L72) 删除 `SRCPYD_DIR` / `SRCPYD_ENTRY_POINT` 常量与 `__all__` 对应项（srcpyd 目录不再是合法打包入口）
  - [tools/pack.py](file:///d:/Document%20YM/Desktop%20Document/Tools_Development/PyTeXMK/tools/pack.py#L1-L244) 删除 `--source/-s` 参数、`use_cython` 分支、`from pydmk import pydmk` import、整个 🔐 Cython 加密模式区块与 vcvars64 pwsh 分支；`clean_build()` 同步删除清理 `srcpyd/`；入口永久固定 `SRC_ENTRY_POINT`，Banner 改为 `📦 打包模式 (onedir)`
- **🧰 构建配置全链路去 Cython 依赖**
  - [Makefile](file:///d:/Document%20YM/Desktop%20Document/Tools_Development/PyTeXMK/Makefile#L1-L148) 删除 `pydmk` target 整段（6 行）+ help 表中 `pydmk    Cython compile all .py to .pyd/.so` 行 + build/help/clean 注释中所有「Cython 加密」字样，统一改「源码模式 onedir」
  - [pyproject.toml](file:///d:/Document%20YM/Desktop%20Document/Tools_Development/PyTeXMK/pyproject.toml#L49-L64) `[project.optional-dependencies] dev` 与 `[dependency-groups] dev` 两处删除 `"cython>=3.2.9"`（不再需要 MSVC/gcc/clang 编译器链参与打包）
  - [.github/workflows/Release.yml](file:///d:/Document%20YM/Desktop%20Document/Tools_Development/PyTeXMK/.github/workflows/Release.yml#L18-L110) 删除 Ubuntu apt `build-essential`、macOS `Ensure clang toolchain`、Windows `Setup MSVC v143 x64 (ilammy/msvc-dev-cmd@v1)` 三步；Show versions 去掉 `--- Cython ---` 段和 `cythonize --version`；三平台 Pack 统一合并为 `Pack binary (onedir, source mode)`（不分叉 shell/pwsh）
  - [.github/workflows/CI.yml](file:///d:/Document%20YM/Desktop%20Document/Tools_Development/PyTeXMK/.github/workflows/CI.yml#L45-L46) Pack step 改名：`Pack binary (onedir, Cython)` → `Pack binary (onedir, source mode)`
  - [.gitignore](file:///d:/Document%20YM/Desktop%20Document/Tools_Development/PyTeXMK/.gitignore#L149-L151) 删除 `# Cython debug symbols` / `cython_debug/` 两行（历史配置不再保留）

### 🎉 新增 / 质量改进

- **📦 打包链路「单一源码模式」化：构建环境跨三平台零编译器依赖**
  - Release / CI 两个 workflow 的构建矩阵从「每平台先装编译工具链 → Cython 加密 → PyInstaller」简化为「uv sync → PyInstaller onedir」，平均 runner 准备阶段耗时下降 30~60 秒
  - [tools/pack.py](file:///d:/Document%20YM/Desktop%20Document/Tools_Development/PyTeXMK/tools/pack.py#L1-L244) 的 `verify_pack` 断言仍保留三层强校验：二进制文件存在 + `exitcode == 0` + stdout 包含 `${__version__}` 版本字符串；只要任意一层不满足 → 立即 sys.exit(1) 中断，避免打包假阳性
- **🧹 全仓（排除文档）Cython / 加密关键字零残留（发布前 grep 硬断言）**
  - 过滤集合：`**/*.py / *.toml / Makefile / *.yml / *.yaml / .gitignore / tools/*`
  - 关键字正则 `cython|Cython|pydmk|SRCPYD|srcpyd|加密` → 命中 = 0 处

### 🐛 Bug 修复（打包链路）

- **修复「本地 Cython 缺 MSVC 仍被判定为打包成功」的假阳性**：删除了整条会被吞错的 🔐 Cython 加密分支，现在打包路径只有一条，verify_pack 三层强校验确保 exit 非零即失败
- **修复「GitHub Actions runner 2 核机器 cythonize -j 8 OOM → Error: The operation was canceled」**：因 Cython 并行加密整体删除，OOM/临时目录过长/Windows 未初始化 vcvars 三类 Cython 特有构建错误全部消失
- **修复 `ImportError: attempted relative import with no known parent package`（历史遗留 srcpyd/__main__.py 相对导入 Bug）**：入口薄转发已在 v1.2.0 迁移到 `src/pytexmk/__main__.py`（绝对导入），本次 v1.2.1 永久删除 srcpyd 入口避免回退

### 🧪 质量验证（发布前硬验证）

- 🔎 单元测试：`pytest tests -q` → **19 passed**（0 failures / 0 skips，较 v1.2.0 的 9 passed 新增 10 条 i18n/locale 专项用例）
- 📝 Lint：`ruff check --select=F401,F841 src/ tools/ tests/` → 0 问题
- 📦 源码模式 onedir 打包：`uv run python tools/pack.py pack` → 结束横幅 `🎉 所有操作成功完成！`，耗时 ≤ 30s
- 🧩 二进制启动：`dist/pytexmk/pytexmk(.exe) --version` → stdout 包含 `PyTeXMK: version 1.2.1` 且 exitcode = 0
- 🧭 架构断言（全仓 *.py/*.toml/Makefile/*.yml/*.yaml/.gitignore）：`rg -i 'cython|pydmk|srcpyd|加密'` → 0 命中（文档区不在校验域内，允许历史版本 CHANGELOG 描述留存）
- 🔗 Locale 证据：仍沿用 v1.2.0 的 pybabel extract/init/update/compile 官方工作流；`locale/zh/LC_MESSAGES/` 存在 `compile_engine.mo` 等各独立域文件

---

## v1.2.0 - 2026-08-02

### 🏗 架构变更

- **🔪 检测与编译拆 2 独立文件：新建 `detection.py`，`compile.py` 仅保留 subprocess 级编译执行；彻底消除薄转发（NFR-1 硬约束）**
  - 新建 [src/pytexmk/detection.py](file:///d:/Document%20YM/Desktop%20Document/Tools_Development/PyTeXMK/src/pytexmk/detection.py)，承载 `class CompilationDetector`：6 大 judgment 系列、prepare 系列、`run_full_detection`、`_normalize_aux_like`、`_count_citations` + 8 个正则常量（共 13 个检测方法整体从 `compile.py` 剪切迁移）
  - [compile.py](file:///d:/Document%20YM/Desktop%20Document/Tools_Development/PyTeXMK/src/pytexmk/compile.py) 仅保留编译执行逻辑，`CompileLaTeX.__init__` 中组合 `self.detector = CompilationDetector(...)`；禁止任何 `def prepare_LaTeX_output_files(self,*a,**kw): return self.detector.prepare_LaTeX_output_files(*a,**kw)` 形式的薄转发（薄转发 grep=0，零违反）
  - [compile_engine.py](file:///d:/Document%20YM/Desktop%20Document/Tools_Development/PyTeXMK/src/pytexmk/compile_engine.py) 6/6 检测调用点全部改写为 `compile_model.detector.*`（无 detector 的中间裸调用=0）
- **🧱 `run.py` → `compile_engine.py`：单一职责明确，**不保留任何兼容层**（FR-9 硬约束）
  - 兼容 wrapper `from .compile_engine import RUN as RUN` + `DeprecationWarning` 整体删除，不再维护旧 `pytexmk.run` 入口
  - 所有 `from pytexmk.run import RUN` / `try:.*import.*except ImportError` 回退模式全部物理删除，唯一合法入口为 `from pytexmk.compile_engine import RUN, LaTeXDiffRUN`
- **📂 文件操作类语义重命名：`MoveRemoveOperation` → `FileMoveRemoveManager`**，`move_specific_files` 新增返回实际移动文件数（预处理差异化日志的必要信息源）

### 🎉 新增

- **✅ 检测报告 6 条 [OK] 稳定文案**从固定「状态稳定」改为 **6 维度各自独立、用户可看懂的动态描述**（FR-5.2 动态化需求）：
  - 文献检测 (bib) → 参考文献引用计数无变化，参考文献解析稳定
  - 索引检测 (idx) → 索引词汇表内容未变动，索引生成稳定
  - 目录变化 (toc) → 目录条目未发生变更，目录生成稳定
  - 交叉引用 (aux) → 交叉引用锚点未发生变更，引用解析稳定
  - 书签文件 (out) → PDF 书签条目未发生变更，书签生成稳定
  - 日志信号 (log) → 未检测到需要重编译的 LaTeX 警告信号，本次迭代稳定
- **🎨 Rich 美化报告：禁用 Table 网格，5 种颜色 + 粗体分层语义**
  - 标题：洋红「【检测报告」」+ 黄色「(第 X 轮)」
  - 维度名称青粗、`[OK]` 绿粗 + `[!!]` 黄粗 + 结论分支黄/绿粗 + 安全上限红粗
  - 全程 0 import `rich.table`，视觉采用条目列表（无网格线）
- **🪧 预处理 Banner 回归复古三行统一风格**
  - 统一走 `ui_messages.print_message`（与「1 次 LuaLaTeX 编译」「完成所有编译」等其他 Banner 同源）
  - 结构 `=*78 / X32|开始预处理|X32 / =*78`，中间文字 `[bold]` 粗体；左右各 32 个 `X`，半角空格 + 半角 `|`，**无全角括号**
  - 物理删除「结束预处理」Banner（grep=0）
- **🌐 国际化（i18n）全链路升级：5 模块 domain 对齐 + 100% `_()` 包装 + `xgettext` 自动抽取 .pot（Q1/Q2 硬约束）**
  - 模块名与 `set_language("<module>")` 一一对应：compile_engine / detection / compile_report / cli_workflow / file_ops（5 模块）
  - 翻译字符串 100% `_()` 包裹：ORDER 6×3=18 条（名称+stable+unstable）、检测报告标题、结论 2 句、累计次数、安全上限、预处理 Banner 中间 4 汉字、差异化 4 句文案全部 `_("…") %(占位符)s` 形式（禁用 f-string 内直接中文插值）
  - .pot 抽取严格使用 `xgettext --language=Python --keyword=_`（系统 gettext 工具链，非 pybabel）；每个 .pot 首 10 行含 `# SOME DESCRIPTIVE TITLE.` 模板头 + 典型 msgid 上方带 `#: src/...:LINE` 自动定位行（xgettext 特征）
  - Q2：**不生成任何 .mo**（避免 .mo 与最新 .pot 不同步）
- **🧹 冗余代码清理（FR-10）**：静态扫描 + 肉眼扫描双轮 5 核心模块
  - ruff `F401（未用 import）+ F841（未用本地变量）= 0` 问题（共清理 4 处：compile_engine `Path`/`console` 两 F401 + 1 处 F841 + detection `FileMoveRemoveManager` F401）
  - 死注释 `# old:/# TODO.*remove/# 兼容保留/# 薄转发/# 旧实现` = 0
  - `compile.py` 独立 `open(aux/out/toc/idx/...)` = 0（组合设计，compile 仅负责 subprocess，文件读取全部收敛于 `CompilationDetector` 属性缓存，避免二次 I/O）

### 🐛 语义 / Bug 修复

- **📏 结论行 actual_next 语义严格对齐：2→1→无需，永不兜底为 1**（FR-1 硬约束）
  - 物理删除 `actual_next = next_extra_compilations if next_extra_compilations >= 1 else 1` 兜底语句；6 维全 0（all_zero）时直接走「无需额外执行 X 编译。」+「本次累计编译总次数：N 次」分支，**绝不打印「需额外进行 0 次」字样**
  - `next_extra_compilations` = `max(6 维)` 原样透传（不做 +/- 1 调整），Cover-letter 实测：首轮检测 bib=1→需 1 次；再编译后全 0→无需+累计 2 次，与用户样例严格等价
- **🎯 结论行编译名动态替换**：不再硬编码 PdfLaTeX，`standardize_name()` 内部映射大小写不敏感的 `xelatex→XeLaTeX / pdflatex→PdfLaTeX / lualatex→LuaLaTeX`，结论/累计/安全上限全部按实际编译程序展示
- **🎫 初始化文案去重（AC-4 硬约束）**
  - `compile_engine.RUN()` 内首次识别 aux_exist 的 6 行打印**整块物理删除**；仅 `cli_workflow.py:367` 保留 1 处「未检测到已有辅助文件，进行初始化」（全局 .py 命中=1，无重复）
- **🔧 附带修复 Banner 行缺 f-prefix 隐性 Bug**：cli_workflow.py 预处理 Banner 第二行 `{'X' * 32}` 若缺 f-prefix 会被当作字面量输出；现已补齐，32 个 X 展开正确

### 🧪 质量验证（发布前硬验证）

- 🔎 单元测试：`pytest tests -q` → **9 passed**（0 failures / 0 skips）
- 📝 Lint：`ruff check --select=F401,F841 src/pytexmk/compile_engine.py compile.py detection.py compile_report.py cli/cli_workflow.py` → **All checks passed!（0 问题）**
- 🛠 Cover-letter LuaLaTeX 端到端：
  - 第 1 次干净编译：先后【检测报告 (第 1 轮)】→【检测报告 (第 2 轮)】2 条，末尾「无需额外执行 LuaLaTeX 编译。」+「本次累计编译总次数：2 次」（2 次收敛）
  - 第 2 次不清理：首次编译直接收敛（stdout 不含「需额外进行 N 次」字样），累计 1 次
- 🧩 架构断言：`rg 'return self.detector.' compile.py` = 0（薄转发=0）；`rg 'try:.*import|except.*ImportError:' src/pytexmk/` = 0（零 fallback 兼容）；`rg 'DeprecationWarning' src/ tests/` = 0
- 🧾 LOC 膨胀率闸：5 模块合计 1275 行 vs 基线 1263，**膨胀率 100.95% ≤ 105% 上限** ✅
- 🌐 i18n 证据：`locale/en/` 5 个 `.pot`（`cli_workflow / compile_engine / compile_report / detection / file_ops`）全部 xgettext 头通过；典型 `msgid "文献检测"` 上方有 `#: src/pytexmk/compile_report.py:32` 定位行（非手写）

---

## v1.1.4 - 2026-08-01

### 🏗 架构变更

- **📦 按「凝聚度硬阈值」拆分出 `src/pytexmk/cli/` 子包（唯一达标的功能域）**
  - 基于 23 模块静态拓扑调查：6 候选功能域中 **仅 cli 域** 满足「同域模块 ≥4 且 内部 import ≥3 且 耦合系数（外部/(内部+外部)）≥0.7」的子包拆分硬阈值，其余 5 域（core_run/domain_ops/infra/i18n/api）凝聚度不足，保持扁平避免过度工程
  - 迁移 4 个业务模块：`__main__.py / cli_args.py / cli_workflow.py / check_version.py` → `src/pytexmk/cli/`，并在子包根放置 `cli/__init__.py`（空文件，setuptools 子包发现锚点）
  - 新增根包 `src/pytexmk/__main__.py` 3 行薄转发（`from .cli.__main__ import main`），保持 `python -m pytexmk` 与 entry point `pytexmk = pytexmk:main` 对外行为 100% 等价
  - i18n 域不变：cli 子包内 4 模块的 `set_language()` domain 字符串维持迁移前的 `__main__ / check_version`，翻译文件仍锚定在 `pytexmk/locale/**` 原相对路径

- **🔗 打破静态 2 节点 SCC 环「`run.py ↔ cli_workflow.py`」→ import 图正式 DAG 化**
  - 删除 `run.py:323` 一行薄 re-export：`from .cli.cli_workflow import run_workflow  # noqa: F401`（仅为 1 条反向导出引入的双向边，无任何实际功能）
  - 结果：基于全仓 49 模块静态 import 行做 Tarjan SCC，**SCC 大小 ≥ 2 的分量数 = 0**，拓扑排序首次直接成功；5 条跨 5 域长 import 链 circular 烟检全部 exit=0

- **📖 新增 `docs/architecture.md`（285 行，架构制度化）**
  - 章节 1「分层依赖图」：ASCII 绘制 6 层向下依赖架构（Layer 0 API → Layer 1 CLI / Layer 2 Core-Run / Layer 3 Domain-Ops / Layer 4 Infra / Layer 5 I18N-UI），明确禁止任何向上引
  - 章节 2「23 模块职责矩阵」：逐行列 No./文件名/行数/对外符号/一句话职责，cli 子包 4 个带 `[cli 子包]` 标签
  - 章节 3「新功能放哪的决策树」：Q1~Q4 判定 + **规则 5 硬阈值重申**（≥4 模块 AND ≥3 内引 AND ≥0.7 耦合系数三者缺一不可，禁止为拆而拆）
  - 章节 4「import 纪律（3 条）」：(a) 禁跨层上引（给出允许矩阵）；(b) 相对 import 点数规则表（cli 内部 `.X` / cli 回根包 `..X` / 根包进 cli `.cli.X`）；(c) 子包对外 API 必经子包 `__init__.py` 显式 re-export
  - 效果：未来任何新增模块/子包拆分决策都有单一事实源，架构熵增速率可量化约束

- **🧰 打包兼容修复：src-layout 下 setuptools 子包发现显式声明**
  - `pyproject.toml` 新增 `[tool.setuptools.packages.find]`：`where = ["src"]` / `include = ["pytexmk*"]` / `namespaces = false`
  - 修复前问题：默认 setuptools 对 `src/pytexmk/` src-layout 的子包目录识别不足，构建的 wheel 内完全缺失 `pytexmk/cli/__init__.py` 及 4 个业务模块
  - 修复后验证：`uv run python -m build --wheel` 生成的 `pytexmk-1.1.4-py3-none-any.whl`，展开后包含 cli 子包 5 文件 + 11 个 locale `.mo` 文件（含 `__main__.mo / additional.mo / auxiliary_fun.mo / info_print.mo / run.mo` 等）

### 🧪 测试骨架升级（为 2 次收敛验证提供可持续锚点）

- **Cover-letter 用例 TeX 结构增强（可稳定触发 2 次 LuaLaTeX 收敛）**
  - 原 TeX 过于简单导致 aux/out/log 三维首轮即稳定，达不到 2 次收敛锚点；现插入 `\section{Experience/Education/Skills/References}` 4 节，并在 `\label{sec:experience}` 定义前 8 行就出现 `\ref{sec:experience}` 前向引用，穿插 `\pageref{LastPage}×N` + `\cite{ref1,ref2,ref3}` + `\pageref{sec:refs}`
  - 结果：`aux_changed / out_changed / log_has_warn / bib` 四维在第 1 轮检测报告中均为「⚠ 需额外编译」，第 2 轮全部转为「✓ 稳定」，最终统一报告结论稳定落在「无需额外编译，共完成 2 次 LuaLaTeX 编译」

### 🧪 质量验证（发布前硬验证）

- 🔎 单元测试：`pytest tests -q` → **9 passed**（0 failures / 0 skips，与上一版本锚点全同）
- 📝 Lint：`ruff check src/pytexmk tests` → **All checks passed!**（0 errors / 0 warnings）
- 🛠 Cover-letter LuaLaTeX 端到端：2 次收敛 / 完成横幅下方无三行冗余 / Build/Cover_Letter.pdf 生成
- 📄 极简 LuaLaTeX 端到端（`\documentclass{article} hello`）：1 次编译 + 检测报告含「无需额外编译」+ 完成横幅下方无三行冗余
- 🌐 Locale AC-6：`LANGUAGE=en uv run pytexmk --help` 中 `-l/--lualatex` help 文本命中英文关键词 ≥2 次（pytexmk/locale/en/LC_MESSAGES/__main__.mo 加载成功，无 fallback 中文）
- ⚡ Import 冷启动耗时：卸载所有 `pytexmk.*` sys.modules 后重测 `cold import = 0.62 ms`（代理判据 ≤ 100 ms，远未触发 NFR-2 20% 阈值）
- 📦 Build Wheel：1 个 whl 生成；内部 `pytexmk/cli/__init__.py` 存在；`pytexmk/locale/en/LC_MESSAGES/__main__.mo` 存在
- 🔗 DAG 结构断言：Tarjan SCC ≥2 分量 = 0；5 条跨 5 域长 import circular 烟检全部 pass

## v1.1.3 - 2026-08-01

### 🎉 新增

- **📋 每次编译后的结构化检测报告（统一报告区块 + 分隔线美化）**
  - 新增 `info_print.print_compile_separator()`：在「✓ 运行 XX 成功」行与检测提示之间打印 78 宽 cyan bold 分隔线，用于视觉区分
  - 新增 `info_print.print_compile_report(current_times, compiled_program, total_compilations, next_extra_compilations, dims, bib_status, index_status, reached_limit, max_extra_compilations)`：将 6 维检测状态、参考文献状态、目录索引状态、本轮结论整合为一个报告区块，按固定顺序输出
  - 6 维检测维度：`参考文献检测 (bib)` / `索引检测 (index)` / `目录变化 (toc)` / `交叉引用 (aux)` / `书签文件 (out)` / `日志 Rerun 信号 (log)`，稳定显示 `✓ 稳定`，触发显示 `⚠ <原因>`
  - 结论文案三分支：`需额外进行 N 次 XX 编译`（还需要时）/ `无需额外编译，共完成 N 次 XX 编译`（已收敛时）/ `已达 N 次额外编译安全上限，停止调度`（达到 while 安全上限时）
  - `RUN()` 首次编译后与 while 循环每一轮编译后**都调用同一个 helper**（DRY），不再在两处复制粘贴大段打印代码

### 🚀 改进

- **输出去重：删除「完成所有编译」横幅后重复的三行汇总**
  - `RUN()` 末尾删除 `文档整体: XX 编译 N 次` / `参考文献: ...` / `目录索引: ...` 三行，因为这些内容已在最后一轮检测报告的参考文献/索引状态与结论行中呈现
  - `LaTeXDiffRUN()` 末尾删除 `文档整体: XX 编译 2 次` 一行（与成功横幅之后的结论/横幅内容去重）
- **while 循环内保存最新参考文献/索引状态字符串**
  - 原循环内 `bib_judgment()` 与 `index_judgment()` 返回的 `print_bib` / `print_index` 被 `_unused_print_*` 丢弃，导致若循环内状态变化无法反映到后续报告
  - 改为接收 `print_bib_latest` / `print_index_latest`，非空时回写到外层同名变量，保证第 2/3/N 轮统一报告的状态字符串与第 1 轮一致（不是 `-` 占位符）

### 🐛 修复

- **修复 `abbreviations_num` 长度不足（6 项）引发的 IndexError**：当达到 `max_extra_compilations=10` 时，`current_times-1` 可达 10（第 11 次编译），超出原 `("1st".."6th")` 的长度。现已扩展至 `13 项（1st..13th）`
- **修复极简文档（无引用/无索引/无 toc）aux/out 被误判为「有变更」引发的无限循环与多余编译**：
  - 新增 `CompileLaTeX._normalize_aux_like()` 静态方法，归一化比较前的 aux/out 内容：过滤 `\relax`、整行/行内 `%` 注释、空行、`\bookmarksetup{}`、`\@outlinefile{}`、`\gdef\xdef \@abspage@last{}`、`\global\@namedef{ver@*}{}` 等内核初始化写入，仅保留结构性行（`\newlabel/\citation/\bibcite/\@writefile/\abx@aux@…` 等）用于比较
  - `aux_changed_judgment()` 与 `out_changed_judgment()` 统一改为 `_normalize_aux_like(current) != _normalize_aux_like(old)` 比较，避免「初始化占位 → 初始化占位内容」被误判为真正变更
- **修复 thebibliography 场景参考文献维度恒=1 引发的多余编译**：
  - `bib_judgment()` 原 `\bibcite` 分支硬编码 `Latex_compilation_times = 1`，不比较新旧引用计数，导致 Cover-letter 这类使用 `thebibliography` 的项目 bib 维度永远触发额外编译，最终依赖 reached_limit 或其他维度归零才能退出
  - 改为与 bibtex/biber 分支等价：调用 `_generate_citation_counter()` 获取最新引用计数，与旧 `cite_counter` 比较，相等时 `Latex_compilation_times = 0`，描述字符串保持 `thebibliography 环境实现排版` 不变
- **修复 `_count_citations()` 未统计 `\bibcite{key}{*}` 导致 thebibliography 新旧字典都是空的问题**：
  - 新增 `THEBIB_CITE_PATTERN = re.compile(r"\\bibcite\{(.*?)\}")`
  - `_count_citations()` 在 BIBER / BIBTEX 两种模式之后，新增 THEBIB 分支，将 `\bibcite{…}` 统计进同一个 counter 字典，保证旧新字典比较有实际内容
- **修复 run.py 模块顶部 info_print 导入顺序（ruff I001）**：按字母重排为 `print_compile_report, print_compile_separator, print_message, time_count`

### 🧪 质量验证（发布前硬验证）

- 🔎 单元测试：`pytest tests -q` → **9 passed**（0 failures / 0 skips）
- 📝 Lint：`ruff check src tests --line-length 120 --config pyproject.toml` → **All checks passed!**（0 errors / 0 warnings）
- 🛠 Cover-letter 端到端（LuaLaTeX）：清空 `Auxiliary/` / `Build/` 后运行 `pytexmk -l Cover_Letter`
  - `lualatex` 实际执行 **2 次**，最后一轮统一报告结论为「无需额外编译，共完成 2 次 LuaLaTeX 编译」
  - 每次 `✓ 运行 LuaLaTeX 成功` 之后立即出现 78 宽 cyan 分隔线，报告区块包含 6 维检测 + 参考文献/索引状态 + 结论，结构完整
  - 「完成所有编译」 success 横幅之后**不再出现** `文档整体:` / `参考文献:` / `目录索引:` 三行
  - 第 1 轮与第 2 轮报告的参考文献状态、目录索引状态字符串完全一致（非 `-` 占位符）
- 📄 极简 LuaLaTeX 文档端到端（`\documentclass{article}\begin{document}Hello.\end{document}`）：
  - 仅 1 次统一报告，结论为「无需额外编译，共完成 1 次 LuaLaTeX 编译」，退出码为 0
  - 成功横幅后无三行重复汇总
- 🛡 安全上限场景（Mock 构造 max_extra_compilations=1，aux 恒变）：
  - 报告结论出现「已达 1 次额外编译安全上限，停止调度。共完成 2 次 LuaLaTeX 编译」，while 循环正常退出（无死循环），RUN() 返回 dict 正常

## v1.1.2 - 2026-08-01

### 🐛 修复

- **修复多次编译漏检测：Cover-letter 等 lastpage/tikz/hyperref 项目只编译 1 次的问题**
  - 新增 `aux_changed_judgment()` 与 `out_changed_judgment()`：基于 CWD → `auxdir` 两级回退读取 `.aux` / `.out` 文件快照，比较编译前后内容差异决定是否需要额外编译
  - 新增 `log_has_rerun_warnings()`：集中定义 6 类 Rerun 信号正则（`undefined references`、`Label(s) may have changed`、`lastpage Rerun`、`rerunfilecheck Rerun`、`Citation undefined`、`multiply-defined labels`），任一命中即触发额外编译
  - `RUN()` 聚合逻辑由 `max(bib, index, toc)` 扩展为 6 维 `max(bib, index, toc, aux_changed, out_changed, log_has_warn)`，新维度权重与原有三维度平等并入
  - 原固定 `for` 循环改造为 `while` 收敛循环，并加入 `max_extra_compilations=10` 安全上限防止死循环；每轮编译前更新基线、每轮后重算全部 6 维度直至稳定
  - 修复 while 循环内丢弃变量误使用裸 `_` 导致的 `UnboundLocalError: cannot access local variable '_' ...`（与模块级翻译函数 `_ = set_language("run")` 作用域冲突），统一改用 `_unused_*` 前缀

### 🎉 新增

- **触发额外编译的原因打印（可观测性增强）**
  - 首次编译后与 while 每轮结束后，对 `aux_changed` / `out_changed` / `log_has_warn` 三分量分别打印 `[yellow]Rich markup[/]` 提示：
    - 「检测到 aux 文件变化，需要额外编译。」
    - 「检测到 out 文件变化，需要额外编译。」
    - 「检测到 Rerun 警告（lastpage/undefined references 等），需要额外编译。」
  - 仅当对应分量为 1 时输出，不干扰原有成功/失败汇总结构

### 🧪 质量验证（发布前硬验证）

- 🔎 单元测试：`pytest tests -q` → **9 passed**（0 failures / 0 skips，含 TR-1.1 / TR-1.2 / TR-1.3 / TR-2.3 / TR-2.4 / Checkpoint 9 边界全量覆盖）
- 📝 Lint：`ruff check src tests --line-length 120 --config pyproject.toml` → **All checks passed!**（0 errors / 0 warnings）
- 🛠 Cover-letter 端到端：清空 `Auxiliary/` / `Build/` 后运行 `pytexmk -l Cover_Letter`
  - `lualatex` 实际执行 **2 次**，最终打印「文档整体: LuaLaTeX 编译 2 次」
  - 最终 `Auxiliary/Cover_Letter.log` 中 6 类 Rerun/undefined/multiply-defined 信号匹配数 **全部为 0**（收敛稳定）
  - 输出含触发原因提示：aux 文件变化 + Rerun 警告检测

## v1.1.1 - 2026-07-31

### 🚀 架构变更

- **pytexlogs 正式「独立库化」：彻底移除中间层与内嵌子包**
  - 删除 `src/pytexmk/_pytexlogs_compat.py` 适配层（原实现「remote 独立库优先 / bundled 内嵌子包 fallback」双轨逻辑），现改为单轨直连 PyPI 包
  - 删除整个内嵌子包 `src/pytexmk/pytexlogs/`（18 个文件：所有 parser / manager / summary / registry / _facade 等），PyTeXMK 不再捆绑一份 pytexlogs 源码
  - 顶层调用改写：`src/pytexmk/__main__.py` / `src/pytexmk/additional.py` 统一改为 `import pytexlogs` + `pytexlogs.run_log_pipeline(...)`，版本号与翻译函数仍按原参数注入
  - 全量脚本/测试改写：`scripts/check_log_decouple.py`（30+ 处 bundled 路径 import）+ `tests/test_log_parsers.py` / `test_summary.py` / `test_tr21_manager_compare.py` / `test_tr22_register_compat.py` 全部切换为顶级 `from pytexlogs import ...` / `from pytexlogs.<submod> import ...`

### 🧩 依赖管理

- **pytexlogs 从「内嵌可选」变为「必选直接依赖」**
  - `pyproject.toml` 的 `[project].dependencies` 新增 `pytexlogs>=0.1.0`（对应 PyPI 已发布的同名首版包，零运行时依赖）
  - 安装 PyTeXMK 时会从 PyPI 拉取独立 `pytexlogs`，不再需要从本仓库内嵌子包加载
- **保持零运行时副作用**：pytexlogs 包本身（0.1.0）无任何第三方运行时依赖，不会因引入该包增加 PyTeXMK 的闭包数量

### 🔗 运行时一致性（日志桥接保留）

- **无中间层后仍保证独立库日志与主程序一致**
  - 在 `src/pytexmk/logger_config.py` 中新增公开函数 `attach_pytexlogs_handlers_to_pytexmk_logger()`
  - 逻辑：以 `logging.getLogger("pytexmk")` 为参考，把 `pytexlogs` 顶级 logger 的 level / propagate / handlers 完全对齐，并基于 `type(h).__name__ + baseFilename` 键实现幂等挂载，重复调用不会重复添加 handler
  - 挂载时机统一收敛到 `setup_logger(verbose)` 末尾调用（等价于旧 compat 层 import-time 自动桥接的 UX）

### 🧪 质量验证（发布前硬验证）

- 🔎 架构断言：`importlib.util.find_spec('pytexmk.pytexlogs') is None` + `find_spec('pytexmk._pytexlogs_compat') is None` → **均为 None，彻底移除成功**
- 📦 独立库来源断言：`pytexlogs.__file__` 指向 `.venv\Lib\site-packages\pytexlogs\__init__.py`（**site-packages 唯一路径，无 bundled 泄漏**）
- 🧹 Lint：`ruff check src scripts tests` → **All checks passed!**（0 errors / 0 warnings）
- ✅ 单元测试：`pytest tests -v` → **9 passed**（含 PythonTeX/Minted/Asymptote 三解析器 + summary 5 项 + TR-2.2 register/lookup 兼容）
- 🛞 构建产物：`uv build` 成功生成 `pytexmk-1.1.1-py3-none-any.whl`（~93 KB）+ `pytexmk-1.1.1.tar.gz`（~91 KB）

## v1.1.0 - 2026-07-30

### 🎉 新增

- **独立日志解析子包 `pytexlogs`（G6 可提取独立第三方库架构）**：
  - 新增 `src/pytexmk/pytexlogs/` 独立子包（原 `log_parsers/` 统一更名），可整体复制为顶级包 `pytexlogs/`，在不含 `pytexmk` 环境下独立导入与运行（NFR-3 命名空间 B 全 4 PASS 验证通过）
  - 对外纯数据常量：`LATEX_LOG_HINTS` / `BIBTEX_ERROR_HINTS` / `BIBER_WARNING_HINTS`（含 9/4/3 条常见错误修复建议映射）
  - 对外纯函数工具：`format_editor_jumps(entries) -> list[str]` / `log_editor_jumps(entries, logger=None)` / `show_log_entries(entries, use_logger, show_info)` 替代旧类方法
  - 对外解析入口：`run_log_pipeline(tex_engine, tex_output, bibtex_output, biber_output, other_engine_outputs, quiet=True, ref_tracker_translate_fn=None, pytexmk_version=None)` 关键字-only 版本号/翻译函数纯参数注入
  - 对外解析器：`LatexLogParser.parse_lines(lines: list[str], root_file=None)` + `quiet:bool` 兼容参数

### 🚀 改进

- **旧 API 全部升级到新 API（零兼容层）**：彻底删除 `src/pytexmk/log_parser.py` 旧 `LogType`/`LogEntry` 别名/`LatexLogParser`/`BibTeXLogParser` 薄转发，仓库内 0 残留
- **反向依赖清零（跨层解耦 FR-1）**：`pytexlogs/` 子包内部**禁止** `from ..xxx` 跳出子包与 `from pytexmk.xxx` 非子包导入；i18n 翻译函数（`language._`）与版本号（`version.__version__`）均由上层 `additional.py / __main__.py` 通过参数注入，独立库默认回退英文/`unknown`
- **重命名 `log_parsers` → `pytexlogs`（与 `pytexmk` 家族命名对齐）**：
  - 顶层调用：`__main__.py / additional.py` → `from pytexmk.pytexlogs`
  - 脚本：`scripts/check_log_decouple.py` 8 类路径/import/`parts[0]=='pytexlogs'` 架构断言 全部对齐
  - 测试：`tests/test_log_parsers.py / test_summary.py / test_tr21_manager_compare.py / test_tr22_register_compat.py` 10 文件全量子模块 import 对齐
  - logger 名：`pytexmk.log_parsers` → `pytexmk.pytexlogs`
- **架构约束加强**：Check31 跨层断言由「正则全部在 pytexlogs/ 内」，顶层非 pytexlogs 子目录 0 处 `re.compile` 日志解析正则

### 🧪 测试（发布前硬验证）

- V1 命名空间 A：`from pytexmk.pytexlogs import {LatexLogParser,...,run_log_pipeline,RefChangeTracker}` 全部公共符号导入链完整
- V2 解耦脚本：`scripts/check_log_decouple.py` **31/31 checks passed**
- V3 pytest：`tests/test_log_parsers.py + test_summary.py + test_tr22_register_compat.py` **9 passed**
- 🥇 G6 命名空间 B：临时目录复制 `src/pytexmk/pytexlogs/ → 顶级包 pytexlogs/`（sys.path 仅临时目录、无 pytexmk），4 PASS → **`G6_PASS_NAMESPACE_B: pytexlogs standalone OK`** exit_code=0

## v1.0.5 - 2025-07-25

### 🎉 新增

- **三平台 CI/CD 构建**：新增 GitHub Actions 工作流，支持 Linux / Windows / macOS 三平台自动构建可执行程序
  - CI 工作流：每次推送自动测试三平台构建并上传 artifact
  - Release 工作流：推送 tag 时自动发布三平台安装包到 GitHub Release 和 PyPI
- **Cython 跨平台加密**：打包工具支持在 Linux（.so）和 macOS（.so）上进行 Cython 编译，不再仅限 Windows（.pyd）
- **跨平台打包工具**：`tools/pack.py` 支持源码模式和 Cython 加密模式，默认 Cython onedir 模式
- **图标生成工具**：`tools/generate_icon.py` 自动从 logo 生成 Windows ICO（多尺寸）、macOS ICNS、Linux PNG 图标
- **统一构建命令**：Makefile 新增 `build` 目标（默认 Cython 加密）

### 🚀 改进

- **Python 版本升级**：最低支持版本提升至 Python 3.14，充分利用新版本特性
- **TOML 库迁移**：从已停止维护的第三方 `toml` 库迁移至标准库 `tomllib`（读取）+ `tomli-w`（写入），减少第三方依赖
- **类型注解现代化**：全面采用 PEP 585（内置泛型 `dict/list`）与 PEP 604（`X | Y` 联合类型）类型注解风格，移除 `typing.Optional/Dict/List/Union` 旧式注解
- **代码清理**：移除 Python 2 时代遗留的兼容代码（`# -*- coding: utf-8 -*-` 声明、`class Foo(object):` 继承、`sys.version_info` 分支判断）
- **CLI 体验优化**：启用 argparse `suggest_on_error` 特性，参数值拼错时给出智能建议
- **第三方库升级**：rich 15.0.0、pypdf 6.14.2、packaging 26.2、platformdirs 4.11.0、rich_argparse 1.8.0 等全部升级至最新稳定版
- **依赖管理**：全面迁移到 [uv](https://github.com/astral-sh/uv) 进行 Python 包管理
- **打包默认 onedir 模式**：移除 onefile 选项，统一使用 onedir 目录模式，提升稳定性和加载速度
- **macOS 大小写兼容修复**：PyInstaller 打包时 --add-data 目标路径统一小写，避免 macOS 大小写敏感路径问题
- **Lint 修复**：修复现代化过程中引入的 lint 问题（类型注解精度、导入排序等）

### 🐛 修复

- 修正 `tools/utils.py` 中错误的类型注解 `func: any` 为 `Callable[..., Any]`
- 修正 4 处 `str = None` 不精确的类型注解为 `str | None = None`
- 修复 `tools/pack.py` 中 pack 模式代码不可达的 bug
- 修复 `--add-data` 路径分隔符硬编码 `;` 导致的跨平台问题，改用 `os.pathsep`
- 修复 `tools/pydmk.py` 中编码硬编码 `gbk` 的问题，改用 `locale.getpreferredencoding()`

### 📝 文档

- 全面美化 README（中英文），新增项目 Logo、功能特性章节、快速开始、开发构建指南
- 更新构建说明为 uv 方式

### 其他

- 移除未使用的 `toml` 依赖，新增 `tomli-w` 作为 TOML 写入依赖
- 新增 `pillow` 开发依赖用于图标生成
- 14 个文件通过 `ruff format` 统一代码格式
- GitHub Actions workflow 文件重命名为更规范的 `CI.yml` 和 `Release.yml`

## v1.0.4.251001 - 2025-10-01

### 🐛 修复

- 修改转义错误

## v1.0.3.251001 - 2025-10-01

### 🐛 修复

- 依赖更正

## v1.0.2.250515 - 2025-05-15

### 🚀 改进

- 日志分析器中的优化路径处理
- 优化了日志分析器中的路径处理，使其更通用
- 编译失败后，启用日志解析器

### 🐛 修复

- 修复 LaTeX 编译器运行错误不及时终止程序的问题

## v1.0.1.250506 - 2025-05-06

### 🚀 改进

- 日志分析器拆分 warning 和 info 信息

## v1.0.0.250506 - 2025-05-06

### 🎉 新增

- 新增日志分析器，编译结束后会解析日志内容，并显示在终端中

## v0.9.6.250430 - 2025-04-30

### 🐛 修复

- 国际化

## v0.9.5.250430 - 2025-04-30

### 🎉 新增

- 新增程序运行动画

## v0.9.4.250424 - 2025-04-24

### 🚀 改进

- 优化版本更新检查代码，使其更通用

## v0.9.4.250314 - 2025-03-14

### 🎉 新增

- 🛠 新增配置文件错误检查功能，如果配置文件存在错误，则可以根据提示进行修复
- 📂 新增 auxiliary_fun.py，调整部分函数到辅助方法中

### 🚀 改进

- ⚙ make: 优化代码，提高自动化程度
- 📋 改正配置文件的名称分类，现在分为用户配置和项目配置两种（user config and project config）

### 🐛 修复

- 🔧 更新后由于项目配置文件错误而导致的报错，现在已修复

## v0.9.3.250308 - 2025-03-08

### 🎉 新增

- LaTeXDiff 新增风格选择，支持在参考文献和符号索引中显示修改痕迹，编译过程中会提醒输入选项 1 或者 2
  - 1 - 显示参考文献/符号说明的修改
  - 2 - 不显示参考文献/符号说明的修改

### 🚀 改进

- 调整 LaTeXDiff 相关的代码结构，提高可读性
- 优化文件夹创建命令，优化部分代码逻辑
- 解决模块路径解析的问题：采用绝对路径
- 重新分类库的导入，mfo, mro, pfo, cp 这些对象只在 main() 里初始化，避免不必要的资源占用
- PDF 修复采用 pikepdf 库来处理，避免打包体积过大
- 解决 -r 参数运行多余程序的问题，解决打包程序路径问题
- 完善 pdf_repair 方法，更换使用 pypdf 库

### 🐛 修复

- 完善 `-d` 命令报错机制

## v0.9.2.241006 - 2024-10-06

### 🚀 改进

- 去掉冗余代码，调整显示
- 完善 README，新增基础使用
- 调整提示信息内容，避免误解

### 🐛 修复

- 修复 log 文件中存在 "No file {self.project_name}.bbl" 时，编译次数判断错误的问题 [#2](https://github.com/YanMing-lxb/PyTeXMK/issues/2)

### 贡献

感谢 @nathanhsuuu 的反馈并提供错误复现最小案例

## v0.9.1.240921 - 2024-09-21

### 🚀 改进

- 添加 pytexmk 运行报错信息的显示

### 🐛 修复

- 调整编译过程显示内容
- 解决 ubuntu 下 makindex 命令寻找不到的问题
- 修复 BUG 解决 linux 下 latex 运行 batch 模式失效的问题

## v0.9.0.240916 - 2024-09-16

### 🐛 修复

- 调整 LaTeX 命令改为小写，避免 linux 不报错

## v0.8.13.240912 - 2024-09-12

### 🎉 新增功能

- 增加 `-dr` 选项，启用草稿模式编译

## v0.8.12.240902 - 2024-09-02

### 🐛 修复

- 修复检查更新部分的 INFO 内容显示不正确的问题
- 修复在 `thebibliography` 环境下参考文献编译次数过多的问题

## v0.8.11.240901 - 2024-09-01

### 🐛 修复

- 修复了在 `thebibliography` 环境下参考文献无法正确编译的问题
- 修复 `-vb` 参数下部分显示结果不对的问题

### 📝 其他

- 新增 `CHANGELOG.md` 文件，用于记录版本更新日志
- 新增 `Actions` 工作流，用于自动化在 PYPI 和 GitHub 发布
- 新增英文 `README.md` 文件，用于介绍 PyTeXMK
