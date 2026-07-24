# 修复国际化默认语言为中文 Spec

## Why
项目以简体中文为源语言（msgid 为中文），英文翻译通过 gettext `.mo` 文件提供。但 `language.py` 的 `_detect_language()` 在中文 Windows 系统上检测失败，错误地 fallback 到英文，导致大量本应显示中文的 `_()` 包裹字符串显示为英文。同时 `engine_detect.py` 和 `additional.py` 中存在未用 `_()` 包裹的硬编码中文字符串，造成中英混杂的输出。

## What Changes
- **修复 `_detect_language()` 的 Windows 语言检测**：
  - 在 locale 名称匹配中增加 `"chinese"` 子串检测（Windows 返回 `'chinese (simplified)_china'` 等格式）
  - 添加 Windows 原生 API 检测（`ctypes` + `GetUserDefaultLocaleName`），返回 BCP-47 名称如 `zh-CN`
  - 将默认 fallback 从 `"en"` 改为 `"zh_CN"`（因为中文是源语言，未知 locale 更可能是中文系统配置异常）
- **包裹 `engine_detect.py` 中 21 个硬编码中文字符串**：所有 `reason_parts.append(...)` 和 `auto_reason` 赋值用 `_()` 包裹
- **包裹 `additional.py` 中 2 个硬编码中文字符串**：`console.status` 文本和成功消息
- 重新生成受影响模块的 `.pot` 文件并编译 `.mo` 文件

## Impact
- Affected code:
  - `src/pytexmk/language.py` — 核心检测逻辑修改
  - `src/pytexmk/engine_detect.py` — 21 处字符串包裹
  - `src/pytexmk/additional.py` — 2 处字符串包裹
  - `src/pytexmk/locale/en/*.pot` 和 `*.mo` — 重新生成和编译
- 不影响编译逻辑、配置解析、工具链调度等核心功能
- 向后兼容：`PYTEXMK_LANG` 环境变量优先级不变，用户仍可手动指定语言

## ADDED Requirements

### Requirement: Windows 原生语言检测
系统 SHALL 在 Windows 平台上使用 `ctypes` 调用 `GetUserDefaultLocaleName` 获取用户区域设置，返回 BCP-47 格式名称（如 `zh-CN`、`en-US`），以可靠检测系统语言。

#### Scenario: 中文 Windows 检测
- **WHEN** 程序在中文 Windows 上运行且未设置 `PYTEXMK_LANG` 等环境变量
- **THEN** `_detect_language()` 返回 `"zh_CN"`，所有 `_()` 包裹的字符串显示中文

#### Scenario: 英文 Windows 检测
- **WHEN** 程序在英文 Windows 上运行
- **THEN** `_detect_language()` 返回 `"en"`，`_()` 包裹的字符串显示英文

### Requirement: 默认 fallback 为中文
当所有检测方法均无法确定语言时，系统 SHALL 默认返回 `"zh_CN"` 而非 `"en"`，因为中文是项目的源语言。

#### Scenario: 未知 locale fallback
- **WHEN** 所有环境变量、`locale.getlocale()`、Windows API 均无法识别语言
- **THEN** 返回 `"zh_CN"`，显示中文（源语言）

## MODIFIED Requirements

### Requirement: locale 名称匹配
`_detect_language()` SHALL 在匹配 locale 名称时同时检查 `"zh"` 前缀和 `"chinese"` 子串，以兼容 Windows 风格的 locale 名称（如 `'chinese (simplified)_china'`）。

#### Scenario: Windows 风格 locale 名称
- **WHEN** `locale.getlocale()` 返回 `('Chinese (Simplified) China', '936')`
- **THEN** 匹配 `"chinese"` 子串，返回 `"zh_CN"`

### Requirement: 所有用户可见字符串必须用 `_()` 包裹
`engine_detect.py` 和 `additional.py` 中所有用户可见的中文字符串 SHALL 使用 `_()` 包裹，以支持国际化翻译。

#### Scenario: 引擎选择原因字符串
- **WHEN** 用户查看引擎选择原因（如"配置文件默认使用 xelatex"）
- **THEN** 该字符串通过 `_()` 包裹，在英文 locale 下显示英文翻译

#### Scenario: 命令执行成功消息
- **WHEN** 命令执行成功显示"运行 X 成功（耗时: Ys）"
- **THEN** 该字符串通过 `_()` 包裹，在英文 locale 下显示英文翻译
