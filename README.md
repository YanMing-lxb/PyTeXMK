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
 * LastEditTime : 2024-04-26 22:37:00 +0800
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

PyTeXMK 默认参数：`xelatex` 编译、主文件名 main、batch 模式（编译过程信息不显，如需显示编译过程信息请使用 `-nq` 参数）、编译结果存放在 LaTeX 项目的 Build 文件夹下 ( VSCode 用户则需要在 `settings.json` 中注意设置 `"latex-workshop.latex.outDir": "./Build",` 使得latex workshop 能够找到pdf )。

请仔细阅读：[主文件及编译类型选定逻辑](#主文件及编译类型选定逻辑)

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
| Option           | Description                                |
|------------------|--------------------------------------------|
| -h, --help       | 显示帮助信息                                 |
| -v, --version    | 显示程序版本号                               |
| -p, --pdflatex   | pdflatex 进行编译                           |
| -x, --xelatex    | xelatex 进行编译                            |
| -l, --lualatex   | lualatex 进行编译                           |
| -c, --clean      | 清除所有辅助文件                              |
| -C, --Clean      | 清除所有辅助文件和 pdf 文件                    |
| -nq, --no-quiet  | 非安静模式运行，此模式下显示编译过程             |
| -cp, --clean-pdf  | 清理所有 pdf 文件             |

**说明：**
`-cp` 参数的功能是 "当 LaTeX 编译过程中报类似 `invalid X X R object at offset XXXXX` 的警告时，可使用此参数清理所有 pdf 文件"

### 魔法注释

PyTeXMK 支持使用魔法注释来自定义编译命令、编译类型、编译结果存放位置等。    

| Magic Comment | Description                                |
|---------------|----------|
| `% !TEX program = xelatex` | 指定编译类型，可选 `xelatex` `pdflatex` `lualatex` |
| `% !TEX root = file.tex` | 指定主 LaTeX 文件名，仅支持主文件在项目根目录下的情况 |
| `% !TEX outdir = PDFfile` | 指定编译结果存放位置，仅支持文件夹名称，如果使用 LaTeX-Workshop，则需要在 `settings.json` 中设置 `"latex-workshop.latex.outDir": "./PDFfile",` |

### 主文件及编译类型选定逻辑
- PyTeXMK 优先使用终端输入命令 `-p` `-x` `-l` 参数指定的编译类型，如果没有指定，则会使用 `% !TEX program = xelatex` 指定的编译类型，如果没有指定，则会使用默认的编译类型 `xelatex`
- PyTeXMK 主文件选定逻辑顺序：
    1. 使用终端输入的文件名
    2. 使用 `% !TEX root = file.tex` 指定的主 LaTeX 文件名
    3. 使用默认的主文件名 `main`
    4. 检索 TeX 文件中的 `\documentclass[]{}` 或 `\begin{document}` 来判断
    5. 根目录下 TeX 文件中只有一个文件，则选择该文件作为主文件
        
- PyTeXMK 会优先使用 `% !TEX outdir = PDFfile` 指定的编译结果存放位置，如果没有指定，则会使用默认的编译结果存放位置 `Build`

# 更新日志

- 2024-03-22 完善编译过程出错后的中断处理机制：在编译过程中出现错误时，程序会自动中断，并提示 `请用 -nq 模式运行以显示错误信息！`,使用 `-nq` 参数运行时，则会显示错误信息。
- 2024-04-26 增加：
    1. 魔法注释功能，使得用户可以自定义编译命令、编译类型、编译结果存放位置等
    2. 完善主文件及编译类型选定逻辑


# 未来工作方向

- [X] 完善编译过程出错后的中断处理机制
- [ ] 完善检索主 LaTeX 文件的功能：
    - [X] 根据魔法注释 `% !TEX root = file.tex` 找到主 LaTeX 文件
    - [ ] 通过检索 TeX 文件中的 `\documentclass[]{}` 或 `\begin{document}` 来判断
- [ ] 完善自动判断编译类型：
    - [X] 根据魔法注释 `% !TEX program = xelatex` 设置需要编译的类型
- [x] 通过魔法注释设置编译结果存放位置
- [X] 通过魔法注释实现编译命令的自定义
- [ ] 增加配置文件功能，用于改变默认设置
    - [ ] 指定生成的结果文件存放位置（目前默认存放在 `Build` 子文件夹下）
    - [ ] 默认的编译命令（目前默认编译命令是 `xelatex`）
- [ ] texlive 宏包检缺失并自动安装
- [ ] 多主文件编译功能