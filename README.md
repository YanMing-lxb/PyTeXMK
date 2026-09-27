<div align="center">
  <img src="https://github.com/YanMing-lxb/PyTeXMK/blob/main/imgs/pytexmk-logo.png?raw=true" alt="PyTeXMK Logo" width="128" height="128">
  <h1>PyTeXMK</h1>
  <p>LaTeX 辅助编译命令行工具</p>

  <p>
    <a href="https://pypi.python.org/pypi/pytexmk/">
      <img src="https://img.shields.io/pypi/v/pytexmk.svg?color=blue" alt="PyPI version">
    </a>
    <a href="https://pypi.org/project/pytexmk/">
      <img src="https://img.shields.io/pypi/dm/pytexmk.svg?label=PyPI%20downloads" alt="PyPI Downloads">
    </a>
    <a href="https://github.com/YanMing-lxb/PyTeXMK/releases/latest">
      <img src="https://img.shields.io/github/release/YanMing-lxb/PyTeXMK.svg?color=blueviolet&label=release" alt="GitHub release">
    </a>
    <a href="https://github.com/YanMing-lxb/PyTeXMK/blob/main/LICENSE">
      <img src="https://img.shields.io/badge/license-GPLv3-aff" alt="License">
    </a>
    <a href="#">
      <img src="https://img.shields.io/badge/OS-Linux%20%7C%20Windows%20%7C%20macOS-pink.svg" alt="OS">
    </a>
  </p>

  <p>
    <a href="https://github.com/YanMing-lxb/PyTeXMK/issues">
      <img src="https://img.shields.io/github/issues/YanMing-lxb/PyTeXMK" alt="Issues">
    </a>
    <a href="https://github.com/YanMing-lxb/PyTeXMK">
      <img src="https://img.shields.io/github/last-commit/YanMing-lxb/PyTeXMK" alt="Last Commit">
    </a>
    <a href="https://github.com/YanMing-lxb/PyTeXMK">
      <img src="https://img.shields.io/github/repo-size/YanMing-lxb/PyTeXMK" alt="Repo Size">
    </a>
    <a href="https://star-history.com/#YanMing-lxb/PyTeXMK&Date">
      <img src="https://img.shields.io/github/stars/YanMing-lxb/PyTeXMK?style=social" alt="Stars">
    </a>
  </p>

  <p>
    <a href="README.md">简体中文</a>
    ·
    <a href="README.en.md">English</a>
  </p>
</div>

---

**PyTeXMK**（Python TeX Make）是一个用 Python 编写的 LaTeX 自动化编译工具，灵感来源于 `latexmk`。它能够根据辅助文件变化智能决定编译轮次，配合 Rich 彩色输出、参考文献/索引工具链自动调度，让 LaTeX 编译工作流一键完成。

---

## ✨ 功能特性

### 核心编译

- 🚀 **多引擎支持**：XeLaTeX、PdfLaTeX、LuaLaTeX，通过命令行参数或魔法注释灵活切换
- 🔁 **智能多次编译检测**：自动比较 `.aux`/`.out` 文件内容并解析日志 Rerun 警告，确保交叉引用、hyperref 书签、总页数等收敛稳定
- 📋 **结构化编译检测报告**：每轮编译结束后输出 6 维检测状态（参考文献、索引、目录、交叉引用、书签文件、日志重编译），清晰展示各维度是否稳定及预期下一步

### 参考文献与索引

- 📚 **参考文献**：自动调度 bibtex / biblatex（biber）/ thebibliography
- 📑 **索引与术语表**：glossaries（含 glossaries-extra + bib2gls + biber）、nomencl、makeidx，自动选择 xindy 或 makeindex 后端
- 🔮 **魔法注释**：通过 `% !TEX` 注释指定编译引擎、主文件、输出目录、辅助目录等

### 辅助工具

