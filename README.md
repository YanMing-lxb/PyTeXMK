<div align="center">
  <img src="https://github.com/YanMing-lxb/PyTeXMK/blob/main/imgs/pytexmk-logo.png?raw=true" alt="PyTeXMK Logo" width="128" height="128">
  <h1>PyTeXMK</h1>
  <p>LaTeX 辅助编译命令行程序</p>

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

## ✨ 功能特性

- 🚀 **多引擎支持**：XeLaTeX、PdfLaTeX、LuaLaTeX 三大编译引擎
- 📚 **参考文献**：支持 bibtex、biblatex、thebibliography
- 📑 **索引支持**：glossaries、nomencl、mkeidx
- 🔁 **智能多次编译检测**：自动比较 aux/out 文件内容并解析日志 Rerun 警告，确保交叉引用、hyperref 书签、lastpage 总页数等收敛稳定
- 🔮 **魔法注释**：通过 `% !TEX` 注释指定编译引擎、主文件、输出目录等
- 🧹 **智能清理**：支持多种清理模式，精确清理辅助文件
- 🌍 **国际化**：支持多语言界面
- 🔍 **日志解析**：编译失败后自动解析 LaTeX 日志，定位错误
- 📝 **LaTeXDiff**：支持 LaTeX 文件差异对比
- ⚙️ **配置文件**：支持用户配置和项目配置两级配置
- 🔔 **版本检查**：自动检查更新，第一时间获取新版本

---

## 📸 预览

<div align="center">
  <img src="https://github.com/YanMing-lxb/PyTeXMK/blob/main/imgs/show1.png?raw=true" alt="PyTeXMK 预览 1" width="45%" style="border-radius: 8px; box-shadow: 0 4px 12px rgba(0,0,0,0.15);">
  <img src="https://github.com/YanMing-lxb/PyTeXMK/blob/main/imgs/show2.png?raw=true" alt="PyTeXMK 预览 2" width="45%" style="border-radius: 8px; box-shadow: 0 4px 12px rgba(0,0,0,0.15);">
</div>

---

## 🚀 快速开始

### 安装

