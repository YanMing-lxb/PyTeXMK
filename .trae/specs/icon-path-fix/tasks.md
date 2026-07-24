# Tasks

- [x] Task 1: 修复 `build.py` 中的图标处理逻辑
  - [x] 1.1 从 `datas` 列表中移除图标文件条目（图标由 `EXE(icon=...)` 嵌入，无需 datas）
  - [x] 1.2 图标路径使用 `resolve().as_posix()` 生成绝对正斜杠路径，并用 `r'...'` 原始字符串包裹，杜绝 Windows 反斜杠转义问题
  - [x] 1.3 清理冗余条件判断代码

- [x] Task 2: 修复路径转义 Bug（关键修复）
  - [x] 2.1 根因：`str(icon_path.resolve())` 在 Windows 上产生反斜杠路径，`\t` 被解释为制表符，`\D`/`\P` 触发 SyntaxWarning
  - [x] 2.2 修复：改用 `icon_path.resolve().as_posix()` + `r'...'` 原始字符串

- [x] Task 3: 全面检查路径安全性
  - [x] 3.1 确认 `datas` 通过 `{datas!r}`（repr()）正确转义反斜杠
  - [x] 3.2 确认 `project_root` 使用 `r'...'` 原始字符串安全
  - [x] 3.3 确认其他路径均在运行时计算，非字符串插值

- [x] Task 4: 验证三平台图标兼容性
  - [x] 4.1 检查 `generate_icon.py` ICO 格式正确（PNG-in-ICO，Vista+ 通用）
  - [x] 4.2 检查 ICNS 生成逻辑仅在 macOS 执行，非 macOS fallback 到 ICO
  - [x] 4.3 Linux 使用 ICO 格式（PyInstaller 支持）

- [x] Task 5: 回归验证
  - [x] 5.1 运行 `make test`：327 passed, 6 deselected
  - [x] 5.2 运行 `make build`：wheel + sdist 构建成功
  - [x] 5.3 运行 `make build-exe`（onedir）：构建成功，图标正确嵌入（15.2 MB）
  - [x] 5.4 运行 `build.py --onefile`（onefile）：构建成功，图标正确嵌入（12.4 MB）
  - [x] 5.5 确认构建输出无 FileNotFoundError、无 SyntaxWarning

# Task Dependencies
- Task 2 是 Task 1 的关键补充（实际构建暴露了转义 bug）
- Task 5 依赖 Task 1-4