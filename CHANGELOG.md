<!--
 *  =======================================================================
 *  ·······································································
 *  ·······································································
 *  ····Y88b···d88P················888b·····d888·d8b·······················
 *  ·····Y88b·d88P·················8888b···d8888·Y8P·······················
 *  ······Y88o88P··················88888b·d88888···························
 *  ·······Y888P··8888b···88888b···888Y88888P888·888·88888b·····d88b·······
 *  ········888······"88b·888·"88b·888·Y888P·888·888·888·"88b·d88P"88b·····
 *  ········888···d888888·888··888·888··Y8P··888·888·888··888·888··888·····
 *  ········888··888··888·888··888·888···"···888·888·888··888·Y88b·888·····
 *  ········888··"Y888888·888··888·888·······888·888·888··888··"Y88888·····
 *  ·······························································888·····
 *  ··························································Y8b·d88P·····
 *  ···························································"Y88P"······
 *  ·······································································
 *  =======================================================================
 * 
 *  -----------------------------------------------------------------------
 * Author       : 焱铭
 * Date         : 2026-07-24 22:39:23 +0800
 * LastEditTime : 2026-09-25 23:50:00 +0800
 * Github       : https://github.com/YanMing-lxb/
 * FilePath     : /PyTeXMK/CHANGELOG.md
 * Description  : 
 *  -----------------------------------------------------------------------
 -->

# CHANGELOG

## 未发布 - 2026-11-24 投稿包默认值与计时口径修正

> 依据 2026-11-24 运行时长核查结论与获批改造清单。基线 426 passed，
> 改动后 **427 passed**（删除两条 `--pack-verify` 用例、合并一条 `.bib/.bbl`
> 用例，新增计时口径用例）。本轮未提交、未打 tag。

### 破坏性变更

- 📦 **`-sp` 默认带全部 `.bib`、不带 `.bbl`**：`[submission] include_bbl` 默认
  改为 `false`；期刊明确要求预编译 `.bbl` 时再打开。删除 `--include-bib`
  （`.bib` 现在始终打包），包内说明文件的检查清单会按是否附 `.bbl` 给出不同提示。
- 🧪 **删除 `--pack-verify`**：不再在临时目录试编译，退出码 `8` 一并退役且不复用；
  `9`（报告导出失败）保持不变。需要验证时解压投稿包自行运行
  `pdflatex -interaction=nonstopmode -halt-on-error <主文件>.tex`。

### 修复

- 🚩 **`-dr/--draft` 失效**：`RUN` 与 `LaTeXDiffRUN` 把 `not draft` 当成第二个
  开关传入，`-dr` 反而走「关闭草稿」分支，draft 既没加到 `\documentclass` 上、
  也不写跨进程标记。现把 `draft_model` 收成单一 `enabled` 开关（`False` 只做
  崩溃标记自愈），调用点改用关键字参数，`RUN`/`LaTeXDiffRUN`/`CompileLaTeX`
  的相邻布尔实参同样改为关键字，避免位置错位；补 RUN 级回归用例
  （编译期间必须有 draft、结束后必须摘除）。
- ⏱️ **BibTeX 两轮只显示一轮**：`runtime_dict["bib_<engine>"]` 原先被后一轮覆盖，
  表里的 LaTeX 合计少算一整轮，差额全部落进 “Python 时长”。现在合计键累加，并写
  `bib_bibtex_1/2`、`index_makeindex_1` 明细键供调用次数统计；同一缺陷也覆盖
  `index_*` 与 `bib2gls`。
- 📊 **统计口径**：`Python 运行时长` → `Python 侧（未细分）`；`运行 LaTeX 程序数目`
  → `外部工具调用 N 次（pdflatex×3、bibtex×2、makeindex×1）`；总时长改用
  `WorkflowState.start_perf` 的 `perf_counter` 差值，墙钟只用于展示。
- 🔁 **第 2..N 轮检测补计时**：`prepare_LaTeX_output_files` / `prepare_aux_out_snapshots`
  / `run_full_detection` 每轮都并入 `detect_aux` / `detect_state`，不再“首轮计时、后续免费”。
- 💬 **摘要提示**：`pytexlogs>=0.6.4`，调用 `print_summary(hint_style="brief",
  show_footer=False)` 并把库的 `format_footer` 译后作为整段摘要最后一行；删除
  PyTeXMK 自己拼的「N 个警告、M 个错误；可运行 pytexmk -r」。旧版 0.6.3 仍可运行
  （运行时探测 `format_footer`，仅展示退化，不影响解析）。

### 测试流程

- 🧪 **测试分层**：`tests/` 从平铺拆为 `unit/`（36）、`cli/`（8）、`integration/`（5）、
  `regressions/`（6）；`pyproject.toml` 声明 4 个 marker，`conftest.py` 按父目录自动打标，
  `-m unit` / `-m integration` 可直接选层。
- 🧭 **共享 fixture**：新增 `repo_root` 与 `run_cli`；修复 3 处 `parents[1]` 路径错误，
  其中 2 处此前因 editable 安装指向 site-packages 而"假通过"。
- 🎯 **补盲**：新增 CLI 旗标契约、真实 CLI 冒烟、构建指纹维度、搬移回滚、
  biber/bib2gls quiet、首轮 `tools_pending`、`stage_bib` 去重、`ui_messages`；
  另补 `paths` / `lifecycle` / `tex_source` / `ui_theme` / `cli_early` / `cli_workflow`
  的直测（此前只有间接路径）。为可测性把构建参数字典与首轮判定抽成
  `_build_options()` / `_first_round_stop_reason()`（行为不变）。
- 🏷️ **命名统一**：文件名改为 `test_<被测对象>_<方面>.py`，回归层为
  `test_<YYYY_MM_DD>_<主题>.py`，去掉 `fixes/improvements/deep` 等无信息词；
  合并 `test_cli_report_alias.py` 并删 2 条重复用例，跨层同名 basename 已消除。
- 📚 **索引**：新增 `docs/测试索引与修改指南.md`（55 个文件逐项索引 + 功能变动
  增删改查流程 + 旧名对照），`tests/README.md` 同步命名规则。
- 📈 **结果**：19 条定向变异初测 9 条存活，补测后全部杀死；全量 **605 passed**。
- 📄 审计明细见 `docs/2026-11-24-测试审计与整理.md`。

### 依赖

- 📦 **`pytexlogs>=0.6.4` 已发布到 PyPI**：`uv.lock` 由 0.6.3 同步到 0.6.4
  （`uv sync --locked` 落地、`uv lock --check` 通过），`pytest -q` 427 passed；
  依赖下限与 `diagnostics.py` 的 0.6.3 探测保持现状（探测只影响展示）。

## 未发布 - 2026-11-23 CLI 精简与清理语义恢复（第七轮）

> 依据 `docs/2026-11-23-CLI精简与清理语义恢复计划.md`；基线 447 passed，
> 本轮删除已移除能力的旧测试并新增报告/清理矩阵用例后为 **426 passed**。
> 本轮未提交、未打 tag。

### 破坏性变更

- 🧹 **删除 20+ 个参数/开关（含 14 个长选项）**：`--json`、`--doctor`、`--completion`、`--validate-config`、
  `--pdflatex-check`、`--synctex-check`、`--report [PATH]`、`--fail-on`、`-q/--quiet`、
  `-f/--force`、`-io/--includeonly`、`--sync-subprojects`、`--clean-dry-run`、
  `--native/--no-native`、`--shell-escape/--no-shell-escape`、`--synctex/--no-synctex`、
  `--max-runs`、`--jobname`、`--submit-dir`、`--keep-preamble`、`--no-preflight`。
  这些参数现在按未知参数退出 `2`。
- 🧾 **`-r` 语义恢复**：只读最近一次编译日志，生成
  `Auxiliary/<主文件>.pytexmk-report.json` 与同名 `.md`，不再触发编译，也不在编译
  结束时自动写报告；缺日志退出 `1`，Markdown 导出失败退出 `9`。
- 📝 **人读报告改为 Markdown**：顶部元信息表 + 分级概览表 + 按等级分节；
  每条给出 `file:line`、日志正文、建议和可执行命令，JSON 仍保留为机器可读数据。
- 🧩 **构建/投稿开关下沉配置**：`[build]` 的 native/shell_escape/synctex/
  max_extra_compilations 与新增 `[submission] output_dir/keep_preamble`、
  `[preflight] enabled` 成为唯一入口。
- 🗂️ **`-ls` 直接写回**：列出并更新根配置 `[subprojects]`；根配置缺失时先用
  内置模板自动创建，再写入清单。
- 🔁 **`-i/-iu` 默认覆盖**：删除 `-f` 后重复执行会直接覆盖已有配置；普通运行与
  `-r` 不会自动创建配置文件。

### 修复

- **终端日志折行对齐**：`ERROR` / `WARNING` 等长消息最多按 100 列折行（窄终端
  跟随终端宽度），续行缩进 9 个空格与正文首列对齐，行尾不再补空格。
- **`-ls` 根配置缺失不再空操作**：恢复先用内置模板创建 `.pytexmkrc`、再写入
  `[subprojects]` 的行为；创建失败以配置错误 `4` 退出，不吞掉扫描结果。
- **清理恢复 2×2 矩阵**：`-c` 只清辅助目录；`-C` 再加根目录并删输出；`-ca` 递归
  全项目辅助文件；`-Ca` 递归并在能确定主文件时删输出。`-c/-C` 没有唯一主文件时
  按原设计退出 `1`；`-ca/-Ca` 不再因多个候选主文件提前退出。
- **移除“作者文件”保护清单**：`.bbl`、`.xdv`、`.xdy` 按后缀一并清理，
  `RECURSIVE_CLEAN_JOBNAME_ONLY_SUFFIXES` 与干跑分支删除。
- **编译结束只在有警告/错误时提示报告**：追加一行
  `可运行 pytexmk -r 生成完整报告`，不再写 JSON、不再执行 `--fail-on`。
- **`machine_report` 与 `cli_doctor` / `cli_completion` 删除**：stdout 不再切换，
  `KeyboardInterrupt` 直接以 `130` 退出。

### 回归

- `ruff check --config pyproject.toml src tests`：All checks passed。
- `python -m compileall -q src\pytexmk`：通过。
- `python -m pytest -q tests`：**426 passed**。
- 真机（MiKTeX，XeLaTeX）：`pytexmk -x` 编译成功、终端显示 `2 警告` 并提示 `-r`，
  `Auxiliary/` 中没有报告文件；随后 `pytexmk -r` 生成 JSON 与 Markdown，Markdown
  含 `main.tex:3`、建议与可执行命令。

## 未发布 - 2026-11-23 清理规则修正（第六轮）

> 依据 `docs/2026-11-23-改进实施记录-第六轮.md`；基线 445 passed，本轮结束 447 passed。
> 本轮仍未提交、未打 tag。

### 修复

- 🧹 **四个清理入口统一**：`-c/-C/-ca/-Ca` 都递归清理所有辅助文件；`-c/-C` 不再要求
  唯一主文件，`-ca/-Ca` 保留为旧名。`-C/-Ca` 额外删除 PDF/SyncTeX 输出。
- **不再保留 `.bbl`**：主文件不唯一时，`.bbl` 不再按“可能属于作者”保留；需要留档时
  应提交到版本库或另存。
- `.xdv` 属于通用辅助后缀；主文件不唯一时同样会被清理。
- `.xdy`、`.bak`、`.ltx` 等仍按主干与 jobname 判断归属，避免误删作者手写的样式/
  备份；帮助页与 README 不再在选项说明里列举 `.bbl/.xdv`。

## 未发布 - 2026-11-23 帮助与参数错误收口（第五轮）

> 依据 `docs/2026-11-23-改进实施记录-第五轮.md`；基线 443 passed，本轮结束 445 passed。
> 本轮仍未提交、未打 tag。

### 改进

- 🧾 **argparse 错误也走 JSON**：`--json` 下的未知参数、互斥参数等解析错误，
  stdout 现在给出 `action=argument-error` 的统一载荷（含 `message`/`usage`/
  `exit_code=2`），usage 与人类可读错误仍写 stderr。
- 🖥️ **帮助页固定宽度**：`-h` 固定 96 列，不随超宽终端拉伸；选项左栏统一对齐。
- 🧹 **移除退出码表**：帮助页不再要求用户记 0–8 的退出码，改为“出错时直接说明
  原因与下一步”；`--fail-on` 等选项也不再以退出码作为说明。
- 📝 **魔法注释说明校正**：明确“只扫描每个主文件的前 50 行”，并列出可设置的
  编译引擎、根文件、输出目录、辅助目录；英文翻译同步更新。
- ✂️ 精简大量冗长帮助文案（预览、PDF 修复、清理、子项目等），减少半行断词。

## 未发布 - 2026-11-23 持续优化（第四轮）

> 依据 `docs/2026-11-23-改进实施记录-第四轮.md`；基线 438 passed，本轮结束 443 passed。
> 本轮仍未提交、未打 tag。

### 改进

- 📄 **压平覆盖 import 宏包**：`\import` / `\subimport` / `\inputfrom` /
  `\includefrom` / `\subinputfrom` / `\subincludefrom` 按宏包语义展开；
  `\subfile`、`\inputsection` 等语义不同或自定义的命令保持原样。目标缺失时
  保留原命令，不静默吞掉正文。
- 📦 **早退出 JSON 载荷**：`--completion --json` 把补全脚本放进 `script`，
  `--show-config --json` 带合并后的 `config` 与来源路径，`-ls` /
  `--sync-subprojects` 带 `subprojects` 条目，不再只剩 action/count。
- 📝 修复 playbook 中已不存在的 `docs/python315-api-audit.md` 引用，并在第二轮
  记录中标注 JSON 信封的后续状态。

## 未发布 - 2026-11-23 复审修复（第三轮）

> 依据 `docs/2026-11-23-改进实施记录-第三轮.md`；基线 421 passed，本轮结束 438 passed。
> 本轮未修改任何用户文件，也未提交、未打 tag。

### 修复

- 🧹 **递归清理收口**：`.xml` / `.tmp` 移出 `AUX_SUFFIXES`，`-ca/-Ca` 不再删除
  `data/records.xml`、`notes.tmp`；`.run.xml` 仍按 biber 产物保留。`-ca` 不再要求
  先唯一确定主文件，多主文件/无主文件时只清理通用后缀并保护 `.bbl/.xdy` 等。
- 🧩 **LaTeXDiff 压平边界**：只展开 LaTeX 内建 `\input`/`\include`，命令名后要求边界；
  `\inputsection` 等自定义宏、行内/整行注释、`verbatim`/`Verbatim`/`lstlisting`/`minted`
  与 `\verb` 内容保持原样。差异编译同样消费 `--native/--no-synctex/--pass-arg/--max-runs`。
- 🛡️ **配置校验进入编译路径**：普通编译在读取配置段前统一校验，`build = "oops"` 这类
  段类型错误以退出码 4 结束，不再抛 `AttributeError` traceback；`scrollmode` 恢复为合法取值。
- 📊 **JSON 真实性**：`-c/-C --json` 的 `cleaned` 改为真实删除成功的路径并附 `failed`；
  `--show-config/-ls/-i/--validate-config` 等早退出动作不再写 `action: unknown`；
  `--watch --json` 只在退出时写一条 JSON，`-A --watch` 不再阻塞在第一个子项目。
- 🔎 **扫描降噪**：preflight 与投稿兼容性扫描跳过注释/verbatim 中的 `\input` 与
  `\usepackage`；`tool-pending` 停止原因有独立结论文案。
