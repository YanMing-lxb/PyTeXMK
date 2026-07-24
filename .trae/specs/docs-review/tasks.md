# Tasks

- [x] Task 1: 大幅扩展 README.en.md 与中文版对齐
  - 补充魔法注释详解表格
  - 补充配置文件详解（TOML 配置示例）
  - 补充环境变量说明
  - 补充完整使用案例（中文文档、BibLaTeX、xindy、CI/CD、草稿模式、PDF 修复）
  - 补充 PVC 实时监听模式详细说明
  - 补充 LaTeXDiff 文档对比详细说明
  - 补充 GitHub Actions 集成示例
  - 补充 FAQ 常见问题
  - 补充贡献指南（开发环境、常用命令、代码规范）
  - 补充完整命令参考表（与中文版对齐）
  - 修正 `--language LANG` 为 `PYTEXMK_LANG` 环境变量

- [x] Task 2: 修正 README.md 中的技术问题
  - 将"Python: 3.13 或更高版本"改为"Python: 3.13+"
  - 在主命令参考表中补充 PVC 和 LaTeXDiff 子参数（已存在，无需额外修改）

- [x] Task 3: 创建 CONTRIBUTING.md 贡献指南
  - 开发环境搭建（uv sync）
  - 常用开发命令（make test/lint/format/build）
  - 代码规范（PEP 8、Ruff、类型注解）
  - 提交 PR 流程
  - 测试要求
  - Issue 报告规范

- [x] Task 4: 修复 .github/pull-request-template.md 断裂链接
  - 将 `[贡献者指南]()` 改为 `[贡献者指南](CONTRIBUTING.md)`

- [x] Task 5: 清理 CHANGELOG.md 和 docs/ 中的过时 HTML 注释格式
  - 移除 `CHANGELOG.md` 中的 HTML 注释头部
  - 移除 `docs/Window 下使用 make.md` 和 `docs/辅助文件类型说明.md` 中的 HTML 注释格式，改为标准 Markdown

- [x] Task 6: 更新 pyproject.toml 版本分类器
  - 添加 `Programming Language :: Python :: 3.14` 分类器

- [x] Task 7: 更新 tools/scoop/pytexmk.json
  - 为 hash 字段添加注释说明需要在发布时更新

- [x] Task 8: 回归验证
  - 运行 `make test`：327 passed, 6 deselected
  - 运行 `make build`：wheel + sdist 构建成功

# Task Dependencies
- Task 1、2 可并行执行
- Task 3、4、5、6、7 可并行执行（独立文件）
- Task 8 依赖 Task 1-7