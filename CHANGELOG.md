# CHANGELOG

## v1.0.5 - 2025-07-25

### 🎉 新增

- **三平台 CI/CD 构建**：新增 GitHub Actions 工作流，支持 Linux / Windows / macOS 三平台自动构建可执行程序
  - CI 工作流：每次推送自动测试三平台构建并上传 artifact
  - Release 工作流：推送 tag 时自动发布三平台安装包到 GitHub Release 和 PyPI
- **Cython 跨平台加密**：打包工具支持在 Linux（.so）和 macOS（.so）上进行 Cython 编译，不再仅限 Windows（.pyd）
- **跨平台打包工具**：`tools/pack.py` 支持源码模式和 Cython 加密模式，默认 Cython onedir 模式
- **图标生成工具**：`tools/generate_icon.py` 自动从 logo 生成 Windows ICO（多尺寸）、macOS ICNS、Linux PNG 图标
- **macOS 打包优化**：自动禁用 UPX 压缩，避免 Mach-O 格式兼容性问题
- **统一构建命令**：Makefile 新增 `build` 目标（默认 Cython 加密），移除过时的 `exe` / `exe-cython`

### 🚀 改进

- **Python 版本升级**：最低支持版本提升至 Python 3.14，充分利用新版本特性
- **TOML 库迁移**：从已停止维护的第三方 `toml` 库迁移至标准库 `tomllib`（读取）+ `tomli-w`（写入），减少第三方依赖
- **类型注解现代化**：全面采用 PEP 585（内置泛型 `dict/list`）与 PEP 604（`X | Y` 联合类型）类型注解风格，移除 `typing.Optional/Dict/List/Union` 旧式注解
- **代码清理**：移除 Python 2 时代遗留的兼容代码（`# -*- coding: utf-8 -*-` 声明、`class Foo(object):` 继承、`sys.version_info` 分支判断）
- **CLI 体验优化**：启用 argparse `suggest_on_error` 特性，参数值拼错时给出智能建议
- **第三方库升级**：rich 15.0.0、pypdf 6.14.2、packaging 26.2、platformdirs 4.11.0、rich_argparse 1.8.0 等全部升级至最新稳定版
- **依赖管理**：全面迁移到 [uv](https://github.com/astral-sh/uv) 进行 Python 包管理
- **打包默认 onedir 模式**：移除 onefile 选项，统一使用 onedir 目录模式，提升稳定性和加载速度
- **macOS 大小写兼容修复**：PyInstaller 打包时 --add-data 目标路径统一小写，避免 macOS 大小写敏感路径问题
- **Lint 修复**：修复现代化过程中引入的 lint 问题（类型注解精度、导入排序等）

### 🐛 修复

- 修正 `tools/utils.py` 中错误的类型注解 `func: any` 为 `Callable[..., Any]`
- 修正 4 处 `str = None` 不精确的类型注解为 `str | None = None`
- 修复 `tools/pack.py` 中 pack 模式代码不可达的 bug
- 修复 `--add-data` 路径分隔符硬编码 `;` 导致的跨平台问题，改用 `os.pathsep`
- 修复 `tools/pydmk.py` 中编码硬编码 `gbk` 的问题，改用 `locale.getpreferredencoding()`

### 📝 文档

- 全面美化 README（中英文），新增项目 Logo、功能特性章节、快速开始、开发构建指南
- 更新构建说明为 uv 方式
- CHANGELOG 格式统一

### 其他

- 移除未使用的 `toml` 依赖，新增 `tomli-w` 作为 TOML 写入依赖
- 新增 `pillow` 开发依赖用于图标生成
- 14 个文件通过 `ruff format` 统一代码格式
- GitHub Actions workflow 文件重命名为更规范的 `CI.yml` 和 `Release.yml`

## v1.0.4.251001 - 2025-10-01

### 🐛 修复

- 修改转义错误

## v1.0.3.251001 - 2025-10-01

### 🐛 修复

- 依赖更正

## v1.0.2.250515 - 2025-05-15

### 🚀 改进

- 日志分析器中的优化路径处理
- 优化了日志分析器中的路径处理，使其更通用
- 编译失败后，启用日志解析器

### 🐛 修复

- 修复 LaTeX 编译器运行错误不及时终止程序的问题

## v1.0.1.250506 - 2025-05-06

### 🚀 改进

- 日志分析器拆分 warning 和 info 信息

## v1.0.0.250506 - 2025-05-06

### 🎉 新增

- 新增日志分析器，编译结束后会解析日志内容，并显示在终端中

## v0.9.6.250430 - 2025-04-30

### 🐛 修复

- 国际化

## v0.9.5.250430 - 2025-04-30

### 🎉 新增

- 新增程序运行动画

## v0.9.4.250424 - 2025-04-24

### 🚀 改进

- 优化版本更新检查代码，使其更通用

## v0.9.4.250314 - 2025-03-14

### 🎉 新增

- 🛠 新增配置文件错误检查功能，如果配置文件存在错误，则可以根据提示进行修复
- 📂 新增 auxiliary_fun.py，调整部分函数到辅助方法中

### 🚀 改进

- ⚙ make: 优化代码，提高自动化程度
- 📋 改正配置文件的名称分类，现在分为用户配置和项目配置两种（user config and project config）

### 🐛 修复

- 🔧 更新后由于项目配置文件错误而导致的报错，现在已修复

## v0.9.3.250308 - 2025-03-08

### 🎉 新增

- LaTeXDiff 新增风格选择，支持在参考文献和符号索引中显示修改痕迹，编译过程中会提醒输入选项 1 或者 2
  - 1 - 显示参考文献/符号说明的修改
  - 2 - 不显示参考文献/符号说明的修改

### 🚀 改进

- 调整 LaTeXDiff 相关的代码结构，提高可读性
- 优化文件夹创建命令，优化部分代码逻辑
- 解决模块路径解析的问题：采用绝对路径
- 重新分类库的导入，mfo, mro, pfo, cp 这些对象只在 main() 里初始化，避免不必要的资源占用
- PDF 修复采用 pikepdf 库来处理，避免打包体积过大
- 解决 -r 参数运行多余程序的问题，解决打包程序路径问题
- 完善 pdf_repair 方法，更换使用 pypdf 库

### 🐛 修复

- 完善 `-d` 命令报错机制

## v0.9.2.241006 - 2024-10-06

### 🚀 改进

- 去掉冗余代码，调整显示
- 完善 README，新增基础使用
- 调整提示信息内容，避免误解

### 🐛 修复

- 修复 log 文件中存在 "No file {self.project_name}.bbl" 时，编译次数判断错误的问题 [#2](https://github.com/YanMing-lxb/PyTeXMK/issues/2)

### 贡献

感谢 @nathanhsuuu 的反馈并提供错误复现最小案例

## v0.9.1.240921 - 2024-09-21

### 🚀 改进

- 添加 pytexmk 运行报错信息的显示

### 🐛 修复

- 调整编译过程显示内容
- 解决 ubuntu 下 makindex 命令寻找不到的问题
- 修复 BUG 解决 linux 下 latex 运行 batch 模式失效的问题

## v0.9.0.240916 - 2024-09-16

### 🐛 修复

- 调整 LaTeX 命令改为小写，避免 linux 不报错

## v0.8.13.240912 - 2024-09-12

### 🎉 新增功能

- 增加 `-dr` 选项，启用草稿模式编译

## v0.8.12.240902 - 2024-09-02

### 🐛 修复

- 修复检查更新部分的 INFO 内容显示不正确的问题
- 修复在 `thebibliography` 环境下参考文献编译次数过多的问题

## v0.8.11.240901 - 2024-09-01

### 🐛 修复

- 修复了在 `thebibliography` 环境下参考文献无法正确编译的问题
- 修复 `-vb` 参数下部分显示结果不对的问题

### 📝 其他

- 新增 `CHANGELOG.md` 文件，用于记录版本更新日志
- 新增 `Actions` 工作流，用于自动化在 PYPI 和 GitHub 发布
- 新增英文 `README.md` 文件，用于介绍 PyTeXMK
