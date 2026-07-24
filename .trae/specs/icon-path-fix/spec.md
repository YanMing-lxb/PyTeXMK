# Icon 打包路径审查与修复 Spec

## Why
用户对图标打包后的路径正确性存在疑虑。代码中存在两个问题：
1. `datas` 中冗余打包了图标文件（PyInstaller 的 `EXE(icon=...)` 已内嵌图标，无需 `datas`）
2. 图标路径嵌入到生成的 `.spec` Python 代码中时，Windows 反斜杠路径中的转义字符（如 `\t`→制表符、`\n`→换行）会导致路径被破坏，引发 `FileNotFoundError` 和 `SyntaxWarning`

## 问题分析

### 图标格式各平台兼容性
| 平台 | PyInstaller `EXE(icon=)` 接受格式 | 当前方案 | 是否正确 |
|------|----------------------------------|---------|---------|
| Windows | `.ico` | `.ico`（PNG 内嵌） | 正确 |
| macOS | `.icns`（推荐），`.ico` 也可 | `.icns` 优先，fallback `.ico` | 正确 |
| Linux | `.ico`、`.png` 均可 | `.ico`（PNG 内嵌） | 正确 |

**结论**：ICO 格式内嵌 PNG 数据是通用做法，Windows Vista+ 原生支持。格式选择正确。

### 图标路径机制
- PyInstaller 的 `EXE(icon=...)` 在**构建时**将图标嵌入可执行文件的资源段
- 打包安装后**不存在运行时路径查找**——图标已编译进二进制
- `datas` 中的图标条目是多余的，且会被放到 dist 根目录，造成混淆

### 路径转义 Bug（已修复）
`build.py` 通过 f-string 将路径嵌入到生成的 `.spec` 文件中：
- `str(path)` 在 Windows 上产生反斜杠路径如 `D:\...\tools\icon.ico`
- 其中 `\t` 被 Python 解释为**制表符**，`\n` 被解释为换行，`\D`/`\P` 等触发 `SyntaxWarning`
- 结果：路径变为 `D:\...PyTeXMK    ools\icon.ico`（tab 替代了 `\t`），导致 `FileNotFoundError`
- `datas` 使用 `{datas!r}`（`repr()`）自动双写反斜杠转义，`project_root` 使用 `r'...'` 原始字符串，二者均安全

## What Changes
- 从 `datas` 中移除图标文件条目（不需要运行时访问）
- 图标路径使用 `icon_path.resolve().as_posix()` 生成绝对正斜杠路径，并包裹在 `r'...'` 原始字符串中，彻底杜绝转义问题
- 确认 `generate_icon.py` 生成的 `.ico` 是正确的 PNG-in-ICO 格式
- 验证各平台图标生成逻辑完整（Windows: ICO, macOS: ICNS+ICO fallback, Linux: ICO）

## Impact
- Affected code: `tools/build.py`（仅 `generate_spec()` 函数）
- 风险等级: **低** — 移除冗余条目 + 修正路径格式，不影响图标嵌入功能

## MODIFIED Requirements

### Requirement: 图标打包路径
PyInstaller 打包时 SHALL 仅通过 `EXE(icon=...)` 参数嵌入图标，不应将图标文件放入 `datas` 列表。

#### Scenario: onedir 模式构建
- **WHEN** 执行 `uv run python tools/build.py --onedir`
- **THEN** 生成的 EXE 文件包含图标（通过 `EXE(icon=...)` 嵌入）
- **AND** `datas` 列表中不包含图标文件条目

#### Scenario: 图标文件不存在
- **WHEN** 图标文件未生成（如 macOS 无 sips 工具）
- **THEN** 构建正常进行，仅无图标嵌入，不报错