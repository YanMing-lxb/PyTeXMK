# Tasks

- [x] Task 1: 提取重复常量到 constants.py
  - 将 `__main__.py` 和 `watcher.py` 中重复的 `suffixes_out`、`suffixes_aux` 列表提取到 `src/pytexmk/constants.py`
  - 更新 `__main__.py` 和 `watcher.py` 从 `constants` 导入
  - 验证两个模块的常量值一致后合并

- [x] Task 2: 统一 toolchain.py 的 Console 实例
  - 将 `toolchain.py` 中模块级 `console = Console(legacy_windows=False)` 替换为 `console = get_console(legacy_windows=False)`
  - 移除 `from rich.console import Console` 导入

- [x] Task 3: 评估 compile.py 废弃代码清理范围
  - **结论**: 以下 deprecated 方法均被 `run.py` 的固定编译流程（compat mode）调用，**不可移除**：
    - `prepare_LaTeX_output_files` → `run.py:51`
    - `bib_judgment` → `run.py:70`
    - `compile_bib` → `run.py:80`
    - `index_judgment` → `run.py:85`
    - `compile_index` → `run.py:94`
    - `toc_changed_judgment` → `run.py:101`
    - `compile_xdv` → `run.py:123,171`
    - `_generate_citation_counter`、`_index_aux_content_get`、`_index_changed_judgment`、`_count_citations` 均被上述方法内部调用
  - **已移除**: 独立的 setter 方法（`set_outdir`、`set_auxdir`、`set_non_quiet`、`set_run_count`、`set_timeout`、`set_engine`）、`move_file`、`clean`、`view_log`（这些在上一轮已移除，且无外部引用）
  - **保留**: `_compat_mode` 标志、`_compile_tex_single_compat` 路径、所有 bib/index 相关方法、`warnings`/`shlex` 导入
  - 清理了 compile.py 末尾的多余空行

- [x] Task 4: 评估并清理 LatexLogParser
  - `LatexLogParser` 在 `tests/unit/test_log_analysis.py` 中有引用 → 保留
  - 已添加 deprecation 注释标记（`log_analysis.py:838-841`）
  - 关联的旧版正则表达式保留

- [x] Task 5: 拆分 __main__.py — 提取参数解析
  - 将 `parse_args()`、`CustomArgumentParser`、`CustomHelpFormatter`、`standardize_name`、`build_cli_args`、`is_tty` 提取到 `src/pytexmk/cli_args.py`
  - 更新 `__main__.py` 从 `cli_args` 导入

- [x] Task 6: 拆分 __main__.py — 提取工作流处理函数
  - 将 `handle_clean`、`handle_diff`、`setup_pdf_preview` 提取到 `src/pytexmk/workflow.py`
  - 更新 `__main__.py` 从 `workflow` 导入

- [x] Task 7: 定义包级公共 API
  - 在 `__init__.py` 中添加 `__all__` 列表
  - 导出关键公共类：`CompileLaTeX`、`ConfigParser`、`ToolchainManager`、`LogAnalysis`、`LaTeXDiffTool`、`PvcMode`、`PyTeXMKError`、`main`

- [x] Task 8: 回归验证
  - 运行 `make test`：327 passed, 6 skipped
  - 运行 `make lint`：workflow.py 仅剩 3 个与代码库一致的风格提示，无新增问题
  - 运行 `make build`：wheel + sdist 构建成功（pytexmk-1.1.2）

# Task Dependencies
- Task 1、2、4 可并行执行
- Task 5、6 可并行执行（但需在 Task 1 完成后执行，因提取常量后导入路径变化）
- Task 7 依赖 Task 3、4、5、6（API 导出需在模块稳定后定义）
- Task 8 依赖 Task 1-7