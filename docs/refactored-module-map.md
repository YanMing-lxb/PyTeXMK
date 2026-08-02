# PyTeXMK 架构重构 V1.2 模块映射文档

> 本文档是 PyTeXMK 模块拆分与重命名（架构重构 V1.2）的辅助维护文档，
> 用于降低未来维护成本。**本文档属于可选辅助文件，不进入源码包。**

---

## 1. 模块映射迁移表（旧 → 新）

根据 `spec.md` Goal 1 ~ Goal 7 的描述，旧模块向新模块的迁移关系如下：

| 旧模块 | 迁入新模块 | 迁移说明 |
|---|---|---|
| `additional.py` | `tex_project.py` | 迁入 `MainFileOperation` 类（主文件检索 / 魔法注释 / 草稿模式） |
| `additional.py` | `file_ops.py` | 迁入 `MoveRemoveOperation` 类（纯文件移动删除） |
| `additional.py` | `subprocess_runner.py` | 迁入 `MySubProcess` 类 + `_format_duration` 函数（剥离领域耦合后的子进程执行，抛 `SubprocessFailedError` 替代硬 exit） |
| `additional.py` | `pdf_tools.py` | 迁入 `PdfFileOperation` 类（PDF 预览相关） |
| `additional.py` | `ui_theme.py` | 迁入 `custom_theme` 常量 + `console` Rich Console 实例（纯常量 / 对象，无翻译调用） |
| `auxiliary_fun.py` | `paths.py` | 迁入 `get_app_path` 函数（应用路径获取） |
| `auxiliary_fun.py` | `lifecycle.py` | 迁入 `exit_pytexmk` 函数（生命周期退出） |
| `info_print.py` | `timing.py` | 迁入 `total_len` 常量 + `get_text_len` + `time_count` + `time_print` 四个符号（计时相关） |
| `info_print.py` | `compile_report.py` | 迁入 `DIVIDER_CHAR` / `DIVIDER_STYLE` / `WARNING_STYLE` / `STABLE_STYLE` / `CONCLUSION_STYLE` + `print_compile_separator` + `print_compile_report`（编译检测报告相关） |
| `info_print.py` | `ui_messages.py` | 迁入 `print_message`（通用横幅） + `magic_comment_desc_table`（CLI 帮助说明表） |
| `__main__.py` | `__main__.py` + `cli_args.py` | CLI 参数解析部分（`CustomArgumentParser` / `CustomHelpFormatter` / `parse_args`）拆到 `cli_args.py`；`__main__.py` 保留 `main()` 骨架与副作用 |
| `compile.py` | `compile.py` + `detection.py` | 6 维检测策略（8 个正则常量 + 10 项检测方法）迁到 `detection.py`；`compile.py` 保留 `CompileLaTeX` 调度职责 |

> 注：旧模块 `additional.py` / `auxiliary_fun.py` / `info_print.py` 三个文件均已在 Task 6 & Task 7 阶段 D 物理删除，不留薄兼容层。

---

## 2. Set-language domain 强制映射表

Locale i18n 域的核心原则：**新模块内部 `_ = set_language("<旧域名>")`，域名必须与迁出的旧模块一致；不得创建新 domain。**
（否则翻译键不匹配 → i18n 翻译回退为英文 → 显示效果改变，违反「显示效果零改变」强约束。）

| 迁出旧模块 | 迁入新模块 | 新模块中强制使用的 `set_language` 域 |
|---|---|---|
| `additional` | `tex_project`, `file_ops`, `subprocess_runner`, `pdf_tools` | `"additional"` |
| `additional` | `ui_theme` | 无需域（无翻译调用） |
| `__main__` | `cli_args` | `"__main__"` |
| `compile` | `detection` | `"compile"` |
| `auxiliary_fun` | `paths`, `lifecycle` | `"auxiliary_fun"` |
| `info_print` | `timing`, `compile_report`, `ui_messages` | `"info_print"` |
| 其他模块 unchanged | — | 保持原值 |

> **Non-Goals 提醒**：`locale/en/LC_MESSAGES/*.mo` 与 `locale/en/*.pot` 的文件名**保持不变**
> （仍为 `additional.mo` / `auxiliary_fun.mo` / `info_print.mo` / `compile.mo` / `__main__.mo` 等）。
> 只要求运行时翻译 domain 正确即可，不做 po/mo 文件重命名。

