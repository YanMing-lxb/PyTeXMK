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
 * Date         : 2024-02-29 10:23:19 +0800
 * LastEditTime : 2025-01-12 21:45:27 +0800
 * Github       : https://github.com/YanMing-lxb/
 * FilePath     : /PyTeXMK/README.md
 * Description  : 
 *  -----------------------------------------------------------------------
 -->

# PyTeXMK

[![GitHub](https://img.shields.io/badge/Github-PyTeXMK-000000.svg)](https://github.com/YanMing-lxb/PyTeXMK) [![License](https://img.shields.io/badge/license-GPLv3-aff)](https://www.latex-project.org/lppl/) ![OS](https://img.shields.io/badge/OS-Linux%2C%20Win%2C%20Mac-pink.svg) [![GitHub release](https://img.shields.io/github/release/YanMing-lxb/PyTeXMK.svg?color=blueviolet&label=version&style=popout)](https://github.com/YanMing-lxb/PyTeXMK/releases/latest) [![Last Commit](https://img.shields.io/github/last-commit/YanMing-lxb/PyTeXMK)](https://github.com/YanMing-lxb/PyTeXMK/zipball/master) [![Issues](https://img.shields.io/github/issues/YanMing-lxb/PyTeXMK)](https://github.com/YanMing-lxb/PyTeXMK/issues) [![PyPI version](https://img.shields.io/pypi/v/pytexmk.svg)](https://pypi.python.org/pypi/pytexmk/) [![PyPI Downloads](https://img.shields.io/pypi/dm/pytexmk.svg?label=PyPI%20downloads)](https://pypi.org/project/pytexmk/) ![GitHub repo size](https://img.shields.io/github/repo-size/YanMing-lxb/PyTeXMK)

[简体中文](https://github.com/YanMing-lxb/PyTeXMK/blob/main/README.md) | [English](https://github.com/YanMing-lxb/PyTeXMK/blob/main/README.en.md)

LaTeX 辅助编译命令行程序

---

<div align="center">
    <img src="https://github.com/YanMing-lxb/PyTeXMK/raw/main/imgs/show1.png" alt="示例部分1" width="45%" style="max-width: 700px; box-shadow: 0 4px 8px 0 rgba(0, 0, 0, 0.4), 0 6px 20px 0 rgba(0, 0, 0, 0.19); margin-right: 2.5px;">
    <img src="https://github.com/YanMing-lxb/PyTeXMK/raw/main/imgs/show2.png" alt="示例部分2" width="45%" style="max-width: 700px; box-shadow: 0 4px 8px 0 rgba(0, 0, 0, 0.4), 0 6px 20px 0 rgba(0, 0, 0, 0.19); margin-left: 2.5px;">
</div>

## 安装

官方版本 PyTeXMK 发布在 [PyPI](https://pypi.org/project/pytexmk/) 上，并且可以通过 pip 包管理器从 PyPI 镜像轻松安装。

请注意，您必须使用 Python 3 版本 pip：

```
pip3 install pytexmk
```

## 升级

```
pip3 install --upgrade pytexmk
```

## 使用入门

基础使用参见：[Issues #1](https://github.com/YanMing-lxb/PyTeXMK/issues/1#issuecomment-2383474600)

请仔细阅读：[待编译主文件及编译类型选定逻辑](#待编译主文件及编译类型选定逻辑)

> PyTeXMK，仅支持 utf-8 编码的 TeX 文件。

### 默认配置

Pytexmk 默认配置如下：

1. 编译程序：`XeLaTeX`
2. 待编译主文件名：`main.tex`
3. 编译结果存放在 LaTeX 项目的 `Build` 文件夹下 (VSCode 用户则需要在 `settings.json` 中注意设置 `"latex-workshop.latex.outDir": "./Build",` 使得 LaTeX-Workshop 能够找到 pdf )
4. 辅助文件存放在 LaTeX 项目的 `Auxiliary` 文件夹下
5. 编译模式：batch 模式（编译过程信息不显，如需显示编译过程信息请使用 `-uq` 参数）

> 注意：以上参数均可在配置文件中修改，具体请参考：[配置文件说明](#配置文件说明)

### 编译命令

PyTeXMK 支持：

- 编译程序：`XeLaTeX` `PdfLaTeX` `LuaLaTeX`
- 参考文献：`bibtex` `biblatex` `thebibliography`
- 符号索引：`glossaries` `nomencl` `mkeidx`

位置参数:

| Option   | Description      |
| -------- | ---------------- |
| document | 要被编译的文件名 |

选项:

| Option                   | Description                                                                                                    |
| ------------------------ | -------------------------------------------------------------------------------------------------------------- |
| -h, --help               | 显示帮助信息                                                                                                   |
| -v, --version            | 显示程序版本号                                                                                                 |
| -p, --PdfLaTeX           | PdfLaTeX 进行编译                                                                                              |
| -x, --XeLaTeX            | XeLaTeX 进行编译                                                                                               |
| -l, --LuaLaTeX           | LuaLaTeX 进行编译                                                                                              |
| -d, --LaTeXDiff          | 使用 LaTeXDiff 进行编译，生成改动对比文件                                                                      |
| -dc, --LaTexDiff-compile | 使用 LaTeXDiff 进行编译，生成改动对比文件并编译新文件                                                          |
| -dr, --draft             | 启用草稿模式进行编译，提高编译速度 (无图显示)                                                                  |
| -c, --clean              | 清除所有主文件的辅助文件                                                                                       |
| -C, --Clean              | 清除所有主文件的辅助文件（包含根目录）和输出文件                                                               |
| -ca, --clean-any         | 清除所有带辅助文件后缀的文件                                                                                   |
| -Ca, --Clean-any         | 清除所有带辅助文件后缀的文件（包含根目录）和主文件输出文件                                                     |
| -nq, --non_quiet         | 非安静模式运行，此模式下显示编译过程                                                                           |
| -vb, --verbose           | 显示 PyTeXMK 运行过程中的详细信息                                                                              |
| -pr, --pdf-repair        | 修复所有根目录以外的 pdf 文件                                                                                  |
| -pv, --pdf-preview       | 尝试编译结束后调用 Web 浏览器或者本地PDF阅读器预览生成的PDF文件，如有填写 'FILE_NAME' 则不进行编译打开指定文件 |

**说明：**

- `-pr` 参数的功能是 "当 LaTeX 编译过程中报类似 `invalid X X R object at offset XXXXX` 的警告时，可使用此参数尝试修复所有 pdf 文件"
  `invalid X X R object at offset XXXXX` 警告的出现是由于 PDF 图片文件在创建、编辑或传输过程中发生了某种形式的损坏或非法操作导致的，可能的原因包括文件部分内容缺失、xref表损坏、或者是文件结构中的其他问题
- `-d` 和 `-dc` 命令输入示例： `pytexmk -d old_tex_file new_tex_file` 和 `pytexmk -dc old_tex_file new_tex_file` 生成的改动对比文件名为 `LaTeXDiff.tex`
- `-pv` 参数的功能是：尝试编译结束后调用 Web 浏览器或者本地PDF阅读器预览生成的PDF文件，仅支持输出目录下的 PDF 文件，如需在命令行中指定待编译主文件，则 `-pv` 命令，需放置 `document` 后面, `-pv` 命令无需指定参数，示例：`pytexmk main -pv`；如无需在命令行中指定待编译主文件，则直接输入 `-pv` 即可，示例：`pytexmk -pv`


`-dc` 和 `-d` 命令新增风格选择，支持在参考文献和符号索引中显示修改痕迹，编译过程中会提醒输入选项 1 或者 2

- 1 - 显示参考文献/符号说明的修改

- 2 - 不显示参考文献/符号说明的修改

### 魔法注释

PyTeXMK 支持使用魔法注释来定义待编译主文件、编译程序、编译结果存放位置等（仅支持检索文档前 50 行）。

| Magic Comment                      | Description                                               | Examples                      |
| ---------------------------------- | --------------------------------------------------------- | ----------------------------- |
| `% !TEX program = <XeLaTeX>`     | 指定编译类型，可选 `XeLaTeX` `PdfLaTeX` `LuaLaTeX`  | `% !TEX program = PdfLaTeX` |
| `% !TEX root = <待编译主文件名>` | 指定待编译 LaTeX 文件名，仅支持主文件在项目根目录下的情况 | `% !TEX root = test_file`   |
| `% !TEX outdir = <out_folder>`   | 指定编译结果存放位置，仅支持文件夹名称                    | `% !TEX outdir = output`    |
| `% !TEX auxdir = <aux_folder>`   | 指定辅助文件存放位置，仅支持文件夹名称                    | `% !TEX auxdir = auxfiles`  |

> 魔法注释仅支持在主文件中定义，不支持在子文件中定义。

### 待编译主文件及编译类型选定逻辑

<details>
<summary><b>待编译主文件选定逻辑</b></summary>

1. 如果命令行参数中指定主文件，则编译该主文件。例如： `pytexmk <主文件名>` 主文件名后可不跟随文件后缀名。
2. 如果当前根目录下存在且只有一个 `TEX` 文件，则默认使用该文件作为待编译主文件。
3. 如果存在魔法注释 `% !TEX root`，则根据魔法注释指定的文件作为待编译主文件。
4. 检索 `TEX` 文件中的  `\documentclass[]{}`或 `\begin{document}` 来判断（仅支持检索文档前 200 行）
5. 如果无法根据魔法注释确定主文件，则尝试根据默认主文件名 `main.tex` 指定待编译主文件。
6. 如果仍然无法确定主文件，则输出错误信息并退出程序。

</details>

<details>
<summary><b>编译类型选定逻辑</b></summary>

1. PyTeXMK 优先使用终端输入命令 `-p` `-x` `-l` 参数指定的编译类型
2. 如果没有指定，则会使用 `% !TEX program = XeLaTeX` 指定的编译类型
3. 如果没有指定，则会使用默认的编译类型 `XeLaTeX`

</details>

PyTeXMK 会优先使用 `% !TEX outdir = PDFfile` 指定的编译结果存放位置，如果没有指定，则会使用默认的编译结果存放位置 `Build`

### 配置文件说明

PyTeXMK 支持两种配置文件，分别为系统配置文件和本地配置文件。配置文件可以用于改变 Pytexmk 默认配置以及配置一些其他功能。
系统配置文件在首次运行 PyTeXMK 时自动生成，位于用户目录下，文件名为 `.pytexmkrc`；
本地配置文件会在该项目首次运行 PyTeXMK 时自动生成，位于当前工作目录下，文件名为 `.pytexmkrc`。
自动生成的配置文件中存在详细的注释，请根据注释进行配置。

#### 配置文件路径

系统配置文件路径：Windows 系统为 `C:\Users\用户名\.pytexmkrc`，Linux 系统为 `~/.pytexmkrc`
本地配置文件路径：为当前工作目录下的 `.pytexmkrc` 文件

#### 配置文件优先级

本地配置文件优先级高于系统配置文件，如果两者对相同参数进行配置，则优先使用本地配置文件的配置。

## 构建 `Wheel`

```
1. 安装 Python3
2. pip install -r requirements-windows.txt
3. pip install pyinstaller
4. make
```

另外在 Windows 中 make 命令需要单独配置：详见 [Window 下使用 make](https://github.com/YanMing-lxb/PyTeXMK/blob/main/docs/Window%20%E4%B8%8B%E4%BD%BF%E7%94%A8%20make.md)

## 更新记录

更新记录详见 [CHANGELOG 文档](https://github.com/YanMing-lxb/PyTeXMK/blob/main/CHANGELOG.md)

## 未来工作方向

- [X] 增加尝试修复根目录以外所有 PDF 文件的功能（在创建、编辑或传输过程中发生了某种形式的损坏或非法操作而导致在编译过程中出现类似 `invalid X X R object at offset XXXXX` 的警告的问题）
- [X] 完善主文件判断功能：

  - [X] 通过检索 TeX 文件中的 `\documentclass[]{}` 或 `\begin{document}` 来判断
  - [ ] 多主文件编译功能
- [X] 魔法注释功能

  - [X] 通过魔法注释设置主文件名
  - [X] 通过魔法注释设置编译引擎类型
  - [X] 通过魔法注释设置编译结果存放位置
  - [X] 根据魔法注释设置辅助文件存放位置
  - [X] 解决魔法注释大小写空格敏感问题
  - [ ] LaTeXDiff 相关魔法注释
  - [ ] 魔法注释重复定义的处理逻辑
    - [ ] 主文件于子文件中魔法注释的冲突处理
    - [ ] 解决多存在多个主文件时的主文件于子文件中魔法注释冲突问题
- [X] 编译次数自动判断功能

  <details><summary>展开查看</summary>

  - [X] 完善编译过程出错后的中断处理机制
  - [X] 自动判断是否需要编译参考文献
  - [X] 自动判断是否需要编译索引文件
  - [X] 自动判断是否要重新编译

  </details>
- [ ] 增加配置文件功能

  - [X] 可配置默认的编译引擎 （目前默认编译命令是 `XeLaTeX`）
  - [X] 可配置默认生成的结果文件存放位置（目前默认存放在 `Build` 子文件夹下）
  - [X] 可配置默认的辅助文件存放位置（目前默认存放在 `Auxiliary` 子文件夹下）
  - [ ] 可配置其他索引宏包的配置
  - [X] 可配置 PDF 编译完是否默认预览
  - [ ] 可配置 PDF 文件打开程序
  - [X] 可配置默认安静模式状态
  - [X] 可配置默认详细模式状态
  - [X] 可配置默认文件名称
  - [X] 可配置默认 LaTeXDiff 新 TeX 文件名
  - [X] 可配置默认 LaTeXDiff 旧 TeX 文件名
  - [X] 可配置默认 LaTeXDiff 输出文件名
- [ ] 预览与日志功能

  - [ ] 解决终端中文显示问题
  - [X] PDF 预览功能
  - [X] 报错信息显示功能
  - [ ] 进一步完善报错信息显示功能
  - [X] 实现日志记录功能
- [X] 完善清理功能

  <details><summary>展开查看</summary>

  - [X] 完善清理辅助文件功能
  - [X] 完善清理所有文件功能
  - [X] 完善清理所有辅助文件功能

  </details>
- [ ] 宏包检缺失并自动安装（texlive）
- [X] 添加 PyTeXMK 更新检查功能
- [ ] LaTeXDiff 相关功能

  - [X] 添加编译结束后将辅助文件移动到根目录下功能
  - [X] LaTeXDiff 命令行参数的实现
  - [X] 添加单个项目的配置文件功能
  - [ ] LaTeXDiff 编译判断逻辑
- [X] 程序国际化
- [ ] README 文档完善

  - [ ] 增加配置文件相关说明

## Star History

[![Star History Chart](https://api.star-history.com/svg?repos=YanMing-lxb/PyTeXMK&type=Date)](https://star-history.com/#YanMing-lxb/PyTeXMK&Date)

<div align="center">

## ༼ つ ◕_◕ ༽つ  Please share.

</div>
