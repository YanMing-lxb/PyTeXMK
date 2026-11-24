# 测试目录说明

测试按"能跑多快、能证什么"分层。目录即层，标记由 `conftest.py` 依据父目录自动打上，
新增文件不需要手写 `@pytest.mark.unit`。

| 目录 | 文件数 | 关注点 | 典型耗时 |
| --- | --- | --- | --- |
| `unit/` | 36 | 纯函数/类、文件搬移、指纹、参数拼装 | 秒级 |
| `cli/` | 8 | 参数解析、分派、日志/报告解析 | 秒级 |
| `integration/` | 5 | 真实子进程、完整 CLI、报告导出 | 约 10 秒 |
| `regressions/` | 6 | 按修复轮次归档的跨模块回归 | 秒级 |

当前共 55 个文件、605 条用例。**每个文件测什么、什么时候该改，见
[`docs/测试索引与修改指南.md`](../docs/测试索引与修改指南.md)**——新增/删除/改名
测试文件时必须在同一次改动里更新那份索引。

## 运行

```powershell
# 全量（提交前必跑）
python -m pytest -q

# 只跑不需要真实子进程的部分（改纯逻辑时用）
python -m pytest -q -m "unit or cli"

# 只跑端到端
python -m pytest -q -m integration

# 单个文件 / 单条用例
python -m pytest -q tests/unit/test_compile_engine.py
python -m pytest -q tests/cli/test_cli_args.py -k draft
```

`pyproject.toml` 已声明四个标记，`--strict-markers` 下拼错标记会直接失败。标记只用于
选择范围，不改变用例本身的断言。

## 命名

- `unit/`：`test_<源模块>_<方面>.py`，如 `test_file_ops_move.py`；
- `cli/`：`test_cli_<阶段>.py`，如 `test_cli_workflow.py`；
- `integration/`：`test_<场景>.py`，如 `test_build_delivery.py`；
- `regressions/`：`test_<YYYY_MM_DD>_<主题>.py`，如 `test_2026_11_23_review.py`。

不用 `fixes`/`improvements`/`deep`/`misc`；跨层也不要同名 basename（pytest 会报
import mismatch）。

## 共享 fixture（`tests/conftest.py`）

- `repo_root`：仓库根目录。新用例**不要**再写 `Path(__file__).parents[N]`——目录挪一层
  就会静默指错，而 editable 安装会让它"假通过"。
- `run_cli`：在指定项目目录里跑 `python -m pytexmk`，自动带 `PYTHONPATH=<repo>/src`，
  返回 `CompletedProcess`。
- `make_parser`：把用户 rc 路径指向临时目录，避免读到真实的 `~/.pytexmkrc`。

## 写用例的硬要求

1. **断言行为，不断言"没抛异常"**。只进出上下文、只调用函数而不检查结果的用例视为
   无效用例；负向用例要用 `pytest.raises` / `pytest.fail` 明确表达。
2. **新开关必须进契约表**。新增/改名 CLI 旗标时，同步修改
   `tests/cli/test_cli_args.py` 的 `FLAG_CASES` 与帮助页清单，否则契约测试会红——
   这是唯一能发现"旗标被删/被改名"的地方。
3. **外部命令用间谍断言 argv**。涉及 biber/bib2gls/TeX 的 quiet、目录、旗标时，
   替换 `MSP.run_command` 捕获完整命令，而不是只断言"调用过"。
4. **路径用 `repo_root` 拼**，不要依赖当前工作目录；子进程统一用 `run_cli`。
5. **回归用例按日期/轮次命名**，放在 `regressions/`，一条用例对应一个曾经的故障。
6. **更新索引**：新增/删除/改名文件，改的是哪条契约，都要写回
   `docs/测试索引与修改指南.md`，否则下次功能变动会找不到该改的用例。

## 盲区与守护

2026-11-24 的变异审计发现并已补上的盲区（对应用例见括号）：

- CLI 短旗标契约（`cli/test_cli_args.py`、`integration/test_cli_invocation.py`）
- biber/bib2gls 的 quiet 旗标（`unit/test_compile_tool_flags.py`）
- 构建指纹漏版本维度（`unit/test_build_key.py`）
- 文件搬移失败后的回滚（`unit/test_file_ops_move.py`）
- `stage_bib` 重复收集（`unit/test_submission_bib.py`）
- 首轮 `tools_pending` 判定（`unit/test_compile_engine_first_round.py`）
- 非打包运行时误触碰 DLL 搜索路径（`unit/test_runtime_env.py`）

完整审计过程、19 条变异的结果与逐文件结论见
`docs/2026-11-24-测试审计与整理.md`；目录与修改流程见
`docs/测试索引与修改指南.md`。
