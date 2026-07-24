# Python 3.14 全面升级 Spec

## Why
项目当前基于 Python 3.14，已完成 `toml` → `tomllib`+`tomli-w` 替换、类型注解现代化、Python 版本升级等核心工作。但存在以下遗留问题：
1. `tools/build.py` 中仍引用已移除的 `toml` 依赖（hiddenimports）
2. 打包后的程序缺少图标
3. 第三方库可能使用了旧版 API 模式（虽然安装的是最新版本）
4. 辅助代码（tools/、.github/）需要同步审查

## 已完成的变更（v1）
- [x] `toml` → `tomllib` + `tomli-w` 替换
- [x] Python 版本升级到 3.14（pyproject.toml、CI workflows、README）
- [x] 类型注解现代化（`X | None`、`dict[str, Any]`、`list[str]`）
- [x] `tomllib.TOMLDecodeError` 增强错误处理
- [x] PEP 758 `except` 语法：已尝试但 Python 3.14.6 不兼容，已回退

## 新增变更（v2）

### 1. 修复 `tools/build.py` 中的 `toml` 残留引用
- 从 `hiddenimports` 列表中移除 `"toml"`（该依赖已从项目中移除）
- 添加 `"tomli_w"` 到 hiddenimports（替代 toml 的写入库）

### 2. 打包程序添加图标
- 创建项目图标文件 `tools/icon.ico`
- 在 `tools/build.py` 的 `generate_spec()` 中为 `EXE()` 添加 `icon` 参数
- 图标文件路径通过 `datas` 打包进产物

### 3. 清理 `from __future__ import annotations`
- Python 3.14 默认启用延迟注解求值（PEP 649/749），无需 `from __future__ import annotations`
- 从 `tools/make.py` 中移除该导入

### 4. 第三方库新特性审查
- 审查所有第三方库的当前使用模式，确认是否使用了最新 API
- 重点检查 `rich`、`rich_argparse`、`pypdf`、`watchdog`、`packaging`、`platformdirs`

### 5. GitHub Actions 工作流审查
- 确认所有 workflows 使用 Python 3.14
- 确认 actions 版本为最新稳定版
- 确认 CI 流程中不包含已移除的 toml 依赖测试

### 6. 全面回归验证
- 单元测试全部通过
- 构建 wheel + sdist 成功
- PyInstaller 打包验证（含图标）
- Lint 检查通过

## Impact
- Affected specs: 无
- Affected code: `tools/build.py`、`tools/make.py`、`.github/workflows/`、`src/pytexmk/`
- 风险等级: **低** — 主要为修复和补充，无 BREAKING 变更

---

## ADDED Requirements

### Requirement: 打包程序图标
PyInstaller 打包的程序 SHALL 包含自定义图标。

#### Scenario: onedir 模式构建
- **WHEN** 执行 `uv run python tools/build.py --onedir`
- **THEN** 生成的 EXE 文件包含项目图标

#### Scenario: onefile 模式构建
- **WHEN** 执行 `uv run python tools/build.py --onefile`
- **THEN** 生成的单文件 EXE 包含项目图标

### Requirement: hiddenimports 不包含已移除依赖
`tools/build.py` 的 `hiddenimports` 列表 SHALL 不包含已从项目中移除的第三方库。

#### Scenario: PyInstaller 构建
- **WHEN** 执行 PyInstaller 打包
- **THEN** hiddenimports 仅包含实际使用的依赖（`tomli_w` 替代 `toml`）

### Requirement: 移除冗余的 `from __future__ import annotations`
Python 3.14 项目中 SHALL 移除 `from __future__ import annotations`（PEP 649/749 默认行为）。

#### Scenario: 代码审查
- **WHEN** 检查项目代码
- **THEN** 不存在 `from __future__ import annotations` 导入

## MODIFIED Requirements

### Requirement: Python 3.14 最低版本
项目 SHALL 要求 Python 3.14 或更高版本。（已实施）

### Requirement: TOML 解析使用内置库
系统 SHALL 使用 `tomllib` 进行 TOML 读取，使用 `tomli-w` 进行 TOML 写入。（已实施）

### Requirement: 延迟注解求值（PEP 649/749）
类型注解 SHALL 利用 Python 3.14 默认的延迟求值特性。（已实施）