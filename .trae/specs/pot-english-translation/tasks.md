# Tasks

- [x] Task 1: 修正已有翻译中的错误条目（8+ 处）
  - [x] 1.1 修正 `__main__.pot`：日志分析失败翻译修正
  - [x] 1.2 修正 `additional.pot`：占位符 `%(args)s` 恢复
  - [x] 1.3 修正 `additional.pot`：`%(size).3f MB` 补全
  - [x] 1.4 修正 `additional.pot`：多余冒号移除
  - [x] 1.5 修正 `check_version.pot`：占位符 `%(args)s` 恢复 + fuzzy 移除
  - [x] 1.6 修正 `compile.pot`：fuzzy 标记移除
  - [x] 1.7 修正 `config.pot` 5 处语义错误
  - [x] 1.8 修正 `latexdiff.pot`：fuzzy + 冒号修正
  - [x] 1.9 修正 `log_analysis.pot`：时态和句号修正
  - [x] 1.10 修正 `run.pot`：占位符名称 + 语法修正

- [x] Task 2: 补全 6 个完全未翻译的 .pot 文件
  - [x] 2.1 `cli_args.pot`（45 条）：全部翻译
  - [x] 2.2 `engine_detect.pot`（16 条）：全部翻译
  - [x] 2.3 `exceptions.pot`（13 条）：全部翻译
  - [x] 2.4 `toolchain.pot`（7 条）：全部翻译
  - [x] 2.5 `watcher.pot`（9 条）：全部翻译
  - [x] 2.6 `workflow.pot`（24 条）：全部翻译

- [x] Task 3: 补全部分未翻译的 .pot 文件
  - [x] 3.1 `__main__.pot`：补全翻译
  - [x] 3.2 `additional.pot`：补全翻译
  - [x] 3.3 `auxiliary_fun.pot`：补全翻译
  - [x] 3.4 `compile.pot`：补全翻译
  - [x] 3.5 `config.pot`：补全翻译
  - [x] 3.6 `latexdiff.pot`：补全翻译
  - [x] 3.7 `log_analysis.pot`：补全翻译

- [x] Task 4: 清理 fuzzy 标记并重新编译 .mo 文件
  - [x] 4.1 移除非 header 条目的 `#, fuzzy` 标记
  - [x] 4.2 运行 `msgfmt` 重新编译所有 .mo 文件（17 个文件全部成功）
  - [x] 4.3 验证 `python-format` 占位符一致性（msgfmt 无报错）

- [x] Task 5: 修复因翻译变更导致的测试失败
  - [x] 5.1 更新 `test_cli.py::test_empty_directory_no_crash`：添加英文断言
  - [x] 5.2 更新 `test_config.py::test_invalid_engine_produces_warning`：添加英文断言
  - [x] 5.3 更新 `test_config.py::test_invalid_timeout_produces_warning`：添加英文断言

- [x] Task 6: 修复标点不一致问题（验证阶段发现）
  - [x] 6.1 `config.pot`：恢复 4 处丢失的尾部冒号（line 69, 73, 99, 103）
  - [x] 6.2 `__main__.pot:69`：修正 `README.html file not found.` 为 `README.html file not found: `（与 msgid 一致）
  - [x] 6.3 `check_version.pot:38`：移除 msgstr 中多余的 `!`
  - [x] 6.4 `compile.pot:230`：移除 msgstr 中多余的 `.`
  - [x] 6.5 重新编译受影响的 .mo 文件
  - [x] 6.6 重新运行单元测试验证无回归

- [x] Task 7: 清理 `__main__.pot` 中 obsolete 条目的 fuzzy 标记
  - [x] 7.1 移除 4 处 obsolete 条目（`#~` 前缀）上的 `#, fuzzy` 标记（line 252, 281, 292, 320）
  - [x] 7.2 重新编译 `__main__.mo`

# Task Dependencies
- Task 1, 2, 3 可并行执行
- Task 4 依赖 Task 1, 2, 3 全部完成
- Task 5 依赖 Task 4（.mo 文件重新编译后暴露的测试适配）
- Task 6, 7 依赖 Task 5（验证阶段发现的问题）
