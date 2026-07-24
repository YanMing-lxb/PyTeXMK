# Tasks

- [x] Task 1: 修复 LaTeXDiff 文件路径检测 bug
  - 修复 `latexdiff.py` 中 `generate_diff` 方法的路径检测逻辑：当 old_file 存在但后缀非 .tex 时不应自动补全，而当文件不存在且加 .tex 后存在时才补全
  - 修复 `compile_diff` 方法中 `os.chdir` 可能导致的副作用，改用 `cwd` 参数传递

- [x] Task 2: 修复 log_analysis.py 中 Biber 检测和错误解析
  - 增强 `_parse_blgfile` 中 Biber 检测：检查日志中是否包含 `INFO - `、`WARN - `、`FATAL - ` 等 Biber 特有模式
  - 修复多行错误消息解析：当错误消息跨行且不包含 `l.` 标识时，确保完整收集错误消息

- [x] Task 3: 清理 compile.py 中未使用的旧方法和重复代码
  - 标记 `bib_judgment`、`index_judgment`、`compile_bib`、`compile_index`、`compile_xdv`、`move_file`、`clean`、`set_*` 等旧方法为 deprecated
  - 合并 `_analyze_logs` 和 `_analyze_logs_update_state` 为单一方法 `_analyze_logs(update_state=True)`
  - 添加智能补编循环的总迭代次数上限警告

- [x] Task 4: 优化 __main__.py 配置合并逻辑
  - 明确配置优先级：CLI > 魔法注释 > output 节 > folder 节 > 默认值
  - 移除 `folder` 和 `output` 两节对同一配置项（outdir/auxdir）的重复覆盖
  - 统一 `quiet_mode` 和 `non_quiet` 的处理逻辑，仅保留 `non_quiet`

- [x] Task 5: 统一 Console 实例管理
  - 在 `src/pytexmk/` 下创建 `console.py` 模块，提供 `get_console()` 函数
  - 修改 `compile.py`、`latexdiff.py`、`log_analysis.py`、`engine_detect.py` 使用统一的 Console 实例
  - 确保 FallbackConsole 兼容无 Rich 环境

- [x] Task 6: 消除 engine_detect.py 模块级全局变量
  - 移除模块级 `MFO = MainFileOperation()` 全局变量
  - 将 `detect_document_features` 和 `parse_magic_comments` 改为函数内按需创建 `MainFileOperation` 实例

- [x] Task 7: 补充 i18n 翻译覆盖
  - 检查 `__main__.py` 中未翻译的硬编码字符串
  - 检查 `compile.py` 中未翻译的 console.print 输出
  - 更新 .pot 模板并编译 .mo 文件

- [x] Task 8: 回归验证
  - 运行 `make test` 确保全部 327 个单元测试通过
  - 运行 `make lint` 确保代码符合规范（ruff 自动修复 309 个问题，剩余 109 个为预存风格/设计决策）
  - 运行 `make build` 确保构建成功（wheel + sdist 均成功）

# Task Dependencies
- Task 5 依赖 Task 1-4（Console 统一后其他模块需同步修改）
- Task 8 依赖 Task 1-7
- Task 1, 2, 3, 4, 6 可并行执行