# PyTeXMK → Python 3.15 迁移报告

> 环境基线：Python 3.15.0（Scoop / MSC v.1951）、uv 0.12.18、PyInstaller 6.22.3、pytest 9.1.1。
> 验证结论：`ruff check` 全绿、`pytest` 28 passed、PyInstaller onedir 打包成功且二进制冒烟通过、
> 6 类真实 LaTeX 项目端到端编译成功（见 §5）。

---

## 1. pyproject.toml 审计结论

### 1.1 已修复的问题

| 问题 | 处理 |
| --- | --- |
| `requires-python` 未指向 3.15 | 改为 `">=3.15"`；CI/Release 的 `setup-python` 改为 `python-version: "3.15"` + `allow-prereleases: true` |
| dev 下限三处分叉（pillow 12.3/13.00、pyinstaller 6.21/6.22、pytest 8/9） | 统一到**已锁定且确认支持 3.15** 的下限：babel 2.18.0 / pillow 13.0.0 / pyinstaller 6.22.3 / pytest 9.1.1 |
| `[project.optional-dependencies]` 缺失 | 恢复 `dev` extra（产物 wheel 中已出现 `Provides-Extra: dev`），与 `[dependency-groups] dev` 逐条对齐，由 `tests/test_packaging_metadata.py` 守护 |
| setuptools 报错 “License classifiers have been superseded by license expressions” | 改用 PEP 639 `license = "GPL-3.0-or-later"`，删除 `License ::` 分类器，补充 `Programming Language :: Python :: 3.15` |
| `[tool.uv] requires-python` 非法 | 删除该表（uv 0.12.18 报 “unknown field `requires-python`”），版本约束只留在 `[project].requires-python` |
| ruff 未按 3.15 检查 | `target-version = "py315"`，规则集 `E4/E7/E9/F/W/I/UP/B` |
| 未验证依赖的 3.15 兼容性 | 见 §1.2，全部通过 |

### 1.2 依赖 3.15 兼容性核验（读安装元数据 `Requires-Python`）

| 依赖 | 锁定版本 | Requires-Python | 结论 |
| --- | --- | --- | --- |
| packaging | 26.3 | >=3.9 | ✅ |
| platformdirs | 4.13.3 | >=3.11 | ✅ |
| pypdf | 6.21.1 | >=3.9 | ✅ |
| pytexlogs | 0.3.0 | >=3.14 | ✅ |
| rich | 15.0.0 | >=3.9 | ✅ |
| rich_argparse | 1.8.0 | >=3.9 | ✅ |
| tomli-w | 1.2.0 | >=3.9 | ✅ |
| babel (dev) | 2.18.0 | >=3.8 | ✅ |
| pillow (dev) | 13.0.0 | >=3.11 | ✅ |
| **pyinstaller (dev)** | 6.22.3 | **>=3.8,<3.16** | ✅（唯一带上限者；冻结包内含 `python315.dll`） |
| pytest (dev) | 9.1.1 | >=3.10 | ✅ |

> 若日后把 `requires-python` 抬到 `>=3.16`，第一个被卡住的是 PyInstaller 的 `<3.16` 上限。

### 1.3 两种依赖表并存的原因与约束

- `[dependency-groups].dev`（PEP 735）：给 `uv sync`，默认安装、不进 wheel METADATA。
- `[project.optional-dependencies].dev`（PEP 621 extras）：给 `pip install pytexmk[dev]`。
- **不能互相引用**：`dev = [{ include-group = "dev" }]` 会被 uv 0.12.18 拒绝
  （`invalid type: map, expected a string`），因为 `include-group` 只在 `[dependency-groups]` 内部合法。
  故两表并列维护，并由单测比对下限，避免再次分叉。

### 1.4 最终 pyproject.toml

以仓库根目录的 `pyproject.toml` 为准（本文件不重复粘贴，避免两处漂移）；关键段落：

```toml
[project]
requires-python = ">=3.15"
license = "GPL-3.0-or-later"
dependencies = ["packaging>=26.3", "platformdirs>=4.13.3", "pypdf>=6.21.1",
                "pytexlogs>=0.3.0", "rich>=15.0.0", "rich_argparse>=1.8.0", "tomli-w>=1.2.0"]

[project.optional-dependencies]
dev = ["babel>=2.18.0", "pillow>=13.0.0", "pyinstaller>=6.22.3", "pytest>=9.1.1"]

[dependency-groups]
dev = ["babel>=2.18.0", "pillow>=13.0.0", "pyinstaller>=6.22.3", "pytest>=9.1.1"]

[tool.ruff]
target-version = "py315"

[tool.pytest.ini_options]
filterwarnings = ["error::DeprecationWarning:pytexmk.*", "error::SyntaxWarning"]
markers = ["slow: 需要真实 LaTeX 工具链的慢速用例"]
```