- 📝 **文档与仓库状态**：模板中 `quiet_mode` 说明与代码/README 对齐；恢复并标注
  `docs/python315-migration.md`；架构文档补当前文件数与 `__init__.py` 真实导出；
  删除 `check_version` 的孤立 `.po/.mo/.pot`；移除失效的 `make all/rst` 目标。

## 未发布 - 2026-11-23 功能审查修复（第二轮）

> 依据 `docs/2026-11-23-功能审查与改进方案.md` 的可复现缺陷逐项修复；
> 完整清单、未做项与验证见 `docs/2026-11-23-改进实施记录.md`。

### 修复

- 🧹 **递归清理不再误删源文件**：`.aux`/`.synctex.gz` 正则加 `$` 锚点；
  `.bbl/.bak/.userbak/.xdy/.ist/.ltx` 在无构建记录时只删 jobname 同名文件，
  `author.xdy` 保留并提示；干跑、执行、JSON 共用同一清单；删除失败进入 `failed`。
- 🛡️ **产物与诊断门禁**：日志缺失/为空/解析失败时 `diagnostics_status.available=false`，
  `--fail-on/--report` 以 `5` 退出；缓存命中要求日志摘要与产物摘要（PDF+SyncTeX）
  同时匹配；旧 PDF、损坏/零页 PDF、搬移失败不再算成功；`auxdir="."` 不再自毁 `.ind`。
- ⏱️ **停止原因可区分**：`--max-runs` 用尽记 `limit`，外部工具产物未被消费记
  `tool-pending`；`converged` 只在真正稳定时为 `true`。
- 🔎 **预检与依赖**：嵌套 `\input`/图片按 TeX 工作目录解析，报真实行号；
  `.bib/.bst/.ist/.xdy` 从 aux/bcf 解析后进入依赖快照，改参考文献必触发重编。
- 🖼️ **预检图片路径**：`\input` 子文件继承主文件声明的 `\graphicspath`，
  子文件自身声明与继承目录宽松合并而非覆盖；修复图片实际存在却报“图片不存在”。
  `\graphicspath{{Pictures/},}` 这类逗号分隔、末项为空的写法也能解析。
- 🧾 **配置校验**：TOML 语法错误不再"校验通过"；`[subprojects]` 类型与
  `glossaries_tool` 枚举校验。
- 🧬 **LaTeXDiff**：压平改用独立临时目录，保留 `\input` 两侧正文，按递归栈判环；
  输出原子替换，失败不毁旧文件；`-pr` 支持只检查或显式文件列表，pypdf 兜底保留书签。
- 🧰 **CLI/批处理**：`-A --json` 只输出一份 JSON 并返回首个失败子项目的退出码；
  文件型别名优先于配置 `default_file`；watch 每轮回到原始目录并监控图片/bib/配置；
  SyncTeX 缺坐标不再崩溃；`--no-shell-escape` 在 MiKTeX 下传 `--disable-write18`。
- 📦 **投稿包**：强制包含主入口 `.tex`，补入项目内全部 `.bib`；原样打包按字节复制，
  不再把 CRLF 归一成 LF。
- 🧾 **进度行更干净**：安静模式的静态提示去掉“（安静模式，实时日志请加 -nq）”，
  只保留 `正在LuaLaTeX…`；`-nq` 仍由 `--help`、配置模板与 20 s 心跳说明。
- 🧭 **失败摘要改为分组版式**：编译失败时改用 PyTeXLogs 的 `[E]` +
  `+-- [分类]` 分组渲染（`print_summary`），保留 `↳` 建议与命令；JSON 计数与
  日志指针不变。
- 🧭 **成功摘要也用同一套分组版式**：`diagnostics.report_summary()` 不再自写
  `! file:line` 紧凑列表，改为 `print_summary(max_entries=3, show_hints=True,
  width=78)`——`==== 警告汇总 ====` 标题、`+-- [分类]` 分组、`↳` 建议与失败摘要
  完全一致，每条编译的输出不再有两套长相。折叠条数由库按「等级 × 类别」分组
  给出；总警告超过 3 条时额外补一行可直接执行的
  `pytexlogs summary <log> --max-entries 0`。`MAX_SUCCESS_WARNINGS` 的语义随之
  变为“每个分组上限”（库的 `max_entries` 口径），排版提示仍只给一行计数。
- ✅ **验证**：`ruff` 全绿、`pytest` 419 通过、`compileall` 退出 0，并完成单项目、
  `--no-native`、批量 JSON、LaTeXDiff 端到端验证。

### 产物与验证契约补齐（同日第三轮）

> 针对上一轮记录里“未实施/报告与现状不一致”之外的剩余 P1/P2 项，逐条以
> 可复现行为为准修复；未做的架构级项仍留在原报告的后续清单。

- 🧷 **明文 SyncTeX 全链路**：`OUT_SUFFIXES` 增加 `.synctex`，归档、缓存校验、
  旧 sidecar 清理与 `-ca` 正则同时识别 `.synctex` / `.synctex.gz`。实测
  `--pass-arg=-synctex=-1` 时 PDF 与明文 sidecar 一起进 `Build/`，JSON
  `synctex_path` 指向真实文件，`--synctex-check` 正向/反向均通过。
- 🛠️ **辅助文件自愈不再误删合法 `.bbl`**：花括号配平跳过未转义 `%` 到行尾的
  TeX 注释；`% template note: { is a brace` 这类模板说明不再被判成截断文件。
- 📦 **`--pack-verify` 始终验证**：不再依赖 `convert_unicode`；关闭 Unicode
  转换后仍会在临时目录真跑 pdflatex，结果写进包内说明。显式请求验证但本机
  没有 pdflatex 时以退出码 `8` 失败，而不是静默给出 `verify_ok=null`。
- 🗜️ **`reproducible=false` 真的生效**：ZIP 条目改用源文件修改时间（1980–2107
  范围内、偶数秒）；开启时仍固定 1980-01-01 并按名称排序，两次打包字节一致。
- 🩺 **`--doctor` 按有效引擎判定**：命令行 `-p/-x/-l` 优先于项目配置的
  `compiled_program`；只有有效引擎缺失才算关键失败，其余引擎降为环境信息，
  JSON 增加 `effective_engine`。
- 🧭 **`--explain` 展示真正会执行的计划**：与编译共用命令行覆盖逻辑
  （native/synctex/interaction/max-runs/includeonly），局部编译显示
  `Build/partial`、`Auxiliary/partial`，最终 PDF 绝对路径单独一行输出；
  `--explain -pv FILE` 不再提前打开阅读器，也不再顺手删除旧 sidecar。
- ✅ **验证**：`ruff` 全绿、`compileall` 退出 0、`pytest` **399 通过**
  （新增 11 例）；真实 MiKTeX 验证明文 SyncTeX 归档与 `--synctex-check`、
  注释型 `.bbl` 保留、`-sp --pack-verify`（`unicode_to_latex=false`）、
  `-p --doctor --json` 与 `--explain --includeonly`。未提交。

### 两项小范围契约收口（同日第四轮）

> 收掉上一轮记录"未改"清单里的前两项：`-ls` 的只读/写回分工，以及子进程
> 输出收尾期限与输出频率耦合。

- 📋 **`-ls` 改为只读**：`-ls` / `--list-subprojects` 只扫描并展示清单，不再
  写回 `.pytexmkrc`，也不会自动创建配置文件；根配置缺失时提示改用显式同步。
  这是对外契约变化，README、`--help` 与英文翻译同步更新。
- 🧷 **新增 `--sync-subprojects`**：显式写回 `[subprojects]` 段；保留仍指向
  真实路径的手写别名、段内注释与原有条目次序，`-A` 不再因为一次同步改变
  编译顺序；路径没变的条目原样保留整行（`alias = "x"` 不会变成
  `"alias" = "x"`），新条目按扫描顺序追加。同一路径已被自动发现时不重复
  保留，避免 `-A` 把同一项目编译两次。
- ⏱️ **子进程收尾不再被输出频率拖住**：每一轮循环（无论队列有没有新行）都先
  `process.poll()`，父进程退出即开始计 `_EOF_GRACE_SECONDS`；孙进程持续写
  stdout 也不能把 2 s 宽限无限推迟。心跳只在进程仍在运行时打印。
- 🔁 **重定向路径统一有界收尾**：`stdout_path` 分支不再用无界
  `communicate()`；stderr 走同一个 `_drain_stream`，静默/持续输出的孙进程都
  按同一宽限期收口；读取队列上限 1024 行，宽限后不会被后续输出撑大。截断
  状态写入 `runner.last_output_truncated`，失败时带进
  `SubprocessFailedError.output_truncated`，真实退出码保持不变。
- 🧪 **回归**：新增 6 例子进程用例（持续 stdout 孙进程、重定向持续 stderr、
  流式静默 stdout、重定向静默 stderr、失败截断标记/退出码、正常命令不误标）；
  子项目侧新增只读 `-ls`、不创建配置、显式同步保序/保原行/追加新条目、
  行尾注释与含等号引号键保留、手写别名优先/同路径去重、表头行尾注释兼容、
  写盘失败返回 False 并由 CLI 以 4 退出（共 11 例）。
- ✅ **验证**：`ruff` 全绿、`compileall` 退出 0、`pytest` **416 通过**；
  真实 CLI 验证 `-ls` 前后 `.pytexmkrc` 哈希一致、`--sync-subprojects` 保留
  `legacy = "legacy"` 在首位并追加 `sub = "sub"`、二次同步字节幂等；中英文
  `--help` 均能看到新选项与对应说明。未提交。

### 2026-11-23 PyTeXLogs 0.6.3 同步：摘要宽度对齐 78 列

> 0.6.3 是「版式可配置 + CJK 显示宽度」的展示层升级，公开签名只多了
> `width` / `summary_width`，PyTeXMK 侧属于调用点对齐，不改诊断语义。

- **依赖**：`pytexlogs>=0.6.3`，`uv.lock` 同步到 0.6.3（`uv lock --check` 通过，22 个包无变化）。
- **摘要宽度对齐**：`print_summary` 新增 `width=` 后，不传会退回库默认 74 列，与 PyTeXMK
  自己 78 列的 `=` 分隔线、`[E]` 横幅错位。`diagnostics._print_failure_groups` 现在显式传
  `width=timing.total_len`（78），`max_entries`/`show_hints` 等既有参数不变。
- **CJK 宽度不重复维护**：0.6.3 内部用 `unicodedata.east_asian_width` 算显示列数，与
  `pytexmk.timing.get_text_len` 完全同口径；`text_len_fn` 继续透传（行为等价，保留本项目的
  单点定义），不再新增第三方宽度函数。
- **版式契约确认（无需改代码）**：0.6.3 恢复旧版 `==== 错误汇总 · N ====` 横幅与
  `+-- [分类] · N ---` 框线，PyTeXMK 的 `[E]`/`+-- [一般编译]`/`↳` 断言继续成立；
  hint 命令加 `$` 前缀与 `_print_entry` 的手写 `$` 一致；`T/F/G/P` 改 dim 灰不影响文本；
  `_MISSING_FILE_RE` 不再排除换行，79 列硬折行拆开的长文件名重新命中
  `missing_file`/`missing_graphic`，`rule_id` 与命令名更准，PyTeXMK 的 JSON `rule_id` 自动受益。
- **未改动**：`run_pipeline` 的 `summary_width` 未启用——PyTeXMK 以 `print_terminal=False`
  关闭库端打印，摘要全部由 `diagnostics` 排版，加一个不生效的参数只会制造误导。
- **验证**：`ruff check --config pyproject.toml src tests` → `All checks passed!`；
  `compileall` 退出 `0`；`pytest -q tests` → **417 passed**（新增 2 例：横幅显示宽度等于
  `total_len`、`print_summary` 收到 `width=78`）；`python -m pytexmk.cli --version`
  → `PyTeXMK 1.2.18`；真实失败日志探针横幅 78 列、hint 悬挂缩进对齐。未提交。

## v1.2.18 - 2026-11-23

> 🎯 一次围绕「CI 可判定、失败可诊断、启动更快」的维护版。

### 🚀 亮点

- 🛡️ **CI 门禁闭环**：预检阻断改为退出码 `5` 并写出阻断项；跳过编译不再绕过 `--fail-on`/`--report`；`--includeonly` 拼错章节名直接以 `1` 拒绝，不再静默产出缺章 PDF。
- 🧬 **编译可靠性**：`-dr` 遇到非 UTF-8 源文件只给可读错误、不改写文件；draft/配置/`.pytexmkrc` 改为原子写；`--no-synctex` 清理旧 `.synctex.gz`，外部命令结束清理 `.pytexmk-tmp`。
- 🎛️ **CLI 调整**：`-r` 从“打开 README”改为默认诊断报告别名（等价 `--report`，不带路径）；移除 `--readme` 与浏览器打开逻辑；`--report [PATH]` 保留自定义路径。
- ⚡ **启动加速**：`python -m pytexmk.cli --version` 在导入 CLI 解析器前直接返回；本机 20 次中位数 `132.6 ms → 52.4 ms`（观察值）。
- 🧯 **安静模式不再能卡死**：`-q` 不再建 rich Live 转圈、编译输出读取加看门狗，终端写被阻塞或残留子进程握管道时会在 20 s 内给出心跳并在 2 s 内收尾，而不是无输出地无限等待。
- 🧹 **清理与文档**：删除测试目录生成物与误提交缓存；README 重构安装、CI、`-r`、国际化命令；移除 README HTML 运行时资源与打包项。
- ✅ **验证**：`ruff` 全绿、`pytest` 全量通过、venv `compileall` 退出 `0`、`PyTeXMK 1.2.18`。未提交。

### 📜 1.2.18 详细记录

### 2026-11-23 修复：安静模式（不加 `-nq`）"卡在编译中"不前进

- **现象**：`pytexmk -l` / `-p` / `-x` 不加 `-nq` 时终端停在"正在编译"不再前进，加 `-nq` 立刻编完。
- **根因一（Live 持锁写终端）**：安静模式走 `console.status()` 的 spinner。rich 的刷新线程每 `1/refresh` 秒进入 `with live._lock` 后 `refresh()`，而 `refresh()` 内部 `console.print(Control())` 是一次真实终端写；`Live.stop()` 同样在 `with self._lock` 里。只要某次终端写被阻塞（Windows 控制台快速编辑模式选中文本、ConPTY 渲染挂起），刷新线程就持锁不还，主线程 `stop()` 无限等锁 —— 表现为零输出、连 Ctrl+C 都不一定回来。最小复现：让一次终端写阻塞 5 s，`with console.status(...)` 退出被拖住 **5.01 s**。`-nq` 完全不建 Live，天然免疫，这也是"加 `-nq` 就立刻编完"的直接原因。
- **根因二（读管道与 `poll()` 的次序）**：旧 `_execute_streaming` 在主线程 `readline()`，`poll()` 只在读到一行之后才被检查。只要 stdout 管道还被残留/派生进程握着（`minted`、`tikz externalize`、`pythontex`、`svg` 这类 `\write18` 调用），TeX 进程已经退出也永远等不到 EOF，而安静模式对此没有任何提示。
- **修法**：
  1. 安静模式不再建 Live：改打一行静态 `正在XeLaTeX…（安静模式，实时日志请加 -nq）`，"看不看得见进度"与"转不转圈"解耦。
  2. 输出读取移到后台线程 + `queue` + 0.25 s 超时轮询：连续 20 s 无输出打一次心跳（带 `-nq` 提示）；子进程退出后 2 s 内管道仍未关闭，则打印"输出管道仍未关闭（可能派生了后台进程），已停止等待"并收尾，`wait()` 也加了超时。
  3. `-q`/`-nq` 只控显示：`-interaction` 不再随安静模式切换，默认恒为 `nonstopmode`（新增 `DEFAULT_INTERACTION` / `effective_interaction()`，`--explain`、构建指纹 `_build_key`、`compile_engine` 的 build options 都走同一函数）；需要 batchmode 只能显式 `--interaction=batchmode`（仍有测试守护）。
