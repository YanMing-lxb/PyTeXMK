<div align="center">
  <img src="https://github.com/YanMing-lxb/PyTeXMK/blob/main/imgs/pytexmk-logo.png?raw=true" alt="PyTeXMK Logo" width="128" height="128">
  <h1>PyTeXMK</h1>
  <p>LaTeX Auxiliary Compilation Command Line Tool</p>

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

**PyTeXMK** (Python TeX Make) is an automated LaTeX build tool written in Python, inspired by `latexmk`. It intelligently determines the number of compilation passes based on auxiliary file changes, with Rich-colored terminal output and automatic bibliography/index toolchain orchestration — making the LaTeX build workflow a one-shot command.

---

## ✨ Features

### Core Compilation

- 🚀 **Multi-engine support**: XeLaTeX, PdfLaTeX, LuaLaTeX — switch freely via CLI flags or magic comments
- 🔁 **Smart multi-pass detection**: Automatically diffs `.aux`/`.out` file contents and parses Rerun warnings in logs, ensuring cross-references, hyperref bookmarks, and page counts converge stably
- 📋 **Structured compile-detection report**: After each pass, outputs a 6-dimension status report (bibliography, index, TOC, cross-references, bookmark file, log rerun), clearly showing which dimensions are stable and what's expected next

### Bibliography & Index

- 📚 **Bibliography**: Auto-orchestrate bibtex / biblatex (biber) / thebibliography
- 📑 **Index & glossary**: glossaries (incl. glossaries-extra + bib2gls + biber), nomencl, makeidx — auto-selects xindy or makeindex backend
- 🔮 **Magic comments**: Customize compilation behavior via `% !TEX` comments (engine, main file, output dir, auxiliary dir)

### Helper Tools

- 🧹 **Smart cleanup**: Multiple clean modes for precise auxiliary file removal by directory scope or file suffix
- 🔍 **Log parsing**: Auto-parse LaTeX logs on failure to locate error positions
- 📝 **LaTeXDiff**: Diff two LaTeX files, producing a PDF with revision marks
- 🖼 **PDF repair & preview**: Auto-repair corrupted PDFs; open default viewer after compilation

### Configuration & Extensibility

- 🌍 **Internationalization**: Multi-language UI support (default: Chinese)
- ⚙️ **Two-level config**: User-level and project-level `.pytexmkrc`, every parameter is customizable
- 🧩 **Multi-subproject management**: Manage and compile multiple independent subprojects under one root directory
- 🪲 **Version check**: Automatic update notifications

---

## 📸 Preview

<div align="center">
  <img src="https://github.com/YanMing-lxb/PyTeXMK/blob/main/imgs/show1.png?raw=true" alt="PyTeXMK Preview 1" width="45%" style="border-radius: 8px; box-shadow: 0 4px 12px rgba(0,0,0,0.15);">
  <img src="https://github.com/YanMing-lxb/PyTeXMK/blob/main/imgs/show2.png?raw=true" alt="PyTeXMK Preview 2" width="45%" style="border-radius: 8px; box-shadow: 0 4px 12px rgba(0,0,0,0.15);">
</div>

---

## 🚀 Quick Start

### Prerequisites

Before installing PyTeXMK, make sure your system has the following:

