<div align="center">
  <img src="https://github.com/YanMing-lxb/PyTeXMK/blob/main/imgs/pytexmk-logo.png?raw=true" alt="PyTeXMK Logo" width="128" height="128">
  <h1>PyTeXMK</h1>
  <p>LaTeX Auxiliary Compilation Command Line Program</p>

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

## ✨ Features

- 🚀 **Multi-engine support**: XeLaTeX, PdfLaTeX, and LuaLaTeX compilation engines
- 📚 **Bibliography**: bibtex, biblatex, thebibliography
- 📑 **Index support**: glossaries (incl. glossaries-extra + bib2gls + biber), nomencl, makeidx
- 📋 **Structured Compile-Detection Report**: Aggregates the 6 detection dimensions (bibliography / index / TOC / cross-refs / bookmark file / log Rerun signals) and the per-pass conclusion into a single report block. The report uses **Rich 5-color layered styling (title magenta, name cyan-bold, [OK] green-bold, [!!] yellow-bold, safety cap red-bold)**. **Table grids are DISABLED**; only plain entry lists are rendered. The old generic 4-character "stable" message is replaced with **6 dimension-specific independent stable messages** (e.g. "Citation count unchanged, bibliography parsing is stable", "PDF bookmark entries unchanged, bookmark generation is stable"). The `actual_next` conclusion semantics strictly follow `2 → 1 → not needed`, **never** fall back to 1, **never** print "0 extra passes required"; the compiler name is dynamically replaced with XeLaTeX / PdfLaTeX / LuaLaTeX based on the actual engine. All report strings are fully wrapped with `_()` for i18n
- 🔁 **Smart multi-pass detection**: Automatically compares aux/out file contents and parses Rerun warnings in logs to ensure cross-references, hyperref bookmarks, lastpage total page counts, etc. converge stably
- 🔮 **Magic comments**: Specify engine, main file, output directory via `% !TEX` comments; regex hardened so TeX-escaped percent signs `\%` in inline code are no longer misidentified as magic comment markers
- 🌍 **Internationalization**: Multi-language interface support. **The default UI language is Chinese** (source strings are in Chinese); we no longer force-en as the default. Since **v1.2.1**, the whole i18n pipeline officially switches to the **Babel (`pybabel`) standard workflow**: `pybabel extract → init → update → compile` (the previous `xgettext / msgfmt` toolchain is dropped entirely). All user-facing strings are wrapped with `_()` + `%(placeholder)s` placeholders. The **3 legacy shared-domain groups are fully split into independent domains** (`lifecycle` / `paths`, `pdf_tools` / `subprocess_runner` / `tex_project`, `timing` / `ui_messages`), in 1:1 strict alignment with `set_language(...)` parameters and `.pot/.po` file names. A set of Makefile helpers is provided: `make lang-add` (interactively prompts for a new language code), `make lang-update` (auto-updates every pot/po), `make lang-mo` (compiles po → mo for every domain), and `make lang-poup` (re-extracts all .pot templates with pybabel)
- 🧹 **Smart cleanup**: Multiple clean modes for precise auxiliary file removal
- 🔍 **Log parsing**: Auto-parse LaTeX logs on failure to locate errors
- 📝 **LaTeXDiff**: LaTeX file diff comparison support
- ⚙️ **Configuration files**: User-level and project-level configuration
- 🔔 **Version check**: Automatic update checks for new versions
- 🪓 **Detection vs. compilation fully decoupled (zero thin-forwarders)**: The standalone `detection.py` module now owns all 6-dimensional detection logic plus `class CompilationDetector`, while `compile.py` only keeps subprocess-level compilation execution. Callers **must** use the composition chain (`compile_model.detector.*`); **any thin forwarder method of the form `return self.detector.xxx(...)` is strictly forbidden** (count = 0), maximizing single-responsibility and maintainability
- 🧱 **Layered architecture + DAG acyclic imports**: Based on the "cohesion hard threshold" derived from the 23-module static topology survey, only the eligible `cli/` subpackage is split (`__main__ / cli_args / cli_workflow / check_version`), while the other 19 modules remain flat to avoid over-engineering; the static 2-node SCC cycle `run ↔ cli_workflow` is broken, so the import graph is formally a DAG (SCC size ≥ 2 count = 0), structurally eliminating circular dependency risks
- 🪧 **Preprocessing Banner + differential preprocessing logs**: The preprocessing console banner returns to the classic three-line `=*78 / X32|开始预处理|X32 / =*78` style, routed through **the unified `ui_messages.print_message`** so it visually matches every other banner in the project; the "End preprocessing" banner is physically removed; the preprocessing block now prints different hints for 4 scenarios (move 0/N auxiliary files + exist 0/N existing auxiliary files) to avoid the ambiguous always-two-lines output regardless of actual migration. The message "未检测到已有辅助文件，进行初始化" is kept in **exactly 1 global location** in `cli_workflow`
- 🚫 **Zero-compatibility promise + dead code cleanup + permanent removal of Cython encryption**: Since **v1.2.1**, **zero compatibility layers are retained** (the old `pytexmk.run` entry / `DeprecationWarning` / try-import fallbacks are physically removed). The **entire Cython encryption pipeline is permanently dropped**: we removed `tools/pydmk.py`, the `srcpyd/` packaging entry, the `cython` dependency, and all three-platform build-toolchain installation steps in GitHub Actions workflows; the packaging pipeline now runs exactly **one permanent code path: "source mode onedir"** via `make build`. A dual pass of `ruff F401/F841` static scan + dead-comment removal keeps running on core modules to control entropy
- 🗺 **Architecture decision institutionalization**: Added [docs/architecture.md](docs/architecture.md) as the single source of truth, providing a 6-layer ASCII layered dependency graph, a 23-module responsibility matrix, a Q1-Q4 decision tree for where to place new features + Rule 5 "Subpackage split hard threshold (≥4 modules AND ≥3 internal imports AND ≥0.7 coupling coefficient)", and 3 import disciplines to constrain architectural entropy growth

