<!--
 *  =======================================================================
 *  ····Y88b···d88P················888b·····d888·d8b·······················
 *  ·····Y88b·d88P·················8888b···d8888·Y8P·······················
 *  ······Y88o88P··················88888b·d88888···························
 *  ·······Y888P··8888b···88888b···888Y88888P888·888·88888b·····d88b·······
 *  ········888······"88b·888·"88b·888·Y888P·888·888·888·"88b·d88P"88b·····
 *  ········888···d888888·888··888·888··Y8P··888·888·888··888·888··888·····
 *  ········888··888··888·888··888·888···"···888·888·888··888·Y88b·888·····
 *  ········888··"Y888888·888··888·888·······888·888·888··888··"Y88888·····
 *  ·······························································888·····
 *  ··························································Y8b·d88P·····
 *  ···························································"Y88P"······
 *  =======================================================================
 * 
 *  -----------------------------------------------------------------------
 * Author       : 焱铭
 * Date         : 2024-09-01 19:38:56 +0800
 * LastEditTime : 2025-05-15 19:26:13 +0800
 * Github       : https://github.com/YanMing-lxb/
 * FilePath     : /PyTeXMK/CHANGELOG.md
 * Description  : 
 *  -----------------------------------------------------------------------
 -->

# CHANGELOG

<!-- ### 新增功能
- 添加了对新文件格式的支持。
- 增加了自动保存功能，防止数据丢失。

### 改进
- 优化了代码结构，提升了运行效率。
- 改进了用户界面，使其更加直观易用。

### 修复
- 修复了在特定情况下程序崩溃的问题。
- 修正了若干已知的bug。

### 其他
- 新增 CHANGELOG.md 文件，用于记录版本更新日志。
 -->

## v1.0.2.250515

### 🚀 改进

- 日志分析器中的优化路径处理
- 优化了日志分析器中的路径处理，使其更通用。
- 编译失败后，启用日志解析器

### 🐛 修复

- 修复 LaTeX 编译器运行错误不及时终止程序的问题

## v1.0.1.250506

### 🚀 改进

- 日志分析器拆分 warning 和 info 信息。

## v1.0.0.250506

### 🎉 新增

- 新增日志分析器，编译结束后会解析日志内容，并显示在终端中。

## v0.9.6.250430

### 🐛 修复

- 国际化

## v0.9.5.250430

### 🎉 新增

- 新增程序运行动画

## v0.9.4.250424

### 改进

- 优化版本更新检查代码，使其更通用


## v0.9.4.250314

### 🎉 新增

- 🛠 新增配置文件错误检查功能，如果配置文件存在错误，则可以根据提示进行修复。
- 📂 新增auxiliary_fun.py, 调整部分函数到辅助方法中


### 🚀 改进

- ⚙ make: 优化代码，提高自动化程度
- 📋改正配置文件的名称分类，现在分为 用户配置和项目配置两种（user config and project config）


### 🐛 修复

- 🔧 更新后由于项目配置文件错误而导致的报错，现在已修复。

## v0.9.3.250308

### 新增

- LaTeXDiff 新增风格选择，支持在参考文献和符号索引中显示修改痕迹，编译过程中会提醒输入选项 1 或者 2
  - 1 - 显示参考文献/符号说明的修改
  - 2 - 不显示参考文献/符号说明的修改

### 改进

- 调整 LaTeXDiff 相关的代码结构，提高可读性
- 优化文件夹创建命令，优化部分代码逻辑
- 解决模块路径解析的问题：采用绝对路进
- 重新分类 库的导入，mfo, mro, pfo, cp 这些对象 只在 main() 里初始化，避免不必要的资源占用。
- PDF 修复采用 pikepdf 库来处理，避免打包体积过大、
- 解决 -r 参数运行多余程序的问题，解决打包程序路径问题
- 完善 pdf_repair 方法，更换使用 pypdf 库

### 修复

- 完善 `-d` 命令报错机制

## v0.9.2.241006

### 改进

- 去掉冗余代码，调整显示
- 完善 README，新增基础使用
- 调整提示信息内容，避免误解

### 修复

- 修复 log文件中存在 “No file {self.project_name}.bbl” 时，编译次数判断错误的问题 https://github.com/YanMing-lxb/PyTeXMK/issues/2

### 贡献

感谢 @nathanhsuuu 的反馈并提供错误复现最小案例

## v0.9.1.240921 - 2024-09-21

### 改进

- 添加 pytexmk 运行报错信息的显示

### 修复

- 调整编译过程显示内容
- 解决 ubuntu 下 makindex 命令寻找不到的问题
- 修复 BUG 解决 linux 下 latex 运行bach模式实效的问题

## v0.9.0.240916 - 2024-09-16

### 修复

- 调整 LaTeX 命令改为小写，避免linux不报错

## v0.8.13.240912 - 2024-09-12

### 新增功能

- 增加 `-dr` 选项，启用草稿模式编译

## v0.8.12.240902 - 2024-09-02

### 修复

- 修复检查更新部分的 INFO 内容显示不正确的问题
- 修复在 `thebibliography` 环境下参考文献编译次数过多的问题。

## v0.8.11.240901 - 2024-09-01

### 修复

- 修复了在 `thebibliography` 环境下参考文献无法正确编译的问题。
- 修复 `-vb` 参属下部分显示结果不对的问题

### 其他

- 新增 `CHANGELOG.md` 文件，用于记录版本更新日志。
- 新增 `Actions` 工作流，用于自动化在 PYPI 和 GitHub 发布。
- 新增英文 `README.md` 文件，用于介绍 PyTeXMK。
