# Tasks

- [x] Task 1: 修复 `language.py` 的 `_detect_language()` 函数
  - [x] 1.1 在 locale 名称匹配中增加 `"chinese"` 子串检测（line 85: `if lang_code.startswith("zh") or "chinese" in lang_code:`）
  - [x] 1.2 添加 Windows 原生 API 检测（`ctypes` + `GetUserDefaultLocaleName`），在 `locale.getencoding()` 检测之后、fallback 之前
  - [x] 1.3 将默认 fallback 从 `"en"` 改为 `"zh_CN"`（line 88: `return "zh_CN"`）

- [x] Task 2: 包裹 `engine_detect.py` 中 21 个硬编码中文字符串
  - [x] 2.1 包裹 `reason_parts.append(f"CLI 指定使用 {norm}")` 等 reason 字符串（lines 324, 329, 334, 367, 392, 435, 440, 445, 448, 461, 503, 508, 513, 516, 525）
  - [x] 2.2 包裹 `auto_reason` 赋值字符串（lines 347, 351, 354, 357, 360）
  - [x] 2.3 确保所有 f-string 中的变量插值正确处理（使用 `%(var)s` 占位符 + `%` 操作符）

- [x] Task 3: 包裹 `additional.py` 中 2 个硬编码中文字符串
  - [x] 3.1 包裹 `console.status` 文本（line 179: `_("[status]正在 %(program)s...") % {"program": program_name}`）
  - [x] 3.2 包裹成功消息（line 224: `_("✓ 运行 %(program)s 成功 [time](耗时: %(duration)s)[/]") % {...}`）

- [x] Task 4: 重新生成 .pot 文件并编译 .mo 文件
  - [x] 4.1 重新生成 `engine_detect.pot`（新增 15 条翻译条目，部分多引用合并）
  - [x] 4.2 重新生成 `additional.pot`（新增 2 条翻译条目）
  - [x] 4.3 为新增条目填写英文翻译
  - [x] 4.4 运行 `msgfmt` 编译 `engine_detect.mo` 和 `additional.mo`
  - [x] 4.5 运行 `msgfmt --check` 验证所有 .pot 文件无错误

- [x] Task 5: 验证和测试
  - [x] 5.1 运行单元测试确认无回归（327 passed, 6 deselected）
  - [x] 5.2 验证 `PYTEXMK_LANG=en` 时 `_detect_language()` 返回 `"en"`
  - [x] 5.3 验证 `PYTEXMK_LANG=zh_CN` 时 `_detect_language()` 返回 `"zh_CN"`
  - [x] 5.4 验证未设置环境变量时 `_detect_language()` 默认返回 `"zh_CN"`

# Task Dependencies
- Task 1 可独立执行
- Task 2, 3 可并行执行（依赖 Task 1 完成以确认 `_` 可用）
- Task 4 依赖 Task 2, 3 完成（需要新的 `_()` 包裹才能提取字符串）
- Task 5 依赖 Task 4 完成