- **口径变化**：安静模式不再等于 batchmode。旧行为让"想少看输出"顺手把 TeX 的错误处理也换掉，两件事被绑死；README / README.en / `docs/2026-11-18-CLI命令速查.md` / 两份配置模板的 `interaction` 注释已同步。
- **locale**：手工补 `subprocess_runner` 4 条（静态提示、心跳、管道收尾）与 `cli_args` 2 条改写的 `-q`/`-nq` 帮助，只对这两个 domain 跑 `pybabel compile`。未跑全量 `make pot`/`update`：那会把 22 份 `.po` 全部重排，且 `check_version.po`（src 侧已无该模块）、`diagnostics`（未纳入 locale）这类既有缺口会一起翻出来，与本轮修复无关。
- **验证**：最小项目 quiet **2.17 s** vs `-nq` **2.12 s**（等价）；GUET 学位论文四组交叉 quiet+batchmode 23.5 s / `-nq`+nonstopmode 21.9 s / `-nq`+batchmode 22.3 s / quiet+nonstopmode 22.6 s，安静模式并无变慢路径；新增 `tests/test_quiet_no_live_and_watchdog.py` 8 例（两种模式恒 `nonstopmode`、`status` 被禁用、静态提示含 `-nq`、心跳文案、孙进程握管道 1 s 内收尾）；`ruff check --config pyproject.toml src tests` → `All checks passed!`；`pytest -q tests` → **348 passed**；`compileall` 退出 `0`；`python -m pytexmk.cli --version` → `PyTeXMK 1.2.18`。未提交。

### 2026-11-22 PyTeXLogs 0.6.2 同步：等级口径 / hint 作用域 / 报告实况

- **依赖**：`pytexlogs>=0.6.2`，`uv.lock` 由 0.6.1 升到 0.6.2（`run_pipeline`、`ProjectStateStore`、`hint_for_entry` 签名本身未变，破坏点都在语义层）。
- **等级顺序**：`diagnostics._iter_entries` 不再自带 `{"typesetting": 2, "info": 3}` 表，改用 `pytexlogs.level_from_value(...).severity`。0.6.1 起 `ERROR < WARNING < INFO < TYPESET < FONT < GRAPHIC < PAGE`，旧表把 `TYPESET` 排在 `INFO` 前，与库口径正好相反。
- **hint 作用域**：`hint_for_entry` 增加 0.6.2 的 `tool_name=` 透传（条目所属工具的 `ToolResultReport.tool_name`），Biber 的 `WARN -` 不再命中 LaTeX 警告规则。
- **JSON 定位**：`--json` 的 `issues` 增加 `rule_id`（仅命中规则时出现）。0.6.2 明确该字段是机器消费方的稳定标识，文案改动不影响映射；未命中时保持旧载荷形态。
- **报告实况**：0.6.2 的 `write_report` 失败不再抛异常，而是回传 `None` + `_report_write_error`。`LogSummary` 新增 `report_path` / `report_error`，成功/失败两条收尾都以 `custom_fields["_report_path"]` 为准，失败时打印“未生成（原因）”而不是虚报一个不存在的路径；`--json` 的 `report` 字段只在真实落盘时给出。
- **验证**：`ruff check --config pyproject.toml src tests` → `All checks passed!`；`pytest -q tests` → **328 passed in 3.00s**（新增 7 例：等级顺序 ×2、tool_name 透传、rule_id 有/无、报告路径成功/失败）；`uv lock --check` 通过；`python -m pytexmk.cli --version` → `PyTeXMK 1.2.17`；真实 0.6.2 探针：写盘成功 `report_path=<aux>/report.json` 且文件存在，写入非法路径时 `report_path=None`、`report_error=FileNotFoundError: ...`。未提交。

### 2026-11-22 `pyproject.toml` 清理：去冗余、补打包缺口

- **构建后端**：`requires = ["setuptools"]` 收紧为 `setuptools>=77`。`license = "GPL-3.0-or-later"` 用的是 PEP 639 SPDX 表达式，setuptools<77 不支持该形态，旧下限只是碰巧被本机 84.x 掩盖。
- **资源清单去重**：删除被 `locale/**/*.mo` 完全覆盖的 `locale/en/LC_MESSAGES/*.mo`；删除与包根 `data/*` 条目重复的 `"pytexmk.data"` 子表；删除 `include-package-data = true`（pyproject 配置下即默认值）。
- **补打包缺口**：`--readme` 在非中文系统优先打开 `README.en.html`，但旧清单只发 `README.html`，英文环境实际总回退到中文版；改为 `data/*.html`，两份都进 wheel/sdist。
- **陈旧配置**：删除从未被任何用例使用的 pytest `slow` 标记声明；把“pillow 12.3/13.00 分叉”“未来可扩展”这类历史叙述注释收敛为当前约束（两份 dev 依赖必须一致、由哪个测试守护）。
- **验证**：`uv build --no-build-isolation` 前后 wheel 104 → 105 项，唯一差异为新增 `pytexmk/data/README.en.html`；sdist 同样只多该文件；METADATA 仅 Keywords 增加 `cli`，`License-Expression` / `Requires-Dist` 不变；`uv lock --check` 通过；`ruff check --config pyproject.toml src tests` → `All checks passed!`；`pytest -q tests` → **321 passed in 3.78s**；`python -m pytexmk.cli --version` → `PyTeXMK 1.2.17`。未提交。

### 2026-11-20 第十轮：纯风格清理

- **19 条 `PTH/SIM/PERF/B` 候选清零**：7 处 `try/except/pass` 改 `contextlib.suppress`，2 处嵌套 `if` 合并，3 处 `if/else` 赋值改条件表达式，4 处 `append` 循环改 `extend`/列表推导，测试中的 `os.getcwd()` 改 `Path.cwd()`、`os.symlink` 改 `Path.symlink_to`。
- **行为保持**：捕获类型、列表顺序、异常边界、符号链接方向均不变；`contextlib.suppress(Exception)` 仍不吞 `KeyboardInterrupt`/`SystemExit`。
- **验证**：`ruff check --select PTH,SIM,PERF,B` 与全量 `ruff check` 均 `All checks passed`；`compileall` 通过；定向回归 **103 passed in 1.21s**；全量 319 passed / 2 failed（仅当前 PATH 缺 `xelatex` 的环境失败）。未提交。

### 2026-11-20 第九轮：PEP 758 与 pathlib 现代化

- **PEP 758**：17 处不带 `as` 的多异常处理器改为 `except A, B`；带 `as e` 的处理器保留括号（`except A, B as e` 在 3.15.2 仍不合法）。只改语法，不改变异常捕获集合与控制流。
- **pathlib 现代化**：`file_ops.py`/`pdf_tools.py` 的 `os.replace` 改为 `Path.replace`；`config.py`/`subproject_scanner.py`/`subprocess_runner.py` 的 `open()` 改为 `Path.open()`；`detection.py`/`cli_compile.py`/`cli_config.py`/`cli_workflow.py` 的 `Path(".")` 改为 `Path()`；`latexdiff.check_aux_files()` 改为 `any(...)` 并去掉中间列表。
- **第三方 API 审计**：未发现旧式 `PdfFileReader`/`PdfFileWriter`/`extractText`/`getPage`；当前 `PdfReader`/`PdfWriter.add_page`/`add_metadata` 与 pypdf 7.1.0 匹配；`RichHelpFormatter` 与 rich-argparse 1.8+、`ProjectStateStore`/`run_pipeline`/`hint_for_entry` 与 pytexlogs 0.6.1 匹配，不做无证据的 API 替换。
- **验证**：`ruff check --config pyproject.toml src tests` → `All checks passed!`；`compileall` 通过；当前 PowerShell 的 PATH 未含 MiKTeX，完整测试 319 passed / 2 failed，两个失败均在 `shutil.which("xelatex")` 为空的引擎发现处，非本轮代码回归。使用完整 TeX PATH 的历史基线为 321 passed。未提交。

### 2026-11-19 第八轮：五项缺口闭环与 native biber 修复

- **惰性导入启用**：`_launcher.py` 在 `--version` 快速路径之后启用 `sys.set_lazy_imports("all")`；本机 `-h` 中位数由直接 CLI 的 138.7 ms 降到 129.2 ms（20 次），冻结包 `--version`/`-h`/真实编译均通过。`--version` 快速路径未改变。
- **3.15 API 闭环**：`Path.copy`、`Path.move`、`Path.walk` 等采用；`Path.info` 经探针确认是缓存快照且 `exists` 为方法，明确否决并回退到 `exists()`；`uuid7` 无运行时场景不采用。新增 `docs/python315-api-audit.md`。
- **D/E 清零**：`_apply_config_file`、`build_pack`/`_build_manifest`、`bib_judgment`、`run_command`、`discover_subprojects`、`_compile` 完成拆分；`radon cc -n D` 无输出，最高 C(20)。
- **native biber 真机修复**：native 构建的 `.bcf` 在 auxdir，旧命令 `--input-directory .` 导致真实 biber exit 5；改为指向 auxdir 后冻结包端到端 exit 0，`.bbl` 与 PDF 正常，新增 `test_native_biber_reads_control_file_from_auxdir`。
- **验证**：全量 **321 passed in 4.27s**（新增 1 例）；`ruff All checks passed`；PyInstaller onedir 13.15 s、`pytexmk.exe` 7.33 MB；冻结简单 article 与 `biblatex+biber` 均 exit 0。迁移文档已校准为当前基线，七轮复盘的五项缺口已闭环。未提交。

### 2026-11-19 第七轮持续优化：PDF 边界、`.fls` 去重、流式 I/O

- **正确性修复**：`source_snapshot` 不再把 `.pdf` 一律当易变产物跳过；主输出 PDF 由 `_iter_source_files()` 按根目录路径身份排除，`\includegraphics{fig.pdf}` 修改后会触发重编。`pdf_tools._referenced_pdfs()` 增加项目根约束，`-pr` 不再把项目外共享 PDF 纳入原地修复。两处均补回归测试。
- **去重**：新增 `pytexmk/fls.py` 的 `iter_fls_inputs()`，`compile_engine`、`submission`、`pdf_tools` 三份 `.fls` INPUT 解析统一；`file_ops.iter_matched_files()` 统一 `-ca/-Ca` 干跑与真删的遍历/排除规则；submission 的 fallback 后缀与 `.fls` 忽略集改由 `layout` 派生，并统一目录排除语义。
- **流式 I/O**：`build_state._digest_file()` 与 submission zip 摘要改用 `hashlib.file_digest()`；zip 写入改为 `ZipFile.open()` + `copyfileobj()`，不再逐文件 `read_bytes()`；`_same_bytes()` 改用 `filecmp.cmp(shallow=False)`。
- **规则单一真相**：detection 的 3 条永久 rerun 正则预编译后同时供 `RERUN_LOG_PATTERNS` 与 `residual_warnings()` 使用，消除 `re.search` 字面量重写。
- **3.15 收尾**：`compile_engine` 两处 `Path().resolve()` → `Path.cwd()`；删除测试中 2 处已无作用的 `from __future__ import annotations`。惰性导入做过全量测试与 3 次粗测，因真实入口收益不稳定且冻结包未验证，本轮未启用。
- **回归**：全量 **320 passed**，`ruff All checks passed`；radon ≥C 由 43 降至 42，最高仍为 `_apply_config_file E(34)`。未提交。

### 2026-11-19 构建期翻译与语言探测缓存

- **构建期翻译**：`Makefile` 的 `build` 依赖 `mo`，`whl: clean mo`；改 `.po` 后构建会先重编 `.mo`，避免 wheel/onedir 打进旧译文。新增 `.PHONY` 列表，防止 `make build` 与 PyInstaller 的 `build/` 目录同名而被时间戳误判。
- **翻译发布质量**：`tools/lang_tool.py` 的 `mo()` 移除 `pybabel compile --use-fuzzy`；fuzzy 条目默认不进入 `.mo`，避免未审校译文发布。
- **语言探测缓存**：`language.get_locale_lang()` 加 `@functools.cache`；22 个 domain 首次 `set_language()` 时只解析一次环境变量与 `locale.setlocale`，不再每域一次。
- **回归**：新增 `tests/test_language_cache.py`；全量 **309 passed**，`ruff All checks passed`；`make -n whl` 为 `clean → mo → uv build`，`make -n build` 为 `mo → pack`。

### 2026-11-19 移除自动更新检查（CLI 默认零联网）

- **删除** `src/pytexmk/cli/check_version.py`（`UpdateChecker`、GitHub API 查询、缓存读写、安装渠道探测与升级文案），以及 `cli/__main__.py`、`cli/cli_args.py`、`cli/cli_compile.py`、`__init__.py` 中的全部引用。
- **行为变化**：`-h/--help`、正常编译收尾、`--version` 都不再发起任何网络请求；帮助页只打印用法与魔法注释表。`PYTEXMK_NO_UPDATE_CHECK` 随功能一起失效（不再需要）。
- **启动开销**：`-h` 由冷缓存 **1395 ms**（含 GitHub 查询）降到本机 **135–152 ms**；`--version` 新增 `pytexmk._launcher` 快速路径（在导入 rich/argparse 前直接输出），本机 5 次 **46–50 ms**（原约 145 ms）；`-X importtime` 不再出现 `urllib/http.client/packaging/platformdirs/tomli_w`。
- **依赖收敛**：core dependencies 移除 `packaging`、`platformdirs`、`tomli-w`；`packaging` 仅测试使用，移入 dev 依赖两份表；`uv lock --offline` 同步移除 `platformdirs`、`tomli-w` 两个锁定包；`tools/pack.py` 删除 `--hidden-import=tomli_w`。
- **翻译目录**：删除 `locale/en/LC_MESSAGES/check_version.po/.mo` 与 `locale/templates/check_version.pot`（域已不存在）。
- **回归**：`308 passed`（移除 1 个更新检查用例，新增 2 个 `--version` 快速路径用例）；`ruff All checks passed`；`--version`、`-h`、`--completion bash` 实跑通过。

### 2026-11-19 第三轮审查整改：常量收拢、计时契约与 3.15 现代化