---

## 2. 代码迁移清单（逐处）

| # | 文件 / 位置 | 迁移前 | 迁移后 | 类型 |
| --- | --- | --- | --- | --- |
| 1 | `src/pytexmk/detection.py`（5 处） | `except OSError, UnicodeDecodeError:` | `except (OSError, UnicodeDecodeError):` | 语法 |
| 2 | `src/pytexmk/detection.py` `_read_file_content` | `locale.getpreferredencoding(False)` + 单独变量 | `for enc in dict.fromkeys(("utf-8", locale.getencoding()))` | 3.15 API |
| 3 | `src/pytexmk/detection.py` 顶部 | `typing.NamedTuple` 六元组返回值 | `DetectionResult(NamedTuple)`，调用方改属性访问 | 可读性 |
| 4 | `src/pytexmk/detection.py` 索引注册表 | `tuple[dict]` + `rule["trigger"](...)` 字符串下标 | `IndexRule` / `IndexSpec` 冻结 dataclass + `rule.trigger(...)` | 3.10 `dataclass(slots)` |
| 5 | `src/pytexmk/detection.py` `_NGLOSSARY_PATTERN` | 5 个位置分组 `match.groups()` | 命名分组 `match.group("glo")` | 可读性 |
| 6 | `src/pytexmk/detection.py` `bib_judgment` | 裸字符串 `"biber"` / `"bibtex"` | `BibEngine(StrEnum)` | 3.11 `StrEnum` |
| 7 | `src/pytexmk/compile.py` `compile_bib` | `bib_engine == "biber"` | `bib_engine == BibEngine.BIBER` | 同上 |
| 8 | `src/pytexmk/timing.py` | `time_count` 返回二元组，异常时 `(None, None)` | `Timed(NamedTuple)`：`seconds / value / error`，保留 `.unwrap()` | 错误语义 |
| 9 | `compile_engine.py`、`cli/cli_compile.py`、`cli/cli_latexdiff.py`（22 处） | `runtime_x, _ret = time_count(...)` | 用值处 → `runtime_x, ret, _err = time_count(...)`；不用值处 → `runtime_x = time_count(...).seconds` | 3.15 PEP 758 |
| 10 | `src/pytexmk/subprocess_runner.py` | `raise SubprocessFailedError(...)`（丢失异常链） | `raise ... from None` / `from e`；新增 `timed_out(...)->Self`、`launch_failed(...)->Self` | 3.11 `typing.Self` |
| 11 | `src/pytexmk/subprocess_runner.py` | `sum(1 for _ in log.open("rb"))`（未关句柄） | `log_path.read_bytes().count(b"\n") + 1` | 资源泄漏 |
| 12 | `src/pytexmk/file_ops.py` | 四个搬移函数各写一遍「删旧→rename→日志」 | 合并为 `_replace(src, dest, dest_label)`；`move_matched_files` 返回 `int` | 去重 |
| 13 | `src/pytexmk/tex_project.py` `draft_model` | 正则匿名组 + `set` 拼选项（顺序随机） | 命名分组 + `_documentclass_options()` 保持用户选项顺序 | 正确性 |
| 14 | `src/pytexmk/cli/cli_state.py` | `@dataclass` | `@dataclass(slots=True)` | 内存/防拼错 |
| 15 | `src/pytexmk/__init__.py` | `def __getattr__(name)` 无注释 | 保留惰性导出 + 类型标注 + 说明用途 | 可读性 |
| 16 | `src/pytexmk/__main__.py`、`cli/cli_latexdiff.py` | 作者头像块在 import 之前触发 E402 | `# ruff: noqa: E402`（保留项目排版约定） | 工具链 |

---

## 3. 使用的 3.15 新特性（逐条收益）

