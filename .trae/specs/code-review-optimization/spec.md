# PyTeXMK 项目全面代码审查与优化 Spec

## Why
对 PyTeXMK 项目进行全量代码审查，发现并修复逻辑缺陷、代码质量问题、冗余代码和潜在 bug，提升项目整体健壮性、可维护性和代码质量。

## What Changes
- 修复 `CompileLaTeX` 中遗留的旧版兼容模式与新模式的重复逻辑
- 修复 `latexdiff.py` 中 `generate_diff` 的文件路径检测 bug
- 修复 `log_analysis.py` 中 Biber 检测逻辑不可靠的问题
- 清理 `compile.py` 中未使用的旧方法（bib_judgment, index_judgment 等）
- 统一 Console 实例化，避免多模块重复创建
- 修复 `__main__.py` 中配置合并逻辑的潜在冲突
- 增强智能补编循环的边界保护
- 补充 i18n 翻译覆盖缺失
- 修复 `engine_detect.py` 模块级全局变量问题

## Impact
- Affected specs: 编译、LaTeXDiff、日志分析、配置管理、引擎检测
- Affected code: `src/pytexmk/compile.py`, `src/pytexmk/latexdiff.py`, `src/pytexmk/log_analysis.py`, `src/pytexmk/__main__.py`, `src/pytexmk/engine_detect.py`, `src/pytexmk/config.py`

---

## ADDED Requirements

### Requirement: 编译模块代码清理
系统应当清理 `CompileLaTeX` 类中遗留的旧版兼容模式代码，移除未使用的方法，消除重复逻辑。

#### Scenario: 移除旧版 bib_judgment 和 index_judgment
- **WHEN** 代码审查发现 `bib_judgment`、`index_judgment`、`compile_bib`、`compile_index`、`compile_xdv`、`move_file`、`clean` 等方法与新编译流程 `_compile_tex_full` 无关
- **THEN** 这些方法应标记为 deprecated 或移除，减少代码维护负担

#### Scenario: 合并重复的日志分析调用
- **WHEN** `_analyze_logs` 和 `_analyze_logs_update_state` 包含几乎相同的逻辑
- **THEN** 应合并为一个方法，通过参数控制行为差异

### Requirement: 智能补编循环边界保护
系统应当在智能补编循环中增加总迭代次数上限，防止无限循环。

#### Scenario: 智能补编达到上限
- **WHEN** 智能补编循环中的 `extra_pass_count` 达到上限但仍有未解决问题
- **THEN** 系统应输出警告并停止，而非继续尝试

---

## MODIFIED Requirements

### Requirement: LaTeXDiff 文件路径检测修复
`LaTeXDiffTool.generate_diff` 方法的文件路径检测逻辑应当正确。

#### Scenario: 文件存在但后缀不匹配
- **WHEN** 传入的 `old_file` 路径已存在但后缀不是 `.tex`，且 `new_file` 不存在
- **THEN** 系统不应为 `new_file` 自动添加 `.tex` 后缀，而应直接报错文件不存在

#### Scenario: 文件后缀自动补全
- **WHEN** 传入的文件路径不存在但加上 `.tex` 后缀后存在
- **THEN** 系统应正确补全后缀并继续

### Requirement: Biber 日志检测逻辑修复
`LogAnalysis._parse_blgfile` 的 Biber 检测逻辑应当更可靠。

#### Scenario: 混合日志文件
- **WHEN** `.blg` 文件内容前 5 行不包含 "Biber" 字样但实际是 Biber 日志
- **THEN** 系统应通过检查日志中的特征模式（如 `INFO - `、`WARN - ` 等 Biber 特有格式）来判定

#### Scenario: 纯 BibTeX 日志
- **WHEN** `.blg` 文件是标准的 BibTeX 输出
- **THEN** 系统应正确识别为 BibTeX 并应用对应解析规则

### Requirement: 多行错误消息解析增强
`LogAnalysis._parse_logfile` 应当正确解析跨多行的错误消息。

#### Scenario: 错误消息跨多行
- **WHEN** LaTeX 错误消息跨越多行，且不包含 `l.` 或 `at line` 标识
- **THEN** 系统应正确收集完整错误消息，而非截断

### Requirement: Console 实例统一管理
项目中多处独立创建 `Console` 实例，应当统一管理。

#### Scenario: 多个模块各自创建 Console
- **WHEN** `compile.py`、`__main__.py`、`latexdiff.py`、`log_analysis.py`、`engine_detect.py` 各自创建 `Console()` 实例
- **THEN** 应通过集中式模块提供统一的 Console 实例，避免配置不一致

### Requirement: 配置合并逻辑优化
`__main__.py` 中 `_main_internal` 的配置合并逻辑应当清晰且无冲突。

#### Scenario: 多来源配置优先级
- **WHEN** 同一配置项在 default、config_dict 的 `folder` 节和 `output` 节中均有定义
- **THEN** 系统应使用明确的优先级（CLI > 魔法注释 > output > folder > default），而非重复覆盖

#### Scenario: quiet_mode 和 non_quiet 互转
- **WHEN** 配置中同时存在 `quiet_mode` 和 `non_quiet` 字段
- **THEN** 系统应明确以哪个为准，避免逻辑冲突

### Requirement: 模块级全局变量消除
`engine_detect.py` 中的模块级 `MFO` 全局变量应当移除。

#### Scenario: 测试环境中 MFO 状态污染
- **WHEN** 多个测试用例调用 `detect_document_features` 或 `parse_magic_comments`
- **THEN** 不应依赖模块级全局 `MFO` 实例，应改为函数内按需创建

---

## REMOVED Requirements

### Requirement: CompileLaTeX 旧版位置参数兼容模式
**Reason**: `_parse_init_args` 中兼容旧版位置参数传递的 `_compat_mode` 与新 kwargs 模式功能重复，增加维护复杂度。
**Migration**: 业务代码已全部使用 kwargs 模式，旧版仅保留向后兼容接口 `_compile_tex_single_compat`，可在下个大版本移除。