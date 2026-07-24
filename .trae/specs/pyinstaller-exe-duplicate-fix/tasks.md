# PyInstaller onedir 多余 EXE 修复 - Implementation Plan

## [x] Task 1: 修复 build.py 中 onedir 模式 EXE() 缺少 exclude_binaries=True
- **Priority**: high
- **Depends On**: None
- **Description**:
  - 在 `tools/build.py` 的 `generate_spec()` 函数中，onedir 模式下需要为 EXE() 调用添加 `exclude_binaries=True` 参数
  - onefile 模式保持不变（已有二进制内嵌，不需要此参数）
  - 具体修改：新增 `exe_extra_kwargs` 变量，onedir 模式设为 `" exclude_binaries=True,"`，onefile 模式设为 `""`
  - 在 EXE 模板中将 `{exe_extra_kwargs}` 插入 `{exe_third_arg}` 之后
- **Acceptance Criteria Addressed**: AC-1, AC-4
- **Test Requirements**:
  - `programmatic` TR-1.1: 生成的 onedir spec 中 EXE() 调用包含 `exclude_binaries=True` ✅
  - `programmatic` TR-1.2: 生成的 onefile spec 中 EXE() 调用不包含 `exclude_binaries=True` ✅
  - `programmatic` TR-1.3: 三平台（Windows/macOS/Linux）onedir 模式均包含该参数 ✅

## [x] Task 2: 清理之前构建的 dist 目录并重新构建验证
- **Priority**: high
- **Depends On**: Task 1
- **Description**:
  - 清理 build/ 和 dist/ 目录
  - 执行 onedir 构建 (`make build-exe`)
  - 检查 dist 目录结构，确认根目录无多余 EXE
  - 执行 onefile 构建 (`python tools/build.py --onefile --no-rename`)
  - 确认 onefile 模式正常
- **Acceptance Criteria Addressed**: AC-1, AC-2, AC-3, AC-5
- **Test Requirements**:
  - `programmatic` TR-2.1: onedir 构建后 dist/ 下仅有 PyTeXMK/ 目录，无多余 exe ✅
  - `programmatic` TR-2.2: onedir 构建的 dist/PyTeXMK/pytexmk.exe -h 正常输出完整帮助信息 ✅
  - `programmatic` TR-2.3: onefile 构建成功，dist/pytexmk.exe 存在（12.4 MB）✅
  - `programmatic` TR-2.4: 单元测试全部通过（327 passed, 6 deselected）✅
  - `programmatic` TR-2.5: onefile 的 pytexmk.exe -v 输出版本号 1.1.2 ✅
  - `human-judgement` TR-2.6: 构建日志显示 `Copying icon to EXE`，图标嵌入正常 ✅

## [x] Task 3: 验证 macOS 重命名逻辑兼容性
- **Priority**: medium
- **Depends On**: Task 1
- **Description**:
  - 检查 `rename_macos_onedir_exe()` 函数逻辑与 `exclude_binaries=True` 的兼容性
  - 在 is_macos=True 条件下模拟生成 spec，确认 COLLECT 目录内 exe 命名为 pytexmk-bin，重命名后为 PyTeXMK
  - 在 is_linux=True 条件下模拟生成 spec，确认 Linux onedir 也正确
- **Acceptance Criteria Addressed**: AC-4, FR-5
- **Test Requirements**:
  - `programmatic` TR-3.1: 模拟 macOS onedir 生成 spec，EXE name 为 'pytexmk-bin' ✅
  - `programmatic` TR-3.2: COLLECT name 为 'PyTeXMK' ✅
  - `programmatic` TR-3.3: `rename_macos_onedir_exe()` 查找路径 DIST_DIR/PyTeXMK/pytexmk-bin → DIST_DIR/PyTeXMK/PyTeXMK，逻辑正确 ✅
  - `programmatic` TR-3.4: Linux onedir spec 同样包含 exclude_binaries=True ✅
