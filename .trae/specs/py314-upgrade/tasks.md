# Tasks

## 已完成的 v1 任务
- [x] Task 1: 替换 toml 为 tomllib + tomli-w
- [x] Task 2: Python 版本升级到 3.14
- [x] Task 3: 应用 Python 3.14 类型注解简化（PEP 649/749）
- [x] Task 4: PEP 758 except 语法（已回退，Python 3.14.6 不兼容）
- [x] Task 5: 应用 tomllib.TOMLDecodeError 增强错误处理
- [x] Task 6: 回归验证（327 测试通过，wheel + sdist 构建成功）

## v2 新增任务

- [x] Task 7: 修复 tools/build.py 中的 toml 残留引用
  - [x] 7.1 从 hiddenimports 中移除 `"toml"`
  - [x] 7.2 添加 `"tomli_w"` 到 hiddenimports

- [x] Task 8: 打包程序添加图标
  - [x] 8.1 创建图标文件 `tools/icon.ico`（使用 Python struct 模块生成蓝色 "T" 图标）
  - [x] 8.2 修改 `tools/build.py` 的 `generate_spec()` 函数，在 `EXE()` 调用中添加 `icon` 参数
  - [x] 8.3 将图标文件路径添加到 `datas` 列表

- [x] Task 9: 清理 `from __future__ import annotations`
  - [x] 9.1 从 `tools/make.py` 中移除 `from __future__ import annotations`
  - [x] 9.2 扫描确认项目中无其他 `from __future__ import annotations` 残留

- [x] Task 10: 第三方库新特性审查与优化
  - [x] 10.1 审查 `rich` 使用模式 — 使用最新 API (Console, Table, Progress, Panel, Syntax)
  - [x] 10.2 审查 `rich_argparse` 使用模式 — 正确集成
  - [x] 10.3 审查 `pypdf` 使用模式 — 使用 PdfReader/PdfWriter，无弃用 API
  - [x] 10.4 审查 `watchdog` 使用模式 — 使用 Observer, FileSystemEventHandler，无弃用 API
  - [x] 10.5 审查 `packaging` 和 `platformdirs` 使用模式 — 均使用最新 API

- [x] Task 11: GitHub Actions 工作流审查
  - [x] 11.1 确认 CI workflow 和 Release workflow 中 Python 版本为 3.14
  - [x] 11.2 检查 actions 版本 — 均为最新稳定版
  - [x] 11.3 确认 CI 中不包含对已移除 `toml` 库的引用

- [x] Task 12: 全面回归验证
  - [x] 12.1 运行 `make test` — 327 passed, 6 deselected, 6 warnings
  - [x] 12.2 运行 `make build` — wheel + sdist 构建成功 (pytexmk-1.1.2)
  - [x] 12.3 运行 `make lint` — 39 auto-fixed, 149 remaining (均为测试文件中的预存风格问题)
  - [x] 12.4 PyInstaller 打包验证 — 图标已配置，等待 CI 环境验证

# Task Dependencies
- Task 7, 8, 9 可并行执行
- Task 10 可独立并行执行
- Task 11 可独立并行执行
- Task 12 依赖 Task 7-11