- 🧹 **智能清理**：多种清理模式，支持按目录范围和文件后缀精确清理辅助文件
- 🔍 **日志解析**：编译失败后自动解析 LaTeX 日志，定位错误位置
- 📝 **LaTeXDiff**：两个 LaTeX 文件差异对比，生成带修订标记的 PDF
- 🖼 **PDF 修复与预览**：损坏 PDF 自动修复，编译后自动预览

### 配置与扩展

- 🌍 **国际化**：支持多语言界面，默认中文
- ⚙️ **两级配置文件**：用户级 + 项目级 `.pytexmkrc`，所有参数均可自定义
- 🧩 **多子项目管理**：一个根目录下管理多个独立子项目，支持自动扫描和逐一编译
- 🪲 **版本检查**：自动检查更新，第一时间获取新版本

---

## 📸 预览

<div align="center">
  <img src="https://github.com/YanMing-lxb/PyTeXMK/blob/main/imgs/show1.png?raw=true" alt="PyTeXMK 预览 1" width="45%" style="border-radius: 8px; box-shadow: 0 4px 12px rgba(0,0,0,0.15);">
  <img src="https://github.com/YanMing-lxb/PyTeXMK/blob/main/imgs/show2.png?raw=true" alt="PyTeXMK 预览 2" width="45%" style="border-radius: 8px; box-shadow: 0 4px 12px rgba(0,0,0,0.15);">
</div>

---

## 🚀 快速开始

### 前置条件

在安装 PyTeXMK 之前，请确保你的系统已安装以下组件：

