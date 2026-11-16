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
- 🐍 **PythonTeX orchestration**: After the first pass creates `.pytxcode`, run `pythontex` automatically and add one LaTeX pass; native builds run inside the auxiliary directory

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

#### Linux / macOS binary package (recommended, no Python required)

Pick the matching asset from [Releases](https://github.com/YanMing-lxb/PyTeXMK/releases):

- Linux x86_64: `pytexmk-<version>-linux-x64.zip`
- macOS Apple Silicon: `pytexmk-<version>-macos-arm64.zip`

Or install it with a single command (the installer detects platform and architecture, resolves the latest version, checks glibc and creates the launcher; re-running it upgrades in place):

```bash
curl -fsSL https://raw.githubusercontent.com/YanMing-lxb/PyTeXMK/main/tools/install.sh | bash -s
```

It installs into `~/.local/opt/pytexmk` and links the launcher to `~/.local/bin/pytexmk`. To customise, append `--` followed by the flags:

```bash
# Custom program directory and launcher directory
curl -fsSL https://raw.githubusercontent.com/YanMing-lxb/PyTeXMK/main/tools/install.sh | bash -s -- -d ~/opt/pytexmk -b ~/.local/bin

# Pin a specific version
curl -fsSL https://raw.githubusercontent.com/YanMing-lxb/PyTeXMK/main/tools/install.sh | bash -s -- -v 1.2.8

# Use the uv channel instead (installs from PyPI, needs uv; for Intel Macs or old glibc)
curl -fsSL https://raw.githubusercontent.com/YanMing-lxb/PyTeXMK/main/tools/install.sh | bash -s -- -m uv

# Show all options
curl -fsSL https://raw.githubusercontent.com/YanMing-lxb/PyTeXMK/main/tools/install.sh | bash -s -- -h
```

> **Notes**
> - The installer only needs `curl` and `unzip` (e.g. `sudo apt install curl unzip`); a LaTeX distribution (TeX Live / MiKTeX / MacTeX) is still required as described in Prerequisites.
> - Output language follows the system locale (Chinese locales get Chinese, everything else gets English); force it with `-l zh` or `-l en`.
> - **Only two binary architectures are published**: `x64` for Linux and `arm64` for macOS. On Intel Macs use the uv channel (`uv tool install pytexmk`, or pass `-m uv` to the script); the installer refuses a package that does not match your architecture.
> - **glibc ≥ 2.28 is required on Linux** (Ubuntu 20.04+, Debian 10+, RHEL 8+, etc.). The binary is built inside a `manylinux_2_28` container and CI asserts that nothing in the bundle (including the bundled `.so` files under `_internal`) exceeds that floor. The script checks this before downloading and points you to `uv tool install pytexmk` when your glibc is too old; pass `-f` to force the install anyway.
> - The install lives in your home directory (`~/.local/opt/pytexmk`) and needs no `sudo`; if `~/.local/bin` is not on your `PATH`, the script prints the exact `export` line to add.
> - The archive is a PyInstaller onedir tree: the `pytexmk` launcher and `_internal/` (which holds `_internal/data` and the `_internal/locale` message catalogs) must stay in the same directory. The script replaces the whole directory; when installing manually, **do not copy the `pytexmk` file on its own**.

### Upgrade

```bash
# pip
pip install --upgrade pytexmk

# uv (upgrade to latest)
uv add pytexmk@latest

# winget
winget upgrade --id YanMing-lxb.PyTeXMK
```

For the Linux / macOS binary package, just re-run the install command (the script detects an existing install and replaces it in place; this is also the command printed by `pytexmk --help`):

```bash
curl -fsSL https://raw.githubusercontent.com/YanMing-lxb/PyTeXMK/main/tools/install.sh | bash -s
```

### Uninstall

```bash
# Linux binary package: remove the program directory and the launcher symlink
# (swap in your own paths if you installed with -d / -b)
rm -rf ~/.local/opt/pytexmk ~/.local/bin/pytexmk

# pip install
pip uninstall pytexmk

# uv install
uv tool uninstall pytexmk
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
| `--native/--no-native` | Native named-directory build (aux files go straight into `Auxiliary/`, default `auto`) |
| `--shell-escape/--no-shell-escape` | Allow `\write18` (default: auto-detect minted/pythontex/etc.) |
| `--interaction MODE` | Override `-interaction` (`batchmode`/`nonstopmode`/`errorstopmode`) |
| `--pass-arg ARG` | Pass an extra argument to the TeX engine (repeatable) |
| `--max-runs N` | Maximum extra compilation passes (default 8) |
| `--jobname NAME` | Name output files (PDF/aux/synctex) after NAME; the `.tex` source keeps its main-file name. Useful for multiple PDF variants |
| `--no-preflight` | Skip pre-compile checks (missing `\end{document}`, `.bib`, graphics, etc.) |
| `--doctor` | Inspect the local TeX toolchain (engines/biber/xindy/latexdiff/PyTeXLogs/config/state) and exit |
| `--watch` | Watch sources and recompile automatically (1s poll, 400ms debounce, Ctrl+C to stop) |
| `-io`, `--includeonly LIST` | Compile only the listed `\include` chapters (comma-separated); output goes to `Build/partial` and `Auxiliary/partial` |
| `-A`, `--all-subprojects` | Compile every `[subprojects]` entry in order, continue on failure, summarize and exit non-zero |
| `--synctex-check` | Run `synctex view/edit` after compiling to verify forward/reverse jumps (exit 7 on failure) |
| `--report [PATH]` | Write the PyTeXLogs diagnostic report as JSON (default `Auxiliary/<job>.pytexmk-report.json`) |
| `--fail-on warning` | Return exit 6 when warnings/typesetting notices exist (for CI; default `none`) |
| `--explain` | Print the effective build configuration and exit without compiling |
| `--show-config` | Print the merged configuration (default < user < project) |
| `--validate-config` | Validate config keys/types and return 4 on errors |
| `--completion SHELL` | Print a bash/zsh/fish/powershell completion script and exit (options are extracted from argparse) |

### Submission & pdflatex Compatibility

| Option | Description |
| --- | --- |
| `-sp`, `--submission-pack` | Build `Submission/<project>-submission.zip`: `.fls` dependencies + `.bbl` + ASCII-converted sources + notes |
| `-pc`, `--pdflatex-check` | Only run the pdflatex compatibility check (fontspec/unicode-math/ctex/xeCJK etc.) |
| `--submit-dir DIR` | Submission output directory (default `./Submission/`) |
| `--keep-preamble` | Keep the original preamble (default comments out fontspec/unicode-math/ctex and adds fontenc/inputenc/textcomp) |
| `--pack-verify` | Compile the pack once with pdflatex in a temporary directory and record the result |
| `--include-bib` | Also include `.bib` sources (default: `.bbl` only) |

> If the journal only accepts pdflatex, `-sp` converts Greek letters, `°℃µ‰`, `–—…`,
> smart quotes and sub/superscripts into pure ASCII LaTeX, comments out
> fontspec/unicode-math/ctex, and lists every conversion plus the exact
> `file:line` of characters it cannot convert (CJK, emoji, …). With
> `--pack-verify` it actually runs pdflatex on the converted copy.

### Cleanup

| Option | Description |
| --- | --- |
| `-c`, `--clean` | Clean auxiliary files of the main file |
| `-C`, `--Clean` | Clean auxiliary files (including root) and output files |
| `-ca`, `--clean-any` | Clean all files with auxiliary suffixes (skips `tests/`, `examples/`, `dist/`, `docs/`, `.venv`) |
| `-Ca`, `--Clean-any` | Clean all auxiliary files (including root) and main output |
| `--clean-dry-run` | Only list files that would be deleted (`-c/-C/-ca/-Ca`) |

### LaTeXDiff Comparison

| Option | Description |
| --- | --- |
| `-d`, `--LaTeXDiff` | Generate a diff between two files, output `LaTeXDiff.tex` |
| `-dc`, `--LaTexDiff-compile` | Generate the diff file and compile it, producing a PDF with revision marks |
| `--diff-style {1,2}` | Diff style: 1 shows bibliography/glossary changes, 2 hides them; non-interactive defaults to 2 |

**Example**:

```bash
pytexmk -d old.tex new.tex     # Generate LaTeXDiff.tex
pytexmk -dc old.tex new.tex    # Generate and compile LaTeXDiff PDF
```

> Supports showing change traces in references and symbol indexes. Interactive terminals prompt for a style; non-interactive defaults to 2 (`--diff-style` overrides).

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
