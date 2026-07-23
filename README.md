<p align="center">
<pre>
 =======================================================================
 ····Y88b···d88P················888b·····d888·d8b·······················
 ·····Y88b·d88P·················8888b···d8888·Y8P·······················
 ······Y88o88P··················88888b·d88888···························
 ·······Y888P··8888b···88888b···888Y88888P888·888·88888b·····d88b·······
 ········888······"88b·888·"88b·888·Y888P·888·888·888·"88b·d88P"88b·····
 ········888···d888888·888··888·888··Y8P··888·888·888··888·888··888·····
 ········888··888··888·888··888·888···"···888·888·888··888·Y88b·888·····
 ········888··"Y888888·888··888·888·······888·888·888··888··"Y88888·····
 ·····························································888·····
 ··························································Y8b·d88P·····
 ···························································"Y88P"·····
 =======================================================================
</pre>
</p>

<h1 align="center">PyTeXMK</h1>

<p align="center">
<strong>LaTeX 智能辅助编译工具</strong><br/>
LaTeX 自动化编译引擎 · 多工具链智能适配 · 类似 latexmk 但更强大
</p>

<p align="center">
<a href="https://github.com/YanMing-lxb/PyTeXMK/actions/workflows/ci.yml"><img src="https://github.com/YanMing-lxb/PyTeXMK/actions/workflows/ci.yml/badge.svg" alt="CI Status"/></a>
<a href="https://pypi.org/project/pytexmk/"><img src="https://img.shields.io/pypi/v/pytexmk.svg" alt="PyPI Version"/></a>
<a href="https://pypi.org/project/pytexmk/"><img src="https://img.shields.io/pypi/pyversions/pytexmk.svg" alt="Python Versions"/></a>
<a href="https://github.com/YanMing-lxb/PyTeXMK/blob/main/LICENSE"><img src="https://img.shields.io/github/license/YanMing-lxb/PyTeXMK.svg" alt="License"/></a>
<a href="https://github.com/astral-sh/ruff"><img src="https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json" alt="Ruff"/></a>
</p>

[English](README.en.md) | 中文

---

## 目录

