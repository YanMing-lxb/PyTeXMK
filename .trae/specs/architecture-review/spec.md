# PyTeXMK 整体架构审查与优化 Spec

## Why
经过上一轮 code-review-optimization 的微观修复，PyTeXMK 项目已处于良好状态。但 `__main__.py`（~897行）和 `compile.py`（~888行）依然过大，存在职责不清、代码重复、废弃代码未清理等架构层面的问题，需要从宏观视角进行架构优化。

## What Changes
- 拆分 `__main__.py` 为 CLI 解析层（`cli_args.py`）+ 工作流编排层（`workflow.py`），降低单文件复杂度
- 评估 `compile.py` 中 ~400 行 deprecated 代码：setter 方法已移除，bib/index 相关方法因被 `run.py` 固定编译流程调用而保留
- 提取 `suffixes_out`/`suffixes_aux` 等重复常量到 `constants.py`
- 统一 `toolchain.py` 的 Console 实例管理（使用 `get_console()`）
- 评估 `log_analysis.py` 中旧版 `LatexLogParser`：测试中有引用，保留并添加 deprecation 标记
- 定义包级公共 API 接口（`__all__`）

## Impact
- Affected specs: 编译、CLI、工具链、日志分析、PVC
- Affected code: `src/pytexmk/__main__.py`, `src/pytexmk/compile.py`, `src/pytexmk/toolchain.py`, `src/pytexmk/constants.py`, `src/pytexmk/log_analysis.py`, `src/pytexmk/__init__.py`
- 风险等级: **中等** — 涉及核心模块拆分，需充分回归测试

---

## MODIFIED Requirements

### Requirement: CLI 入口与工作流编排分离
`__main__.py` 当前职责过多（参数解析 + 配置合并 + 工作流编排 + 错误处理），应拆分为关注点分离的模块。

#### Scenario: 参数解析独立
- **WHEN** 需要新增 CLI 参数或修改已有参数
- **THEN** 只需修改独立的参数解析模块，不影响工作流编排逻辑

#### Scenario: 工作流编排独立
- **WHEN** 编译、清理、Diff、PVC 等工作流被调用
- **THEN** 各工作流在独立模块中实现，不依赖 argparse 内部结构

### Requirement: 评估 compile.py 中已废弃的旧版兼容代码
`compile.py` 中约 400 行代码已被标记为 deprecated 并用 `warnings.warn` 发出警告。经评估后：

#### Scenario: 已移除的废弃方法
- **WHEN** 独立的 setter 方法（`set_outdir`、`set_auxdir`、`set_non_quiet`、`set_run_count`、`set_timeout`、`set_engine`）、`move_file`、`clean`、`view_log` 无外部引用
- **THEN** 这些方法已移除，对应测试已更新为 kwargs 构造方式

#### Scenario: 保留的废弃方法（被 run.py 调用）
- **WHEN** `run.py` 的固定编译流程（compat mode）仍依赖以下方法：`prepare_LaTeX_output_files`、`bib_judgment`、`compile_bib`、`index_judgment`、`compile_index`、`toc_changed_judgment`、`compile_xdv`、`_generate_citation_counter`、`_index_aux_content_get`、`_index_changed_judgment`、`_count_citations`、`_compat_mode`、`_compile_tex_single_compat`
- **THEN** 这些方法保留不动，`_compat_mode` 路径作为固定编译核心机制继续存在

### Requirement: 提取重复常量到共享模块
`suffixes_out` 和 `suffixes_aux` 列表在 `__main__.py` 和 `watcher.py` 中重复定义，应提取到 `constants.py` 统一管理。

#### Scenario: 添加/修改辅助文件后缀
- **WHEN** 需要新增或修改辅助文件后缀
- **THEN** 只需修改 `constants.py` 一处，所有模块自动同步

### Requirement: 统一 toolchain.py 的 Console 实例
`toolchain.py` 模块级创建了独立的 `Console(legacy_windows=False)`，应使用 `get_console()` 统一管理。

#### Scenario: 多模块 Console 一致性
- **WHEN** 多个模块使用 Console 输出
- **THEN** 所有模块通过 `get_console()` 获取同一实例，保证输出风格一致

### Requirement: 评估并清理旧版 LatexLogParser
`log_analysis.py` 中同时存在新版 `LogAnalysis`（~800行）和旧版 `LatexLogParser`（~300行），应评估旧版是否仍有引用，若无则移除。

#### Scenario: 旧版解析器无引用
- **WHEN** 项目内所有代码均使用 `LogAnalysis` 而非 `LatexLogParser`
- **THEN** 移除 `LatexLogParser` 及关联的旧版正则表达式

#### Scenario: 旧版解析器仍有引用
- **WHEN** 存在对 `LatexLogParser` 的外部引用
- **THEN** 保留 `LatexLogParser` 但添加更明确的 deprecation 标记

---

## ADDED Requirements

### Requirement: 定义包级公共 API
`__init__.py` 当前仅包含 banner 注释和 `main()` 函数，应明确定义对外暴露的公共接口。

#### Scenario: 外部导入
- **WHEN** 第三方代码通过 `from pytexmk import X` 导入
- **THEN** `__init__.py` 通过 `__all__` 明确定义公共 API 列表