- **常量单一真相**：新增 `pytexmk/layout.py`，集中 `OUT/AUX/VOLATILE/SOURCE/DEPENDENCY/INDEX/DIFF` 后缀与 `EXCLUDED/GENERATED/CLEAN_EXCLUDED/WATCH_SKIP` 目录集；`cli_state`、`build_state`、`aux_repair`、`compile_engine`、`cli_compile`、`cli_latexdiff`、`file_ops`、`cli_watch`、`subproject_scanner` 全部改为只读引用。顺带修掉 `build_state` 的裸 `.gz` 与缺失的 glossary 组后缀（`D10`）。
- **计时与 `--json`**：`runtime_dict` 的键统一为稳定 ASCII slug（`latex_1`、`detect_aux`、`bib_biber`…），显示名在 `time_print()` 里按语言翻译，`--json` 的 `timings` 不再随 locale 漂移（`D5`）；`time_print()` 不再原地把字典值改写成字符串，`machine_report` 始终读到数值（`D2`）。
- **行为修复**：`--json` 未预期异常也会补发可解析载荷（`D1`）；`-ca/-Ca --dry-run` 与真实删除共用同一份排除目录（`D3`）；`detection._read_aux_like` 首个候选不可读时继续尝试下一个（`D6`）；配置校验拒绝 `bool` 冒充数字（`D9`）；`move_specific_files` 区分"源目录缺失"与"目标目录缺失"（`D12`）；删除 `tex_project` 永不触发的 `except re.error`（`D13`）；`-r` 用 `as_uri()` 并检查浏览器打开结果（`D11`）。
- **启动与开销**：`--version` 不再打印魔法注释表/触发联网（只有 `-h` 才做），`urllib/packaging/platformdirs/tomli_w` 全部下沉到使用处，`UpdateChecker` 的缓存路径改为惰性属性；`--version` 墙钟由基线 235 ms 降到约 145 ms（本机 5 次取样）。`runtime_env.is_dir_writable` 按路径缓存探针结果，一次构建不再逐条命令写删探针文件。
- **3.15 现代化**：删除 7 处 `from __future__ import annotations`；修正误标 PEP 758 的注释；`cli_workflow` 的批量编译改用 `contextlib.chdir()` 保证异常路径也回到原 cwd；`timing` 用 `math.ceil` + `itertools.zip_longest` 取代手写折行与 ceil；`get_text_len` 改用 `unicodedata.east_asian_width`。
- **去重与小重构**：`set_language` 加 `@functools.cache`（cli 侧 7 个模块共用域时不再重复 `setlocale` + `.mo` stat）；`check_version` 显式导入 `urllib.error`、`lstrip("v")` → `removeprefix("v")`；`subproject_scanner` 用 `Path(item).name` 归一化 exclude 并对含分隔符条目告警；`WorkflowState.refresh_file_lists()` 统一输出/辅助清单；`submission.build_pack` 拆出 `_accumulate_remaining / _read_rounds / _build_manifest / _write_zip`，复杂度由 radon `F(58)` 降到 `D(26)`。
- **回归**：`.venv` 全量 **307 passed**（4.4 s），`ruff check --config pyproject.toml src tests` 为 `All checks passed`；`python -m pytexmk --version` 与空目录 `--json` 均实跑通过。
- **本轮未做（已记录设计与风险）**：`-d` 改 `nargs=2`（会破坏三条既有语义，保持现状）；`build_parser` 434 行拆分（仅影响可读性，收益/风险比不足）；`_apply_config_file` 表驱动与投稿文案整句模板化（涉及 `.po/.mo` 同步）；13 个文件的 ASCII banner 迁移。

### 2026-11-19 系统临时目录不可写时的编译兜底

- **现象**：`pytexmk -fr -vb` 在第一步就失败，`Auxiliary\main.log` 固定截断在 `[1`（10206 字节、没有 `Output written on ...`），只剩 0 字节的 `main.synctex(busy)`，没有任何 LaTeX 错误条目；把 `TEMP`/`TMP` 指到项目内目录后，同一条命令 0.8s 通过并正常产出 PDF。
- **根因**：该环境下 Python 进程（以及它拉起的 TeX 工具）写不了 `%TEMP%`，xelatex 在 shipout 阶段被杀掉，日志因此只写到第一页标记；xindy 同样因为临时文件建不出来报 `Win32 error 267`。这不是 PyTeXMK 改了环境变量——`child_env()` 从不碰 `TEMP/TMP/TMPDIR`，是外部程序的默认落点本身不可用。
- **改动**：`runtime_env.py` 新增 `ensure_writable_temp()`（用探针文件实测 `TEMP` 可写，不可写就把 `TEMP/TMP/TMPDIR` 一起指向调用方给的兜底目录，兜底目录建不出来时保持原环境、不影响编译）；`MySubProcess.run_command` 在 `child_env()` 之后调用它，兜底目录为本次运行的 `run_cwd/.pytexmk-tmp`，改写时打一条 `WARNING 系统临时目录不可写，本次编译改用 ...`。
- **回归**：`tests/test_runtime_env.py` 新增 3 例（可写时原样返回、不可写时三个变量一起切换且兜底目录被创建、兜底目录不可用时放弃改写）；全量 **302 passed / 1 skipped**，ruff `All checks passed`。

### 2026-11-19 xindy 启动失败的两条重试路径（启动器日志 / 267）

- **现象**：`TEMP` 修好之后，`\usepackage[xindy]{glossaries}` 走到索引一步仍失败，报 `log4cxx ... 720005(拒绝访问)` + `Sorry, but xindy did not succeed.`，`.gls` 不产出。
- **根因**：MiKTeX 的 `xindy.exe` 只是启动器，启动时要先写 `<texmfs>/data/miktex/log/xindy.log`；该路径不可写时启动器直接放弃（**xindy 内核根本没被执行**）。xelatex 遇到同一问题只记一条告警照常编译，所以这条只在 xindy 上暴露。
- **改动**：`compile.py` 新增 `xindy_perl_command()`（从 `xindy.exe` 的位置推导 `scripts/xindy/xindy.pl`，用系统 `perl` 直调，绕开启动器的日志前置动作）；`_retry_xindy()` 统一处理两类启动期失败——`720005`/`log4cxx` 走 perl 形态、`267`/`ERROR_DIRECTORY` 走绝对参数形态，两者都在「原目录 + 兜底目录」里逐个重试，且只对 `is_dir_writable()` 为真的目录尝试。非启动期错误（`.xdy` 内容错、输入缺失）仍然不重试。
- **回归**：`tests/test_xindy_fallback.py` 增至 9 例（新增 720005 走 perl、`xindy_perl_command` 的路径推导与缺 perl 返回 None）；全量 **306 passed / 1 skipped**，ruff `All checks passed`。
- **产物级验证**：索引矩阵 7 例全部 `exit 0`，PDF 文本均检出索引内容——`a_makeidx`（`Index`：alpha/beta/delta/gamma）、`b_nomencl`（`Nomenclature`：α/β）、`c_imakeidx`（`Subject Index`）、`d_glossaries`（makeindex 后端，`Glossary` + `Acronyms`）、`e_ctex_nomencl`（中文术语）、`f_imakeidx_named`（`Subject Index` + `Author Index` 双索引）、`g_xindy`（`Glossary`：`Alpha first letter. 1 / Beta second letter. 1`）。xindy 一例在项目辅助目录报 267 后自动改到 `C:\WINDOWS\Temp` 重试成功（0.55s），`Auxiliary\main.gls` 2190 字节。
- **环境备注**：本次故障的最后一环是**进程完整性级别**——项目目录内的 `.venv` 原先带低完整性强制标签，其 `python.exe` 以 `Low Mandatory Level` 运行，xelatex/xindy 因此写不了 `%TEMP%`、`C:\Windows\Temp` 与 MiKTeX 数据目录。已由管理员执行 `icacls ... /setintegritylevel "(OI)(CI)Medium"` 修复，venv 内的 python 恢复 `Medium`，上述矩阵即在修复后的 venv 上复跑。

### 2026-11-18 xindy 启动脚本路径兜底（glossaries 的 xindy 后端）

- **现象**：`\usepackage[xindy]{glossaries}` 项目在项目目录里编译时，`glossaries (main, xindy)` 一条必定失败，输出 `*** - Win32 error 267 (ERROR_DIRECTORY)`。实测同一份 `.glo`/`.xdy`、同一组参数，在 `C:\Windows\Temp` 下可以正常产出 `.gls`，说明不是 xindy 二进制损坏，也不是命令拼装错误。
- **根因**：MiKTeX 的 `xindy.pl` 在 Windows 上把 xindy 表达式写到**当前目录**的临时文件，再交给 `xindy-lisp.exe` 载入；部分目录（项目目录、含空格/深层路径、含 `.tmp` 段）在载入这一步返回 267，换目录就恢复正常。
- **改动**：`compile.py` 新增 `is_xindy_command()` / `xindy_fallback_workdirs()` / `absolutize_xindy_tokens()`；`compile_index()` 首次执行失败且命令是 `xindy`/`texindy`、输出里出现 `267` / `ERROR_DIRECTORY` 时，按候选目录重试——先 `%TEMP%\pytexmk-xindy`，再 `%SystemRoot%\Temp`，重试时把 `-M/-t/-o/-x/-i/-s` 与输入文件全部转成绝对路径，产物仍落在项目辅助目录。`makeindex` / `bib2gls` 等其它工具不进入这条重试；真正的样式/输入错误（非 267）也不重试，避免把原始报错刷掉。
- **回归**：新增 `tests/test_xindy_fallback.py`（7 例：工具名识别、参数绝对化保留 `-L/-I` 取值、输入缺失不伪造路径、非 Windows 不启用、267 失败后重试一次且 cwd 正确、makeindex 不重试、非 267 的 xindy 错误不重试）；全量 **299 passed / 1 skipped**，ruff `All checks passed`。

### 2026-11-18 第二轮全仓复审修复（latexdiff / bib2gls / 清理安全）

- **latexdiff 不再被 stderr 污染（P1）**：`MySubProcess.run_command` 的重定向分支原来写死 `stderr=subprocess.STDOUT`，latexdiff 的告警（MiKTeX 的 log4cxx"数据目录不可写"每次必报）被并进 `LaTeXDiff.tex`，xelatex 必然报 `Missing \begin{document}`（`--diff-style 1/2` 全部失败，退出码 5）。现在 stderr 走独立管道、只进 debug 日志与失败异常，生成稿只含 latexdiff 的 stdout。
- **LaTeXDiffRUN 不再对不存在的 `.xdv` 调 dvipdfmx（P2）**：`RUN` 有 `XeLaTeX and not native` 守卫，`LaTeXDiffRUN` 漏了 `not native`；native 构建下 xelatex 直接产 PDF，dvipdfmx 拿 `Auxiliary\LaTeXDiff.xdv` 失败并以退出码 5 结束。两处判断统一收进 `_run_xdv_if_needed()`，避免再次各写一遍。
- **`-d/-dc` 在未编译项目上不再崩（P2）**：`move_matched_files` 在源目录不存在时抛 `FileNotFoundError`，被 `time_count` 包成"执行函数 {'move_matched_files'} 时出错"。现在源目录缺失返回 0（`finally` 里的反向搬移同样受益）。
- **`-dc` 产物归档到输出目录**：`cli_latexdiff` 原来只从项目根目录搬 PDF，native 构建把 PDF 留在辅助目录，结果"编译成功但 `Build/` 里没有 `LaTeXDiff.pdf`"。现改为与主流程同口径（native 从 auxdir、非 native 从根目录）。
- **bib2gls 真正被调用（P1，含识别缺口）**：`_run_bib_if_needed` 读的是 `DetectionResult` 上并不存在的 `bib2gls_mode`（`getattr(..., False)` 恒为假），且 `bib_judgment` 把 bib2gls 识别嵌在 biber 分支里——纯 `glossaries-extra` record 项目只写 `\glsxtr@record`、不写 `\abx@aux@refcontext`，于是既不跑索引工具、也不跑 bib2gls，术语表静默为空。现在识别与 biber 解耦（`.aux` 的 `\glsxtr@record` 或 `.bcf` 的 `<bcf:glossary`），纯 bib2gls 项目返回 2 轮额外 LaTeX，引擎读 `detector.bib2gls_mode` 并调用 `bib2gls`。真机验证：`\gls{alpha}` 从 `??` 变为 `Alpha`，术语表条目与描述正常排出。
- **用户手写 `.ist` / `.xdy` 不再被静默删除（P2）**：`SUFFIXES_AUX` 移除 `.ist`（makeindex 的样式文件是用户输入，`-c/-C` 不再连带删除）；`_sweep_stale_root_aux` 对 `.xdy` 这类"既可能由 makeglossaries 生成、也可能手写"的后缀，只在根目录副本与 auxdir 内容完全一致时才删，不同则保留并提示。
- **SyncTeX 缺产物提示改用结构化标记（P3）**：`SyncTeXReport.missing_artifact`（`pdf`/`synctex`/`tex`）替代 `any("不存在" in error ...)` 的中文字面量匹配，`LANGUAGE=en` 下也能给出"加 `-fr` 重编"的正确提示。
- **`[submission]` 配置接通、`[index]` 死键清除（P3）**：`unicode_to_latex / include_bbl / reproducible` 逐键接到 `WorkflowState` 并传给 `build_pack`（此前 `convert_unicode/include_bbl` 硬编码 True，配置无效）；`[index] input_suffix/output_suffix` 从 `DEFAULT_CONFIG` 与两份模板删除（后缀由 detection 注册表按索引包决定），两份模板补上 `[submission]` 段示例。
- **死代码与重复收敛**：删除 `build_state._digest_text`、`detection.log_has_rerun_warnings`、`subproject_scanner.DEFAULT_EXCLUDE_FILES`/`DEFAULT_EXCLUDE_FILE_SUFFIXES`；`detection` 的索引摘要循环抽成 `_update_index_digest()`（`index_signature` 与 `state_fingerprint` 共用）；`diagnostics` 里"PyTeXLogs 0.5"的陈旧注释改为 `>=0.6.1`；RUN 与 LaTeXDiffRUN 的 xdv 判断合并。
- **回归**：新增 `tests/test_review2_fixes.py`（12 例，覆盖上述 R1–R7）；全量 **292 passed / 1 skipped**（skip 仍是 Windows 无权建符号链接），ruff `All checks passed`。

### 2026-11-18 索引编译适配（多索引包 + 多命名索引）

- **命名索引**：`IndexSpec` 增加 `stem`（`None` 表示 jobname）与 `in_name()/out_name()`；`_discover_index_stems(auxdir)` 扫描 CWD + 辅助目录的全部 `*.idx`，`imakeidx` 的 `\makeindex[name=author]` 现在会跑 `makeindex author.idx`，时长表里显示为 `makeidx (author)`。此前只有 jobname 一个主干，命名索引从不调度，`\printindex[author]` 长期空白。
- **执行目录**：`compile_index` 删除按 jobname 前缀猜路径的 `_resolve_index_token`，native 构建改为在辅助目录里执行索引工具（命令写相对该目录的文件名），non-native 仍在项目根目录。
- **定位权威**：`CompilationDetector` 增加 `native` 标志，`_ordered_candidates()` 决定 auxdir 优先还是 CWD 优先；`_locate` / `_locate_named` / `_candidate_paths` 统一走它。修掉"切过 `--no-native` 后根目录同名 `author.idx` 遮蔽辅助目录新文件、命名索引永不重跑"。
- **辅助文件归位**：`SUFFIXES_AUX` 补 `.glg .alg .acn .acr .xdy`；新增 `_collect_named_index_aux(state)`（把命名索引主干的 `.idx/.ind/.ilg` 补进清理/搬运清单，native 编译前、non-native 后处理前、`_clean` 开头三处调用）与 `_sweep_stale_root_aux(state)`（native 编译前删掉被辅助目录遮蔽的根目录旧索引产物，或把孤立产物搬进辅助目录；`.bbl/.aux` 不动）。
- **glossaries 的 xindy 后端**：`_resolve_glossaries_backend` 改为同时查 CWD 与辅助目录的 `<jobname>.xdy`（glossaries 只在 xindy 后端写 `.xdy`，makeindex 后端写 `.ist`）。此前 native 构建拿不到 `.xdy`，被判成 makeindex 后拿不存在的 `main.ist` 直接失败；现在正确切到 `xindy -L <lang> -I xindy -M main.xdy -t main.glg -o main.gls main.glo`。
- **`--no-shell-escape` 真正生效**：新增 `normalize_shell_escape_flag()` + `SHELL_ESCAPE_FALSE_VALUES`，`RUN`、latexdiff 路径、构建键统一归一化。此前字符串 `"false"` 被 `bool()` 判真，`--no-shell-escape` 等于没写。
- **索引工具失败诊断**：`run_command(..., log_hint=False)` 不再提示"查看 LaTeX 日志"（索引错误不进 `.log`），改为 `%(prog)s 执行失败 (退出码 %(code)s)`；`compile.py` 新增 `_on_index_failure()`，打印 `索引工具执行失败: <名称>` + 工具输出末尾 12 行。此前索引失败只会打印"日志里没有解析出 error 条目"，把 xindy 报出的 Win32 267 这类环境原因完全藏住。
- **`-c / -C`**：清理前先 `_collect_named_index_aux(state)`，命名索引产物与多套 glossary 产物一并清掉。
- **测试**：新增 `tests/test_index_named.py`（9 例）；`tests/test_preflight_latexdiff.py` 两例随签名变更调整。全量 **280 passed / 1 skipped**，ruff `All checks passed`。

