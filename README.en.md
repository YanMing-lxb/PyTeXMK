<!--
 *  =======================================================================
 *  PyTeXMK - LaTeX Auxiliary Compilation Command Line Tool
 *  =======================================================================
 *  Author       : 焱铭 (YanMing)
 *  Github       : https://github.com/YanMing-lxb/PyTeXMK
 *  Description  : A modern, cross-platform LaTeX build automation tool
 *  =======================================================================
-->

<h1 align="center">PyTeXMK</h1>

<p align="center">
<strong>Smart LaTeX Build Automation Tool</strong><br/>
Automated LaTeX compilation engine · Multi-toolchain smart adaptation · Like latexmk but more powerful
</p>

<p align="center">
<a href="https://github.com/YanMing-lxb/PyTeXMK/actions/workflows/ci.yml"><img src="https://github.com/YanMing-lxb/PyTeXMK/actions/workflows/ci.yml/badge.svg" alt="CI Status"/></a>
<a href="https://pypi.org/project/pytexmk/"><img src="https://img.shields.io/pypi/v/pytexmk.svg" alt="PyPI Version"/></a>
<a href="https://pypi.org/project/pytexmk/"><img src="https://img.shields.io/pypi/pyversions/pytexmk.svg" alt="Python Versions"/></a>
<a href="https://github.com/YanMing-lxb/PyTeXMK/blob/main/LICENSE"><img src="https://img.shields.io/github/license/YanMing-lxb/PyTeXMK.svg" alt="License"/></a>
<a href="https://github.com/astral-sh/ruff"><img src="https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json" alt="Ruff"/></a>
</p>

[简体中文](README.md) | English

---

## Table of Contents