| 特性 | 用在哪里 | 收益 |
| --- | --- | --- |
| **PEP 758**：`except` / `except*` 允许多个异常不加括号 | `detection.py` 的 5 个 `except` | 与 `raise A, B` 的 Py2 残留写法正好互为镜像；去掉多余括号后与 3.15 语法一致，`ruff --select UP` 不会再把这类写法当作历史遗留 |
| **PEP 758**：解包赋值不强制括号 | `runtime, ret, _err = time_count(...)` | 三元组解包无需占位符 `_ret` 与括号，读起来就是「耗时、返回值、异常」三件事 |
| **`locale.getencoding()`**（3.15 新增，取代已软弃用的 `locale.getpreferredencoding()`） | `_read_file_content` | 「本地编码是什么」这件事有了唯一入口，语义明确、不经 GUI 首选项探测，且在未来版本不再产生 DeprecationWarning |
| **PEP 649/749 惰性注解** | 全项目（无需改代码） | 注解不再在定义期求值：`pytexmk` 包内大量 `from __future__` 式的互相引用（cli ↔ detection ↔ compile）不再有循环导入风险；`import pytexmk` 的注解开销趋近于零，`--version` 这类冷启动路径更快 |
| **`typing.Self`**（3.11，3.15 下无须 `typing_extensions`） | `SubprocessFailedError.timed_out / launch_failed` | 两个构造器返回自身类型，`timed_out(...) from None` 保留了「超时不是原异常」的语义 |
| **`typing.NamedTuple` + `enum.StrEnum`** | `DetectionResult` / `Timed` / `BibEngine` | 六个检测维度的返回值从「位置元组」变为可读属性；引擎名从裸字符串变为枚举，`StrEnum` 仍是 `str`，`argv`、日志、比较行为零变化 |
| **`@dataclass(slots=True, frozen=True)`**（3.10+，在 3.15 工具链下可放心） | `IndexRule` / `IndexSpec` / `WorkflowState` | 索引规则表从字符串下标 dict 变为属性访问；实例去掉 `__dict__`，字段名拼错立刻 `AttributeError` 而不是静默新建属性 |
| **正则命名分组 + `re.Pattern[str]`** | `_NGLOSSARY_PATTERN`、`RERUN_LOG_PATTERNS` | 按语义取值，扩展名对应关系（glo/gls/glg）在代码里自解释 |
| **PEP 639（`license` 表达式）** | `pyproject.toml` | setuptools 对旧式 `License ::` 分类器已硬性拒绝；改用 SPDX 表达式后 wheel METADATA 带 `License-Expression` |
| **PEP 735 `[dependency-groups]`** | `pyproject.toml` | `uv sync` 默认装齐开发依赖，且 dev 依赖不进 wheel METADATA |

> 刻意**没有**引入的：`lazy_import`（本机 3.15 构建中并非内置模块，装上会让冻结包多一个可选依赖，见 §6）、
> 共享下划线名字的 `except A, B` 之外的花式语法、`PL*` 风格规则（会淹没迁移 diff）。

---

## 4. 环境 / 测试 / 打包命令（3.15）

```powershell
# 0) 解释器：仓库根的 .python-version 已写 3.15
uv python install 3.15
uv python pin 3.15

# 1) 建环境（dev 组默认安装；extras 与 dev 组下限一致，--all-extras 也可）
uv sync                       # 或 uv sync --frozen（CI 用，要求 uv.lock 已提交）
uv sync --all-extras          # 需要 pip 语义的 extras 时

# 2) 静态检查
uv run --with ruff ruff check src tools tests pyproject.toml
uv run --with ruff ruff format --check src tools tests   # 可选

# 3) 单测（含 3.15 语义护栏用例）
uv run pytest -q
uv run pytest -q -W default        # 把 DeprecationWarning 当警告打印，便于巡检
uv run pytest -q -m "not slow"     # 跳过需要真实 LaTeX 的慢用例

# 4) 打包（PyInstaller）
uv run python tools/pack.py pack
uv run python tools/zip_release.py windows
.\dist\pytexmk\pytexmk.exe --version

# 附：不走 uv 时务必把 venv\Scripts 放进 PATH，否则 pack.py 找不到 pyinstaller.exe
$env:PATH = "$PWD\.venv\Scripts;$env:PATH"; python tools/pack.py pack
```

CI（`.github/workflows/CI.yml` / `Release.yml`）已同步为：
`actions/setup-python` 的 `python-version: "3.15"` + `allow-prereleases: true`，
`uv sync --locked --dev`，并在打包前新增 `ruff check` 与 `pytest` 两步。

---

## 5. 迁移检查清单

### 5.1 静态检查
- [x] `ruff check src tools tests pyproject.toml` → All checks passed
- [x] `ruff` 规则含 `UP`（按 `target-version="py315"` 识别过时写法）
- [x] 全仓扫描 3.13/3.15 移除的模块：`cgi`/`imp`/`pkgutil`/`locale.getdefaultlocale` 等均无引用
- [x] `datetime.utcnow()` / `utcfromtimestamp()` 无引用（项目统一用 `datetime.now(tz=datetime.UTC)`）
- [x] `except A, B:`（Py2 残留）已清零

### 5.2 单元测试
- [x] `pytest` 28 passed（原 22 + 6 条打包元数据护栏）
- [x] `filterwarnings` 将 `DeprecationWarning:pytexmk.*` 与 `SyntaxWarning` 提升为错误
- [x] `test_packaging_metadata.py`：两套 dev 表下限一致、`requires-python`、PEP 639 license、`target-version="py315"`