官方版本 PyTeXMK 发布在 [PyPI](https://pypi.org/project/pytexmk/) 上，可以通过 pip 或 uv 轻松安装：

```bash
# 使用 pip 安装
pip install pytexmk

# 使用 uv 安装（推荐）
uv pip install pytexmk
```

### 升级

```bash
# pip
pip install --upgrade pytexmk

# uv
uv pip install --upgrade pytexmk
```

### 基本使用

在 LaTeX 项目根目录下运行：

```bash
# 使用默认配置编译
pytexmk

# 指定主文件编译
pytexmk main.tex

# 使用 XeLaTeX 编译
pytexmk -x main.tex

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
| 编译模式 | batch 模式 | 编译过程不显示详细信息 |

> **提示**：以上参数均可在配置文件中修改，详见 [配置文件说明](#配置文件说明)。
>
> VSCode 用户需在 `settings.json` 中设置 `"latex-workshop.latex.outDir": "./Build"` 以便 LaTeX-Workshop 找到 PDF 文件。

---

## 📖 使用说明

### 编译命令

PyTeXMK 支持的编译选项：

**位置参数**

| 参数 | 说明 |
| --- | --- |
| `document` | 要被编译的文件名 |

**选项参数**

| 选项 | 说明 |
| --- | --- |
| `-h`, `--help` | 显示帮助信息 |
| `-v`, `--version` | 显示程序版本号 |
| `-p`, `--PdfLaTeX` | 使用 PdfLaTeX 进行编译 |
| `-x`, `--XeLaTeX` | 使用 XeLaTeX 进行编译 |
| `-l`, `--LuaLaTeX` | 使用 LuaLaTeX 进行编译 |
| `-d`, `--LaTeXDiff` | 使用 LaTeXDiff 生成改动对比文件 |
| `-dc`, `--LaTexDiff-compile` | 使用 LaTeXDiff 生成对比文件并编译新文件 |
| `-dr`, `--draft` | 启用草稿模式（无图显示，提高编译速度） |
| `-c`, `--clean` | 清除主文件的辅助文件 |
| `-C`, `--Clean` | 清除辅助文件（含根目录）和输出文件 |
| `-ca`, `--clean-any` | 清除所有带辅助文件后缀的文件 |
| `-Ca`, `--Clean-any` | 清除所有辅助文件（含根目录）和主文件输出 |
| `-nq`, `--non_quiet` | 非安静模式，显示编译过程 |
| `-vb`, `--verbose` | 显示 PyTeXMK 运行详细信息 |
| `-pr`, `--pdf-repair` | 修复所有根目录以外的 PDF 文件 |
| `-pv`, `--pdf-preview` | 编译后预览 PDF 文件 |

**参数说明**

- **`-pr`**：当 LaTeX 编译过程中报类似 `invalid X X R object at offset XXXXX` 的警告时，可使用此参数尝试修复所有 PDF 文件。该警告通常由 PDF 图片文件损坏导致。
- **`-d` / `-dc`**：输入示例：`pytexmk -d old_tex_file new_tex_file`，生成的改动对比文件名为 `LaTeXDiff.tex`。
- **`-pv`**：编译结束后调用浏览器或本地 PDF 阅读器预览。示例：`pytexmk main -pv` 或 `pytexmk -pv`。
- **`-dc` / `-d`**：支持在参考文献和符号索引中显示修改痕迹，编译过程中会提示选择风格（1-显示修改 / 2-不显示修改）。

### 魔法注释

PyTeXMK 支持使用魔法注释来自定义编译行为（仅检索文档前 50 行）。

| 魔法注释 | 说明 | 示例 |
| --- | --- | --- |
| `% !TEX program = <XeLaTeX>` | 指定编译类型 | `% !TEX program = PdfLaTeX` |
| `% !TEX root = <主文件名>` | 指定待编译主文件 | `% !TEX root = test_file` |
| `% !TEX outdir = <输出目录>` | 指定编译结果存放位置 | `% !TEX outdir = output` |
| `% !TEX auxdir = <辅助目录>` | 指定辅助文件存放位置 | `% !TEX auxdir = auxfiles` |

> **注意**：魔法注释仅支持在主文件中定义，不支持在子文件中定义。

### 主文件与编译类型选定逻辑

<details>
<summary><b>📂 待编译主文件选定逻辑</b></summary>

1. 命令行参数中指定主文件 → 编译该文件（如 `pytexmk <主文件名>`，可省略后缀）
2. 当前目录仅有一个 `.tex` 文件 → 默认使用该文件
3. 存在魔法注释 `% !TEX root` → 使用注释指定的文件
4. 检索 `\documentclass[]{}` 或 `\begin{document}` 判定（仅前 200 行）
5. 默认主文件名 `main.tex` → 尝试使用
6. 以上均失败 → 输出错误信息并退出

</details>

<details>
<summary><b>⚙️ 编译类型选定逻辑</b></summary>

1. 命令行参数 `-p` / `-x` / `-l` 指定 → 优先级最高
2. 魔法注释 `% !TEX program` 指定 → 使用注释值
3. 均未指定 → 使用默认 `XeLaTeX`

</details>

> 输出目录优先级：`% !TEX outdir` 魔法注释 > 默认 `Build`

### 配置文件说明

PyTeXMK 支持两级配置文件：**系统配置**和**项目配置**。

- **系统配置**：首次运行时自动生成，位于用户主目录下 `.pytexmkrc`
- **项目配置**：项目首次运行时自动生成，位于当前工作目录下 `.pytexmkrc`

自动生成的配置文件中包含详细注释，可根据需要进行修改。

**配置文件路径**

| 类型 | Windows | Linux / macOS |
| --- | --- | --- |
| 系统配置 | `C:\Users\用户名\.pytexmkrc` | `~/.pytexmkrc` |
| 项目配置 | 当前目录 `.pytexmkrc` | 当前目录 `.pytexmkrc` |

**优先级**：项目配置 > 系统配置

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

# 构建 Cython 加密的可执行程序（onedir 模式）
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

---

## 📄 许可证

本项目基于 [GPLv3](LICENSE) 许可证开源。

---

## 📝 更新记录

详细更新记录请参阅 [CHANGELOG.md](CHANGELOG.md)。

---

## ⭐ Star History

[![Star History Chart](https://api.star-history.com/svg?repos=YanMing-lxb/PyTeXMK&type=Date)](https://star-history.com/#YanMing-lxb/PyTeXMK&Date)

---

<div align="center">

**如果这个项目对你有帮助，欢迎点个 Star ⭐ 支持一下！**

</div>