- [Project Introduction](#-project-introduction)
- [Core Features](#-core-features)
- [Environment Requirements](#-environment-requirements)
- [Installation Guide](#-installation-guide)
- [Quick Start](#-quick-start)
- [Complete Command Reference](#-complete-command-reference)
- [Magic Comments](#-magic-comments)
- [Configuration File Details](#-configuration-file-details)
- [Environment Variables](#-environment-variables)
- [Usage Examples](#-usage-examples)
- [PVC Continuous Watch Mode](#-pvc-continuous-watch-mode)
- [LaTeXDiff Document Comparison](#-latexdiff-document-comparison)
- [GitHub Actions Integration](#-github-actions-integration)
- [FAQ](#-faq)
- [Contribution Guide](#-contribution-guide)
- [Changelog](#-changelog)
- [License](#-license)

---

## 📖 Project Introduction

**PyTeXMK** is a modern LaTeX build automation CLI tool written in Python 3.14, designed as an enhanced replacement for latexmk. It automatically detects LaTeX source file dependencies, intelligently selects the optimal compilation engine, manages auxiliary files, and provides an elegant terminal output experience.

PyTeXMK's core design philosophy is **"fixed compilation count + smart supplemental compilation as fallback"**: under normal circumstances it compiles stably according to preset counts, and only triggers supplemental compilation when it detects fixable issues such as undefined references — balancing both compilation efficiency and reliability.

---

## ✨ Core Features

| Feature | Description |
|----------|-------------|
| 🔧 **Multi-Engine Smart Adaptation** | Auto-detect XeLaTeX/LuaLaTeX/PdfLaTeX, intelligent fallback: XeLaTeX → LuaLaTeX → PdfLaTeX |
| 📚 **Automatic Bibliography Handling** | Auto-detect BibTeX/Biber requirements and invoke the corresponding tool |
| 📇 **Index Tool Support** | Supports both makeindex and **xindy** index tools, with auto-detection |
| 👀 **PVC Continuous Watch Mode** | File watching + auto-compilation mode similar to `latexmk -pvc`, save to compile |
| 📊 **Structured Log Parsing** | Precise parsing of compilation logs, highlighted errors/warnings with line numbers |
| 📄 **LaTeXDiff Integration** | One-click generation of document version comparison PDFs, supports flattening sub-files and fast mode |
| 🌏 **Internationalization** | Chinese/English bilingual interface, switchable via `PYTEXMK_LANG` environment variable |
| 📁 **Clean Directory Structure** | Automatically outputs PDFs to `Build/`, auxiliary files to `Auxiliary/`, keeping the workspace tidy |
| 🖥️ **Cross-platform Support** | Windows / macOS / Linux, compatible with MiKTeX and TeX Live |
| ⚙️ **Flexible Configuration** | Three-tier configuration: TOML config files + magic comments + CLI arguments |
| 🚀 **Python 3.14** | Based on the latest Python version, excellent performance, fast startup |

---

## 🖥️ Environment Requirements

- **Python**: 3.14 or later (for pip installation)
- **LaTeX distribution**: TeX Live 2022+ or MiKTeX (must include xelatex/lualatex/pdflatex)
- **Optional tools**:
  - `latexdiff`: for document version comparison
  - `xindy`: for xindy index support
  - `biber`: for BibLaTeX bibliography support

---

## 📦 Installation Guide

### pip (recommended, cross-platform)

```bash
pip install pytexmk
```

Upgrade to the latest version:
```bash
pip install --upgrade pytexmk
```

### Windows - Scoop

The Scoop manifest is ready. After the official release, install via:
```powershell
scoop bucket add pytexmk https://github.com/YanMing-lxb/PyTeXMK
scoop install pytexmk
```

### Windows - Winget

Available after publishing to the winget repository:
```powershell
winget install YanMing.PyTeXMK
```

### Pre-built binaries

Download platform-specific executables from [GitHub Releases](https://github.com/YanMing-lxb/PyTeXMK/releases), extract and add the directory to your system PATH.

### From source (development)

```bash
git clone https://github.com/YanMing-lxb/PyTeXMK.git
cd PyTeXMK
uv sync
uv run pytexmk --version
```

### TeX Distribution Integration

PyTeXMK works seamlessly with major TeX distributions:

- **MiKTeX**: Auto-detected after installation, automatically finds installed engines and tools
- **TeX Live**: Fully compatible, supports the complete toolchain managed by tlmgr
- **Manual paths**: If the TeX distribution is not in PATH, specify paths via config file or environment variables

---

## 🚀 Quick Start

### Minimal Example

1. Have a main file `main.tex` in your LaTeX project root:

```latex
% !TEX program = XeLaTeX
\documentclass{article}
\begin{document}
Hello, PyTeXMK!
\end{document}
```

2. Run in the project directory:

```bash
pytexmk
```

3. After compilation, the PDF is generated at `Build/main.pdf`, with auxiliary files in the `Auxiliary/` directory.

### Compile a Specific File

```bash
pytexmk mydocument
```

### Auto-Preview PDF After Compilation

```bash
pytexmk -pv
```

### Clean Auxiliary Files

```bash
pytexmk -c    # Clean auxiliary files
pytexmk -C    # Clean auxiliary files and output PDF
```

---

## 📋 Complete Command Reference

Run `pytexmk --help` to view the full help message.

### Basic Options

| Option | Description |
|--------|-------------|
| `-v`, `--version` | Show version and exit |
| `-h`, `--help` | Show help and exit |
| `-r`, `--readme` | Open README documentation in browser |

### Engine Selection

| Option | Description |
|--------|-------------|
| `-x`, `--XeLaTeX` | Force XeLaTeX compilation |
| `-l`, `--LuaLaTeX` | Force LuaLaTeX compilation |
| `-p`, `--PdfLaTeX` | Force PdfLaTeX compilation |
| `--engine {xelatex,lualatex,pdflatex}` | Explicitly specify TeX engine |
| `--auto` | Enable smart engine auto-detection (default) |
| `--no-auto` | Disable smart engine auto-detection |

### Bibliography & Index

| Option | Description |
|--------|-------------|
| `--bib {auto,bibtex,biber}` | Specify bibliography tool |
| `--index {auto,makeindex,xindy}` | Specify index tool |

### Compilation Control

| Option | Description |
|--------|-------------|
| `-n N`, `--runs N` | Fixed compilation count (default 2; set to 3 to include bib compilation) |
| `-dr`, `--draft` | Draft mode (no images, faster compilation) |
| `--timeout SECONDS` | Single compilation timeout (default 300 seconds) |
| `--non-interactive` | Non-interactive mode, no user prompts, suitable for CI/CD |
| `-nq`, `--non-quiet` | Non-quiet mode, show full compilation log in terminal |
| `-vb`, `--verbose` | Show detailed debug information |

### Output Control

| Option | Description |
|--------|-------------|
| `-o DIR`, `--outdir DIR` | Specify PDF output directory (overrides magic comments and config) |
| `--auxdir DIR` | Specify auxiliary files directory |
| `-O`, `--open` | Auto-open PDF preview after successful compilation |
| `-pv [FILE]`, `--pdf-preview [FILE]` | Preview PDF after compilation; specify FILE to open directly |
| `-pr`, `--pdf-repair` | Attempt to repair PDF files (fixes `invalid X X R object` warnings) |

### SyncTeX & Shell Escape

| Option | Description |
|--------|-------------|
| `--synctex` | Enable SyncTeX (default) |
| `--no-synctex` | Disable SyncTeX |
| `--shell-escape` | Enable `-shell-escape` (default) |
| `--no-shell-escape` | Disable `-shell-escape` |

### Cleanup Commands

| Option | Description |
|--------|-------------|
| `-c`, `--clean` | Clean auxiliary files for current main file |
| `-C`, `--Clean` | Clean auxiliary files (including root directory) and output PDF |
| `-ca`, `--clean-any` | Clean all files with auxiliary file suffixes |
| `-Ca`, `--Clean-any` | Clean all auxiliary files and main file output PDF (including root directory) |

### PVC Continuous Watch Mode

| Option | Description |
|--------|-------------|
| `--pvc`, `--continuous` | Enable PVC mode (continuous watch + auto-compile) |
| `--pvc-debounce SECONDS` | File change debounce time (default 1.0 seconds) |
| `--pvc-preview` | Auto-open preview on successful compilation in PVC mode |

### LaTeXDiff Document Comparison

| Option | Description |
|--------|-------------|
| `-d [OLD NEW]`, `--LaTeXDiff [OLD NEW]` | Generate LaTeXDiff comparison file (no compilation) |
| `-dc [OLD NEW]`, `--LaTeXDiff-compile [OLD NEW]` | Generate comparison file and compile |
| `--diff-flatten` | Flatten `\input`/`\include` sub-files during LaTeXDiff |
| `--diff-fast` | Use latexdiff `--fast` mode |
| `--diff-output FILE` | LaTeXDiff output filename |
| `--diff-style {1,2}` | Display style: 1-show bibliography changes, 2-hide (default 2) |

---

## 🔮 Magic Comments

PyTeXMK supports magic comments in the first 50 lines of TeX files to configure compilation behavior. Priority is higher than configuration files.

| Magic Comment | Description |
|---------------|-------------|
| `% !TEX program = XeLaTeX` | Specify compilation engine: XeLaTeX / PdfLaTeX / LuaLaTeX |
| `% !TEX root = main.tex` | Specify the main file to compile (root directory files only) |
| `% !TEX outdir = out_folder` | Specify PDF output location |
| `% !TEX auxdir = aux_folder` | Specify auxiliary file location |
| `% !TEX bib = biber` | Specify bibliography tool: bibtex / biber |
| `% !TEX index = xindy` | Specify index tool: makeindex / xindy |

**Configuration Priority** (highest to lowest):
1. CLI arguments
2. Magic comments
3. Project config file (`.pytexmkrc` in project directory)
4. User config file (`~/.pytexmkrc`)
5. Built-in defaults

---

## ⚙️ Configuration File Details

PyTeXMK uses TOML format configuration files, supporting two levels:

- **User-level config**: `~/.pytexmkrc` — applies to all projects
- **Project-level config**: `./.pytexmkrc` — applies only to the current project, overrides user config

A default configuration file is auto-generated on first run.

### Full Configuration Options

```toml
# ============ Basic Settings ============
default_file = "main"           # Default main filename (without .tex extension)
compiled_program = "XeLaTeX"    # Default compiler: XeLaTeX / PdfLaTeX / LuaLaTeX
non_quiet = false               # true=show compilation log, false=quiet mode
quiet_mode = true               # Quiet mode (inverse of non_quiet, kept for backward compatibility)

# ============ PDF Preview Settings ============
[pdf]
pdf_preview_status = false      # Auto-open PDF after compilation
pdf_viewer = "default"          # PDF viewer: default=system default viewer

# ============ Directory Settings ============
[folder]
auxdir = "./Auxiliary/"         # Auxiliary files directory
outdir = "./Build/"             # PDF output directory

# ============ Engine Settings ============
[engine]
default = "xelatex"             # Default engine: xelatex / lualatex / pdflatex
auto_detect = true              # Enable smart engine auto-detection
fallback_order = ["xelatex", "lualatex", "pdflatex"]  # Fallback priority
timeout = 300                   # Single compilation timeout in seconds

# ============ Bibliography Settings ============
[bib]
default_tool = "auto"           # auto=auto-detect / bibtex / biber

# ============ Index Settings ============
[index]
default_tool = "auto"           # auto=auto-detect / makeindex / xindy
index_style_file = "nomencl.ist" # Index style file
input_suffix = ".nlo"           # Index input file suffix
output_suffix = ".nls"          # Index output file suffix

# ============ Compilation Settings ============
[compilation]
default_run_count = 2           # Default fixed compilation count
max_extra_passes = 2            # Max supplemental compilation retries
shell_escape = true             # Enable -shell-escape
synctex = true                  # Enable SyncTeX
quiet = true                    # Quiet compilation (batchmode)

# ============ PVC Continuous Watch Settings ============
[pvc]
enabled = false                 # Enable PVC mode by default
debounce = 1.0                  # File change debounce in seconds
auto_open_preview = false       # Auto-open preview on successful compilation
watch_extensions = [".tex", ".bib", ".bst", ".cls", ".sty", ".idx", ".ist", ".png", ".jpg", ".pdf", ".eps"]
exclude_dirs = ["build", ".git", "__pycache__", ".venv", "node_modules"]

# ============ LaTeXDiff Settings ============
[diff]
flatten = false                 # Flatten sub-files by default
fast = false                    # Use latexdiff --fast mode
auto_compile = true             # Auto-compile after generating diff

[latexdiff]                     # Legacy config (backward compatible)
old_tex_file = "old_file"
new_tex_file = "new_file"
diff_tex_file = "LaTeXDiff"
```

---

## 🌐 Environment Variables

| Variable | Description | Example |
|----------|-------------|---------|
| `PYTEXMK_LANG` | Force UI language | `PYTEXMK_LANG=en` or `PYTEXMK_LANG=zh_CN` |
| `LANGUAGE` / `LANG` / `LC_ALL` / `LC_MESSAGES` | System language (auto-detected) | `LANG=zh_CN.UTF-8` |

Language detection priority: `PYTEXMK_LANG` → `LANGUAGE` → `LANG` → `LC_ALL` → `LC_MESSAGES` → system locale → default English.

---

## 📝 Usage Examples

### Example 1: Basic Compilation (Chinese Document)

**Scenario**: Compile a Chinese paper using XeLaTeX.

**`main.tex`**:
```latex
% !TEX program = XeLaTeX
\documentclass{ctexart}
\title{Test Document}
\author{Author}
\begin{document}
\maketitle
Hello, PyTeXMK!
\end{document}
```

**Command**:
```bash
pytexmk
```

**Expected output**:
- `Build/main.pdf` — compiled PDF
- `Auxiliary/` — auxiliary files (.aux, .log, .out, etc.)

---

### Example 2: BibLaTeX + Biber

**Scenario**: Use the BibLaTeX package with the Biber backend for bibliography processing.

**`main.tex`**:
```latex
% !TEX program = XeLaTeX
% !TEX bib = biber
\documentclass{article}
\usepackage[backend=biber]{biblatex}
\addbibresource{refs.bib}
\begin{document}
Citation test~\cite{knuth1984texbook}.
\printbibliography
\end{document}
```

**Command**:
```bash
pytexmk -n 3    # Compile 3 times to ensure bibliography is correctly generated
```

Or let PyTeXMK auto-detect (recommended):
```bash
pytexmk
```

---

### Example 3: xindy Index

**Scenario**: Generate Chinese/English indexes using xindy for Unicode sorting support.

**Command**:
```bash
pytexmk --index xindy
```

Or via magic comment:
```latex
% !TEX index = xindy
```

---

### Example 4: Non-Interactive Mode (CI/CD)

**Scenario**: Automatically compile LaTeX documents in CI environments like GitHub Actions.

```bash
pytexmk --non-interactive --timeout 120
```

---

### Example 5: Draft Mode for Fast Compilation

**Scenario**: Quick preview during editing, without images.

```bash
pytexmk -dr
```

---

### Example 6: Repair Corrupted PDF

**Scenario**: When the compilation log shows `invalid X X R object` warnings.

```bash
pytexmk -pr
```

---

## 👀 PVC Continuous Watch Mode

PVC (Preview Continuous) mode is similar to `latexmk -pvc`. Once started, it continuously monitors the project directory for file changes and automatically triggers compilation when `.tex`, `.bib`, `.sty`, and other files are saved.

### Start PVC Mode

```bash
pytexmk --pvc
```

### With Auto-Preview

```bash
pytexmk --pvc --pvc-preview
```

### Custom Debounce Time

```bash
pytexmk --pvc --pvc-debounce 2.0
```

### PVC Mode Features

- Uses the watchdog library for efficient filesystem event monitoring
- Debouncing mechanism prevents multiple triggers during save operations
- Automatically filters directories like `.git`, `__pycache__`, `build`
- Press `Ctrl+C` to exit watch mode
- Displays error summary on compilation failure, auto-recompiles after fixes

---

## 📄 LaTeXDiff Document Comparison

The LaTeXDiff feature generates a diff comparison PDF of two versions of a TeX file, making it easy to review changes.

### Basic Usage

```bash
# Generate comparison file without compiling
pytexmk -d old_version.tex new_version.tex

# Generate comparison file and compile to PDF
pytexmk -dc old_version.tex new_version.tex
```

### Flatten Sub-files

If your document uses `\input` or `\include`:

```bash
pytexmk -dc old.tex new.tex --diff-flatten
```

### Config File Presets

Configure in `.pytexmkrc` to omit command-line arguments:

```toml
[latexdiff]
old_tex_file = "v1.tex"
new_tex_file = "v2.tex"
diff_tex_file = "diff"
```

Then simply run:
```bash
pytexmk -dc
```

---

## 🤖 GitHub Actions Integration

Use PyTeXMK to compile LaTeX documents in GitHub Actions:

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
          python-version: '3.14'

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

## ❓ FAQ

### Q1: How to switch between Chinese and English interface?

Set the `PYTEXMK_LANG` environment variable:
```bash
# Windows PowerShell
$env:PYTEXMK_LANG = "en"

# Linux/macOS
export PYTEXMK_LANG=en
```

### Q2: Compilation shows engine not found?

Make sure TeX Live or MiKTeX is properly installed and added to the system PATH:
```bash
xelatex --version
```
If the command is not found, check your TeX distribution installation.

### Q3: How to output PDF to the current directory instead of Build/?

Use the `-o` option or a magic comment:
```bash
pytexmk -o .
```
Or add to the TeX file header:
```latex
% !TEX outdir = .
```

### Q4: Which engine should I use for Chinese documents?

We recommend **XeLaTeX** (the default engine), which has the best support for Chinese and Unicode. PyTeXMK's smart fallback also prioritizes XeLaTeX.

### Q5: Which files trigger recompilation in PVC mode?

By default, files with extensions `.tex`, `.bib`, `.bst`, `.cls`, `.sty`, `.idx`, `.ist`, `.png`, `.jpg`, `.pdf`, `.eps` are monitored. You can customize this in the `[pvc]` section's `watch_extensions` in the config file.

### Q6: How to use PyTeXMK with VS Code?

Configure in VS Code's LaTeX Workshop extension:
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

### Q7: How to fully clean a project?

```bash
pytexmk -Ca    # Clean all auxiliary and output files (including root directory)
```

### Q8: Which operating systems are supported?

PyTeXMK supports all major platforms:
- **Windows**: 10/11, supports MiKTeX and TeX Live
- **macOS**: 10.15+, Intel and Apple Silicon
- **Linux**: Major distributions (Ubuntu 20.04+, Fedora, Arch, etc.)

---

## 👥 Contribution Guide

Issues and Pull Requests are welcome!

### Development Environment Setup

```bash
git clone https://github.com/YanMing-lxb/PyTeXMK.git
cd PyTeXMK
uv sync --dev
```

### Common Development Commands

| Command | Description |
|---------|-------------|
| `make help` | Show all available commands |
| `make test` | Run unit tests |
| `make test-cov` | Run tests and generate coverage report |
| `make lint` | Ruff code style check |
| `make lint-fix` | Auto-fix lint issues |
| `make format` | Ruff code formatting |
| `make build` | Build wheel package |
| `make i18n-update` | Update internationalization translation files |
| `make ci-test` | Run full CI test pipeline |
| `make clean` | Clean build artifacts |

### Code Standards

- Follow PEP 8 conventions
- Use Ruff for linting and formatting
- Add type annotations
- Supplement unit tests for new features

---

## 📋 Changelog

See [CHANGELOG.md](CHANGELOG.md) for details.

**v1.1.2 Highlights**:
- New PVC continuous watch mode (file monitoring + auto-compilation)
- New xindy index tool support
- Smart engine fallback: XeLaTeX → LuaLaTeX → PdfLaTeX
- Enhanced LaTeXDiff functionality (flatten, fast mode)
- Chinese/English internationalization support
- Python 3.14 support
- Complete GitHub Actions CI/CD pipeline
- Cross-platform packaging support (PyInstaller)
- 327+ unit test coverage

---

## 📄 License

This project is open-sourced under the **GNU General Public License v3.0 or later**.

See the [LICENSE](LICENSE) file for details.

---

<p align="center">
Made with ❤️ by <a href="https://github.com/YanMing-lxb">焱铭 (YanMing)</a><br/>
For questions, please report on <a href="https://github.com/YanMing-lxb/PyTeXMK/issues">GitHub Issues</a>
</p>

## 📊 Star History

[![Star History Chart](https://api.star-history.com/svg?repos=YanMing-lxb/PyTeXMK&type=Date)](https://star-history.com/#YanMing-lxb/PyTeXMK&Date)