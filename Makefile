# ==============================================================================
# PyTeXMK Makefile - 项目构建与开发自动化脚本
# ==============================================================================
# 使用方法：make <目标>
# 示例：
#   make build   - 构建源码模式的可执行程序（onedir 目录）
#   make clean   - 清理所有构建产物
#   make whl     - 构建 wheel 和 sdist 分发包
#   make help    - 显示所有可用目标及说明
# ==============================================================================

# 默认目标：显示帮助
.DEFAULT_GOAL := help

# 这些目标是命令而非同名文件/目录；尤其 `build` 与 PyInstaller 的 build/ 目录同名，
# 不声明 .PHONY 时 `make build` 可能被目录时间戳误判为“已是最新”。
.PHONY: help build icon whl inswhl clean pot add-lang update mo dryrun actions upload

# 当前 dist 下的 wheel；inswhl 直接交给外层 uv，避免 uv run 嵌套 uv tool 时的锁冲突
WHL = $(wildcard dist/*.whl)

# Windows 下使用 cmd 作为 shell（确保 echo 等内置命令可用）
ifeq ($(OS),Windows_NT)
SHELL := cmd.exe
endif

# ------------------------------------------------------------------------------
# 帮助信息
# ------------------------------------------------------------------------------
# 显示可用目标列表（详细说明见 Makefile 中的注释）
help:
	@echo PyTeXMK - 可用目标：
	@echo   build    构建源码模式可执行文件（单目录打包）
	@echo   icon     根据标志图生成各平台图标
	@echo   whl      构建 Python 分发包（wheel 包 + sdist 源码包）
	@echo   inswhl   安装本地编译生成的 wheel 包
	@echo   clean    清理所有构建产物
	@echo   pot      提取文本字符串至 POT 模板文件（locale/templates/*.pot）
	@echo   add-lang 交互式新增语言代码并初始化全部 .po 文件
	@echo   update   重新提取 POT，合并更新到所有已有语言的 .po 文件
	@echo   mo       将所有语言的 .po 文件编译为二进制 .mo 文件
	@echo   dryrun   触发 GitHub Actions 打包 dry_run（只构建不发布，默认跟踪结果）
	@echo   actions  检查 CI 引用的 action 是否有新版本（ARGS=--apply 可直接更新）
	@echo   upload   上传包至 PyPI
	@echo   help     显示本帮助信息

# ------------------------------------------------------------------------------
# 构建相关目标
# ------------------------------------------------------------------------------

# 构建源码模式可执行程序（onedir 目录模式） - 产物：dist/pytexmk/
# 依赖 mo：保证打包进二进制的 .mo 与当前 .po 一致，避免发布旧译文。
build: mo
	@uv run python ./tools/build/pack_binary.py pack

# 从项目 logo 生成各平台特定的图标文件
# - 输入: imgs/pytexmk-logo.png
# - 输出:
#   - tools/icon.ico  - Windows 多尺寸图标 (16/32/48/64/128/256px)
#   - tools/icon.icns - macOS 图标包（仅在 macOS 上生成）
#   - tools/icon.png  - Linux 256x256 PNG 图标
# - 需要 Pillow 库（已在 dev 依赖中）
icon:
	@uv run python ./tools/build/generate_icon.py

# 清理后构建 Python 分发包（wheel + sdist）
# - 先执行 clean 清理旧产物
# - 先执行 mo：.po 改过但忘记编译时，不能把旧 .mo 打进 wheel
# - 使用 uv build 构建 wheel 和源码分发包
# - 产物输出到 dist/ 目录
whl: clean mo
	uv build

# 安装本地构建的 wheel 包
# - 用于本地测试安装后的程序行为
# - 注意：不要在 `uv run` 里再调 `uv tool`：父 uv 会持有工具目录锁，
#   Windows 上子 uv 会因 `.lock` 拒绝访问而失败。这里直接在 Makefile 外层执行。
# - 卸载失败（未安装）不阻断后续安装
inswhl:
	-@uv tool uninstall pytexmk
	@uv tool install $(WHL)

# ------------------------------------------------------------------------------
# 清理相关目标
# ------------------------------------------------------------------------------

# 清理所有构建和打包产生的临时文件与目录
# - 删除 build/ (PyInstaller 工作目录)
# - 删除 dist/ (打包产物目录)
# - 删除 staging/ (CI 打包临时目录)
# - 删除根目录下所有 .spec 文件 (PyInstaller 规格文件)
clean:
	@uv run python ./tools/build/pack_binary.py clean

# ------------------------------------------------------------------------------
# 文档相关目标
# ------------------------------------------------------------------------------
# docs/ 目前是 Markdown 源，没有 RST/Sphinx 构建链；旧 all/rst 目标调用的
# 未注册子命令已直接退出 1，相关目标已移除，避免误导。

# ------------------------------------------------------------------------------
# 国际化 (i18n) 相关目标 —— 严格遵循 pybabel 官方 4 命令工作流
# 工作流：pot (extract) → add-lang (init) → update (合并新 msgid) → mo (compile)
# ------------------------------------------------------------------------------

# 1) pot：从 Python 源码的 _() 标记中提取 msgid，生成 POT 翻译模板（语言无关）
#    · 仅扫 src/pytexmk/**/*.py
#    · 输出到 src/pytexmk/locale/templates/<domain>.pot（Babel/gettext 目录规范：模板单独存放，不隶属于具体 locale）
pot:
	@uv run python ./tools/i18n/babel.py pot

# 2) add-lang：交互式新增一种语言 —— 终端询问 locale code（如 en_US / ja_JP / fr_FR / zh_Hans）
#    · 先确保 pot 最新；为所有 domain 生成对应的 .po 翻译文件
#    · 若该语言已存在则不覆盖，改为提示使用 update
add-lang:
	@uv run python ./tools/i18n/babel.py add-lang

# 3) update：重新抽取 POT 模板，然后将新 msgid 合并到所有已存在 locale 的 .po 文件
#    · 自动扫所有 locale（只要 locale/<x>/LC_MESSAGES/ 存在即视为一种语言）
#    · 使用 pybabel update 合并，保留已填的 msgstr，不会被覆盖；缺的 domain 自动补 init
#    · 合并完成后人工补空 msgstr，再跑 mo 编译
update:
	@uv run python ./tools/i18n/babel.py update

# 4) mo：将所有已存在 locale 的 .po 翻译文件编译为二进制 .mo（pybabel compile；运行时由标准库 gettext 加载）
#    · 某个 .po 缺只会 warning 跳过，不会抛错阻塞其他语言
mo:
	@uv run python ./tools/i18n/babel.py mo

# ------------------------------------------------------------------------------
# 发布相关目标
# ------------------------------------------------------------------------------

# 上传分发包到 PyPI
# - 需先配置 PyPI API token
# - 上传前请确保已运行 make whl 构建产物
upload:
	@uv run python ./tools/release/upload.py upload

# 触发 GitHub Actions 的 Release 工作流做一次 dry_run：只构建、不发布
# - 用于在打 tag 前验证打包链路（Linux manylinux_2_28 容器、macOS arm64、glibc 门禁、环境探针）
# - 需要 GitHub token：设置 GH_TOKEN / GITHUB_TOKEN，或先 gh auth login（需 actions:write）
# - 跑的是远端代码：本地改动要先 push，否则测的是旧版本
# - 脚本只用标准库，故走 --no-project，不受 .venv 平台切换影响
#   make dryrun                 触发并跟踪到结束（失败时命令返回非 0）
#   make dryrun ARGS=--check    只校验 token 与目标，不真的触发
#   make dryrun ARGS=--no-watch 触发后立即返回，只打印运行地址
dryrun:
	@uv run --no-project python ./tools/release/ci_dryrun.py $(ARGS)

# 检查 .github/workflows 与 .github/actions 引用的 action 版本
#   make actions              只读检查；有过期引用时退出码 1
#   make actions ARGS=--apply 把可升级的 semver 引用改写为最新标签（主版本标签不动）
actions:
	@uv run --no-project python ./tools/release/check_actions.py $(ARGS)

# 注意：winget 发布不提供本地/Make 入口。
# 发布完全在 GitHub Action（Release.yml 的 publish-to-winget job）内联调用
# 官方 wingetcreate 完成；版本号取 src/pytexmk/version.py 的 __version__。