### 2026-11-18 与 PyTeXLogs 0.6.1 对齐的缺陷修复

- **依赖**：`pytexlogs>=0.6.1`（0.6.1 删除了 `run_log_pipeline`、旧 `run_pipeline` 位置参数、`write_report` 旧名、`StateFileCorrupted` 与 CLI 别名，PyTeXMK 侧不做任何旧版本兼容层）。
- **`--fail-on` 分级**：`TYPESET` 明确为"提示"后，`--fail-on warning` 只看真正的 warning（Overfull/Underfull 不再让 CI 变红）；新增 `--fail-on typesetting` 供需要卡排版提示的流水线使用。
- **主文件名**：`check_project_name` 改用 `Path.with_suffix("")`，修 `main.tex` → `main` 之外 `text.tex` 之类被 `rstrip(".tex")` 吃成空串的问题。
- **索引/术语/目录规则**：`IndexRule.trigger` 增加 `(proj, aux_content, auxdir)` 形参，扩展名触发同时查 CWD 与辅助目录；`.idx`/`.toc` 快照统一走 `_locate()`（native 构建的实际位置）。
- **latexdiff**：`compile_LaTeXDiff` 删除虚构的 `--style=1/2`（latexdiff 的 `--style` 是样式文件路径）；编译分支补 `shell_escape/synctex/native/extra_args/interaction/jobname`，并在 `finally` 中还原 `draft`。
- **索引命令**：`compile_index` 用 `shlex.split(..., posix=False)` 并去掉外层引号，路径含空格不再被拆开。
- **`restore_draft`**：改为"在当前内容上摘除 draft token"，不再整份回写旧快照（编译期间的手动编辑不会被覆盖）。
- **`--max-runs 0`**：允许 0（首轮后不再追加编译），不再被 `max(1, ...)` 悄悄改成 1。
- **构建基线**：`_artifact_path` 在根目录与辅助目录都有产物时取 mtime 较新者（native 构建的新产物在辅助目录，旧实现比的是根目录旧副本 → 误判"未变化"）。
- **file_ops**：`remove_matched_files` 由"每个 pattern 一次全树 rglob"改为单次遍历；`_replace` 改为"临时文件 + `os.replace` 原子覆盖"，失败回滚，不再先 `unlink` 目标（中途失败会连旧 PDF 一起丢）。
- **subprocess_runner**：删除无调用路径的 `SubprocessFailedError.timed_out()` 与 `except TimeoutExpired` 死分支；`run_command(out_files/aux_files)` 注解修正为 `list[str]`；`_quote_arg` docstring 明确"仅展示层加引号，不承诺可粘贴"。
- **CLI 启动**：删 `builtins.print = print` 空语句；`UpdateChecker` 由模块级移入 `main()`；Windows UTF-8 重包装保留原件引用，避免旧 `TextIOWrapper` 被 GC 后关闭底层 buffer。
- **`--json` 机器可读输出**：新增 `machine_report`（`schema_version=1`）：`stdout` 只输出一个 JSON（`status`/`exit_code`/`project`/`build`/`diagnostics`/`issues`/`timings`/`out_files`），进度与错误全部转到 `stderr`；`emit` 幂等、失败退出码非 0 时强制 `status="failed"`；覆盖 `-c/-C/-ca/-Ca`（`action`）、`-A`（`subprojects`）、`--doctor`（`checks`/`missing_critical`/`config_errors`）、`--explain`、成功/失败/跳过三条编译路径。`issues` 带前 20 条 error/warning 的 `level/file/line/text`（`text` 压成单行），失败时也照样给出——编辑器插件与 CI 注释可直接跳到出错行，不必再解析 stderr。rich `Console` 改持 `_SwappableStream` 代理（未切换时跟随 `sys.stdout`），`--json` 时切到 `stderr`，避免混进 stdout 且不破坏 `capsys`/`redirect_stdout`。
- **i18n 补齐**：新建 `diagnostics` 域英文目录（`diagnostics.po/.mo` + `templates/diagnostics.pot`，9 条），`cli_args`/`cli_workflow` 各补 2 条；`diagnostics.py` 的 `_()` 原本指向不存在的域，等于英文环境仍输出中文；`cli_compile.py` 归类为 `cli_workflow` 域（与 `cli_workflow.py` 共用）；`preflight.py`/`submission.py` 删掉定义了却 0 调用的 `set_language`/`_`。

### 2026-11-18 `-q` / `-nq` 只管"编译过程可见性"（控制台级别回归 1.2.7）

- **`-nq` 现在真的会显示编译日志**：由 `MySubProcess(stream_output=state.non_quiet)` 决定——非安静模式逐行 `console.print` TeX/biber/makeindex 的输出，安静模式照常读取但不显示（失败诊断仍拿得到全文）。逐行输出时不再套 `console.status` 的 Live 渲染，避免在真实终端里日志"时有时无"。
- **安静模式不再改控制台日志级别**：级别只由 `-vb` 决定，与 1.2.7 一致（`-vb` → INFO，否则 WARNING；不再升 DEBUG）。删除 `logger_config.set_quiet_verbosity()`，`-q`/`-nq` 与日志级别彻底解耦；`setup_logger` 在"已有 handler"的早退分支也补落一次级别，`--watch` 重入或二次调用时 `-vb` 不会被上一轮的级别吃掉。
- **日志不再自相打脸**：只在命令行显式给出 `-q` / `-nq` 时输出一行结论（哪一侧覆盖了 `quiet_mode`）；由配置文件驱动的默认行为保持安静，需要结论用 `--explain`。
- **`-q` 覆盖所有命令**：不再等到编译阶段才改 `state.non_quiet`，`-ls` / `-c` / `--explain` 等不走编译的命令同样按安静模式处理。
- **`-q` 与 `-nq` 互斥**：argparse 互斥组，同时给出直接报参数错误并退出 2，不再让"后解析的那个"悄悄胜出。
- **`-iu` 生成的用户配置不再含死键**：`default_user_config.toml` 里写的是早年的 `non_quiet`（运行时只认 `quiet_mode`），导致 `pytexmk -iu` 生成的文件一上来就被 `--validate-config` 判"未知配置项"；模板统一改为 `quiet_mode`，项目模板同步补充语义注释。
- **i18n 抽取清单补漏**：`cli_context.py` 使用 `cli_workflow` 域，却一直不在抽取清单里；本轮把同域另外 5 个文件（`cli_config.py` / `cli_doctor.py` / `cli_early.py` / `cli_latexdiff.py` / `cli_watch.py`）也纳入抽取——不纳入时 `babel update` 会把它们的旧翻译打成 `#~` 弃用条目，`compile` 阶段直接丢弃，英文环境下这些提示会莫名退回中文。纳入后旧翻译全部保留（实测 `cli_workflow` 目录 69 条生效），仍空待译的有 `cli_workflow` 96 条、`cli_args` 31 条（帮助文本居多），单独一轮补齐。
- **文档里的长选项写错**：`README.md` / `README.en.md` / `src/pytexmk/data/README*.html` 一直写作 `--non_quiet`，而 argparse 注册的是 `--non-quiet`——照文档抄会直接 `error: unrecognized arguments: --non_quiet`；已统一为 `--non-quiet`，并补上此前完全没写的 `-q` / `--quiet` 行，同时把 `-q`/`-nq`/`-vb` 三者的职责写清。
- **测试**：`tests/test_quiet_mode.py`（11 例：优先级矩阵、`-vb` 只到 INFO、`-q`/`-nq` 不改级别、子进程输出开关、互斥参数）、`tests/test_config_templates.py`（3 例：随包模板必须通过 `--validate-config` 同一套检查）；`test_packaging_metadata.py` 的 pytest 下限断言改为"不低于 9.1"，不再因为 dev 依赖升级而需要手改测试。
- **索引（nomencl / makeidx）在默认配置下恢复触发**：1.2.17 的扩展名 trigger 只查 CWD，而 `native=auto` 把 `.nlo`/`.idx` 写进 `Auxiliary/`，于是 `\printnomenclature` 永远等不到 makeindex——用户看到的就是"nomencl 没有编译"。现在 trigger 同时查 CWD 与辅助目录，新增 `tests/test_index_nomencl.py`（7 例：两种布局、已收敛不重跑、输入变化重跑、`[index] index_style_file` 带空格路径进 `-s`）。
- **删除兼容/死代码**：`BuildState.record_fingerprint`、`remove_state_file_if_empty`、`Diagnostics.report_success`、`ConfigParser.init_config_file`、`detection.locate_aux`、`file_ops.move_by_extensions`、`print_compile_report` 的 `prog`/`stalled` 旧参数、`cli_compile._iter_tex_sources` 薄包装。
- **文档**：README 的 `Python 3.14+` 改为 `3.15+`（与 `requires-python` 一致）；CLI 参数表补 `--json` 与 `--fail-on typesetting`；`docs/python315-migration.md` 去掉已删除的 `Timed.unwrap()` / `timed_out()` 描述。
- **测试**：新增 `tests/test_2026_11_18_p0_fixes.py`（12 例）、`tests/test_json_output.py`（10 例，含失败编译的 `issues` 定位与 `--doctor`/`--explain` 载荷）与 `--fail-on` 分级 2 例；全量 **271 passed, 1 skipped**。

### 运行命令打印只求对齐

- **按横幅宽度折行**：`运行命令: …` 块按 `total_len`（78 列）折行，优先在参数之间断行；缩进与 `运行命令: ` 前缀同宽，因此每行都不超过横幅宽度，与 `======` 分隔线视觉齐平。
- **超长参数按显示宽度切开**：外部 `auxdir` 的深路径这类单参数超宽时，按显示宽度切成几片续行（只折行、不丢字符），不再让整行溢出或超出终端。
- 折行块定位为“阅读/记录用”，不再承诺原样粘贴进 bash/pwsh/cmd 执行；相应地移除了 shell 进程链探测、续行符开关（`--command-line-continuation`）与 shell 特化转义。

### 打印信息与实现对齐

- **`--fail-on error` 真正生效**：原先 `choices` 里有 `error`，代码却只判 `warning`。现在成功路径上日志仍有 error 级条目即退出 6；`--fail-on warning` 改用警告+排版提示总数。成功摘要主体抽成 `diagnostics.report_summary() -> LogSummary(errors/warnings/typesetting)`，`report_success()` 保留旧返回值口径。
- **`--doctor` 配置检查不再恒 ✓**：`ConfigParser` 新增 `load_errors`，`_load_toml` 解析失败时记录原因；`--doctor` 据此打 ✗ 并以退出码 1 结束，不再在配置写坏时照样说“体检通过”。
- **PyTeXLogs 命令可执行**：失败提示与成功摘要里的 `pytexlogs <log> --format json` / `--open` 在 0.5.x 会被 argparse 拒掉（`invalid choice`），改为 `pytexlogs export <log> --format json`、`pytexlogs check <log> --open`、`pytexlogs summary <log> --max-entries 0`（路径含空格自动加引号）。
- **`--explain` 交互模式**：未显式设置时按实际生效值显示（安静模式 `batchmode`、`-nq` 为 `nonstopmode`），不再恒显示 `nonstopmode`。
- **`-ls` 不再谎报“已更新”**：对比写入前后的 `.pytexmkrc`，无变化时提示“已是当前清单，未改动”；帮助与模板注释同步为“重建 `[subprojects]`、保留仍指向真实路径的手写条目”。
- **归档提示跟随 SyncTeX 开关**：`--no-synctex` 时只说“归档 PDF 到输出目录”，不再提 synctex。
- **帮助不再吞字**：`-A` 帮助里的 `[subprojects]` 只转义左方括号（rich 不认 `\]`，会留下反斜杠）；`-h` 的退出码表补上 `2=命令行参数解析错误`，`6` 改为“诊断阈值”。
- **诊断报告路径校验**：`--report` 写入失败时明确提示“诊断报告未生成（写入失败）”，不再打印一个并不存在的路径。

### SyncTeX 校验与产物归档加固

- **假失败修复**：`--synctex-check` 的取样行改为从 `\begin{document}` 之后挑选正文行（原先取第 2 行的 `\usepackage`，前言行没有版面盒子，反向必然落到 `\begin{document}`，几十行前言就会报“行号偏差过大”）；并改为多候选重试，任一候选通过即判定可用。
- **多文件论文**：反向落在项目内的 `.tex`（`\input`/`\include` 子文件）不再判为“定位到错误文件”，只在回到主文件时比较行号，容差 5 行。
- **产物自愈**：`_can_skip_compile` 现在同时要求 outdir 里有 PDF 与 `.synctex.gz`；缺 synctex 会重新编译，而不是跳过编译后永远无法反向跳转。
- **校验不再被跳过**：`--synctex-check` 移到编译后的统一收尾，命中“源文件未变、跳过编译”分支时同样会执行。
- **`outdir` 与 `auxdir` 同目录不再删产物**：归档前先判定两个目录是否同一位置（`file_ops._replace` 也加了同文件保护），修复“先 unlink 目标再 move 源”把刚编译出的 PDF/SyncTeX 删掉、退出码仍为 0 的问题；归档失败改为以退出码 5 明确报出。
- **诊断更准**：缺失 `.synctex.gz` 时直接提示“需要重新编译”并给出 `-fr` 建议；陈旧 synctex 给黄色警告；失败回显只保留 `Page / Input / Line` 等有用行。
- **清理不再误伤**：`SUFFIXES_AUX` 去掉裸 `.gz`（`-ca` 不再删用户自己的 `*.gz`），`-ca` 单独精确匹配 `*.synctex.gz`。
- 新增 `tests/test_synctex_regressions.py`（12 例）：前言取样、子文件落点、缺失/陈旧产物、同目录归档、跳过编译前置条件。

## v1.2.17 - 2026-11-16

### Smoke test 的 SIGPIPE 修复

- Rocky Linux 8 的 smoke test 同样使用 `ldd --version | head -n 1`，在 `pipefail` 下返回 141，导致 Linux 二进制明明已构建成功、smoke 却失败，GitHub Release 被跳过。
- 改为 `ldd --version 2>&1 | awk 'NR==1'`，读取完整输出后再取首行。

## v1.2.16 - 2026-11-16

### Linux 二进制改用带共享库的 managed CPython

- **根因**：manylinux_2_28 镜像自带的 `/opt/python/cp315-cp315` 是静态构建，PyInstaller 报 `Python was built without a shared library`，导致 `Pack binary` 直接退出。
- **修复**：容器内先 `uv python install 3.15`，再以 `UV_PYTHON=3.15` 执行 `uv sync`，使用 uv 管理的带 `libpython.so` 的 CPython 3.15；镜像自带的静态 Python 只用于安装 uv。
- glibc 水位仍由 `check_glibc.py` 对产物做硬门禁，不因更换解释器而放松。

