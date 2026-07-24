# .pot 文件英译补全与修正 Spec

## Why
项目国际化（i18n）的 .pot 翻译模板文件中，349 条可翻译条目里有 194 条 `msgstr` 为空（未翻译），另有 8+ 条已有翻译存在严重错误（占位符不匹配、语义完全相反、标点不一致等）。这导致英文 locale 下大量信息仍显示中文，且部分已翻译条目会引发 Python `python-format` 格式校验失败。

## What Changes
- 将所有 17 个 .pot 文件中空的 `msgstr ""` 填写为正确的英文翻译
- 修正 8+ 条已有翻译中的错误：
  - 修复占位符不匹配问题（`%(args)s` vs `%(args1)s`、硬编码替代占位符等）
  - 修正语义完全错误的翻译（如"加载"译为"创建"、"存在以下问题"译为"does not exist"）
  - 修正标点不一致问题（多余冒号、多余句号）
  - 移除不应有的 `fuzzy` 标记（翻译正确但被误标）
- 移除 `#, fuzzy` 标记（header 除外），确保所有条目为确定翻译

## Impact
- Affected code: `src/pytexmk/locale/en/*.pot`（17 个文件）
- 间接影响：编译后的 `.mo` 文件需重新生成以反映翻译更新
- 不影响源代码逻辑，仅影响 i18n 显示文本

## ADDED Requirements
### Requirement: 完整的英文翻译
所有 .pot 文件中的 `msgstr` 字段必须填写正确的英文翻译，不得留空（header 除外）。

#### Scenario: 空 msgstr 补全
- **WHEN** .pot 文件中某条目的 `msgstr` 为空
- **THEN** 填入与 `msgid` 语义一致的英文翻译，保留所有格式占位符（如 `%(args)s`、`%(size).3f`）

### Requirement: 占位符一致性
所有标记为 `#, python-format` 或 `#, python-brace-format` 的条目，其 `msgstr` 中的占位符必须与 `msgid` 完全匹配。

#### Scenario: 占位符匹配
- **WHEN** msgid 包含 `%(args)s` 占位符
- **THEN** msgstr 必须包含相同的 `%(args)s` 占位符，不得替换为硬编码值或其他占位符名

## MODIFIED Requirements
### Requirement: 翻译准确性
已有翻译中存在语义错误的条目必须修正为与 `msgid` 含义一致的英文翻译。

#### Scenario: 语义修正
- **WHEN** msgstr 的含义与 msgid 不一致（如"加载"译为"创建"）
- **THEN** 修正 msgstr 使其与 msgid 语义一致

#### Scenario: 标点一致性
- **WHEN** msgstr 包含 msgid 中不存在的标点（如多余冒号、句号）
- **THEN** 移除多余标点，使标点与 msgid 一致

### Requirement: fuzzy 标记清理
翻译正确的条目不应保留 `fuzzy` 标记；翻译错误的条目在修正后应移除 `fuzzy` 标记。

#### Scenario: 移除正确翻译的 fuzzy 标记
- **WHEN** 条目的翻译正确但被标记为 `fuzzy`
- **THEN** 移除 `#, fuzzy` 标记，保留格式标记（如 `#, python-format`）