1. **Python 3.14+** (managing with uv recommended)
2. **A LaTeX distribution** (pick one):
   - **Windows**: [MiKTeX](https://miktex.org/) or [TeX Live](https://tug.org/texlive/)
   - **macOS**: [MacTeX](https://www.tug.org/mactex/) or BasicTeX
   - **Linux**: TeX Live (distro package or official install)
3. **Optional tools** (install as needed):
   - `biber` (biblatex backend for bibliography processing)
   - `xindy` (glossaries backend for glossary compilation)
   - `latexdiff` (LaTeX file diff comparison)

### Installation

#### Via pip or uv

```bash
# Install with pip
pip install pytexmk

# Install with uv (recommended)
uv add pytexmk
```

#### Windows winget (recommended, no Python required)

```powershell
winget install --id YanMing-lxb.PyTeXMK
```

### Upgrade

```bash
# pip
pip install --upgrade pytexmk

# uv (upgrade to latest)
uv add pytexmk@latest

# winget
winget upgrade --id YanMing-lxb.PyTeXMK
```

### Basic Usage

Run in your LaTeX project root:

```bash
# Compile with defaults (XeLaTeX + main.tex + Build/)
pytexmk

# Compile a specific main file
pytexmk main.tex

# Compile with PdfLaTeX
pytexmk -p main.tex

# Compile + preview PDF
pytexmk main.tex -pv

# Clean auxiliary files
pytexmk -c
```

> **Note**: PyTeXMK only supports UTF-8 encoded TeX files.

---

## ⚙️ Default Configuration

| Option | Default | Description |
| --- | --- | --- |
| Compiler | `XeLaTeX` | Options: XeLaTeX, PdfLaTeX, LuaLaTeX |
| Main file | `main.tex` | LaTeX main file to compile |
| Output dir | `Build` | Compilation result directory |
| Auxiliary dir | `Auxiliary` | Auxiliary files directory |
| Compile mode | batch mode | Silent compilation, no verbose log output in terminal |

> **Tip**: All parameters can be customized in config files. See [Configuration File](#configuration-file).
>
> **VSCode users**: Set `"latex-workshop.latex.outDir": "./Build"` in `settings.json` so LaTeX-Workshop can find the PDF.

---

## 📖 Usage

### Compilation Engine & Modes

| Option | Description |
| --- | --- |
| `-p`, `--PdfLaTeX` | Compile with PdfLaTeX |
| `-x`, `--XeLaTeX` | Compile with XeLaTeX (default) |
| `-l`, `--LuaLaTeX` | Compile with LuaLaTeX |
| `-dr`, `--draft` | Draft mode: compile without including images (faster) |
| `-nq`, `--non_quiet` | Non-quiet mode, show compilation process in terminal |
| `-vb`, `--verbose` | Verbose mode, show PyTeXMK runtime details |

### Cleanup

| Option | Description |
| --- | --- |
| `-c`, `--clean` | Clean auxiliary files of the main file |
| `-C`, `--Clean` | Clean auxiliary files (including root) and output files |
| `-ca`, `--clean-any` | Clean all files with auxiliary suffixes |
| `-Ca`, `--Clean-any` | Clean all auxiliary files (including root) and main output |

### LaTeXDiff Comparison

| Option | Description |
| --- | --- |
| `-d`, `--LaTeXDiff` | Generate a diff between two files, output `LaTeXDiff.tex` |
| `-dc`, `--LaTexDiff-compile` | Generate the diff file and compile it, producing a PDF with revision marks |

**Example**:

```bash
pytexmk -d old.tex new.tex     # Generate LaTeXDiff.tex
pytexmk -dc old.tex new.tex    # Generate and compile LaTeXDiff PDF
```

> Supports showing change traces in references and symbol indexes. You'll be prompted to choose a style during compilation.

### PDF Tools

| Option | Description |
| --- | --- |
| `-pr`, `--pdf-repair` | Repair corrupted PDF files (e.g. `invalid X X R object` warnings caused by bad images) |
| `-pv`, `--pdf-preview` | Open browser or local PDF viewer after compilation |

### Multi-Subproject Management

PyTeXMK lets you manage multiple independent subprojects under a single project root, each with its own compilation config and output directory.

**Typical workflow**:

```bash
# 1. Generate root config file
pytexmk -i

# 2. Auto-scan and show subproject list (also updates config)
pytexmk -ls

# 3. Compile a specific subproject (can be combined with a main file)
pytexmk -s thesis main.tex
```

| Option | Description |
| --- | --- |
| `-s`, `--subproject <name>` | Select a subproject and compile/clean in its directory |
| `-ls`, `--list-subprojects` | Scan subprojects and show the list, syncing root config |

### Config File Generation

| Option | Description |
| --- | --- |
| `-i`, `--init` | Generate a project-level `.pytexmkrc` in the current directory |
| `-iu`, `--init-user` | Generate a user-level `.pytexmkrc` in your home directory |
| `-f`, `--force` | With `-i`/`-iu`, force-overwrite an existing config file |

### Others

| Option | Description |
| --- | --- |
| `document` | Positional argument: filename to compile (extension optional) |
| `-h`, `--help` | Show help message |
| `-v`, `--version` | Show program version |

### Magic Comments

PyTeXMK supports magic comments in the first 50 lines of your LaTeX main file to customize compilation behavior:

| Magic Comment | Description | Example |
| --- | --- | --- |
| `% !TEX program = <engine>` | Set compilation engine | `% !TEX program = PdfLaTeX` |
| `% !TEX root = <filename>` | Set main file to compile | `% !TEX root = main` |
| `% !TEX outdir = <dir>` | Set output directory | `% !TEX outdir = output` |
| `% !TEX auxdir = <dir>` | Set auxiliary directory | `% !TEX auxdir = auxfiles` |

> **Note**: Magic comments only work in the main file; comments in sub-files are ignored.

### How It Works

<details>
<summary><b>📂 Main File Auto-Detection</b></summary>

1. CLI argument explicitly specifies a file → use it
2. Only one `.tex` file in current directory → auto-select
3. `% !TEX root` magic comment exists → use the comment value
4. Search for `\documentclass` or `\begin{document}` (first 200 lines) → identify main file
5. Fallback to default `main.tex`

</details>

<details>
<summary><b>⚙️ Engine Selection</b></summary>

1. CLI flag `-p` / `-x` / `-l` → highest priority
2. Magic comment `% !TEX program` → use the comment value
3. None specified → default `XeLaTeX`

</details>

<details>
<summary><b>🔁 Automatic Compile Passes</b></summary>

1. First LaTeX compilation pass
2. If `.aux` contains bibliography references, invoke bibtex / biber
3. If glossaries/index are present, invoke makeindex / xindy
4. Continue LaTeX passes; after each pass, detect whether each dimension has converged
5. Stop when all dimensions are stable or the safety cap is reached

</details>

### Configuration File

PyTeXMK supports two levels of TOML-format configuration:

| Level | Windows | Linux / macOS |
| --- | --- | --- |
| User-level | `C:\Users\username\.pytexmkrc` | `~/.pytexmkrc` |
| Project-level | `./.pytexmkrc` | `./.pytexmkrc` |

**Priority**: Project-level > User-level > Built-in defaults

Generate a template with `pytexmk -i` (project-level) or `pytexmk -iu` (user-level). Generated templates include detailed inline comments.

---

## 🛠 Development & Build

### Requirements

- Python 3.14+
- [uv](https://github.com/astral-sh/uv) (recommended) or pip

### Development Setup

```bash
# Clone the repository
git clone https://github.com/YanMing-lxb/PyTeXMK.git
cd PyTeXMK

# Install development dependencies
uv sync --all-extras --dev

# Run development version
uv run pytexmk --help
```

### Build Distribution

```bash
# Build wheel and sdist
uv build
```

### Build Binary

```bash
# Generate platform icons
make icon

# Build source-mode executable (onedir layout)
make build

# Clean build artifacts
make clean
```

> **make on Windows** requires separate setup. See [Using make on Windows](docs/Window%20下使用%20make.md).

### Code Linting

```bash
uv run ruff check src/
uv run ruff format src/
```

### Internationalization Workflow

```bash
# Add a new language
make lang-add

# Update all pot/po files
make lang-update

# Compile po → mo
make lang-mo

# Re-extract all pot templates
make lang-poup
```

---

## 📄 License

This project is open-sourced under the [GPLv3](LICENSE) license.

---

## 📝 Changelog

For detailed changelog, please refer to [CHANGELOG.md](CHANGELOG.md).

---

## 🤝 Contributing

Issues and Pull Requests are welcome!

- 🐛 Found a bug? Please file an [Issue](https://github.com/YanMing-lxb/PyTeXMK/issues)
- 💡 Have a feature request? Start a discussion
- 🌍 Want to help translate? See the [i18n workflow](#internationalization-workflow) above

---

## ⭐ Star History

[![Star History Chart](https://api.star-history.com/svg?repos=YanMing-lxb/PyTeXMK&type=Date)](https://star-history.com/#YanMing-lxb/PyTeXMK&Date)

---

<div align="center">

**If you find this project helpful, please give it a Star ⭐ to show your support!**

</div>