---

## 📸 Preview

<div align="center">
  <img src="https://github.com/YanMing-lxb/PyTeXMK/blob/main/imgs/show1.png?raw=true" alt="PyTeXMK Preview 1" width="45%" style="border-radius: 8px; box-shadow: 0 4px 12px rgba(0,0,0,0.15);">
  <img src="https://github.com/YanMing-lxb/PyTeXMK/blob/main/imgs/show2.png?raw=true" alt="PyTeXMK Preview 2" width="45%" style="border-radius: 8px; box-shadow: 0 4px 12px rgba(0,0,0,0.15);">
</div>

---

## 🚀 Quick Start

### Installation

The official version of PyTeXMK is published on [PyPI](https://pypi.org/project/pytexmk/) and can be easily installed via pip or uv:

```bash
# Install with pip
pip install pytexmk

# Install with uv (recommended)
uv pip install pytexmk
```

### Windows winget install (recommended)

For Windows 10 1809+ / Windows 11 users, install via [winget](https://learn.microsoft.com/en-us/windows/package-manager/) in one command (no Python environment required):

```powershell
winget install --id YanMing-lxb.PyTeXMK
```

> Tip: Once moniker is registered, the short form `winget install pytexmk` will also work.

### Upgrade

```bash
# pip
pip install --upgrade pytexmk

# uv
uv pip install --upgrade pytexmk
```

### Basic Usage

Run in your LaTeX project root directory:

```bash
# Compile with default configuration
pytexmk

# Compile a specific main file
pytexmk main.tex

# Compile with XeLaTeX
pytexmk -x main.tex

# Clean auxiliary files
pytexmk -c
```

> **Note**: PyTeXMK only supports TeX files encoded in UTF-8.

---

## ⚙️ Default Configuration

| Option | Default | Description |
| --- | --- | --- |
| Compiler | `XeLaTeX` | Options: XeLaTeX, PdfLaTeX, LuaLaTeX |
| Main file | `main.tex` | LaTeX main file to compile |
| Output dir | `Build` | Compilation result directory |
| Auxiliary dir | `Auxiliary` | Auxiliary files directory |
| Compile mode | batch mode | Silent compilation, no verbose output |

> **Tip**: All parameters can be customized in config files, see [Configuration File](#configuration-file).
>
> VSCode users: set `"latex-workshop.latex.outDir": "./Build"` in `settings.json` so LaTeX-Workshop can find the PDF.

---

## 📖 Usage

### Compilation Commands

PyTeXMK supports the following options:

**Positional arguments**

| Argument | Description |
| --- | --- |
| `document` | The filename to be compiled |

**Optional arguments**

| Option | Description |
| --- | --- |
| `-h`, `--help` | Show help message |
| `-v`, `--version` | Show program version |
| `-p`, `--PdfLaTeX` | Compile with PdfLaTeX |
| `-x`, `--XeLaTeX` | Compile with XeLaTeX |
| `-l`, `--LuaLaTeX` | Compile with LuaLaTeX |
| `-d`, `--LaTeXDiff` | Generate diff comparison file with LaTeXDiff |
| `-dc`, `--LaTexDiff-compile` | Generate diff file and compile new file |
| `-dr`, `--draft` | Enable draft mode (no images, faster compilation) |
| `-c`, `--clean` | Clean auxiliary files of the main file |
| `-C`, `--Clean` | Clean auxiliary files (including root) and output files |
| `-ca`, `--clean-any` | Clean all files with auxiliary suffixes |
| `-Ca`, `--Clean-any` | Clean all auxiliary files (including root) and main output |
| `-nq`, `--non_quiet` | Non-quiet mode, show compilation process |
| `-vb`, `--verbose` | Show detailed PyTeXMK runtime information |
| `-pr`, `--pdf-repair` | Repair all PDF files outside the root directory |
| `-pv`, `--pdf-preview` | Preview PDF file after compilation |
| `-s`, `--subproject` | Select a subproject from root config `[subprojects]` and compile in its directory |
| `-ls`, `--list-subprojects` | Scan subprojects and show the list (auto-syncs the root `[subprojects]` section) |
| `-i`, `--init` | Generate a root project `.pytexmkrc` config file |
| `-iu`, `--init-user` | Generate a user-level `~/.pytexmkrc` config file |
| `-f`, `--force` | With `-i`/`-iu`, force overwrite an existing config file |

**Parameter notes**

- **`-pr`**: When LaTeX compilation produces warnings like `invalid X X R object at offset XXXXX`, use this option to attempt repairing all PDF files. This warning is typically caused by corrupted PDF image files.
- **`-d` / `-dc`**: Example: `pytexmk -d old_tex_file new_tex_file`. The generated diff file is named `LaTeXDiff.tex`.
- **`-pv`**: Opens a browser or local PDF viewer after compilation. Example: `pytexmk main -pv` or `pytexmk -pv`.
- **`-dc` / `-d`**: Supports showing change traces in references and symbol indexes. You will be prompted to choose a style during compilation (1-show changes / 2-hide changes).

### Multi-Subproject Compilation

PyTeXMK lets you manage and compile multiple independent subprojects under a single project root.

Options `-s` / `-ls` / `-i` / `-iu` / `-f`:

| Option | Description |
| --- | --- |
| `-s`, `--subproject <name>` | Select a subproject from the `[subprojects]` section of the root `.pytexmkrc` and compile/clean in its directory; the process switches its working root internally, **without changing your terminal cwd**, and it can coexist with a main-file argument (e.g. `pytexmk -s sub main`); if the alias is not found it errors, prompts you to run `-ls` first, and exits with the "project not found" code |
| `-ls`, `--list-subprojects` | Scan subprojects using the root `[project_scan]` rules and show the list as a table; if the root `.pytexmkrc` exists, the `[subprojects]` section is **replaced entirely** with the scan result (idempotent), while the `[project_scan]` section is left untouched; if no rc exists it prompts you to run `-i` first and writes nothing |
| `-i`, `--init` | Generate a root project `.pytexmkrc` config file |
| `-iu`, `--init-user` | Generate a user-level `~/.pytexmkrc` config file |
| `-f`, `--force` | Only used with `-i`/`-iu` to overwrite existing files; if the target already exists without `-f`, it prompts and writes nothing |

**Typical workflow**

1. Run `pytexmk -i` in the root to generate the root `.pytexmkrc` (add `-f` to overwrite an existing one); use `-iu` for a global user-level config
2. Run `pytexmk -ls` to scan and show the subproject list (it automatically updates the `[subprojects]` section in the root config)
3. Select a subproject with `pytexmk -s subproject` and compile; it can coexist with a main file via `pytexmk -s subproject main`; cleaning scope also applies, e.g. `pytexmk -s subproject -c`

**Configuration**

- `[project_scan]`: subproject scanning rules section (default `depth=3`, with an `exclude` list). Used only by `-ls`/`-s` scanning; scan parameters always come from the root config. Neither `-ls` nor `-s` overwrites or modifies this section
- `[subprojects]`: the subproject list section used by `-s`; `-ls` replaces it entirely with the scan result

**Local rc scope**

- When invoked with `-s` from the root, any local `.pytexmkrc` under the subproject directory is ignored (`-vb` prints a one-line note); the root config is the absolute source
- When you `cd` into the subproject directory and run it standalone, the local rc applies (backward compatible)

### Magic Comments

PyTeXMK supports magic comments to customize compilation behavior (searches first 50 lines only).

| Magic Comment | Description | Example |
| --- | --- | --- |
| `% !TEX program = <XeLaTeX>` | Specify compilation type | `% !TEX program = PdfLaTeX` |
| `% !TEX root = <main_file>` | Specify main file to compile | `% !TEX root = test_file` |
| `% !TEX outdir = <output_dir>` | Specify output directory | `% !TEX outdir = output` |
| `% !TEX auxdir = <aux_dir>` | Specify auxiliary files directory | `% !TEX auxdir = auxfiles` |

> **Note**: Magic comments only work in the main file, not in sub-files.

### Main File & Compilation Type Selection Logic

<details>
<summary><b>📂 Main File Selection Logic</b></summary>

1. Command-line argument specifies main file → compile that file (e.g. `pytexmk <main-file>`, extension optional)
2. Only one `.tex` file in current directory → use that file
3. Magic comment `% !TEX root` exists → use the specified file
4. Search for `\documentclass[]{}` or `\begin{document}` (first 200 lines only)
5. Default main file name `main.tex` → try that
6. All above fail → output error and exit

</details>

<details>
<summary><b>⚙️ Compilation Type Selection Logic</b></summary>

1. Command-line option `-p` / `-x` / `-l` → highest priority
2. Magic comment `% !TEX program` → use comment value
3. None specified → use default `XeLaTeX`

</details>

> Output directory priority: `% !TEX outdir` magic comment > default `Build`

### Configuration File

PyTeXMK supports two levels of configuration: **user config** and **project config**. Normal runs **no longer auto-generate** config files; generate them manually with `-iu` (user level) or `-i` (project level).

- **User config**: generated manually with `pytexmk -iu`, located as `.pytexmkrc` in your user home
- **Project config**: generated manually with `pytexmk -i`, located as `.pytexmkrc` in the working directory

Generated config files include detailed comments. Modify as needed.

**Config File Paths**

| Type | Windows | Linux / macOS |
| --- | --- | --- |
| User config | `C:\Users\username\.pytexmkrc` | `~/.pytexmkrc` |
| Project config | `./.pytexmkrc` | `./.pytexmkrc` |

**Priority**: Project config > User config > built-in defaults; missing config is silently handled with built-in defaults, and mismatched keys only warn without writing to disk.

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

---

## 📄 License

This project is open-sourced under the [GPLv3](LICENSE) license.

---

## 📝 Changelog

For detailed changelog, please refer to [CHANGELOG.md](CHANGELOG.md).

---

## ⭐ Star History

[![Star History Chart](https://api.star-history.com/svg?repos=YanMing-lxb/PyTeXMK&type=Date)](https://star-history.com/#YanMing-lxb/PyTeXMK&Date)

---

<div align="center">

**If you find this project helpful, please give it a Star ⭐ to show your support!**

</div>
