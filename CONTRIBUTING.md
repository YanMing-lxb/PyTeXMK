# 贡献指南

感谢你对 PyTeXMK 的关注！我们欢迎任何形式的贡献，包括但不限于：报告 Bug、提出新功能建议、改进文档、提交代码。

## 开发环境搭建

本项目使用 [uv](https://github.com/astral-sh/uv) 进行 Python 环境管理。

```bash
# 克隆仓库
git clone https://github.com/YanMing-lxb/PyTeXMK.git
cd PyTeXMK

# 安装开发依赖
uv sync
```

## 常用开发命令

项目提供统一的 Makefile / task runner（`tools/make.py`），推荐使用 `make` 命令：

| 命令 | 说明 |
|------|------|
| `make help` | 显示所有可用命令 |
| `make test` | 运行单元测试 |
| `make test-cov` | 运行测试并生成覆盖率报告 |
| `make lint` | Ruff 代码规范检查 |
| `make lint-fix` | 自动修复 lint 问题 |
| `make format` | Ruff 格式化代码 |
| `make build` | 构建 wheel 和 sdist 包 |
| `make i18n-update` | 更新国际化翻译文件 |
| `make ci-test` | 运行完整 CI 测试流程 |
| `make clean` | 清理构建产物 |

如果没有 GNU Make，也可以直接使用 Python 运行：

```bash
uv run python tools/make.py test
uv run python tools/make.py lint
uv run python tools/make.py build
```

## 代码规范

- 遵循 [PEP 8](https://peps.python.org/pep-0008/) 编码规范
- 使用 [Ruff](https://github.com/astral-sh/ruff) 进行代码检查和格式化
- 所有公开函数和方法需添加类型注解（Type Hints）
- 使用 Python 3.13+ 语法特性（如 `X | None` 替代 `Optional[X]`）
- 保持代码简洁，避免过度设计

## 提交 PR 流程

1. **Fork 仓库**：在 GitHub 上 Fork 本仓库到你的账号下
2. **创建分支**：从 `main` 分支创建功能分支，命名规范：`feature/xxx`、`fix/xxx`、`docs/xxx`
3. **编写代码**：在本地进行开发，确保代码符合规范
4. **运行测试**：确保所有测试通过（`make test`）
5. **运行 Lint**：确保代码风格符合要求（`make lint`）
6. **提交代码**：编写清晰的 Commit Message，参考 [Conventional Commits](https://www.conventionalcommits.org/)
7. **创建 PR**：向 `main` 分支提交 Pull Request，填写 PR 模板
8. **等待审核**：维护者会审核你的代码，可能需要修改

## 测试要求

- 新功能必须包含对应的单元测试
- 修复 Bug 需要包含回归测试
- 测试文件位于 `tests/` 目录
- 使用 pytest 框架，测试标记：
  - `@pytest.mark.unit`：单元测试
  - `@pytest.mark.integration`：集成测试
  - `@pytest.mark.regression`：回归测试
  - `@pytest.mark.slow`：慢测试（真实编译）
  - `@pytest.mark.requires_latex`：需要 TeX 环境

```bash
# 运行所有测试
make test

# 运行特定测试
pytest tests/test_compile.py -v

# 运行并生成覆盖率报告
make test-cov
```

## Issue 报告规范

### Bug 报告

请使用以下模板：

- **环境信息**：操作系统、Python 版本、PyTeXMK 版本
- **问题描述**：清晰描述 Bug 的表现
- **复现步骤**：提供最小复现案例
- **期望行为**：描述你期望的正确行为
- **实际行为**：描述实际发生的行为
- **日志信息**：使用 `-vb` 参数运行，提供完整输出

### 功能建议

- **使用场景**：描述你的使用场景
- **建议内容**：清晰描述你期望的功能
- **替代方案**：是否有其他方案可以达到类似效果

## 项目结构

```
PyTeXMK/
├── src/pytexmk/          # 源代码
│   ├── __main__.py       # 程序入口
│   ├── workflow.py       # 工作流编排
│   ├── cli_args.py       # CLI 参数解析
│   ├── compile.py        # 编译核心
│   ├── toolchain.py      # 工具链适配
│   ├── engine_detect.py  # 引擎智能检测
│   ├── log_analysis.py   # 日志解析
│   ├── watcher.py        # 文件监听（PVC）
│   ├── config.py         # 配置文件管理
│   ├── i18n.py           # 国际化
│   ├── constants.py      # 常量定义
│   ├── console.py        # 控制台输出
│   ├── exceptions.py     # 自定义异常
│   └── version.py        # 版本信息
├── tests/                # 测试文件
├── docs/                 # 文档
├── tools/                # 构建工具
├── .github/              # GitHub 配置
├── locale/               # 翻译文件
├── README.md             # 中文 README
├── README.en.md          # 英文 README
├── CHANGELOG.md          # 更新日志
├── LICENSE               # 开源协议
├── Makefile              # GNU Make 入口
└── pyproject.toml        # 项目配置
```

## 行为准则

- 尊重所有贡献者，保持友好和专业的交流
- 对新手保持耐心，乐于解答问题
- 接受建设性批评，专注于技术讨论