## v1.2.15 - 2026-11-16

### CI 失败尾行逐行注释

- `run_command` 在 Actions 中除汇总错误外，把最近 8 行输出逐行打成独立 `::error::tailN::` 注释，避免长命令或单条注释被截断后看不到 PyInstaller 的真实错误。
- 用于定位 manylinux 容器内 `pack.py` 在 PyInstaller 启动阶段退出的具体原因。

## v1.2.14 - 2026-11-16

### 容器内 PyInstaller 显式安装与失败尾行

- Release 在 `uv sync --locked --dev` 后增加 `uv pip install 'pyinstaller>=6.22.3'`，把 PyInstaller 明确装进 manylinux 的 `.venv`，不再依赖 dev 组在容器内的解析/安装结果。
- `run_command` 的 Actions 错误注释改为只输出退出码与最近输出尾行，避免长命令列表把真正的 PyInstaller 报错挤出注释。

## v1.2.13 - 2026-11-16

### CI 打包失败可观测与命令回退

- Release 的 `Pack binary` 回退为项目环境内的 `uv run python tools/pack.py pack`；上一版额外叠加 `--with pyinstaller` 会在容器内重新解析并安装依赖，反而引入网络/临时环境变量。
- `tools/utils.py` 的 `run_command` 在 GitHub Actions 中失败时输出 `::error::` 注释，并附带最近 8 行命令输出；无需登录 GitHub 即可在 job 注释中看到 PyInstaller 的真实错误行。
- 本地 `uv run python tools/pack.py pack` 在 Windows 与 WSL/Linux 均已成功（Linux 产物约 6.95 MB）。

## v1.2.12 - 2026-11-16

### Linux Release 诊断步骤修复

- **真实根因**：manylinux 容器的 `Show versions for diagnostics` 使用 `ldd --version | head -n 1`，在 GitHub Actions 的 `bash -e -o pipefail` 下被 `head` 提前关闭管道触发 SIGPIPE，步骤返回 141，后续 `Pack binary` 全部被跳过。改为 `awk 'NR==1'`（读取完整输入，不再产生 SIGPIPE）。
- `gcc -dumpfullversion -dumpversion` 增加 `|| true`，避免诊断命令本身成为发布门禁。
- 保留 `uv run --with 'pyinstaller>=6.22.3'` 与 `::error::` 注释，作为后续 CI 打包的可观测性保障。

## v1.2.11 - 2026-11-16

### CI 打包诊断与依赖显式化

- **Linux 打包命令**：Release 工作流改为 `uv run --with 'pyinstaller>=6.22.3'`，不依赖开发依赖组是否已进入运行环境；解决 manylinux 容器中 `python -m PyInstaller` 找不到模块时快速失败、但普通日志不可见的问题。
- **失败可观测**：`tools/pack.py` 未捕获异常时额外输出 GitHub Actions `::error::` 注释，未登录也能在 job 注释里看到异常类型与消息，不再只看到 `Process completed with exit code 1`。
- 本版本仅用于验证并补齐 GitHub Release 的三平台二进制；PyPI `1.2.10` 已发布。

## v1.2.10 - 2026-11-16

### 发布工具链修复

- **Linux 二进制打包**：`tools/pack.py` 改为 `sys.executable -m PyInstaller` 调用，不再依赖 PATH 中的 `pyinstaller` 可执行脚本；避免 manylinux 容器里 `uv run` 环境下入口脚本不可见时，`Pack binary (onedir, source mode)` 在启动阶段直接失败。
- **`make upload` 返回值校验**：`git tag` / `git push` 失败时立即停止并返回非零退出码，不再打印“成功上传标签”的假成功日志；标签已存在且指向当前 HEAD 时视为可重试成功，指向其他提交时拒绝覆盖。
- 本版本是 `1.2.9` 的发布工具链补丁；`1.2.9` 的 PyPI 发行已成功，补发 `1.2.10` 以补齐 GitHub Release 的三平台二进制资产。

## v1.2.9 - 2026-11-16

### PyTeXLogs 0.5.0 接入与诊断增强

- **依赖升级**：`pytexlogs>=0.5.0`，删除 `diagnostics.py` 中对 0.4 的 `inspect.signature` 参数探测和 `TypeError` 最小参数降级；直接使用 `write_report_file` / `report_path`。
- **可执行建议上下文**：改用 `hint_for_entry(..., jobname=..., root_file=..., language=...)`，失败命令里的 `biber <jobname>`、`xelatex <主文件>.tex` 会显示成 `biber main`、`xelatex main.tex`。
- **警告也有建议**：成功摘要的 top-3 警告不再只给一行文本，同样打印 `↳` 建议与命令；中英文跟随终端 locale。
- **排序修正**：错误/警告按级别、文件、行号排序，不再只按文件排序。
- **uv 源**：为 `pytexlogs` 单独指定官方 PyPI 源，避免刚发布时清华镜像未同步导致 `uv sync --locked` 失败；`publish-url` 修正为 `https://upload.pypi.org/legacy/`。
- **PythonTeX 自动调度**：首轮 LaTeX 生成 `*.pytxcode` 后，自动在该文件所在目录运行 `pythontex <jobname>`，再补一轮 LaTeX；native 构建在 `Auxiliary` 内运行，传统构建在项目根目录运行。`MySubProcess.run_command` 新增 `cwd` 参数，不改变既有调用的默认行为。
- **preflight 误报修复**：`\input`/`\include` 正则增加控制序列边界，避免把 `\inputsection{...}` 解析成 `\input section`；路径中含 `#1` 或 `\langdir` 等宏时只给 warning 并跳过存在性检查；`\newcommand`/`\def`/`\newenvironment` 的定义体先屏蔽再检查，定义里的模板 `\input` 不再被当成真实输入。真实缺失的静态文件仍报错。
- **`make inswhl` 嵌套 uv 锁修复**：原目标先用 `uv run` 启动脚本，父 uv 持有工具目录锁，脚本内再调 `uv tool uninstall/install` 会在 Windows 报 `.lock` 拒绝访问；现改为在 Makefile 外层直接执行两条 `uv tool` 命令，并用 `$(wildcard dist/*.whl)` 传入 wheel。
- **Windows venv 兼容修复**：项目 `.venv` 被 WSL `uv` 创建成 Linux 布局后，Windows `uv` 会因 `lib64 -> lib` reparse point 拒绝删除而让 `make clean` / `make whl` 在脚本启动前失败；已在 Windows 侧重跑 `uv sync` 重建为 `Scripts/` + `Lib/` 布局，并让符号链接权限不足的测试按环境跳过。
- 测试：`tests/test_diagnostics.py` 新增 4 项，`tests/test_external_tools.py` 新增 3 项，preflight 新增 4 项，全量 **176 passed, 1 skipped**；ruff 通过。

> 依据 `docs/2026-11-16-功能与CLI审查.md` 的全量整改。编译正确性（C1–C6）、
> 失败诊断（3.3）、原生命名目录（3.7）、投稿打包与 Unicode 转换（3.9）
> 已落地；`preflight`（3.2）、`--diff-style`（3.5）、索引样式配置（3.8）、
> 清理安全（U6）同步补齐。**尚未落地**的条目见 `docs/2026-11-16-整改遗留.md`。

### 🔴 编译正确性（C1–C6）

- **C1 源文件快照**：改用 `.fls` 的 `INPUT` 记录识别真实依赖（跨目录 `\input`、图片、`.bib`、`.cls`），无 `.fls` 时才按后缀兜底；按 `resolve()` 去重，`--skip` 判断不再漏判。
- **C2 构建指纹**：`BuildState.save_round` 落盘 `build_key`（引擎/交互模式/shell-escape/草稿/原生/输出目录/辅助目录/额外参数/版本 的 sha256）。参数一变即重编译；同参数重复运行才跳过。
- **C3 草稿模式自愈**：开启时先完整备份源文件并注册 `atexit`，`try/finally` 中调用 `restore_draft()` 精确还原；异常退出也不再把 `\includeonly`/草稿标记留在正文里。
- **C4 bib2gls**：识别 `.pytxcode`/bib2gls 信号后单独调度一次，原生命名目录下传 `--dir=<auxdir>`。
- **C5 shell-escape**：`detect_shell_escape()` 扫描 minted/pythontex/shellesc/svg/gnuplottex/tikzexternalize/`\write18`，默认 `auto` 只在需要时加 `-shell-escape`。
- **C6 PDF 修复零残留**：同目录临时文件 → `fsync` → `os.replace` 原子替换；失败只删临时文件，原 PDF 逐字节不变；不再产生 `.bak`/`.tmp`。优先 `qpdf`（保留书签/元数据），`pypdf` 兜底。

### 🧭 构建与目录（3.3 / 3.6 / 3.7 / 3.9）

- **原生目录构建（3.7 中期方案）**：`[build] native = auto` 时 `xelatex` 直接 `-output-directory=<auxdir> -jobname=<project>`，辅助文件从源头写进 `Auxiliary/`，根目录不再"搬进搬出"；`-o` 归档只移动最终 PDF/SyncTeX。
- **失败诊断（3.3）**：新增 `diagnostics.py`，失败打印"发现 N 个错误 + 最多 5 条 `file:line` + ↳ 可执行建议 + 安装命令 + `pytexlogs <log> --open`"；成功只报 top-3 警告并给出剩余条数。
- **投稿打包（3.9）**：新增 `submission.py`。按 `.fls` 收集项目内依赖、复制 `.bbl`、生成 `pytexmk-submission-notes.txt`（转换清单 + pdflatex 兼容警告），zip 固定 1980 时间戳可复现，staging 目录必删、无 `.tmp` 残留。
- **Unicode 深度转换**：覆盖希腊字母大小写、集合/逻辑/运算/箭头、`°℃µ‰§©®™€£¥Å•`、破折号/引号、全部上下标数字、`½¼¾`、全角标点、连字 `ﬁﬂ`，以及 NFKD 组合音标（`é`→`\'{e}`）与全角字符；`\verb`/verbatim/lstlisting/minted 内的内容不转换。
- **导言区净化**：`-sp` 默认注释 `fontspec/unicode-math/ctex/xeCJK/luacode/luatexja/polyglossia/selnolig` 及 `\setmainfont` 等字体设置，补 `fontenc`/`inputenc`/`textcomp`；一行多宏包只摘掉不兼容项。可用 `--keep-preamble` 关闭。
- **`.bbl` 也转换**：biber 生成的 `.bbl` 常带 Unicode，投稿包会对它做同一套转换，否则 pdflatex 在参考文献处仍会炸。
- **残留字符定位**：无法转换的字符（中文、日文、emoji、`☃` 等）不再"静默保留"，而是按 `file:line` 列进说明文件与终端，并明确提示 pdflatex 无法处理中文正文。
- **`--pack-verify`**：在临时 staging 目录真跑一次 pdflatex，结果（通过/失败 + 日志尾部）写进说明文件；`--include-bib` 可把 `.bib` 一并打包。

### 🧰 CLI 体验（U1–U8 部分）

- `-d/-dc` 由 `nargs="*"` 改为 `nargs="?"` + 后处理：`-d OLD NEW` 不再吞掉 `document`，`-d` 单独使用等价于全部。
- 新增 `-q/--quiet`、`--native/--no-native`、`--shell-escape/--no-shell-escape`、`--interaction`、`--pass-arg`、`--max-runs`、`-sp/--submission-pack`、`-pc/--pdflatex-check`、`--submit-dir`、`--no-preflight`、`--clean-dry-run`、`--diff-style`、`--doctor`、`--watch`、`--keep-preamble`、`--pack-verify`、`--include-bib`。
- 新增 `-io/--includeonly`（隔离的 `Build/partial`、`Auxiliary/partial`）、`-A/--all-subprojects`（批量编译 + 汇总表）、`--synctex-check`（正向/反向定位校验，错误码 7）、`--report [PATH]`（PyTeXLogs JSON 报告，成功/失败都写）、`--fail-on warning`（警告/排版提示触发退出码 6）、`--explain`（只解释本次有效配置）、`--show-config`、`--validate-config`。
- 新增 `--jobname NAME`：PDF/aux/synctex/报告与构建状态按输出名组织，`.tex` 源文件仍按主文件名；投稿包把 `.bbl` 回落到主文件名，避免期刊端缺 `.bbl`。
- `-ls` 会保留仍指向真实路径的手写子项目别名，不再整体清空。
- `[index] glossaries_tool = "makeglossaries"` 可让多 glossary 项目改走 `makeglossaries`（默认仍 `makeindex`；相同命令自动去重）。
- `finalize` 预览后不再提前 `exit`，后续步骤仍会执行。
- 退出码在 epilog 公开：0 成功 / 1 参数或环境错误 / 3 子项目未找到 / 4 配置错误 / 5 编译失败 / 6 `--fail-on warning` / 7 SyncTeX 校验失败 / 8 投稿包 pdflatex 验证失败。
- 版本串去掉 `[i]`；更新检查可用 `PYTEXMK_NO_UPDATE_CHECK` 关闭。

### 🧪 质量验证

- 新增 `--completion bash|zsh|fish|powershell`：从 argparse 自动提取全部选项，输出纯文本补全脚本后退出（不经过 rich 横幅）。
- 全量 `pytest`：**176 passed, 1 skipped**（Windows 专属用例在 Linux 跳过）。
- WSL + MiKTeX 26.5 真机端到端：失败用例 exit 5 且根目录零辅助文件残留；成功用例 `Build/main.pdf` + `Auxiliary/main.{aux,fls,log,out}`；二次运行正确跳过；`-sp` 产出可复现 zip 并列出 fontspec 不兼容项；`-pc` 正确报错。
- 投稿包真机验证：含 fontspec/unicode-math/`α β ≤ ° ² é µ`/verbatim 的稿件，`-sp --pack-verify` 在临时目录 pdflatex **编译通过**；含中文的稿件正确报出 `cjk.tex:18 中` 并以验证失败提示人工处理。
- 新增能力真机验证：`--synctex-check` 正向第 1 页 / 反向 `main.tex` 行定位通过；`-io sec1` 只输出指定 `\include` 章节到 `Build/partial`；`-A` 批量编译两个子项目并汇总；`--fail-on warning` 对 Overfull 警告返回 6；`--explain` / `--show-config` / `--validate-config` 输出正常。


## v1.2.8 - 2026-11-15

### ⚠️ 破坏性变更（二进制分发）

- **Linux 二进制的 glibc 水位从 2.38 降到 2.28**：以前在 `ubuntu-latest`（已升至 26.04 / glibc 2.43）上编译，产物实际要求 2.38，Ubuntu 22.04、Debian 11/12 等一大批发行版装上也起不来。现在改为在 `quay.io/pypa/manylinux_2_28_x86_64`（AlmaLinux 8 / glibc 2.28）容器内构建，覆盖 Ubuntu 20.04+ / Debian 10+ / RHEL 8+；构建环境不再随 runner 升级而漂移。
- **macOS 二进制只发布 arm64**：`macos-latest` 早已切到 arm64，但 `zip_release.py` 里写死了 `-x64` 后缀，导致发出去的是"名字写 x64、实际是 arm64"的错标包，`install.sh` 又只接受 x64 因而直接拒绝安装。现在资产统一为 `pytexmk-<版本>-macos-arm64.zip`，Intel Mac 走 uv 通道（`uv tool install pytexmk` 或给脚本加 `-m uv`）。

### 🏗 打包与 CI

