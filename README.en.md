<!--
 *  =======================================================================
 *  PyTeXMK - LaTeX Auxiliary Compilation Command Line Tool
 *  =======================================================================
 *  Author       : 焱铭 (YanMing)
 *  Github       : https://github.com/YanMing-lxb/PyTeXMK
 *  Description  : A modern, cross-platform LaTeX build automation tool
 *  =======================================================================
-->

# PyTeXMK

[![GitHub](https://img.shields.io/badge/Github-PyTeXMK-000000.svg)](https://github.com/YanMing-lxb/PyTeXMK)
[![License](https://img.shields.io/badge/license-GPLv3-blue.svg)](LICENSE)
![OS](https://img.shields.io/badge/OS-Linux%2C%20Windows%2C%20macOS-pink.svg)
[![GitHub release](https://img.shields.io/github/release/YanMing-lxb/PyTeXMK.svg?color=blueviolet&label=version)](https://github.com/YanMing-lxb/PyTeXMK/releases/latest)
[![PyPI version](https://img.shields.io/pypi/v/pytexmk.svg)](https://pypi.python.org/pypi/pytexmk/)
[![Python](https://img.shields.io/badge/python-3.13+-green.svg)](https://www.python.org/)
[![CI](https://github.com/YanMing-lxb/PyTeXMK/actions/workflows/ci.yml/badge.svg)](https://github.com/YanMing-lxb/PyTeXMK/actions/workflows/ci.yml)

[简体中文](README.md) | [English](README.en.md)

**PyTeXMK** is a modern, cross-platform LaTeX build automation CLI tool written in Python 3.13.
Inspired by latexmk, with strong focus on Chinese LaTeX workflows.

---

## ✨ Features

- 🔧 **Smart Engine Selection**: XeLaTeX → LuaLaTeX → PdfLaTeX automatic fallback priority
- 📚 **Complete Toolchain**: BibTeX / Biber, makeindex, **xindy**, glossaries, nomencl
- 🔄 **Fixed Compilation Count**: Core mechanism preserved with smart recompile as fallback
- 👀 **PVC Mode (Continuous Preview)**: File watcher auto-recompiles on changes, like `latexmk -pvc`
- 📝 **Enhanced LaTeXDiff**: Non-interactive mode, --flatten, custom styles, reference tracking
- 🌍 **i18n**: Chinese/English UI, switchable via `PYTEXMK_LANG` environment variable
- 🎯 **Magic Comments**: `% !TEX program`, `% !TEX root`, `% !TEX outdir`, `% !TEX auxdir`
- 📊 **Structured Log Parsing**: Precise error/warning extraction with line numbers, colored output
- ⚙️ **TOML Configuration**: User-level + project-level config with clear precedence
- 🖥️ **Cross-platform**: Native support for Windows (MiKTeX/TeX Live), Linux, macOS
- 🚀 **CI/CD Ready**: First-class GitHub Actions support

## 📦 Installation

### pip (recommended, cross-platform)

```bash
pip install pytexmk
```

Upgrade:
```bash
pip install --upgrade pytexmk
```

### Windows - Scoop

```powershell
# Add bucket (available after release)
scoop bucket add pytexmk https://github.com/YanMing-lxb/PyTeXMK
scoop install pytexmk
```

### Windows - Winget

```powershell
# Available after publishing to winget
winget install YanMing.PyTeXMK
```

### Pre-built binaries

Download platform-specific executables from [GitHub Releases](https://github.com/YanMing-lxb/PyTeXMK/releases), extract and add to PATH.

### From source (development)

```bash
git clone https://github.com/YanMing-lxb/PyTeXMK.git
cd PyTeXMK
uv sync
uv run pytexmk --version
```

### Prerequisites

- **Python**: 3.13 or later (for pip installation)
- **LaTeX distribution**: TeX Live or MiKTeX (available in PATH)
- **Optional**: gettext (for updating translation files, development only)

### TeX Distribution Integration

PyTeXMK works seamlessly with major TeX distributions:

- **MiKTeX**: Auto-detected after installation, automatically finds installed engines and tools
- **TeX Live**: Fully compatible, supports tlmgr-managed toolchains
- **Manual**: If TeX distribution is not in PATH, specify paths via config file or environment variables

## 🚀 Quick Start

In your LaTeX project root directory, simply run:

```bash
pytexmk                # Auto-detect main file and compile
pytexmk mydoc          # Specify filename (auto-detect engine)
pytexmk mydoc -x       # Compile with XeLaTeX
pytexmk mydoc -x -pv   # Compile and open PDF preview
pytexmk -pvc           # Continuous watch mode (auto-recompile on changes)
```

## 📖 CLI Options

### Positional Arguments

| Argument | Description |
|----------|-------------|
| `document` | TeX filename to compile (`.tex` suffix optional) |

### Engine Selection

| Option | Description |
|--------|-------------|
| `-x`, `--XeLaTeX` | Use XeLaTeX |
| `-l`, `--LuaLaTeX` | Use LuaLaTeX |
| `-p`, `--PdfLaTeX` | Use PdfLaTeX |

### Main Features

| Option | Description |
|--------|-------------|
| `-d`, `--LaTeXDiff` | LaTeXDiff mode: `pytexmk -d old.tex new.tex` |
| `-dc`, `--LaTeXDiff-compile` | LaTeXDiff then compile to PDF |
| `-pvc` | Continuous watch mode (auto-recompile) |
| `-c`, `--clean` | Clean auxiliary files |
| `-C`, `--Clean` | Clean auxiliary + output files |
| `-ca`, `--clean-any` | Clean all auxiliary-suffixed files |
| `-Ca`, `--Clean-any` | Clean all auxiliary + output files |

### Output Control

| Option | Description |
|--------|-------------|
| `-nq`, `--non-quiet` | Non-quiet mode (show compilation output) |
| `-vb`, `--verbose` | Verbose mode (show PyTeXMK details) |
| `-dr`, `--draft` | Draft mode (no images, faster compilation) |
| `-pv`, `--pdf-preview` | Open PDF preview after compilation |
| `-pr`, `--pdf-repair` | Try to repair corrupted PDF images |
| `-o OUTDIR`, `--outdir OUTDIR` | Output directory (default: Build) |
| `-aux AUXDIR`, `--auxdir AUXDIR` | Auxiliary files directory (default: Auxiliary) |

### Miscellaneous

| Option | Description |
|--------|-------------|
| `-h`, `--help` | Show help message |
| `-v`, `--version` | Show version |
| `--language LANG` | Force UI language (`zh` or `en`) |

## 🔍 Smart Engine Priority

1. CLI flags `-x`/`-l`/`-p` (highest priority)
2. Magic comment `% !TEX program = XeLaTeX`
3. Document feature detection (Unicode/Chinese → XeLaTeX)
4. Available engine auto-detection (XeLaTeX → LuaLaTeX → PdfLaTeX)
5. Default: XeLaTeX

## 🔮 Magic Comments

Use magic comments in the first 50 lines of your TeX file:

```tex
% !TEX program = XeLaTeX
% !TEX root = main
% !TEX outdir = output
% !TEX auxdir = auxfiles
```

| Magic Comment | Description | Example |
|--------------|-------------|---------|
| `% !TEX program = <engine>` | Set engine | `% !TEX program = LuaLaTeX` |
| `% !TEX root = <filename>` | Set main file | `% !TEX root = thesis` |
| `% !TEX outdir = <dir>` | Output directory | `% !TEX outdir = PDF` |
| `% !TEX auxdir = <dir>` | Auxiliary directory | `% !TEX auxdir = build` |

## ⚙️ Configuration

PyTeXMK supports TOML configuration files:

- **User config**: `~/.pytexmkrc` (auto-generated on first run)
- **Project config**: `./.pytexmkrc` (project root, higher priority)

Configurable items: default engine, output dir, aux dir, quiet mode, PDF preview, LaTeXDiff options, etc.

## 👀 PVC Continuous Watch Mode

Similar to `latexmk -pvc`:

```bash
pytexmk -pvc                  # Watch current directory
pytexmk mydoc -x -pvc         # Specify file and engine
pytexmk -pvc -pv              # Watch + auto-preview
```

Watches `.tex`, `.bib`, `.bst`, image files, etc., with debouncing.
Press `Ctrl+C` to stop.

## 🌍 Internationalization

Language is auto-detected, or set manually:

```bash
# Force English
PYTEXMK_LANG=en pytexmk

# Force Chinese
PYTEXMK_LANG=zh pytexmk
```

## 🔨 Development

The project uses [uv](https://github.com/astral-sh/uv) for Python environment management, with a unified Makefile/task runner:

```bash
# Install dev dependencies
uv sync

# Run tests
uv run python tools/make.py test

# Lint
uv run python tools/make.py lint

# Format
uv run python tools/make.py format

# Build wheel
uv run python tools/make.py build

# Build PyInstaller executable (Windows)
uv run python tools/make.py build-exe

# See all commands
uv run python tools/make.py help
```

If you have GNU Make, you can also use `make` directly:
```bash
make help
make test
make lint
make build
make build-exe
make clean
```

## 🤖 GitHub Actions Integration

Use PyTeXMK in your LaTeX project's CI:

```yaml
- name: Setup Python
  uses: actions/setup-python@v5
  with:
    python-version: '3.13'

- name: Install PyTeXMK
  run: pip install pytexmk

- name: Build LaTeX
  run: pytexmk main -x
```

## 📄 License

This project is licensed under [GPL-3.0-or-later](LICENSE).

## 📊 Star History

[![Star History Chart](https://api.star-history.com/svg?repos=YanMing-lxb/PyTeXMK&type=Date)](https://star-history.com/#YanMing-lxb/PyTeXMK&Date)
