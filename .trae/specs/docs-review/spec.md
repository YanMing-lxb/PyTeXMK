# 项目文档全面审查与改进 Spec

## Why
项目代码框架已通过 architecture-review 优化完成。但文档层面存在中英文 README 不对称、关键文档缺失（CONTRIBUTING.md）、部分文件包含过时的 HTML 注释格式、GitHub 模板链接断裂等问题，影响项目的专业性和可维护性。

## What Changes
- 大幅扩展 `README.en.md`，使其与中文版 `README.md` 内容对齐（当前英文版仅 275 行，中文版 725 行）
- 修正 `README.md` 中 Python 版本要求表述（从"3.13"改为"3.13+"，与 pyproject.toml 一致）
- 修正 `README.en.md` 中不存在的 `--language` CLI 参数（实际为 `PYTEXMK_LANG` 环境变量）
- 创建 `CONTRIBUTING.md` 贡献指南（PR 模板中引用了但文件不存在）
- 修复 `.github/pull-request-template.md` 中的断裂链接 `[贡献者指南]()`
- 清理 `CHANGELOG.md` 和 docs/ 文件中的过时 HTML 注释格式
- 更新 `pyproject.toml` 的 Python 版本分类器，增加 3.14 支持
- 在 `README.md` 主命令表中补充 PVC 和 LaTeXDiff 的所有子参数
- 更新 `tools/scoop/pytexmk.json` 的 hash 字段说明

## Impact
- Affected specs: 无
- Affected code: `README.md`, `README.en.md`, `CHANGELOG.md`, `CONTRIBUTING.md`（新建）, `.github/pull-request-template.md`, `pyproject.toml`, `docs/`, `tools/scoop/pytexmk.json`
- 风险等级: **低** — 仅文档变更，不影响代码功能

---

## MODIFIED Requirements

### Requirement: 中英文 README 内容对齐
英文版 README 应包含与中文版同等的完整信息，包括：魔法注释详解、配置文件详解、环境变量、使用案例、FAQ、贡献指南、GitHub Actions 集成等。

#### Scenario: 英文用户获取完整信息
- **WHEN** 英文用户访问 README.en.md
- **THEN** 能看到与中文版同等详细的安装、配置、使用、FAQ 和贡献信息

### Requirement: 修正 README 中的技术错误
- README.md 环境要求中"Python 3.13"应改为"Python 3.13+"以匹配 pyproject.toml 中的 `>=3.13`
- README.en.md 中 `--language LANG` 参数不存在，应改为 `PYTEXMK_LANG` 环境变量说明

#### Scenario: 版本要求一致
- **WHEN** 用户按 README 安装
- **THEN** Python 版本要求与 pyproject.toml 一致

### Requirement: 创建缺失的贡献指南
项目 PR 模板中引用了 `[贡献者指南]()` 但 CONTRIBUTING.md 文件不存在，需创建。

#### Scenario: 新贡献者上手
- **WHEN** 新贡献者阅读 PR 模板
- **THEN** 能通过链接访问完整的贡献指南

### Requirement: 清理过时格式
`CHANGELOG.md`、`docs/` 文件夹中的 HTML 注释格式（`<!-- ... -->`）应改为标准 Markdown 格式，与项目整体风格一致。

#### Scenario: 文档格式统一
- **WHEN** 查看项目文档
- **THEN** 所有 .md 文件使用一致的 Markdown 格式，无 HTML 注释包裹的元数据

---

## ADDED Requirements

### Requirement: 创建 CONTRIBUTING.md
项目 SHALL 提供完整的贡献指南，包括开发环境搭建、代码规范、提交 PR 流程、测试要求等。

#### Scenario: 开发者贡献流程
- **WHEN** 开发者想贡献代码
- **THEN** 能通过 CONTRIBUTING.md 了解完整的开发环境和贡献流程

### Requirement: README 主命令表补充完整
中文 README 的主命令参考表应包含 PVC 和 LaTeXDiff 的所有子参数，而非仅在子章节中提及。

#### Scenario: 用户快速查阅命令
- **WHEN** 用户查看主命令参考表
- **THEN** 能找到所有可用参数，无需跳转到子章节