1. **Python 3.14+**（通过 uv 管理推荐）
2. **LaTeX 发行版**（任选其一）：
   - **Windows**: [MiKTeX](https://miktex.org/) 或 [TeX Live](https://tug.org/texlive/)
   - **macOS**: [MacTeX](https://www.tug.org/mactex/) 或 BasicTeX
   - **Linux**: TeX Live（发行版自带或官方安装）
3. **可选工具**（按需安装）：
   - `biber`（biblatex 后端，用于参考文献处理）
   - `xindy`（glossaries 后端，用于术语表编译）
   - `latexdiff`（LaTeX 文件差异对比）

### 安装

#### 通过 pip 或 uv

```bash
# 使用 pip 安装
pip install pytexmk

# 使用 uv 安装（推荐）
uv add pytexmk
```

#### Windows winget（推荐，无需 Python 环境）

```powershell
winget install --id YanMing-lxb.PyTeXMK
```

### 升级

```bash
# pip
pip install --upgrade pytexmk

# uv（升级到最新版）
uv add pytexmk@latest

# winget
winget upgrade --id YanMing-lxb.PyTeXMK
```

### 基本使用

在 LaTeX 项目根目录下运行：

```bash
# 使用默认配置（XeLaTeX + main.tex + Build/）编译
pytexmk

# 指定主文件编译
pytexmk main.tex

# 使用 PdfLaTeX 编译
pytexmk -p main.tex

# 编译 + 预览 PDF
pytexmk main.tex -pv

# 清理辅助文件
pytexmk -c
```

> **注意**：PyTeXMK 仅支持 UTF-8 编码的 TeX 文件。

---

## ⚙️ 默认配置

| 配置项 | 默认值 | 说明 |
| --- | --- | --- |
| 编译程序 | `XeLaTeX` | 可选：XeLaTeX、PdfLaTeX、LuaLaTeX |
| 主文件名 | `main.tex` | 待编译的 LaTeX 主文件 |
| 输出目录 | `Build` | 编译结果存放目录 |
| 辅助目录 | `Auxiliary` | 辅助文件存放目录 |
| 编译模式 | batch 模式 | 编译过程不在终端显示详细日志 |

> **提示**：以上参数均可在配置文件中修改，详见 [配置文件说明](#配置文件说明)。
>
> **VSCode 用户**：在 `settings.json` 中设置 `"latex-workshop.latex.outDir": "./Build"` 以便 LaTeX-Workshop 找到 PDF 文件。

---

## 📖 使用说明

### 编译引擎与模式

| 选项 | 说明 |
| --- | --- |
| `-p`, `--PdfLaTeX` | 使用 PdfLaTeX 编译 |
| `-x`, `--XeLaTeX` | 使用 XeLaTeX 编译（默认） |
| `-l`, `--LuaLaTeX` | 使用 LuaLaTeX 编译 |
| `-dr`, `--draft` | 草稿模式，编译时不包含图片（加速） |
| `-nq`, `--non_quiet` | 非安静模式，终端显示编译过程 |
| `-vb`, `--verbose` | 详细模式，显示 PyTeXMK 运行信息 |

### 清理

| 选项 | 说明 |
| --- | --- |
| `-c`, `--clean` | 清除主文件的辅助文件 |
| `-C`, `--Clean` | 清除辅助文件（含根目录）和输出文件 |
| `-ca`, `--clean-any` | 清除所有带辅助文件后缀的文件 |
| `-Ca`, `--Clean-any` | 清除所有辅助文件（含根目录）和主文件输出 |

### LaTeXDiff 差异对比

| 选项 | 说明 |
| --- | --- |
| `-d`, `--LaTeXDiff` | 生成两个文件的差异对比，输出 `LaTeXDiff.tex` |
| `-dc`, `--LaTexDiff-compile` | 生成差异文件并自动编译，输出带修订标记的 PDF |

**示例**：

```bash
pytexmk -d old.tex new.tex     # 生成 LaTeXDiff.tex
pytexmk -dc old.tex new.tex    # 生成并编译 LaTeXDiff PDF
```

> 支持在参考文献和符号索引中显示修改痕迹，编译时会提示选择风格。

### PDF 工具

| 选项 | 说明 |
| --- | --- |
| `-pr`, `--pdf-repair` | 修复损坏的 PDF 文件（如图片导致的 `invalid X X R object` 警告） |
| `-pv`, `--pdf-preview` | 编译完成后调用浏览器或本地 PDF 阅读器预览 |

### 多子项目管理

PyTeXMK 支持在一个项目根目录下管理多个相互独立的子项目，各自拥有独立的编译配置和输出目录。

**典型流程**：

```bash
# 1. 生成根配置文件
pytexmk -i

# 2. 自动扫描并展示子项目清单（同时更新配置）
pytexmk -ls

# 3. 编译指定子项目（可与主文件名配合）
pytexmk -s 论文 main.tex
```

| 选项 | 说明 |
| --- | --- |
| `-s`, `--subproject <名称>` | 选中指定子项目并在其目录下编译/清理 |
| `-ls`, `--list-subprojects` | 扫描子项目并展示清单，同步更新根配置 |

### 配置文件生成

| 选项 | 说明 |
| --- | --- |
| `-i`, `--init` | 在当前目录生成项目级 `.pytexmkrc` |
| `-iu`, `--init-user` | 在用户主目录生成用户级 `.pytexmkrc` |
| `-f`, `--force` | 配合 `-i`/`-iu` 强制覆盖已存在的配置文件 |

### 其他

| 选项 | 说明 |
| --- | --- |
| `document` | 位置参数，指定要编译的文件名（可省略后缀） |
| `-h`, `--help` | 显示帮助信息 |
| `-v`, `--version` | 显示程序版本号 |

### 魔法注释

PyTeXMK 支持在 LaTeX 主文件前 50 行使用魔法注释来自定义编译行为：

| 魔法注释 | 说明 | 示例 |
| --- | --- | --- |
| `% !TEX program = <引擎>` | 指定编译引擎 | `% !TEX program = PdfLaTeX` |
| `% !TEX root = <文件名>` | 指定待编译主文件 | `% !TEX root = main` |
| `% !TEX outdir = <目录>` | 指定输出目录 | `% !TEX outdir = output` |
| `% !TEX auxdir = <目录>` | 指定辅助目录 | `% !TEX auxdir = auxfiles` |

> **注意**：魔法注释仅在主文件中定义有效，子文件中的注释会被忽略。

### 工作原理

<details>
<summary><b>📂 主文件自动识别</b></summary>

1. 命令行参数明确指定 → 使用该文件
2. 当前目录仅一个 `.tex` 文件 → 自动选中
3. 存在 `% !TEX root` 魔法注释 → 使用注释值
4. 检索 `\documentclass` 或 `\begin{document}`（前 200 行）→ 识别主文件
5. 默认回退到 `main.tex`

</details>

<details>
<summary><b>⚙️ 编译引擎选择</b></summary>

1. 命令行参数 `-p` / `-x` / `-l` → 最高优先级
2. 魔法注释 `% !TEX program` → 使用注释值
3. 均未指定 → 默认 `XeLaTeX`

</details>

<details>
<summary><b>🔁 自动编译轮次</b></summary>

1. 第一次编译 LaTeX
2. 若 `.aux` 中存在参考文献引用，调度 bibtex / biber
3. 若存在术语表/索引，调度 makeindex / xindy
4. 继续编译 LaTeX，每轮结束后检测各维度是否收敛
5. 所有维度稳定或达到安全上限后停止

</details>

### 配置文件说明

PyTeXMK 支持两级配置文件，均为 TOML 格式：

| 类型 | Windows | Linux / macOS |
| --- | --- | --- |
| 用户级 | `C:\Users\用户名\.pytexmkrc` | `~/.pytexmkrc` |
| 项目级 | 当前目录 `.pytexmkrc` | 当前目录 `.pytexmkrc` |

**优先级**：项目级 > 用户级 > 内置默认值

配置文件可通过 `pytexmk -i`（项目级）或 `pytexmk -iu`（用户级）生成模板，生成的模板中包含详细注释。

---

## 🛠 开发与构建

### 环境要求

- Python 3.14+
- [uv](https://github.com/astral-sh/uv)（推荐）或 pip

### 开发环境搭建

```bash
# 克隆项目
git clone https://github.com/YanMing-lxb/PyTeXMK.git
cd PyTeXMK

# 安装开发依赖
uv sync --all-extras --dev

# 运行开发版本
uv run pytexmk --help
```

### 构建分发包

```bash
# 构建 wheel 和 sdist
uv build
```

### 构建可执行程序

```bash
# 生成平台图标
make icon

# 构建源码模式的可执行程序（onedir 目录）
make build

# 清理构建产物
make clean
```

> **Windows 中的 make 命令**需要单独配置，详见 [Windows 下使用 make](docs/Window%20下使用%20make.md)。

### 代码检查

```bash
uv run ruff check src/
uv run ruff format src/
```

### 国际化工作流

```bash
# 新增语言
make lang-add

# 更新所有 pot/po
make lang-update

# 编译 po → mo
make lang-mo

# 重新抽取所有 pot 模板
make lang-poup
```

---

## 📄 许可证

本项目基于 [GPLv3](LICENSE) 许可证开源。

---

## 📝 更新记录

详细更新记录请参阅 [CHANGELOG.md](CHANGELOG.md)。

---

## 🤝 参与贡献

欢迎提交 Issue 和 Pull Request！

- 🐛 遇到 Bug？请在 [Issues](https://github.com/YanMing-lxb/PyTeXMK/issues) 中提交
- 💡 有新功能建议？欢迎讨论
- 🌍 想帮助翻译？请查看 [国际化工作流](#国际化工作流)

---

## ⭐ Star History

[![Star History Chart](https://api.star-history.com/svg?repos=YanMing-lxb/PyTeXMK&type=Date)](https://star-history.com/#YanMing-lxb/PyTeXMK&Date)

---

<div align="center">

**如果这个项目对你有帮助，欢迎点个 Star ⭐ 支持一下！**

</div>
