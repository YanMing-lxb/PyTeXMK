# PyInstaller onedir 模式多余 EXE 修复 Spec

## Overview
- **Summary**: 修复 PyInstaller onedir 构建后 dist 根目录残留无法运行的多余 `pytexmk.exe` 文件的问题
- **Purpose**: onedir 模式构建后 dist 根目录存在一个无法加载 Python DLL 的残缺 EXE，正确的 EXE 在 `dist/PyTeXMK/` 子目录内。用户可能误执行根目录的 EXE 导致报错
- **Target Users**: 所有下载/使用 PyInstaller 打包的 PyTeXMK 可执行文件的用户（Windows/macOS/Linux）

## Goals
- onedir 模式构建后，dist 根目录**不再**出现多余的 `pytexmk.exe`（Windows）或 `pytexmk`（macOS/Linux）
- 正确的可执行文件**仅**位于 COLLECT 输出目录（`dist/PyTeXMK/` 或重命名后的版本目录）内
- 可执行文件能正常启动、加载 Python DLL 和所有依赖
- onefile 模式不受影响（EXE 直接在 dist 根目录是正确行为）

## Non-Goals (Out of Scope)
- 不改变 PyInstaller 打包的其他行为（图标嵌入、UPX 压缩、hiddenimports 等）
- 不改变 wheel/sdist 打包流程
- 不改变 macOS 的 `pytexmk-bin → PyTeXMK` 重命名逻辑
- 不修改 `copy_additional_files` 或 `rename_output` 的文件复制逻辑

## Background & Context
PyInstaller 6.x 的 onedir 模式需要 EXE() 调用中包含 `exclude_binaries=True` 参数：

```python
# onedir 模式（正确写法）:
exe = EXE(pyz, a.scripts, [], exclude_binaries=True, name='app', ...)
coll = COLLECT(exe, a.binaries, a.zipfiles, a.datas, name='app')

# onefile 模式（正确写法）:
exe = EXE(pyz, a.scripts, a.binaries, a.zipfiles, a.datas, name='app', ...)
# （无 COLLECT）
```

缺少 `exclude_binaries=True` 时：
1. PyInstaller 将 EXE 视为"半独立"构建，输出到 dist 根目录
2. COLLECT 再将 EXE 及所有依赖复制到 dist/PyTeXMK/ 目录
3. 根目录的 EXE 找不到 `_internal/` 下的 DLL（因为 `_internal/` 在 PyTeXMK/ 子目录中）
4. 报错：`Failed to load Python DLL ... LoadLibrary: ?????????`

当前代码 [build.py#L93-L94](file:///d:/Document%20YM/Desktop%20Document/Tools_Development/PyTeXMK/tools/build.py#L93-L94) 中 onedir 模式的 EXE 第三个参数是 `[]` 但缺少 `exclude_binaries=True`。

## Functional Requirements
- **FR-1**: onedir 模式下，EXE() 调用必须包含 `exclude_binaries=True`
- **FR-2**: onedir 模式构建完成后，dist 根目录不得存在独立的可执行文件（仅应有 COLLECT 目录）
- **FR-3**: COLLECT 目录内的可执行文件必须可正常运行
- **FR-4**: onefile 模式下 EXE 行为不变（dist 根目录直接输出单个可执行文件）
- **FR-5**: macOS onedir 模式下 exe 重命名逻辑（pytexmk-bin → PyTeXMK）仍然正常工作
- **FR-6**: 三平台（Windows/macOS/Linux）均正确

## Non-Functional Requirements
- **NFR-1**: 修复后构建产物大小不应显著变化
- **NFR-2**: 构建时间不应显著增加
- **NFR-3**: 现有图标嵌入功能继续正常工作

## Constraints
- **Technical**: Python 3.14, PyInstaller 6.x, 跨平台兼容
- **Dependencies**: `tools/generate_icon.py` 图标生成逻辑不变
- **Platform**: 修复必须在 Windows/macOS/Linux 三平台生效（通过模板生成的 spec 文件控制）

## Assumptions
- PyInstaller 6.x 在所有平台上均使用 `exclude_binaries=True` 作为 onedir 模式的标准参数
- `rename_macos_onedir_exe()` 查找 COLLECT 目录内的 exe 重命名，exclude_binaries=True 不影响此逻辑（因为 COLLECT 仍然将 exe 放在目录内）
- `copy_additional_files()` 将 README/LICENSE 等复制到 COLLECT 目录，此逻辑不受影响

## Acceptance Criteria

### AC-1: onedir 构建 dist 根目录无多余 EXE
- **Given**: 执行 `uv run make build-exe`（onedir 模式）
- **When**: 构建成功完成
- **Then**: dist 根目录下**不**存在 `pytexmk.exe`（Windows）或 `pytexmk`（macOS/Linux）
- **Then**: dist 根目录下仅有 `PyTeXMK/` 目录（或带版本号的目录）
- **Verification**: `programmatic`

### AC-2: COLLECT 目录内 EXE 可正常运行
- **Given**: onedir 构建成功
- **When**: 执行 `dist/PyTeXMK/pytexmk.exe -h`（或对应平台可执行文件）
- **Then**: 正常输出帮助信息，不出现 DLL 加载错误
- **Verification**: `programmatic`

### AC-3: onefile 模式不受影响
- **Given**: 执行 `uv run make build-exe-onefile`（onefile 模式）
- **When**: 构建成功完成
- **Then**: dist 根目录存在单个 `pytexmk.exe`（或对应平台名称）
- **Then**: 该 EXE 可正常运行
- **Verification**: `programmatic`

### AC-4: 三平台均无此问题
- **Given**: 检查生成的 spec 文件模板
- **When**: 分别在 Windows/macOS/Linux 条件下生成 spec
- **Then**: onedir 模式的 EXE() 调用均包含 `exclude_binaries=True`
- **Verification**: `programmatic`（检查生成的 spec 模板字符串）

### AC-5: 图标和其他 EXE 参数正确
- **Given**: 构建成功
- **When**: 查看生成的 EXE
- **Then**: EXE 包含嵌入的图标（Windows 下文件资源管理器可见自定义图标）
- **Verification**: `human-judgment`

## Open Questions
- 无
