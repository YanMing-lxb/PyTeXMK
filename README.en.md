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
 * Date         : 2024-09-01 22:20:03 +0800
 * LastEditTime : 2025-01-23 20:57:56 +0800
 * Github       : https://github.com/YanMing-lxb/
 * FilePath     : /PyTeXMK/README.en.md
 * Description  : 
 *  -----------------------------------------------------------------------
 -->

# PyTeXMK

[![GitHub](https://img.shields.io/badge/Github-PyTeXMK-000000.svg)](https://github.com/YanMing-lxb/PyTeXMK) [![License](https://img.shields.io/badge/license-GPLv3-aff)](https://www.latex-project.org/lppl/) ![OS](https://img.shields.io/badge/OS-Linux%2C%20Win%2C%20Mac-pink.svg) [![GitHub release](https://img.shields.io/github/release/YanMing-lxb/PyTeXMK.svg?color=blueviolet&label=version&style=popout)](https://github.com/YanMing-lxb/PyTeXMK/releases/latest) [![Last Commit](https://img.shields.io/github/last-commit/YanMing-lxb/PyTeXMK)](https://github.com/YanMing-lxb/PyTeXMK/zipball/master) [![Issues](https://img.shields.io/github/issues/YanMing-lxb/PyTeXMK)](https://github.com/YanMing-lxb/PyTeXMK/issues) [![PyPI version](https://img.shields.io/pypi/v/pytexmk.svg)](https://pypi.python.org/pypi/pytexmk/) [![PyPI Downloads](https://img.shields.io/pypi/dm/pytexmk.svg?label=PyPI%20downloads)](https://pypi.org/project/pytexmk/) ![GitHub repo size](https://img.shields.io/github/repo-size/YanMing-lxb/PyTeXMK)

[简体中文](https://github.com/YanMing-lxb/PyTeXMK/blob/main/README.md) | [English](https://github.com/YanMing-lxb/PyTeXMK/blob/main/README.en.md)

LaTeX Auxiliary Compilation Command Line Program

---

<div align="center">
    <img src="https://github.com/YanMing-lxb/PyTeXMK/raw/main/imgs/show1.png" alt="示例部分1" width="45%" style="max-width: 700px; box-shadow: 0 4px 8px 0 rgba(0, 0, 0, 0.4), 0 6px 20px 0 rgba(0, 0, 0, 0.19); margin-right: 2.5px;">
    <img src="https://github.com/YanMing-lxb/PyTeXMK/raw/main/imgs/show2.png" alt="示例部分2" width="45%" style="max-width: 700px; box-shadow: 0 4px 8px 0 rgba(0, 0, 0, 0.4), 0 6px 20px 0 rgba(0, 0, 0, 0.19); margin-left: 2.5px;">
</div>

## Installation

The official version of PyTeXMK is released on [PyPI](https://pypi.org/project/pytexmk/) and can be easily installed via the pip package manager from the PyPI mirror.

Please note that you must use the Python 3 version of pip:

```
pip3 install pytexmk
```

## Upgrade

```
pip3 install --upgrade pytexmk
```

## Getting Started

For basic usage see: [Issues #1](https://github.com/YanMing-lxb/PyTeXMK/issues/1#issuecomment-2383474600)

Please read carefully: [Logic for Selecting the Main File to Compile and Compilation Type](#logic-for-selecting-the-main-file-to-compile-and-compilation-type)

> PyTeXMK only supports TeX files encoded in utf-8.

### Default Configuration

The default configuration of Pytexmk is as follows:

1. Compilation program: `XeLaTeX`
2. Main file to be compiled: `main.tex`
3. Compilation results are stored in the `Build` folder of the LaTeX project (VSCode users need to set `"latex-workshop.latex.outDir": "./Build",` in `settings.json` so that LaTeX-Workshop can find the pdf)
4. Auxiliary files are stored in the `Auxiliary` folder of the LaTeX project
5. Compilation mode: batch mode (compilation process information is not displayed, use the `-uq` parameter to display compilation process information)

> Note: The above parameters can be modified in the configuration file. For details, please refer to: [Configuration File Description](#configuration-file-description)

### Compilation Commands

PyTeXMK supports:

- Compilation programs: `XeLaTeX` `PdfLaTeX` `LuaLaTeX`
- Bibliography: `bibtex` `biblatex` `thebibliography`
- Symbol index: `glossaries` `nomencl` `mkeidx`

Positional arguments:

| Option   | Description                 |
| -------- | --------------------------- |
| document | The filename to be compiled |

Options:

| Option                   | Description                                                                                                                                                                              |
| ------------------------ | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| -h, --help               | Display help information                                                                                                                                                                 |
| -v, --version            | Display program version number                                                                                                                                                           |
| -p, --PdfLaTeX           | Compile with PdfLaTeX                                                                                                                                                                    |
| -x, --XeLaTeX            | Compile with XeLaTeX                                                                                                                                                                     |
| -l, --LuaLaTeX           | Compile with LuaLaTeX                                                                                                                                                                    |
| -d, --LaTeXDiff          | Compile using LaTeXDiff to generate a comparison file                                                                                                                                    |
| -dc, --LaTexDiff-compile | Compile using LaTeXDiff to generate a comparison file and compile the new file                                                                                                           |
| -dr, --draft             | Enable draft mode for compilation, improving compilation speed (no images displayed)                                                                                                     |
| -c, --clean              | Clean all auxiliary files of the main file                                                                                                                                               |
| -C, --Clean              | Clean all auxiliary files (including root directory) and output files of the main file                                                                                                   |
| -ca, --clean-any         | Clean all files with auxiliary file suffixes                                                                                                                                             |
| -Ca, --Clean-any         | Clean all files with auxiliary file suffixes (including root directory) and main file output files                                                                                       |
| -nq, --non_quiet         | Run in non-quiet mode, displaying the compilation process in this mode                                                                                                                   |
| -vb, --verbose           | Display detailed information during PyTeXMK runtime                                                                                                                                      |
| -pr, --pdf-repair        | Repair all pdf files outside the root directory                                                                                                                                          |
| -pv, --pdf-preview       | Attempt to call a Web browser or local PDF reader to preview the generated PDF file after compilation. If 'FILE_NAME' is filled in, it will not compile and will open the specified file |

**Explanation:**

- The function of the `-pr` parameter is "When a warning similar to `invalid X X R object at offset XXXXX` appears during LaTeX compilation, this parameter can be used to attempt to repair all pdf files." The warning `invalid X X R object at offset XXXXX` occurs due to some form of corruption or illegal operation during the creation, editing, or transmission of the PDF image file, which may be caused by missing parts of the file, a damaged xref table, or other issues in the file structure.
- Examples for the `-d` and `-dc` commands: `pytexmk -d old_tex_file new_tex_file` and `pytexmk -dc old_tex_file new_tex_file`. The generated comparison file is named `LaTeXDiff.tex`.
- The function of the `-pv` parameter is: Attempt to call a Web browser or local PDF reader to preview the generated PDF file after compilation. It only supports PDF files in the output directory. If you need to specify the main file to be compiled in the command line, the `-pv` command should be placed after `document`, `-pv` command does not need to specify parameters, example: `pytexmk main -pv`; if you do not need to specify the main file in the command line, simply enter `-pv`, example: `pytexmk -pv`.


The `-dc` and `-d` commands have a new style option to support displaying traces of changes in reference and symbol indexes, with a compilation prompt to enter option 1 or 2

- 1 - Show changes in reference/symbol descriptions
- 2 - Do not show changes in references/symbol descriptions

### Magic Comments

PyTeXMK supports using magic comments to define the main file to be compiled, compilation program, location to store compilation results, etc. (only supports searching the first 50 lines of the document).

| Magic Comment                    | Description                                                                                          | Examples                      |
| -------------------------------- | ---------------------------------------------------------------------------------------------------- | ----------------------------- |
| `% !TEX program = <XeLaTeX>`   | Specify the compilation type, optional `XeLaTeX` `PdfLaTeX` `LuaLaTeX`                         | `% !TEX program = PdfLaTeX` |
| `% !TEX root = <main_file>`    | Specify the LaTeX filename to be compiled, only supports the main file in the project root directory | `% !TEX root = test_file`   |
| `% !TEX outdir = <out_folde>`  | Specify the location to store compilation results, only supports folder names                        | `% !TEX outdir = output`    |
| `% !TEX auxdir = <aux_folder>` | Specify the location to store auxiliary files, only supports folder names                            | `% !TEX auxdir = auxfiles`  |

> Magic comments only support definition in the main file, not in sub-files.

### Logic for Selecting the Main File to Compile and Compilation Type

<details>
<summary><b>Logic for Selecting the Main File to Compile</b></summary>

1. If a master file is specified in the command line arguments, the master file is compiled. For example: `pytexmk <main file name>` The main file name may not be followed by a file suffix. 3.
2. If there is only one `TEX` file in the current root directory, that file is used as the master file to be compiled. 4.
3. If there is a magic comment `% !TEX root`, the file specified by the magic comment is used as the master file to be compiled.
4. retrieve `\documentclass[]{}` or `\begin{document}` from `TEX` file (only supports retrieving the first 200 lines of the document)
5. if the main file cannot be determined from the magic comment, try to specify the main file to be compiled based on the default main file name, `main.tex`. 7.
6. If you still cannot determine the main file, output an error message and exit the program.

</details>

<details>
<summary><b>Logic for Selecting the Compilation Type</b></summary>

1. PyTeXMK prioritizes using the compilation type specified by the terminal input command `-p` `-x` `-l` parameters.
2. If not specified, it will use the compilation type specified by `% !TEX program = XeLaTeX`.
3. If not specified, it will use the default compilation type `XeLaTeX`.

</details>

PyTeXMK will prioritize using the compilation result storage location specified by `% !TEX outdir = PDFfile`. If not specified, it will use the default compilation result storage location `Build`.

### Configuration File Description

PyTeXMK supports two types of configuration files, system configuration files and local configuration files. Configuration files can be used to change the default configuration of Pytexmk and configure some other functions. The system configuration file is automatically generated when PyTeXMK is first run, located in the user directory, with the filename `.pytexmkrc`; the local configuration file is automatically generated when PyTeXMK is first run in the project, located in the current working directory, with the filename `.pytexmkrc`. Detailed comments exist in the automatically generated configuration file, please configure according to the comments.

#### Configuration File Path

System configuration file path: For Windows systems, it is `C:\Users\username\.pytexmkrc`, for Linux systems, it is `~/.pytexmkrc`.
Local configuration file path: The `.pytexmkrc` file in the current working directory.

#### Configuration File Priority

The local configuration file has a higher priority than the system configuration file. If both configure the same parameters, the configuration in the local configuration file will be prioritized.

## Building the `Wheel`

```
1. Installing Python3
2. pip install -r requirements-windows.txt
3. pip install pyinstaller
4. make
```

In addition, the make command needs to be configured separately on Windows: see [Using make on Windows](https://github.com/YanMing-lxb/PyTeXMK/blob/main/docs/Window%20%E4%B8%8B%E4%BD%BF%E7%94%A8%20make.md) for details.

## Update Log

For the update log, please see the [CHANGELOG document](https://github.com/YanMing-lxb/PyTeXMK/blob/main/CHANGELOG.md)

## Future Work Directions

- [X] Add the function to attempt to repair all PDF files outside the root directory (to solve the problem of warnings similar to `invalid X X R object at offset XXXXX` during compilation due to some form of corruption or illegal operation during the creation, editing, or transmission of the PDF file)
- [X] Improve the main file judgment function:

  - [X] Determine by searching for `\documentclass[]{}` or `\begin{document}` in the TeX file
  - [ ] Multi-main file compilation function
- [X] Magic comment function

  - [X] Set the main file name via magic comments
  - [X] Set the compilation engine type via magic comments
  - [X] Set the location to store compilation results via magic comments
  - [X] Set the location to store auxiliary files via magic comments
  - [X] Solve the case and space sensitivity problem of magic comments
  - [ ] LaTeXDiff related magic comments
  - [ ] Handling logic for repeated definition of magic comments
    - [ ] Conflict handling for magic comments in the main file and sub-files
    - [ ] Solve the conflict problem of magic comments in the main file and sub-files when multiple main files exist
- [X] Automatic judgment function for the number of compilations

  <details><summary>Expand to view</summary>

  - [X] Improve the interruption mechanism after an error occurs in the compilation process
  - [X] Automatically judge whether to compile the bibliography
  - [X] Automatically judge whether to compile the index file
  - [X] Automatically judge whether to recompile

  </details>
- [ ] Add configuration file function

  - [X] Configurable default compilation engine (currently the default compilation command is `XeLaTeX`)
  - [X] Configurable default location to store result files (currently stored in the `Build` subfolder by default)
  - [X] Configurable default location to store auxiliary files (currently stored in the `Auxiliary` subfolder by default)
  - [ ] Configurable configuration for other index packages
  - [X] Configurable whether to preview the PDF by default after compilation
  - [ ] Configurable PDF file opening program
  - [X] Configurable default quiet mode status
  - [X] Configurable default verbose mode status
  - [X] Configurable default file name
  - [X] Configurable default new TeX file name for LaTeXDiff
  - [X] Configurable default old TeX file name for LaTeXDiff
  - [X] Configurable default output file name for LaTeXDiff
- [ ] Preview and log function

  - [ ] Solve the problem of Chinese display in the terminal
  - [X] PDF preview function
  - [X] Error information display function
  - [ ] Further improve the error information display function
  - [X] Implement log recording function
- [X] Improve cleaning function

  <details><summary>Expand to view</summary>

  - [X] Improve the function to clean auxiliary files
  - [X] Improve the function to clean all files
  - [X] Improve the function to clean all auxiliary files

  </details>
- [ ] Check for missing packages and automatically install (texlive)
- [X] Add PyTeXMK update check function
- [ ] LaTeXDiff related functions

  - [X] Add the function to move auxiliary files to the root directory after compilation
  - [X] Implementation of LaTeXDiff command line parameters
  - [X] Add configuration file function for a single project
  - [ ] LaTeXDiff compilation judgment logic
- [X] Program internationalization
- [ ] README document improvement

  - [ ] Add configuration file related instructions

## Star History

[![Star History Chart](https://api.star-history.com/svg?repos=YanMing-lxb/PyTeXMK&type=Date)](https://star-history.com/#YanMing-lxb/PyTeXMK&Date)

<div align="center">

## ༼ つ ◕_◕ ༽つ  Please share.

</div>