- [项目简介](#-项目简介)
- [核心特性](#-核心特性)
- [环境要求](#-环境要求)
- [安装指南](#-安装指南)
- [快速开始](#-快速开始)
- [完整命令参考](#-完整命令参考)
- [魔法注释](#-魔法注释)
- [配置文件详解](#-配置文件详解)
- [环境变量](#-环境变量)
- [使用案例](#-使用案例)
- [PVC 实时监听模式](#-pvc-实时监听模式)
- [LaTeXDiff 文档对比](#-latexdiff-文档对比)
- [GitHub Actions 集成](#-github-actions-集成)
- [常见问题 FAQ](#-常见问题-faq)
- [贡献指南](#-贡献指南)
- [更新日志](#-更新日志)
- [开源协议](#-开源协议)

---

## 📖 项目简介

PyTeXMK 是一个现代化的 LaTeX 自动化编译工具，作为 latexmk 的增强替代方案。它能够自动检测 LaTeX 源文件依赖，智能选择最优编译引擎，管理辅助文件，并提供优雅的终端输出体验。

PyTeXMK 的核心设计理念是**「固定编译次数 + 智能补编兜底」**：正常情况下按照预设次数稳定编译，检测到引用未定义等可修复问题时才自动触发补编，兼顾编译效率与可靠性。

---

## ✨ 核心特性

| 特性 | 说明 |
|------|------|
| 🔧 **多引擎智能适配** | 自动检测 XeLaTeX/LuaLaTeX/PdfLaTeX，按优先级智能降级：XeLaTeX → LuaLaTeX → PdfLaTeX |
| 📚 **参考文献自动处理** | 自动识别 BibTeX/Biber 需求并调用对应工具 |
| 📇 **索引工具支持** | 支持 makeindex 和 **xindy** 两种索引工具，自动检测 |
| 👀 **PVC 实时监听** | 类似 `latexmk -pvc` 的文件监听+自动编译模式，保存即编译 |
| 📊 **结构化日志解析** | 精准解析编译日志，高亮错误/警告，定位到具体行号 |
| 📄 **LaTeXDiff 集成** | 一键生成文档版本对比 PDF，支持压平子文件和 fast 模式 |
| 🌏 **国际化支持** | 中英文双语界面，通过 `PYTEXMK_LANG` 环境变量切换 |
| 📁 **目录整洁** | 自动将 PDF 输出到 `Build/`，辅助文件归集到 `Auxiliary/`，保持工作区整洁 |
| 🖥️ **跨平台支持** | Windows / macOS / Linux 全平台，兼容 MiKTeX 和 TeX Live |
| ⚙️ **灵活配置** | 支持 TOML 配置文件 + 魔法注释 + 命令行参数三级配置 |
| 🚀 **Python 3.13** | 基于最新 Python 版本，性能优异，启动快速 |

---

## 🖥️ 环境要求

- **Python**: 3.13 或更高版本（pip 安装方式）
- **LaTeX 发行版**: TeX Live 2022+ 或 MiKTeX（需包含 xelatex/lualatex/pdflatex）
- **可选工具**:
  - `latexdiff`：用于文档版本对比功能
  - `xindy`：用于 xindy 索引支持
  - `biber`：用于 BibLaTeX 参考文献支持

---

## 📦 安装指南

### pip 安装（推荐，跨平台）

```bash
pip install pytexmk
```

升级到最新版本：
```bash
pip install --upgrade pytexmk
```

### Windows - Scoop

Scoop manifest 已准备好，待正式发布后可通过以下命令安装：
```powershell
scoop bucket add pytexmk https://github.com/YanMing-lxb/PyTeXMK
scoop install pytexmk
```

### Windows - Winget

待发布到 winget 仓库后可用：
```powershell
winget install YanMing.PyTeXMK
```

### 预编译二进制文件

从 [GitHub Releases](https://github.com/YanMing-lxb/PyTeXMK/releases) 下载对应平台的可执行文件，解压后将目录添加到系统 PATH 即可使用。

### 从源码安装（开发版）

```bash
git clone https://github.com/YanMing-lxb/PyTeXMK.git
cd PyTeXMK
uv sync
uv run pytexmk --version
```

### TeX 发行版集成

PyTeXMK 可以与主流 TeX 发行版无缝配合：

- **MiKTeX**: 安装后自动识别，自动检测已安装的引擎和辅助工具
- **TeX Live**: 完全兼容，支持 tlmgr 管理的完整工具链
- **手动路径**: 如果 TeX 发行版不在 PATH 中，可通过配置文件或环境变量指定

---

## 🚀 快速开始

### 最小化示例

1. 在 LaTeX 项目根目录下有主文件 `main.tex`：

```latex
% !TEX program = XeLaTeX
\documentclass{article}
\begin{document}
Hello, PyTeXMK!
\end{document}
```

2. 在项目目录下运行：

```bash
pytexmk
```

3. 编译完成后，PDF 文件生成在 `Build/main.pdf`，辅助文件在 `Auxiliary/` 目录。

### 编译指定文件

```bash
pytexmk mydocument
```

### 编译后自动预览 PDF

```bash
pytexmk -pv
```

### 清理辅助文件

```bash
pytexmk -c    # 清理辅助文件
pytexmk -C    # 清理辅助文件和输出 PDF
```

---

## 📋 完整命令参考

运行 `pytexmk --help` 查看完整帮助信息。

### 基础选项

| 参数 | 说明 |
|------|------|
| `-v`, `--version` | 显示版本号并退出 |
| `-h`, `--help` | 显示帮助信息并退出 |
| `-r`, `--readme` | 在浏览器中打开 README 文档 |

### 引擎选择

| 参数 | 说明 |
|------|------|
| `-x`, `--XeLaTeX` | 强制使用 XeLaTeX 编译 |
| `-l`, `--LuaLaTeX` | 强制使用 LuaLaTeX 编译 |
| `-p`, `--PdfLaTeX` | 强制使用 PdfLaTeX 编译 |
| `--engine {xelatex,lualatex,pdflatex}` | 显式指定 TeX 引擎 |
| `--auto` | 启用智能引擎自动判定（默认） |
| `--no-auto` | 禁用智能引擎自动判定 |

### 参考文献与索引

| 参数 | 说明 |
|------|------|
| `--bib {auto,bibtex,biber}` | 指定参考文献工具 |
| `--index {auto,makeindex,xindy}` | 指定索引工具 |

### 编译控制

| 参数 | 说明 |
|------|------|
| `-n N`, `--runs N` | 固定编译次数（默认 2，设为 3 时包含 bib 编译） |
| `-dr`, `--draft` | 草稿模式（无图显示，提高编译速度） |
| `--timeout SECONDS` | 单次编译超时时间（默认 300 秒） |
| `--non-interactive` | 非交互模式，不询问用户，适合 CI/CD 环境 |
| `-nq`, `--non-quiet` | 非安静模式，终端显示完整编译日志 |
| `-vb`, `--verbose` | 显示详细调试信息 |

### 输出控制

| 参数 | 说明 |
|------|------|
| `-o DIR`, `--outdir DIR` | 指定 PDF 输出目录（覆盖魔法注释和配置） |
| `--auxdir DIR` | 指定辅助文件目录 |
| `-O`, `--open` | 编译成功后自动打开 PDF 预览 |
| `-pv [FILE]`, `--pdf-preview [FILE]` | 编译后预览 PDF；指定 FILE 则直接打开该文件 |
| `-pr`, `--pdf-repair` | 尝试修复 PDF 文件（解决 invalid X X R object 警告） |

### SyncTeX 和 Shell Escape

| 参数 | 说明 |
|------|------|
| `--synctex` | 启用 SyncTeX（默认） |
| `--no-synctex` | 禁用 SyncTeX |
| `--shell-escape` | 启用 `-shell-escape`（默认） |
| `--no-shell-escape` | 禁用 `-shell-escape` |

### 清理命令

| 参数 | 说明 |
|------|------|
| `-c`, `--clean` | 清除当前主文件的辅助文件 |
| `-C`, `--Clean` | 清除辅助文件（含根目录）和输出 PDF |
| `-ca`, `--clean-any` | 清除所有带辅助文件后缀的文件 |
| `-Ca`, `--Clean-any` | 清除所有辅助文件和主文件输出 PDF（含根目录） |

### PVC 实时监听模式

| 参数 | 说明 |
|------|------|
| `--pvc`, `--continuous` | 启用 PVC 模式（实时监听+自动编译） |
| `--pvc-debounce SECONDS` | 文件变更防抖时间（默认 1.0 秒） |
| `--pvc-preview` | PVC 模式下编译成功自动打开预览 |

### LaTeXDiff 文档对比

| 参数 | 说明 |
|------|------|
| `-d [OLD NEW]`, `--LaTeXDiff [OLD NEW]` | 生成 LaTeXDiff 对比文件（不编译） |
| `-dc [OLD NEW]`, `--LaTeXDiff-compile [OLD NEW]` | 生成对比文件并编译 |
| `--diff-flatten` | LaTeXDiff 时压平 `\input`/`\include` 子文件 |
| `--diff-fast` | 使用 latexdiff `--fast` 模式 |
| `--diff-output FILE` | LaTeXDiff 输出文件名 |
| `--diff-style {1,2}` | 显示风格：1-显示参考文献修改，2-不显示（默认 2） |

---

## 🔮 魔法注释

PyTeXMK 支持在 TeX 文件前 50 行使用魔法注释来配置编译行为。优先级高于配置文件。

| 魔法注释 | 说明 |
|----------|------|
| `% !TEX program = XeLaTeX` | 指定编译引擎：XeLaTeX / PdfLaTeX / LuaLaTeX |
| `% !TEX root = main.tex` | 指定待编译主文件名（仅支持根目录下文件） |
| `% !TEX outdir = out_folder` | 指定编译结果（PDF）存放位置 |
| `% !TEX auxdir = aux_folder` | 指定辅助文件存放位置 |
| `% !TEX bib = biber` | 指定参考文献工具：bibtex / biber |
| `% !TEX index = xindy` | 指定索引工具：makeindex / xindy |

**配置优先级**（从高到低）：
1. 命令行参数
2. 魔法注释
3. 项目配置文件 (`.pytexmkrc` in project dir)
4. 用户配置文件 (`~/.pytexmkrc`)
5. 内置默认值

---

## ⚙️ 配置文件详解

PyTeXMK 使用 TOML 格式的配置文件，支持两级配置：

- **用户级配置**: `~/.pytexmkrc` — 对所有项目生效
- **项目级配置**: `./.pytexmkrc` — 仅对当前项目生效，会覆盖用户配置

首次运行时 PyTeXMK 会自动生成默认配置文件。

### 完整配置项说明

```toml
# ============ 基础设置 ============
default_file = "main"           # 默认主文件名（不含 .tex 后缀）
compiled_program = "XeLaTeX"    # 默认编译器：XeLaTeX / PdfLaTeX / LuaLaTeX
non_quiet = false               # true=显示编译日志，false=安静模式
quiet_mode = true               # 安静模式（与 non_quiet 相反，保留向后兼容）

# ============ PDF 预览设置 ============
[pdf]
pdf_preview_status = false      # 编译结束后是否自动打开 PDF
pdf_viewer = "default"          # PDF 查看器：default=系统默认查看器

# ============ 目录设置 ============
[folder]
auxdir = "./Auxiliary/"         # 辅助文件存放目录
outdir = "./Build/"             # PDF 输出目录

# ============ 编译引擎设置 ============
[engine]
default = "xelatex"             # 默认引擎：xelatex / lualatex / pdflatex
auto_detect = true              # 是否启用智能引擎自动判定
fallback_order = ["xelatex", "lualatex", "pdflatex"]  # 降级优先级
timeout = 300                   # 单次编译超时秒数

# ============ 参考文献设置 ============
[bib]
default_tool = "auto"           # auto=自动检测 / bibtex / biber

# ============ 索引设置 ============
[index]
default_tool = "auto"           # auto=自动检测 / makeindex / xindy
index_style_file = "nomencl.ist" # 索引样式文件
input_suffix = ".nlo"           # 索引输入文件后缀
output_suffix = ".nls"          # 索引输出文件后缀

# ============ 编译设置 ============
[compilation]
default_run_count = 2           # 默认固定编译次数
max_extra_passes = 2            # 智能补编最大重试次数
shell_escape = true             # 是否启用 -shell-escape
synctex = true                  # 是否启用 SyncTeX
quiet = true                    # 是否静默编译（batchmode）

# ============ PVC 实时监听设置 ============
[pvc]
enabled = false                 # 是否默认开启 PVC 模式
debounce = 1.0                  # 文件变更防抖秒数
auto_open_preview = false       # 编译成功后自动打开预览
watch_extensions = [".tex", ".bib", ".bst", ".cls", ".sty", ".idx", ".ist", ".png", ".jpg", ".pdf", ".eps"]
exclude_dirs = ["build", ".git", "__pycache__", ".venv", "node_modules"]

# ============ LaTeXDiff 设置 ============
[diff]
flatten = false                 # 是否默认压平子文件
fast = false                    # 是否使用 latexdiff --fast 模式
auto_compile = true             # 生成 diff 后是否自动编译

[latexdiff]                     # 旧版配置（向后兼容）
old_tex_file = "old_file"
new_tex_file = "new_file"
diff_tex_file = "LaTeXDiff"
```

---

## 🌐 环境变量

| 环境变量 | 说明 | 示例 |
|----------|------|------|
| `PYTEXMK_LANG` | 强制指定界面语言 | `PYTEXMK_LANG=en` 或 `PYTEXMK_LANG=zh_CN` |
| `LANGUAGE` / `LANG` / `LC_ALL` / `LC_MESSAGES` | 系统语言（自动检测） | `LANG=zh_CN.UTF-8` |

语言检测优先级：`PYTEXMK_LANG` → `LANGUAGE` → `LANG` → `LC_ALL` → `LC_MESSAGES` → 系统 locale → 默认英语。

---

## 📝 使用案例

### 案例 1：基础编译（中文文档）

**场景**：使用 XeLaTeX 编译中文论文。

**`main.tex`**：
```latex
% !TEX program = XeLaTeX
\documentclass{ctexart}
\title{测试文档}
\author{作者}
\begin{document}
\maketitle
你好，PyTeXMK！
\end{document}
```

**命令**：
```bash
pytexmk
```

**预期输出**：
- `Build/main.pdf` — 编译后的 PDF
- `Auxiliary/` — 辅助文件（.aux, .log, .out 等）

---

### 案例 2：使用 BibLaTeX + Biber

**场景**：使用 BibLaTeX 宏包和 Biber 后端处理参考文献。

**`main.tex`**：
```latex
% !TEX program = XeLaTeX
% !TEX bib = biber
\documentclass{article}
\usepackage[backend=biber]{biblatex}
\addbibresource{refs.bib}
\begin{document}
引用测试~\cite{knuth1984texbook}。
\printbibliography
\end{document}
```

**命令**：
```bash
pytexmk -n 3    # 编译3次以确保参考文献正确生成
```

或让 PyTeXMK 自动检测（推荐）：
```bash
pytexmk
```

---

### 案例 3：使用 xindy 索引

**场景**：生成中英文索引，使用 xindy 支持 Unicode 排序。

**命令**：
```bash
pytexmk --index xindy
```

或通过魔法注释：
```latex
% !TEX index = xindy
```

---

### 案例 4：非交互模式（CI/CD 环境）

**场景**：在 GitHub Actions 等 CI 环境中自动编译 LaTeX 文档。

```bash
pytexmk --non-interactive --timeout 120
```

---

### 案例 5：草稿模式快速编译

**场景**：编写阶段快速预览，不需要图片。

```bash
pytexmk -dr
```

---

### 案例 6：修复损坏的 PDF

**场景**：编译日志出现 `invalid X X R object` 警告时。

```bash
pytexmk -pr
```

---

## 👀 PVC 实时监听模式

PVC（Preview Continuous）模式类似 `latexmk -pvc`，启动后持续监听项目目录下的文件变化，当检测到 `.tex`、`.bib`、`.sty` 等文件保存时自动触发编译。

### 启动 PVC 模式

```bash
pytexmk --pvc
```

### 带自动预览

```bash
pytexmk --pvc --pvc-preview
```

### 自定义防抖时间

```bash
pytexmk --pvc --pvc-debounce 2.0
```

### PVC 模式特点

- 使用 watchdog 库高效监听文件系统事件
- 防抖机制避免保存过程中的多次触发
- 自动过滤 `.git`、`__pycache__`、`build` 等目录
- 按 `Ctrl+C` 退出监听模式
- 编译失败时显示错误摘要，修复后自动重编

---

## 📄 LaTeXDiff 文档对比

LaTeXDiff 功能可以生成两个版本 TeX 文件的差异对比 PDF，方便查看修改内容。

### 基本用法

```bash
# 生成对比文件但不编译
pytexmk -d old_version.tex new_version.tex

# 生成对比文件并编译成 PDF
pytexmk -dc old_version.tex new_version.tex
```

### 压平子文件

如果文档使用了 `\input` 或 `\include`：

```bash
pytexmk -dc old.tex new.tex --diff-flatten
```

### 配置文件预设

在 `.pytexmkrc` 中配置后可省略命令行参数：

```toml
[latexdiff]
old_tex_file = "v1.tex"
new_tex_file = "v2.tex"
diff_tex_file = "diff"
```

然后直接运行：
```bash
pytexmk -dc
```

---

## 🤖 GitHub Actions 集成

在 GitHub Actions 中使用 PyTeXMK 编译 LaTeX 文档：

```yaml
name: Build LaTeX
on: [push, pull_request]

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Install uv
        uses: astral-sh/setup-uv@v4
        with:
          python-version: '3.13'

      - name: Install PyTeXMK
        run: uv pip install pytexmk

      - name: Install TeX Live (minimal)
        run: |
          sudo apt-get update
          sudo apt-get install -y texlive-xetex texlive-latex-extra texlive-bibtex-extra biber

      - name: Compile LaTeX
        run: pytexmk --non-interactive --timeout 120

      - name: Upload PDF artifact
        uses: actions/upload-artifact@v4
        with:
          name: compiled-pdf
          path: Build/*.pdf
```

---

## ❓ 常见问题 FAQ

### Q1: 如何切换中英文界面？

设置环境变量 `PYTEXMK_LANG`：
```bash
# Windows PowerShell
$env:PYTEXMK_LANG = "en"

# Linux/macOS
export PYTEXMK_LANG=en
```

### Q2: 编译时提示引擎未找到？

确保 TeX Live 或 MiKTeX 已正确安装且添加到系统 PATH：
```bash
xelatex --version
```
如果命令找不到，请检查 TeX 发行版安装。

### Q3: 如何让 PDF 输出到当前目录而非 Build/？

使用 `-o` 参数或魔法注释：
```bash
pytexmk -o .
```
或在 TeX 文件头部添加：
```latex
% !TEX outdir = .
```

### Q4: 中文文档应该用哪个引擎？

推荐使用 **XeLaTeX**（默认引擎），它对中文和 Unicode 的支持最好。PyTeXMK 的智能降级也会优先选择 XeLaTeX。

### Q5: PVC 模式下哪些文件会触发重编译？

默认监听 `.tex`, `.bib`, `.bst`, `.cls`, `.sty`, `.idx`, `.ist`, `.png`, `.jpg`, `.pdf`, `.eps` 等后缀的文件。可在配置文件 `[pvc]` 段的 `watch_extensions` 中自定义。

### Q6: 如何在 VS Code 中使用 PyTeXMK？

在 VS Code 的 LaTeX Workshop 扩展中配置：
```json
"latex-workshop.latex.recipes": [
  {
    "name": "PyTeXMK",
    "tools": ["pytexmk"]
  }
],
"latex-workshop.latex.tools": [
  {
    "name": "pytexmk",
    "command": "pytexmk",
    "args": ["--non-interactive", "-nq", "%DOCFILE%"]
  }
]
```

### Q7: 如何完全清理项目？

```bash
pytexmk -Ca    # 清理所有辅助文件和输出文件（含根目录）
```

### Q8: 支持哪些操作系统？

PyTeXMK 全平台支持：
- **Windows**: 10/11，支持 MiKTeX 和 TeX Live
- **macOS**: 10.15+，Intel 和 Apple Silicon
- **Linux**: 主流发行版（Ubuntu 20.04+, Fedora, Arch 等）

---

## 👥 贡献指南

欢迎提交 Issue 和 Pull Request！

### 开发环境设置

```bash
git clone https://github.com/YanMing-lxb/PyTeXMK.git
cd PyTeXMK
uv sync --dev
```

### 常用开发命令

| 命令 | 说明 |
|------|------|
| `make help` | 显示所有可用命令 |
| `make test` | 运行单元测试 |
| `make test-cov` | 运行测试并生成覆盖率报告 |
| `make lint` | Ruff 代码规范检查 |
| `make lint-fix` | 自动修复 lint 问题 |
| `make format` | Ruff 格式化代码 |
| `make build` | 构建 wheel 包 |
| `make i18n-update` | 更新国际化翻译文件 |
| `make ci-test` | 运行完整 CI 测试流程 |
| `make clean` | 清理构建产物 |

### 代码规范

- 遵循 PEP 8 规范
- 使用 Ruff 进行 lint 和格式化
- 添加类型注解
- 新功能需补充单元测试

---

## 📋 更新日志

详见 [CHANGELOG.md](CHANGELOG.md)。

**v1.1.0 主要更新**：
- 新增 PVC 实时监听模式（文件监听+自动编译）
- 新增 xindy 索引工具支持
- 智能引擎降级：XeLaTeX → LuaLaTeX → PdfLaTeX
- 增强 LaTeXDiff 功能（flatten、fast 模式）
- 中英文国际化支持
- Python 3.13 支持
- 完整的 GitHub Actions CI/CD 流程
- 跨平台打包支持（PyInstaller）
- 327+ 单元测试覆盖

---

## 📄 开源协议

本项目采用 **GNU General Public License v3.0 or later** 协议开源。

详见 [LICENSE](LICENSE) 文件。

---

<p align="center">
由 <a href="https://github.com/YanMing-lxb">焱铭</a> 用 ❤️ 制作<br/>
如有问题请在 <a href="https://github.com/YanMing-lxb/PyTeXMK/issues">GitHub Issues</a> 反馈
</p>