---

## 3. 最终模块清单（22 个）

Task 7 最终 `ls src/pytexmk/*.py` 结果（22 个 `.py` 文件）：

| No. | 文件名 | 核心职责 | 对应旧来源 |
|---|---|---|---|
| 01 | `__init__.py` | 包导出（`__version__` / `__app_name__`） | `__init__`（Task 5 修复未导出版本号 Bug） |
| 02 | `__main__.py` | 主程序入口骨架（约 80 行） | 旧 `__main__`（Task 2 拆 CLI 后精简） |
| 03 | `check_version.py` | 版本检查（GitHub API + 本地缓存） | unchanged |
| 04 | `cli_args.py` | CLI 参数解析（`CustomArgumentParser` / `CustomHelpFormatter` / `parse_args`） | 从旧 `__main__` 迁出（Task 2） |
| 05 | `compile.py` | 编译调度核心（`CompileLaTeX` 类，收敛循环） | 旧 `compile`（Task 3 拆 detection 后精简） |
| 06 | `compile_report.py` | 编译检测报告打印（6 维检测报告、分隔线） | 从旧 `info_print` 迁出（Task 6） |
| 07 | `config.py` | 配置文件读取与合并（TOML 用户/项目/默认配置） | unchanged |
| 08 | `detection.py` | 6 维检测策略（bib/index/toc/aux/out/log） | 从旧 `compile` 迁出（Task 3） |
| 09 | `file_ops.py` | 纯文件移动删除（`MoveRemoveOperation`） | 从旧 `additional` 迁出（Task 1） |
| 10 | `language.py` | i18n gettext 包装（`set_language`） | unchanged |
| 11 | `latexdiff.py` | LaTeXDiff 差异编译功能 | unchanged（Task 5 修复 Popen 重定向 Bug） |
| 12 | `lifecycle.py` | 生命周期退出（`exit_pytexmk`） | 从旧 `auxiliary_fun` 迁出（Task 4） |
| 13 | `logger_config.py` | 日志配置与初始化 | unchanged |
| 14 | `paths.py` | 应用路径获取（`get_app_path`） | 从旧 `auxiliary_fun` 迁出（Task 4） |
| 15 | `pdf_tools.py` | PDF 预览操作（`PdfFileOperation`） | 从旧 `additional` 迁出（Task 1） |
| 16 | `run.py` | 对外运行函数（`RUN` / `LaTeXDiffRUN`） | unchanged |
| 17 | `subprocess_runner.py` | 子进程执行（`MySubProcess`，抛自定义异常） | 从旧 `additional` 迁出（Task 1） |
| 18 | `tex_project.py` | 主文件检索 / 魔法注释 / 草稿模式（`MainFileOperation`） | 从旧 `additional` 迁出（Task 1） |
| 19 | `timing.py` | 计时统计（`time_count` / `time_print`） | 从旧 `info_print` 迁出（Task 6） |
| 20 | `ui_messages.py` | 通用横幅 + 帮助说明表（`print_message` / `magic_comment_desc_table`） | 从旧 `info_print` 迁出（Task 6） |
| 21 | `ui_theme.py` | Rich 主题与 `console` 实例（`custom_theme`） | 从旧 `additional` 迁出（Task 1） |
| 22 | `version.py` | 版本号常量（`__version__` / `script_name`） | unchanged |

---

## 附：模块依赖健康约束

对应 `spec.md` Goal 6（结构合规）与 NFR-1 / NFR-2 / NFR-3：

1. **无循环依赖**：`import pytexmk.run; import pytexmk.compile; import pytexmk.__main__` 三条长路径不出现 circular import。
2. **500 行上限 + 例外**：除 `detection.py` 允许 ≤ 600 行外，其他所有模块 `len(lines) ≤ 500`。
3. **唯一符号来源**：全库 grep 每个对外类/函数/常量名（`MainFileOperation` / `MoveRemoveOperation` / `MySubProcess` / `PdfFileOperation` / `CustomArgumentParser` / `parse_args` / `get_app_path` / `exit_pytexmk` / `CompileLaTeX` 等）仅出现**一处定义**（兼容层 re-export 不算定义；Task 7 阶段 D 已删除兼容层，故全库唯一）。
