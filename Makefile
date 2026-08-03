# ==============================================================================
# PyTeXMK Makefile - 项目构建与开发自动化脚本
# ==============================================================================
# 使用方法：make <目标>
# 示例：
#   make build   - 构建 Cython 加密的可执行程序
#   make clean   - 清理所有构建产物
#   make whl     - 构建 wheel 和 sdist 分发包
#   make help    - 显示所有可用目标及说明
# ==============================================================================

# 默认目标：显示帮助
.DEFAULT_GOAL := help

# Windows 下使用 cmd 作为 shell（确保 echo 等内置命令可用）
ifeq ($(OS),Windows_NT)
SHELL := cmd.exe
endif

# ------------------------------------------------------------------------------
# 帮助信息
# ------------------------------------------------------------------------------
# 显示可用目标列表（详细说明见 Makefile 中的注释）
help:
	@echo PyTeXMK - Available targets:
	@echo   build    Build Cython-encrypted binary (onedir mode)
	@echo   pydmk    Cython compile all .py to .pyd/.so
	@echo   icon     Generate platform icons from logo
	@echo   whl      Build Python distribution (wheel + sdist)
	@echo   inswhl   Install locally built wheel
	@echo   clean    Clean all build artifacts
	@echo   all      Build all document formats
	@echo   html     Build HTML documents
	@echo   rst      Build RST documents
	@echo   pot      Extract msgid to POT templates (locale/templates/*.pot)
	@echo   add-lang Interactive add a new locale code and init all .po files
	@echo   update   Re-extract POT then merge into all existing locales' .po
	@echo   mo       Compile all locales' .po to binary .mo
	@echo   upload   Upload to PyPI
	@echo   help     Show this help message

# ------------------------------------------------------------------------------
# 构建相关目标
# ------------------------------------------------------------------------------

# 构建 Cython 加密的可执行程序（onedir 目录模式）
# - 默认使用 Cython 加密所有 Python 源码后再打包
# - 如需源码模式打包（不加密），直接运行: uv run python ./tools/pack.py pack --source
# - 产物输出到 dist/pytexmk/ 目录
build:
	@uv run python ./tools/pack.py pack

# 使用 Cython 编译所有 .py 文件为平台扩展模块（仅编译，不打包）
# - Windows 生成 .pyd，Linux/macOS 生成 .so
# - 编译产物输出到 srcpyd/ 目录
# - 主要用于验证 Cython 编译是否正常，或单独使用加密后的源码
pydmk:
	@uv run python ./tools/pydmk.py

# 从项目 logo 生成各平台特定的图标文件
# - 输入: imgs/pytexmk-logo.png
# - 输出:
#   - tools/icon.ico  - Windows 多尺寸图标 (16/32/48/64/128/256px)
#   - tools/icon.icns - macOS 图标包（仅在 macOS 上生成）
#   - tools/icon.png  - Linux 256x256 PNG 图标
# - 需要 Pillow 库（已在 dev 依赖中）
icon:
	@uv run python ./tools/generate_icon.py

# 清理后构建 Python 分发包（wheel + sdist）
# - 先执行 clean 清理旧产物
# - 使用 uv build 构建 wheel 和源码分发包
# - 产物输出到 dist/ 目录
whl: clean
	uv build

# 安装本地构建的 wheel 包
# - 用于本地测试安装后的程序行为
inswhl:
	@uv run python ./tools/make.py inswhl

# ------------------------------------------------------------------------------
# 清理相关目标
# ------------------------------------------------------------------------------

# 清理所有构建和打包产生的临时文件与目录
# - 删除 build/ (PyInstaller 工作目录)
# - 删除 dist/ (打包产物目录)
# - 删除 srcpyd/ (Cython 编译产物目录)
# - 删除 staging/ (CI 打包临时目录)
# - 删除根目录下所有 .spec 文件 (PyInstaller 规格文件)
clean:
	@uv run python ./tools/pack.py clean

# ------------------------------------------------------------------------------
# 文档相关目标
# ------------------------------------------------------------------------------

# 构建所有格式的文档（html + rst 等）
all:
	@uv run python ./tools/make.py all

# 构建 HTML 格式文档
html:
	@uv run python ./tools/make.py html

# 构建 RST 格式文档
rst:
	@uv run python ./tools/make.py rst

# ------------------------------------------------------------------------------
# 国际化 (i18n) 相关目标 —— 严格遵循 pybabel 官方 4 命令工作流
# 工作流：pot (extract) → add-lang (init) → update (合并新 msgid) → mo (compile)
# ------------------------------------------------------------------------------

# 1) pot：从 Python 源码的 _() 标记中提取 msgid，生成 POT 翻译模板（语言无关）
#    · 仅扫 src/pytexmk/**/*.py
#    · 输出到 src/pytexmk/locale/templates/<domain>.pot（gettext 标准：模板单独存放，不隶属于具体 locale）
pot:
	@uv run python ./tools/lang_tool.py pot

# 2) add-lang：交互式新增一种语言 —— 终端询问 locale code（如 en_US / ja_JP / fr_FR / zh_Hans）
#    · 先确保 pot 最新；为所有 domain 生成对应的 .po 翻译文件
#    · 若该语言已存在则不覆盖，改为提示使用 update
add-lang:
	@uv run python ./tools/lang_tool.py add-lang

# 3) update：重新抽取 POT 模板，然后将新 msgid 合并到所有已存在 locale 的 .po 文件
#    · 自动扫所有 locale（只要 locale/<x>/LC_MESSAGES/ 存在即视为一种语言）
#    · 使用 pybabel update 合并，保留已填的 msgstr，不会被覆盖；缺的 domain 自动补 init
#    · 合并完成后人工补空 msgstr，再跑 mo 编译
update:
	@uv run python ./tools/lang_tool.py update

# 4) mo：将所有已存在 locale 的 .po 翻译文件编译为二进制 .mo（程序运行时 gettext 加载）
#    · 某个 .po 缺只会 warning 跳过，不会抛错阻塞其他语言
mo:
	@uv run python ./tools/lang_tool.py mo

# ------------------------------------------------------------------------------
# 发布相关目标
# ------------------------------------------------------------------------------

# 上传分发包到 PyPI
# - 需先配置 PyPI API token
# - 上传前请确保已运行 make whl 构建产物
upload:
	@uv run python ./tools/make.py upload