- `Release.yml` 拆出独立的 `build-binary-linux` job（容器内构建），Windows / macOS 留在矩阵里，macOS 指定 `macos-26` + `arm64`，并在打 zip 前用 `file` 断言架构。
- 新增 `tools/check_glibc.py`：扫描产物（连同 `_internal` 里捆绑的 `.so`）引用的 `GLIBC_*` 符号，超过基线就让 CI 失败，不再把问题留给用户。
- 新增 `smoke-linux-artifact` job：在 `rockylinux:8`（真实 glibc 2.28）里解压并运行一次 `pytexmk --version`，验证"声称能跑的最老环境"确实能启动。
- 新增子进程环境回归探针：用假 TeX 引擎回写 `LD_LIBRARY_PATH`，断言外部程序拿不到打包目录（防止 `OPENSSL_3.2.0` 类问题复发）。
- `tools/zip_release.py` 支持 `--arch {x64,arm64}`（默认 `x64`），资产命名由平台 + 架构共同决定。

### 🐛 Bug 修复

- **🔴 打包后调用 lualatex 报 `version 'OPENSSL_3.2.0' not found`**：PyInstaller 把 `_internal` 前插到 `LD_LIBRARY_PATH`（Windows 上还有 `SetDllDirectoryW`），子进程继承后优先加载了打包目录里的 `libssl.so.3` / `libcrypto.so.3`。新增 `pytexmk.runtime_env`：
  - `child_env()`：有 `*_ORIG` 就用它还原（空值表示原本没有该变量），否则按 `realpath` 把打包目录条目摘掉
  - `external_process_scope()`：Windows 下在 spawn 的瞬间 `SetDllDirectoryW(None)`，退出后恢复
  - `subprocess_runner` 的两处 `Popen` 均已接线；配 `tests/test_runtime_env.py`（源码运行 / 摘除 / `*_ORIG` 优先 / 空值删除 / `DYLD_LIBRARY_PATH` / 软链 realpath / Windows 清空-恢复）

### 🛠️ 安装与升级

- `tools/install.sh` 新增 `-m zip|uv` 双通道：`zip`（默认，下载打包二进制）与 `uv`（从 PyPI 源码安装，适用于 Intel Mac、glibc 过低或想要源码版）；uv 通道用 `uv tool dir --bin` 定位启动器，`-d/-b` 会给出"被忽略"的提示。
- 架构映射补齐 `arm64`：Linux arm64 / macOS x64 明确拒绝并指向 uv；glibc 门槛文案改为 2.28。
- 修复消息以 `-` 开头时 `printf` 把格式串当成选项（`printf: -m: invalid option`）的问题，四个打印助手统一改为 `printf -- "$fmt"`。
- `check_version` 的升级文案按平台分流：Linux/macOS 的 `onedir`（zip 解压版）统一提示**重跑 `install.sh`**（`curl -fsSL … | bash -s`）并附 uv 备选；`unknown` 的 Linux/mac 渠道补上"安装脚本"一行。en 译文同步更新（`make pot` → `update` → 手工 msgstr → 编译 `.mo`）。

### 🧪 质量验证

- 全量 `pytest`：**118 passed, 1 skipped**（Windows 专属用例在 Linux 上跳过）；`ruff check src tests tools` 全绿。
- `install.sh` 真机验证：`bash -n` 通过；zip 通道装 1.2.7 后 `--version` 正常、重复执行即就地升级；uv 通道 `-m uv -v 1.2.7` 安装成功且启动器路径正确；macOS Intel / Linux arm64 / macOS arm64 三个架构分支行为符合预期。
- `check_glibc.py` 自测：对 `/usr/bin/git`（需 GLIBC_2.38）用基线 2.28 判失败、2.99 判通过，退出码 1 / 0 正确。
- `zip_release.py` 自测：`macos --arch arm64` 生成 `pytexmk-<版本>-macos-arm64.zip`，内含 `pytexmk/pytexmk`。

## v1.2.7 - 2026-10-17

### 🐛 Bug 修复

- **🔴 `pytexmk -l` 一直编译到安全上限（11 次）**：`bib_judgment()` 里 `bib_file_path = Path(self.bib_file)` 拿的是 `.aux` 中 `\bibdata{References}` 的**裸文件名**（无 `.bib` 后缀），`Path("References").exists()` 永远为 False，于是每一轮都重新判定"文献需要 2 次编译"；而 `_is_log_stalled()` 要求 `bib/idx/toc/aux/out` **全部**归零才肯判定停滞，只要 bib 维度非零就一路空转到 `max_extra_compilations=10`（合计 11 次）。修复三处：
  - 新增 `_resolve_bib_files()`，按 `<name>.bib` → `<name>` 逐个探测（支持 `\bibdata{a,b}` 逗号分隔多文件），`self.bib_files` 保存真实存在的路径
  - 判定改为"引用计数稳定 **且** `.bbl` 存在 **且** 日志无 `No file *.bbl` / `Citation undefined` **且** `.bbl` 不比 `.bib` 旧 → 归零"；找不到任何 `.bib` 时直接归零并告警（bibtex 无法产出 `.bbl`，继续重跑只是空转）
  - 删除 `self.out` 相关的死代码（该属性只在 `__init__` 赋值 `""`，此后从未更新，`re.search(..., self.out)` 恒为 False），改用真实 `.log` 内容
- **🔴 收敛判据过于脆弱，任何一个维度卡住就跑到上限**：`_is_log_stalled()` 的"全维度归零 + 相邻两轮日志签名相同"条件在实践中几乎不可能满足（lineno 的 `\def\@LN@column{N}` 会让 `.aux` 每轮都变）。改为**状态指纹不动点检测** `_convergence_stop_reason()`：
  - 新增 `CompilationDetector.state_fingerprint()`：把 `.aux/.out/.toc` 的归一化内容、各索引系统输入、日志警告签名、`.bbl` 大小合成一个 sha256 指纹
  - 指纹**等于上一轮** → `fixed_point`；指纹**等于更早轮次** → `cycle`（两态震荡）；没有任何变更类维度非零 → `log_stalled`（日志仍有警告）或 `stable`
  - `log` 维度被明确排除在"可推进维度"之外（`ACTIONABLE_DIMS`），它只是警告信号，继续编译无法消除
  - 结果：指纹是"整体是否原地踏步"的最终裁判，某个维度因宏包 churn 长期非零也不会再拖满 10 轮
- **🔴 循环内从不重跑 bibtex/makeindex，`bib`/`idx` 维度必然长期非零**：原实现只在循环**外**跑一次 `compile_bib` / `compile_index`，之后每轮 `run_full_detection` 又报告"需要文献/索引处理"，而循环体丢弃了返回的 `bib_engine` / `index_run_cmds`。修复：循环内就地补跑，并用 `aux_signature()` / `index_signature()` 去重，保证"同一输入状态只调用一次外部工具"
- **🔴 中断的编译留下截断辅助文件，之后每次编译都在同一处失败**：Ctrl+C 或关闭终端时 LaTeX 正在写 `.aux`，磁盘上留下半截文件（例如 16384 字节、末尾停在 `\@writefile{toc}{\contentsline`），下一次编译直接报 `! File ended while scanning use of \@writefile.` + `==> Fatal error occurred`，且此后每次重现——因为坏文件还在。新增 `aux_repair.py`：编译前检查 `.aux/.toc/.lof/.lot/.out/.bbl/.idx/.ind/.nlo/.nls/.glo/.gls/.nav/.snm`，按"花括号是否配平"+"文件大小是否正好是 4 KiB 整数倍却无结尾换行"识别截断文件，删除后由本轮编译重建
- **🟡 `-ls` 在根 `.pytexmkrc` 缺失时是空操作**：`write_subprojects_to_rc()` 遇到不存在的文件直接返回 False，`_list_subprojects()` 只打印"请先运行 pytexmk -i"，于是 `-ls` 扫描出了清单却什么都没保存，紧接着的 `-s <名字>` 必然失败。修复：`-ls` 先用模板自动创建根配置再写入 `[subprojects]`
- **🟡 `-s` 子项目解析脆弱**：`build_subprojects()` 只读持久化的 `[subprojects]`，别名表为空就抛 `ProjectNotFoundError`（"扫描得到却编译不了"）；深层子项目的别名是完整相对路径（如 `Section/en02`），用户写 `en02` 匹配不上；条目直接指向 `.tex` 时把文件路径交给 `os.chdir()` 会抛 `NotADirectoryError`。修复：新增 `discover_subprojects()` 兜底扫描、`_match()` 四级匹配（精确别名 → 大小写不敏感 → 相对路径后缀 → 叶子目录名，并兼容反斜杠）、`ProjectContext.work_file` 记录 `.tex` 条目并把 `work_root` 落到其父目录
- **🟡 `abbreviations_num` 固定 13 元组**：编译次数超过 13 会抛 `IndexError`（v1.2.6 已从 6 扩到 13，只是把边界推远）。改为 `_ordinal()` 按需生成，上限调整不再有越界风险

### ✨ 新增

- **`residual_warnings()` 收尾提示**：编译结束后明确告诉用户"哪些警告是再编译也消不掉的"（未定义的交叉引用键名、`.bib` 缺少条目、重复标签），避免用户误以为是编译流程的问题
- **`aux_repair` 独立 i18n domain**（`.po` / `.pot` / `.mo`）

### ⚙️ 调整

- `MAX_EXTRA_COMPILATIONS` 从 `10` 降到 `8`：正常情况下指纹不动点检测在 2~4 轮收敛，上限只用于防御"每轮都产生新指纹"的病态项目，把最坏情况限制在 9 次以内
- `print_compile_report()` 的 `stalled` 参数保留为兼容层（等价 `stop_reason="log_stalled"`），新增 `stop_reason` / `residual_notes` 参数，停止原因文案集中在 `STOP_REASON_MESSAGES` 常量表里

### 🧪 质量验证

- `pytest -q`：**68 passed**（新增 `tests/test_compile_convergence.py` 31 例 + `tests/test_subproject_resolution.py` 9 例）
- 真实论文项目（30 页，`paper-01-dr-ym`）**冷启动全量构建**：清空 `Auxiliary/` + `Build/` 后 `pytexmk -l` → **4 次** LuaLaTeX 收敛（bib 维度第 3 轮归零），bibtex 跑 2 次（第 1、2 轮，`.aux` 变化后需要重跑）、makeindex 跑 1 次，随后去重生效
- 同一项目**热态重建**：**2 次** LuaLaTeX 收敛，第 2 轮命中 `fixed_point`
- **截断辅助文件自愈**：把 `main.aux` 截断到 16384 字节后直接 `pytexmk -l` → 自动删除并重建，3 次编译收敛，输出 PDF 与修复前**字节完全一致**（11530517 B，30 页）
- `-s Review -l`：子项目正常编译（1 次 LuaLaTeX，无额外空转）
- `python -m compileall src/pytexmk`：通过；所有新增 msgid 已同步到 `.po` / `.pot` / `.mo`，`LANGUAGE=en` 下译文正确加载

### ⚡ 收敛判定 v2：省掉确认轮 + 跨进程基线复用

> 承接上文：修复后冷启动仍需 4 次编译（实测第 4 轮），热态 1~2 次。多出的那一轮是**纯粹的观察轮**——辅助文件其实早已稳定，但因为"上一轮快照只活在内存里"，进程每次都必须再编一次才能确认。本节把这一轮彻底消掉。

#### 1. 单文件多命名空间状态（依赖 PyTeXLogs 0.4.0）

- **不新增任何辅助文件**：`.pytexmk_refcache.json` 本来由依赖库 `pytexlogs` 写入（存引用缓存），现升级为**多工具共享状态文件**（schema v3）：

  ```jsonc
  {
    "schema_version": 3,
    "pytexlogs": { "refs": { "keys": [...], "key_counts": {...} } },
    "pytexmk":   { "build": { "fingerprint": "...", "artifacts": {...}, "sources": {...}, "converged": true, "stop_reason": "stable", "signals": {...} } },
    "jobs":      { "main": { "updated_at": "..." } }
  }
  ```

- 读写统一交给 `pytexlogs.ProjectStateStore`：**命名空间隔离**（各写各的键，不会互相覆盖）+ **原子写**（临时文件 + `os.replace`）+ **轻量文件锁**（超时降级，不阻塞编译）
- 新增 `src/pytexmk/build_state.py`：`BuildState` 负责产物摘要、源快照、收敛标记的业务读写；**PyTeXMK 不自己碰 JSON**

#### 2. 判定矩阵：信号分类 + 省掉确认轮

核心变化是把日志信号分成两类（`CompilationDetector.classify_signals()`）：

| 类别 | 内容 | 含义 | 决策作用 |
|------|------|------|---------|
| `permanent` | 未定义引用、`Citation undefined`、重复标签 | 只有改源码才能消除 | **不得**作为"再编一轮"的理由 |
| `transient` | `Label(s) may have changed`、`Rerun to get cross-references right`、lastpage/rerunfilecheck rerun | 会随轮次消失 | **必须**再编一轮让 LaTeX 自行确认 |

只有 `transient` 需继续编译，`permanent` 不能触发额外编译——这样“至少编一轮确认”就不再需要：

| 优先级 | 情形 | 判定 | 停止原因 |
|--------|------|------|---------|
| 1 | 本轮指纹等于上一轮 / 更早轮次 | **停** | `fixed_point` / `cycle` |
| 2 | `bib/idx/toc/aux/out` 全为 0 | **停** | `stable` |
| 3 | 仍有维度非零，但日志**只剩 permanent** 信号、无 transient | **停** | `log_stalled`（新增路径） |
| 4 | 仍有 transient 信号 / 维度非零且无信号信息 | **继续** | — |

- 第 3 条只保留为兜底：第 2 条已覆盖绝大多数情况，这里只防止“被永久信号拖着的伪需求”空转到上限
- 若 `RERUN_LOG_PATTERNS` 顺序被调整，`_PERMANENT_PATTERN_TOKENS` 会由正则文本自动重算，不会错位

#### 3. 源文件未改动则整次跳过编译

- 新增 `-fr / --force-rebuild` 参数；不指定时，满足以下全部条件则**完全跳过编译**：
  1. 上次判定为收敛（`converged: true`）
  2. 所有 `.tex` 源文件的 `(size, mtime_ns)` 与快照一致（用纳秒，避免“同秒内修改”漏判）
  3. 产物摘要与基线一致，且输出 PDF 确实存在
- 源快照**不递归别人的子项目**：`Cover/`、`Review/` 这类自带 `.pytexmkrc` 的目录有自己的 PDF，改动它们不该触发主项目重编译；同时排除隐藏目录与 `Build/`、`Auxiliary/` 等产物目录
- `-dr/--draft` 与 `-fr` 永不跳过
- **只有收敛的构建才写 `converged`**：停在 `limit`（安全上限用尽）不写，避免把未收敛的 PDF 当成成品

#### 4. 清理与状态一致性

- `-c / -C`：调用 `BuildState.discard()`，**只删 `pytexmk.build`**，保留 `pytexlogs.refs`（引用缓存不属于 PyTeXMK）
- `-ca / -Ca` 及状态文件为空骨架时自动删除文件
- 所有状态读写异常一律降级（最多多编一轮），**绝不阻断编译**

#### 5. 其他修正

- 首轮若所有变更维度已归零，直接判 `stable`，不再多编一轮（对应此前"行为退化：首轮必编 2 次"）
- `-s NAME` 支持按目录名 / 相对路径末段匹配（`-s en02` 可命中 `Section/en02`）；`ProjectContext` 新增 `work_file`，条目直接指向 `.tex` 时会正确设置主文件
- `-ls` 在根 `.pytexmkrc` 缺失时自动创建（此前只打印警告、扫描结果被丢弃，导致随后 `-s` 无处可查）

#### 性能实测（`paper-01-dr-ym`，30 页）

