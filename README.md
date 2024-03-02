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
 * LastEditTime : 2024-03-02 20:57:36 +0800
 * Github       : https://github.com/YanMing-lxb/
 * FilePath     : /PyTeXMK/README.md
 * Description  : 
 *  -----------------------------------------------------------------------
 -->

# PyTeXMK

[![GitHub](https://img.shields.io/badge/Github-PyTeXMK-000000.svg)](https://github.com/YanMing-lxb/PyTeXMK) [![License](https://img.shields.io/badge/license-GPLv3-aff)](https://www.latex-project.org/lppl/) ![OS](https://img.shields.io/badge/OS-Linux%2C%20Win%2C%20Mac-pink.svg) [![GitHub release](https://img.shields.io/github/release/YanMing-lxb/PyTeXMK.svg?color=blueviolet&label=version&style=popout)](https://github.com/YanMing-lxb/PyTeXMK/releases/latest) [![Last Commit](https://img.shields.io/github/last-commit/YanMing-lxb/PyTeXMK)](https://github.com/YanMing-lxb/PyTeXMK/zipball/master) [![Issues](https://img.shields.io/github/issues/YanMing-lxb/PyTeXMK)](https://github.com/YanMing-lxb/PyTeXMK/issues) [![Github Action](https://github.com/YanMing-lxb/PyTeXMK/workflows/Build/badge.svg)](https://github.com/YanMing-lxb/PyTeXMK/actions) [![PyPI version](https://img.shields.io/pypi/v/pytexmk.svg)](https://pypi.python.org/pypi/pytexmk/) [![PyPI Downloads](https://img.shields.io/pypi/dm/pytexmk.svg?label=PyPI%20downloads)](https://pypi.org/project/pytexmk/) ![GitHub repo size](https://img.shields.io/github/repo-size/YanMing-lxb/PyTeXMK)

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

PyTeXMK 默认使用 `xelatex` 编译，默认主文件名为 main（如果不是 main 就在 `pytexmk` 命令后添加文件名），默认 batch 模式编译，编译过程信息不显示（如需显示编译过程信息请使用 `-nq` 参数），默认将编译结果存放在 LaTeX 项目的 Build 文件夹下 ( VSCode 用户则需要在 `settings.json` 中注意设置 `"latex-workshop.latex.outDir": "./Build",` 使得latex workshop 能够找到pdf )。

在终端打开 LaTeX 项目所在文件夹，输入 `pytexmk` 即可使用默认参数进行编译，编译结果默认存放在 LaTeX 项目的 Build 文件夹下。

PyTeXMK 支持：

- 编译命令：`xelatex` `pdflatex` `lualatex`
- 参考文献：`bibtex` `biblatex`
- 符号索引：`glossaries` `nomencl`

位置参数:
| Option              | Description                    |
|---------------------|-------------------------------|
| document          | 要被编译的文件名                   |

选项:
| Option           | Description                                |
|------------------|--------------------------------------------|
| -h, --help       | 显示帮助信息                                 |
| -v, --version    | 显示程序版本号                               |
| -c, --clean      | 清除所有辅助文件                              |
| -C, --Clean      | 清除所有辅助文件和 pdf 文件                    |
| -nq, --no-quiet  | 非安静模式运行，此模式下显示编译过程             |
| -p, --pdflatex   | pdflatex 进行编译                           |
| -x, --xelatex    | xelatex 进行编译                            |
| -l, --lualatex   | lualatex 进行编译                           |
