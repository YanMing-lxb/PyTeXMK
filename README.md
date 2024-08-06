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
 * LastEditTime : 2024-08-06 08:56:01 +0800
 * Github       : https://github.com/YanMing-lxb/
 * FilePath     : /PyTeXMK/README.md
 * Description  : 
 *  -----------------------------------------------------------------------
 -->

# PyTeXMK

[![GitHub](https://img.shields.io/badge/Github-PyTeXMK-000000.svg)](https://github.com/YanMing-lxb/PyTeXMK) [![License](https://img.shields.io/badge/license-GPLv3-aff)](https://www.latex-project.org/lppl/) ![OS](https://img.shields.io/badge/OS-Linux%2C%20Win%2C%20Mac-pink.svg) [![GitHub release](https://img.shields.io/github/release/YanMing-lxb/PyTeXMK.svg?color=blueviolet&label=version&style=popout)](https://github.com/YanMing-lxb/PyTeXMK/releases/latest) [![Last Commit](https://img.shields.io/github/last-commit/YanMing-lxb/PyTeXMK)](https://github.com/YanMing-lxb/PyTeXMK/zipball/master) [![Issues](https://img.shields.io/github/issues/YanMing-lxb/PyTeXMK)](https://github.com/YanMing-lxb/PyTeXMK/issues) [![Github Action](https://github.com/YanMing-lxb/PyTeXMK/workflows/Test/badge.svg)](https://github.com/YanMing-lxb/PyTeXMK/actions) [![PyPI version](https://img.shields.io/pypi/v/pytexmk.svg)](https://pypi.python.org/pypi/pytexmk/) [![PyPI Downloads](https://img.shields.io/pypi/dm/pytexmk.svg?label=PyPI%20downloads)](https://pypi.org/project/pytexmk/) ![GitHub repo size](https://img.shields.io/github/repo-size/YanMing-lxb/PyTeXMK)

LaTeX 辅助编译命令行程序 LaTeX Auxiliary Compilation Command Line Tool

---

## 安装

官方版本 PyTeXMK 发布在 [PyPI](https://pypi.org/project/pytexmk/) 上，并且可以通过 pip 包管理器从 PyPI 镜像轻松安装。

请注意，您必须使用 Python 3 版本pip：

```
pip3 install pytexmk
```

## 升级

```
pip3 install --upgrade pytexmk
```

## 使用入门

PyTeXMK 默认参数：`xelatex` 编译、待编译主文件名 main.tex、batch 模式（编译过程信息不显，如需显示编译过程信息请使用 `-uq` 参数）、编译结果存放在 LaTeX 项目的 Build 文件夹下 ( VSCode 用户则需要在 `settings.json` 中注意设置 `"latex-workshop.latex.outDir": "./Build",` 使得 LaTeX-Workshop 能够找到 pdf )、辅助文件存放在 LaTeX 项目的 Auxiliary 文件夹下。

请仔细阅读：[待编译主文件及编译类型选定逻辑](#待编译主文件及编译类型选定逻辑)

> PyTeXMK，仅支持 utf-8 编码的 TeX 文件。

### 编译命令
PyTeXMK 支持：

- 编译命令：`xelatex` `pdflatex` `lualatex`
- 参考文献：`bibtex` `biblatex` `thebibliography`
- 符号索引：`glossaries` `nomencl` `mkeidx`

位置参数:
| Option              | Description                    |
|---------------------|-------------------------------|
| document          | 要被编译的文件名                   |

选项:
| Option           | Description                                          |
|------------------|------------------------------------------------------|
| -h, --help       | 显示帮助信息                                          |
| -v, --version    | 显示程序版本号                                        |
| -p, --pdflatex   | pdflatex 进行编译                                     |
| -x, --xelatex    | xelatex 进行编译                                      |
| -l, --lualatex   | lualatex 进行编译                                     |
| -d, --LaTeXDiff  | 使用 LaTeXDiff 进行编译，生成改动对比文件|
| -dc, --LaTexDiff-compile  | 使用 LaTeXDiff 进行编译，生成改动对比文件并编译新文件|
| -c, --clean      | 清除所有主文件的辅助文件                               |
| -C, --Clean      | 清除所有主文件的辅助文件（包含根目录）和输出文件         |
| -ca, --clean-any | 清除所有带辅助文件后缀的文件                           |
| -Ca, --Clean-any | 清除所有带辅助文件后缀的文件（包含根目录）和主文件输出文件|
| -uq, --unquiet   | 非安静模式运行，此模式下显示编译过程                    |
| -vb, --verbose   | 显示 PyTeXMK 运行过程中的详细信息                      |
| -pr, --pdf-repair| 修复所有根目录以外的 pdf 文件                         |

**说明：**
`-pr` 参数的功能是 "当 LaTeX 编译过程中报类似 `invalid X X R object at offset XXXXX` 的警告时，可使用此参数尝试修复所有 pdf 文件"
`invalid X X R object at offset XXXXX` 警告的出现是由于 PDF 图片文件在创建、编辑或传输过程中发生了某种形式的损坏或非法操作导致的，可能的原因包括文件部分内容缺失、xref表损坏、或者是文件结构中的其他问题

`-d` 和 `-dc` 命令输入示例： `pytexmk -d old_tex_file new_tex_file` 和 `pytexmk -dc old_tex_file new_tex_file` 生成的改动对比文件名为 `LaTeXDiff.tex`

### 魔法注释

PyTeXMK 支持使用魔法注释来自定义编译命令、编译类型、编译结果存放位置等（仅支持检索文档前 50 行）。

| Magic Comment              | Description                                            |
|----------------------------|--------------------------------------------------------|
| `% !TEX program = xelatex` | 指定编译类型，可选 `xelatex` `pdflatex` `lualatex`       |
| `% !TEX root = file.tex`   | 指定待编译 LaTeX 文件名，仅支持主文件在项目根目录下的情况   |
| `% !TEX outdir = PDFfile`  | 指定编译结果存放位置，仅支持文件夹名称                     |
| `% !TEX auxdir = auxfiles` | 指定辅助文件存放位置，仅支持文件夹名称                     |

> 魔法注释仅支持在主文件中定义，不支持在子文件中定义。

### 待编译主文件及编译类型选定逻辑

- PyTeXMK 优先使用终端输入命令 `-p` `-x` `-l` 参数指定的编译类型，如果没有指定，则会使用 `% !TEX program = xelatex` 指定的编译类型，如果没有指定，则会使用默认的编译类型 `xelatex`
- PyTeXMK 待编译主文件选定逻辑顺序：
    1. 如果命令行参数中指定了主文件，则使用该主文件名。
    2. 如果当前根目录下存在且只有一个主文件，则使用该文件作为待编译主文件。
    3. 如果存在魔法注释 `% !TEX root`，则根据魔法注释指定的文件作为主文件。
    4. 检索 TeX 文件中的 `\documentclass[]{}` 或 `\begin{document}` 来判断（仅支持检索文档前 200 行）
    5. 如果无法根据魔法注释确定主文件，则尝试根据默认主文件名 `main.tex` 指定待编译主文件。
    6. 如果仍然无法确定主文件，则输出错误信息并退出程序。
        
- PyTeXMK 会优先使用 `% !TEX outdir = PDFfile` 指定的编译结果存放位置，如果没有指定，则会使用默认的编译结果存放位置 `Build`

# 未来工作方向

- [X] 增加尝试修复根目录以外所有 PDF 文件的功能（在创建、编辑或传输过程中发生了某种形式的损坏或非法操作而导致在编译过程中出现类似 `invalid X X R object at offset XXXXX` 的警告的问题）
- [X] 完善主文件判断功能：
    - [X] 通过检索 TeX 文件中的 `\documentclass[]{}` 或 `\begin{document}` 来判断
    - [ ] 多主文件编译功能
- [x] 魔法注释功能
    - [X] 通过魔法注释设置主文件名
    - [X] 通过魔法注释设置编译引擎类型
    - [x] 通过魔法注释设置编译结果存放位置
    - [X] 根据魔法注释设置辅助文件存放位置
    - [x] 解决魔法注释大小写空格敏感问题
    - [ ] 魔法注释重复定义的处理逻辑
        - [ ] 主文件于子文件中魔法注释的冲突处理
        - [ ] 解决多存在多个主文件时的主文件于子文件中魔法注释冲突问题
- [X] 编译次数自动判断功能
    - [X] 完善编译过程出错后的中断处理机制
    - [X] 自动判断是否需要编译参考文献
    - [X] 自动判断是否需要编译索引文件
    - [X] 自动判断是否要重新编译
- [ ] 增加配置文件功能
    - [ ] 自定义默认的编译引擎 （目前默认编译命令是 `xelatex`）
    - [ ] 自定义默认生成的结果文件存放位置（目前默认存放在 `Build` 子文件夹下）
    - [ ] 自定义默认的辅助文件存放位置（目前默认存放在 `Auxiliary` 子文件夹下）
    - [ ] 自定义其他索引宏包的配置
    - [ ] 自定义 PDF 文件打开方式
- [ ] 预览与日志功能
    - [ ] 解决终端中文显示问题
    - [ ] PDF 预览功能
    - [X] 报错信息显示功能
    - [X] 实现日志记录功能
- [X] 完善清理功能
    - [X] 完善清理辅助文件功能
    - [X] 完善清理所有文件功能
    - [X] 完善清理所有辅助文件功能
- [ ] 宏包检缺失并自动安装（texlive）
- [X] 添加 PyTeXMK 更新检查功能
- [ ] LaTeXDiff 相关功能
    - [X] 添加编译结束后将辅助文件移动到根目录下功能
    - [ ] 添加单个项目的配置文件功能
    - [ ] 实现配置文件的解析功能
    - [ ] LaTeXDiff 编译判断逻辑