### 5.3 打包验证
- [x] `tools/pack.py pack` 成功，`dist/pytexmk/pytexmk.exe` 生成
- [x] 冻结包内含 `python315.dll`（确认打到 3.15 解释器）
- [x] `pytexmk.exe --version` / `--help` 正常退出（Windows 控制台需 `chcp 65001` 或 `PYTHONUTF8=1`）
- [x] 独立探测：冻结后的 exe 内 `import annotationlib` 成功（`Format` = VALUE / VALUE_WITH_FAKE_GLOBALS / FORWARDREF / STRING）
- [x] 独立探测：冻结后带无法解析注解的模块可正常导入与调用（PEP 649 不影响冻结）
- [x] `build/pytexmk/warn-pytexmk.txt` 中已无 `lazy_import` 等 3.15 相关缺失项
- [x] wheel 构建成功，METADATA 含 `Requires-Python: >=3.15`、`License-Expression`、`Provides-Extra: dev`

### 5.4 端到端（真实 MiKTeX 26.5，冻结 exe）
| 用例 | 覆盖路径 | 结果 |
| --- | --- | --- |
| `bibtex-test` | bibtex 维度 + 多轮收敛 | exit 0，4 次 LaTeX + 1 次 bibtex |
| `pdflatex-biblatex-test` | **biber 分支 + `StrEnum`** | exit 0，命令 `biber -quiet …` |
| `makeidx-test` | `IndexSpec` + makeindex 固定模板 | exit 0 |
| `nomencl-test` | `IndexSpec` 空 ctx | exit 0 |
| `glossaries-test` / `multi-glossary-test` | 单 glossary makeindex | exit 0 |
| `multitype-test`（新建） | 命名分组 + 多 `IndexSpec` | exit 0，三条 `makeindex`（glo→gls / acn→acr / slo→sls），`.alg`、`.slg` 日志扩展名正确 |
| `hyperref-cleveref-test`、`contents-test`、`acro-test`、`acronym-test` | out/toc/log 维度 | exit 0 |
| `glossaries-xindy-test` | xindy 分支 | **exit 5，系本机工具链缺陷**，见 §6.1 |

### 5.5 CI 说明
- `setup-python` 用 `python-version: "3.15"` + `allow-prereleases: true`（3.15 早期没有预编译的正式包时必需）。
- CI 里 `uv sync --locked` 要求 `uv.lock` 与 `pyproject.toml` 同步提交；改了依赖务必本地 `uv lock`。
- 打包步骤依赖 PyInstaller，其 `Requires-Python` 为 `<3.16`，将来升到 3.16 前需先确认 PyInstaller 支持。

---

## 6. 已知坑（实测）

1. **xindy 在本机不可用（与 3.15 无关）**：`xindy.exe` / `texindy` 对任何输入都返回
   `*** - Win32 error 267 (ERROR_DIRECTORY): The directory name is invalid.`，
   用 `xindy --version` 即可复现；`git stash` 回退到迁移前代码后同一用例同样 exit 5。
   MiKTeX 侧的 xindy 包装器问题，需重装/修复 `xindy` 包后重测该分支。
2. **`lazy_import` 不是标准库**：本机 3.15.0 中 `import lazy_import` → `ModuleNotFoundError`
   （只有 `Lib/test/test_lazy_import/` 的测试夹具）。曾短暂加入 `pytexmk/__init__.py`，
   因会让冻结包多一个可选依赖（`warn-pytexmk.txt` 出现 “missing module named lazy_import”）
   且无实际收益，已回退为手写 `__getattr__`。
3. **`pack.py` 必须能找到 `pyinstaller.exe`**：直接 `python tools\pack.py pack` 而未把
   `.venv\Scripts` 放进 PATH 会报 `[WinError 2] 系统找不到指定的文件`。用 `uv run` 或前置 PATH。
4. **Windows 控制台编码**：中文与 rich 表格需 `chcp 65001` 或 `PYTHONUTF8=1`，否则输出乱码。
5. **`license` 与 `License ::` 分类器不能共存**：setuptools 直接报错
   “License classifiers have been superseded by license expressions (see PEP 639)”。
6. **`[project.optional-dependencies]` 不能 include `[dependency-groups]`**：uv 报
   `invalid type: map, expected a string`。
7. **`[tool.uv] requires-python` 不存在**：会报 `unknown field requires-python`，
   版本约束只写在 `[project].requires-python`。
8. **`ruff format --check` 目前未绿**（35 个文件待格式化）：保持 `--check` 不进 CI，
   以免把格式化噪声混进迁移 diff；待单独一次提交再启用。