| 场景 | 改造前 | 改造后 |
|------|--------|--------|
| 清除辅助文件后全量重建 | 4 次（约 16 s） | 4 次 |
| 无改动重复运行 | 2 次（约 8 s） | **0 次（0.3 s，直接跳过）** |
| 修改某个章节后 | 2 次 | 1 次 |

#### 测试

- `pytest -q`：**108 passed**（新增 `tests/test_build_state.py` 24 例 + `tests/test_signal_classification.py` 12 例，`test_compile_convergence.py` 扩展判定矩阵用例）
- 真实项目端到端：`-fr` 刷新快照 → 无改动 0.3 s 跳过 → 改章节立即重编 → `-c` 只清 `pytexmk.build`（`pytexlogs.refs` 的 39 条引用缓存保留）→ 清理后首次编译自动重建 4 次 → 再跑即跳过
- `ruff check src/pytexmk tests`：通过

---

## v1.2.6 - 2026-09-25

### 🐛 Bug 修复

- **🔴 魔法注释正则误匹配 TeX 转义百分号 `\%`**：`tex_project.py` 中魔法注释正则 `rf"%(?:\s*)!TEX ..."` 开头的 `%` 不检查前导反斜杠，导致行内 TeX 代码 `\texttt{\% !TEX program = XeLaTeX}` 中的 `\%` 被误识别为魔法注释的起始标记，值末尾多带 `}`。修复：正则开头加 `(?<!\\)` 否定后行断言，确保 `%` 前不是反斜杠（TeX 转义百分号）。真实注释行（行首 `%`）行为不变
- **🔴 bib2gls（glossaries-extra 后端 + biber）模式下错误触发 makeindex**：`bib_judgment()` 正确检测到 bib2gls 模式并设置 `self.bib2gls_mode = True`，但 `_INDEX_REGISTRY` 驱动的 glossaries 规则不知道该标记，仍按普通 glossaries 返回 makeindex 命令。bib2gls 的 glossary 条目由 biber 统一处理（写 `.gls` / `.glstex`），完全不生成 `.glo` / `.ist` / `.xdy`，makeindex 调用必然因输入文件缺失而失败。修复：在 `_INDEX_REGISTRY` 两处遍历循环（`_index_aux_content_get` 快照采集 + `index_judgment` 命令生成）里，若 `bib2gls_mode` 且 `rule["name"] == "glossaries"` 则 `continue` 跳过

### 🧪 质量验证

- `ruff check src/pytexmk/tex_project.py src/pytexmk/detection.py`：**All checks passed!**
- 正则对比测试：旧版 `\texttt{\% !TEX program = XeLaTeX}` → 误匹配 `XeLaTeX}`；新版 → None ✅
- bib2gls 端到端（`pytexmk -x glossaries-extra-bib2gls-test`）：3 XeLaTeX + DVIPDFMX 收敛，**零 makeindex/xindy 调用** ✅
- 普通 glossaries 回归（`pytexmk -x glossaries-test`）：`glossaries main 编译 makeindex -s ...` 正常调度 ✅
- 综合项目回归（`pytexmk -x main`）：运行 LaTeX 程序数目 = 5，与修复前一致 ✅

---

## v1.2.5 - 2026-09-25

### 🏗 架构变更

- **CLI 工作流拆分（方案 C）**：`cli/cli_workflow.py` 从 437 行单函数瘦身至 30 行薄入口，具体实现下沉到 4 个叶子模块 + 1 个共享状态容器：
  - `cli_state.py`（叶子模块，不 import 任何其他 cli_*）：`WorkflowState` dataclass 承载 20+ 运行时变量 + `PREVIEW_AFTER_COMPILE / SUFFIXES_OUT / SUFFIXES_AUX / MAGIC_COMMENT_KEYS` 四组常量
  - `cli_early.py`：`handle(args, cp, logger)` 处理 `-r / -i / -iu / -ls` 早退出子命令
  - `cli_context.py`：`build → resolve_target → apply_magic_comments` 三步完成 上下文解析 + 三层配置合并 + 魔法注释覆盖 + 文件清单派生
  - `cli_compile.py`：`handle_clean_any / run / finalize` 覆盖 `-ca/-Ca / -c/-C / -pr / 完整编译 / PDF 预览 / time_print / UpdateChecker`
  - `cli_latexdiff.py`：`run` 覆盖 LaTeXDiff 全流程（校验 → 辅助文件检查 → flatten → 风格交互 → 差异编译 → finally 归还辅助文件）
  - 依赖严格单向：`cli_workflow → {cli_early, cli_context, cli_compile, cli_latexdiff} → cli_state`，无循环依赖
  - 全流程共享状态由隐式全局变量 → 显式 `WorkflowState` dataclass，消除 20 个散落变量的层层覆盖
  - 13 处函数内 import 全部上移顶部，依赖关系静态可见
  - 所有新模块沿用 `set_language("cli_workflow")` 域，**翻译文件 `cli_workflow.mo` 无需修改**
  - 对外接口 `run_workflow(args)` 签名不变，`__main__.py` / 打包配置 / CI 无感

- **索引系统重构**：`detection._index_aux_content_get` 与 `index_judgment` 两套 50 行分支逻辑统一改为 `_INDEX_REGISTRY` 注册表驱动，glossaries/nomencl/makeidx 三种索引的触发条件、解析规则、文件后缀、命令模板集中管理，新增第四种索引系统（如 acronym）只需在注册表追加一条
- **`standardize_name()` 三处重复定义合并**：`compile_engine.py / compile_report.py / cli_workflow.py` 各自拷贝的 7 行函数 → 统一 `tex_project.standardize_name`，原位置改为 import 复用
- **compile.py 四段相同错误处理提取**：`compile_tex / compile_bib / compile_index / compile_xdv` 四个方法的 `except SubprocessFailedError` 块一字不差 → 提取为类方法 `_on_subprocess_failure`

### 🐛 Bug 修复

- **🔴 glossaries 快照读错文件**：`detection._index_aux_content_get` glossaries 分支快照 `_read_file_content(Path(f"{ext_o}"))` 但 key 用 `{ext_i}`，导致快照存了输出文件 `.gls` 内容却标为输入文件 `.glo`，检测阶段永远在拿不同文件比较 → 每轮编译都误判需要重跑索引。修正为 `_read_file_content(Path(f"{ext_i}"))`（与 nomencl/makeidx 分支保持一致，都以输入文件 ext_i 为快照/比较对象）
- **🔴 配置项 `pdf_preview_status` 完全失效**：三层证据
  1. `config.py` 默认值为 `False`（布尔），但 L205 被 `args.pdf_preview`（`-pv` 未传时 argparse const 为 `None`）无条件覆盖
  2. L429 又拿布尔值去和字符串哨兵 `"preview after compile"` 比较 → 永远不相等
  3. 出厂 `default_user_config.toml` 注释写着"编译结束后是否打开 PDF"，却因上述三层矛盾静默不生效。修复：统一为 `state.preview_after_compile: bool`，配置合并（L132-137）与 `-pv` 合并（L165-182）都以布尔语义赋值，消除字符串哨兵 + 无条件覆盖
- **🔴 `[index]` 段三参数静默谎言**：`index_style_file / input_suffix / output_suffix` 在原 `cli_workflow.py:177-186` 中被读取后只打日志、下文零引用，而实际索引后缀由 `detection._INDEX_REGISTRY` 硬编码统一管理；glossaries 输入后缀又本就由 `.aux` 动态解析多个值，单一后缀覆盖语义不成立。已从 `cli_context._apply_config_file` 删除该段读取，留注释说明原因；配置文件中的 `[index]` 段暂时保留兼容但不参与运行时
- **恒真条件**：`cli_workflow.py:232` `elif not args.readme:`（此时已在 L83-98 走 `finally: exit_pytexmk()` 退出）→ `else:`

### 🛠️ 完善

- **13 处函数内冗余 `set_language("detection")` 清理**：`detection.py` 模块级已调一次，函数体内的重复调用完全多余（运行时模块级 state 已就绪），已删除
- **移除 `from __future__ import annotations`**：`context.py / subproject_scanner.py` 中该 import 在 Python 3.14 下（PEP 563 延迟注解默认启用）完全多余，已删除
- **`_count_citations` 三重嵌套简化**：先用 `.search()` 再 `.finditer()` 导致 search 结果被忽略 → 直接用 tuple + 单层 `for pattern in _CITE_PATTERNS` 迭代，一次遍历完成三模式匹配
- **未使用的 `get_gettext()` 删除**：`language.py:74-75` 此函数仅做 `return set_language(lang_file)`，搜索全 src 目录无任何调用方
- **`print_message` dict 查表替代 if/elif**：`ui_messages.py` 三种 state 对应的 `in_dec_chars / out_dec_chars / *_style` 硬编码 if/elif → 用 `_STATE_STYLES` 集中管理的 dict 查表
- **`pyproject.toml` per-file-ignores 清理**：6 条指向不存在文件（`scripts/*`、`tests/test.py`、`tests/test_tr21_manager_compare.py`、`tests/test_tr22_register_compat.py`、`scripts/check_log_decouple.py`）的忽略规则已清理
- **`_index_changed_judgment` `.get()` 兜底**：原裸 `dict[key]` 查找有隐性 KeyError 风险（快照用 `all()`、检测用 `any()` 的触发条件不一致时），改为 `.get(key, "")`

### 📝 文档更新

- `docs/architecture.md` 同步至 v1.2.5：模块规模 23 → 28、Layer 1 CLI 子包列表 4 → 9、职责矩阵重写（含 `cli_state/cli_early/cli_context/cli_compile/cli_latexdiff` 新行）、烟检命令更新、子包拆分阈值背景补充说明"CLI 域扩展后三阈值条件仍成立"

### 🧪 质量验证

- `ruff check src/pytexmk/`：**All checks passed**（0 错误；修复前 1 条 SIM102 同步消除）
- `pytest -q`：**14 passed**（无新增失败）
- 6 个新模块静态导入烟检：**ALL IMPORT OK**
- 真实端到端 XeLaTeX 编译（XeLaTeX×3 + bibtex + nomencl + dvipdfmx + 日志解析 + 统计表 + UpdateChecker）：**Exit=0，全绿**
- 7 组 CLI 路径逐一冒烟：`-i` 初始化、`-ls` 子项目清单、`-d / -dc` LaTeXDiff 参数校验、`-c / -C / -ca` 清理路径、`-pv FILE` 单次预览：全部符合预期

---

## v1.2.4 - 2026-09-18

### 🎉 新增

- 📚 **多子项目编译**：新增 `-s/--subproject`、`-ls/--list-subprojects`、`-i/--init`、`-iu/--init-user`、`-f/--force` 子命令，支持在一个项目根目录下管理并逐一编译多个相互独立的子项目
  - `-s/--subproject <名称>`：从根 `.pytexmkrc` 的 `[subprojects]` 段选中一个子项目并进入其 root 编译/清理；进程内部切换工作根，**不改变用户终端 cwd**，可与位置参数 `document` 共存（如 `pytexmk -s 子项目 main`）；alias 未命中时报错并提示先运行 `-ls`，以「项目不存在」退出码退出
  - `-ls/--list-subprojects`：按根配置 `[project_scan]` 规则扫描并表格展示子项目清单；若根 `.pytexmkrc` 存在，会将 `[subprojects]` 段**整体替换**为扫描结果（结果幂等，含用户手写内容一并覆盖），`[project_scan]` 段**不被改动**；若 rc 不存在则提示先运行 `-i`、不写盘
  - `-i/--init`：生成根项目 `.pytexmkrc`；`-iu/--init-user`：生成用户级 `~/.pytexmkrc`
  - `-f/--force`：仅配合 `-i/-iu` 覆盖已存在文件；目标已存在且未加 `-f` 时提示且不写入

### ⚠️ 破坏性变更（BREAKING）

- **移除 `project_config_auto_init` 配置键**：正常运行**不再自动生成配置文件、不再有 `input()` 交互**
- 配置为纯读取合并，优先级：内置默认 ← 用户级 rc ← 项目级 rc；缺失配置用内置默认静默运行，键不匹配仅警告、不写盘
- 用户级 `~/.pytexmkrc` 不再自动生成，改用 `-iu` 手动生成

### ⚡ 性能优化

- **子项目发现器重写**：`discover_subprojects` 改用 `Path.walk(top_down=True)` 单遍遍历 + `dirnames[:]` 原地剪枝（排除/超深/动态黑名单/命中目录零下钻），免重复 glob/readdir，`-ls` 明显更快；全程 pathlib
- **主文件判定提速**：改为共享 `has_magic`（一次字节读前 16KB，检查 `\documentclass`/`\begin{document}`，避免 utf-8 全量解码与逐行迭代），发现器与编译期 `find_tex_commands` 共用

### 🎉 新增

- 🪟 **新增 winget 发布渠道**：Windows 10 1809+ / Windows 11 用户可通过 `winget install --id YanMing-lxb.PyTeXMK -e` 一键安装 PyTeXMK，无需 Python 环境；清单由官方 wingetcreate 直接生成（仅 en-US 单语言），InstallerType=zip + NestedInstallerType=portable，安装后 `pytexmk` 命令自动加入 PATH
- 🔄 **Release 工作流新增 publish-to-winget job**：打 tag 发布（非 dry_run）时在 job 内**直接内联官方 wingetcreate**（curl 下载 + `wingetcreate update --submit`）生成清单并提交 PR 到 `microsoft/winget-pkgs`；不再依赖本地发布脚本。winget 发布失败会让 job 红标，确保发布问题可立即暴露（首次提交需人工审核合并）
- 🔒 **Token 安全**：仅从环境变量 `WINGET_CREATE_GITHUB_TOKEN` 读取 PAT（CI 由 `secrets.WINGET_GITHUB_TOKEN` 注入），wingetcreate 同从该环境变量读取，token **不进入命令行参数/argv**，也不会落日志
- 📚 **新增 docs/winget_publish.md 开发者文档**：涵盖 PAT 申请步骤、首次提交人工审核说明、清单验证失败排查思路，便于长期维护

### 🛠️ 完善

- 🐛 **修复 GBK 编码辅助文件导致的编译检测崩溃**：中文字典类文档（CTeX/cct 的 GBK 方案）生成的 `.aux`/`.toc`/`.out`/`.bcf` 等辅助文件为本地编码而非 UTF-8，`detection.py` 中硬编码 `encoding="utf-8"` 逐字节解码会抛出 `UnicodeDecodeError`，使 `run_full_detection` 报错并返回 `None`，进一步在 `compile_engine` 解包时崩溃。新增容错读取函数 `_read_file_content`（优先 UTF-8 严格解码，失败退回系统本地编码 cp936，最后以 `errors="replace"` 兜底），并将全部辅助文件快照读取统一改走该函数，保证「快照—重读」解码一致、永不因编码异常中断检测

---

## v1.2.2 - 2026-08-04

### 🐛 Bug 修复

- **修复 `uv build` / `uv build --wheel` 构建时 setuptools `Package 'pytexmk.data' is absent from the packages configuration` 警告**：为 `src/pytexmk/data/`、`src/pytexmk/locale/`、`src/pytexmk/locale/templates/` 补充 `__init__.py`，将隐式命名空间包转为显式包，setuptools `find_packages()` 可正确发现并纳入 wheel/sdist

### 🧪 质量验证

- 📦 `uv build` 全量构建验证：源码分发包 (tar.gz) + wheel 均成功生成，setuptools 包发现零警告（`pytexmk.data` / `pytexmk.locale.templates` 已通过 `__init__.py` 显式注册）

---

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
