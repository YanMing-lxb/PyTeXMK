#!/usr/bin/env python3
"""
PyTeXMK unified build & development task runner.

Usage:
    uv run python tools/make.py <target> [args...]

Targets:
    help              Show this help message
    clean             Clean build artifacts, caches, __pycache__
    install           Install all dependencies with uv (sync)
    install-dev       Install dev dependencies
    test              Run pytest unit tests
    test-cov          Run pytest with coverage report
    test-integration  Run integration tests (requires LaTeX)
    lint              Run ruff linter
    lint-fix          Run ruff linter with auto-fix
    format            Run ruff formatter
    format-check      Check formatting without modifying files
    build             Build wheel + sdist with uv build
    build-exe         Build PyInstaller onedir distribution
    build-exe-onefile  Build PyInstaller onefile distribution
    install-pkg       Install built wheel locally
    uninstall-pkg     Uninstall pytexmk
    inswhl            Install built wheel for testing (alias for install-pkg)
    pot               Generate .pot translation templates
    mo                Compile .pot to .mo binary files
    i18n-update       Update translations (pot + mo)
    poup              Alias for i18n-update
    html              Generate README.html from README.md (pandoc)
    version           Print current version
    dist              Build wheel + PyInstaller exe (full distribution)
    publish-tag       Create and push git tag for release
    ci-test           CI: lint + test (no LaTeX required)
    ci-full           CI: lint + test + integration + build
"""

from __future__ import annotations

import os
import platform
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path

TOOLS_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = TOOLS_DIR.parent
SRC_DIR = PROJECT_ROOT / "src" / "pytexmk"
DIST_DIR = PROJECT_ROOT / "dist"
BUILD_DIR = PROJECT_ROOT / "build"
TESTS_DIR = PROJECT_ROOT / "tests"
LOCALE_DIR = SRC_DIR / "locale"

console = None


def _get_console():
    global console
    if console is None:
        try:
            from rich.console import Console
            from rich.theme import Theme

            theme = Theme(
                {
                    "success": "bold green",
                    "warning": "bold yellow",
                    "error": "bold red",
                    "info": "bold blue",
                    "status": "bold cyan",
                    "time": "bold magenta",
                    "cmd": "dim",
                }
            )
            console = Console(theme=theme)
        except ImportError:

            class FallbackConsole:
                def print(self, *args, **kwargs):
                    print(*args)

                def rule(self, *args, **kwargs):
                    print("=" * 60)

                def log(self, *args, **kwargs):
                    print(*args)

            console = FallbackConsole()
    return console


def _run(
    cmd: list[str],
    success_msg: str = "",
    error_msg: str = "",
    process_name: str = "",
    check: bool = True,
    stream: bool = False,
    **kwargs,
) -> subprocess.CompletedProcess:
    """Run a subprocess command with styled output.

    Args:
        cmd: Command list to execute.
        success_msg: Message shown on success.
        error_msg: Message shown on failure.
        process_name: Name shown in the status spinner.
        check: If True, exit on non-zero return code.
        stream: If True, stream output in real-time.
    """
    c = _get_console()
    cmd_str = " ".join(str(x) for x in cmd)
    c.print(f"  [cmd]$ {cmd_str}[/cmd]")
    env = os.environ.copy()
    kwargs.setdefault("cwd", PROJECT_ROOT)
    kwargs.setdefault("env", env)

    if stream:
        return _run_streaming(cmd, check, **kwargs)

    start_time = time.time()
    try:
        result = subprocess.run(cmd, check=check, **kwargs)
        duration = time.time() - start_time
        if duration > 60:
            dur_str = f"{duration // 60:.0f}m {duration % 60:.1f}s"
        else:
            dur_str = f"{duration:.2f}s"
        if success_msg:
            c.print(f"✓ {success_msg} [time](耗时: {dur_str})[/time]", style="success")
        return result
    except subprocess.CalledProcessError as e:
        if error_msg:
            c.print(f"✗ {error_msg}: {e}", style="error")
        if check:
            sys.exit(e.returncode)
        raise


def _run_streaming(
    cmd: list[str], check: bool = True, **kwargs
) -> subprocess.CompletedProcess:
    """Run a command with real-time output streaming."""
    c = _get_console()
    kwargs.pop("capture_output", None)
    kwargs.pop("stdout", None)
    kwargs.pop("stderr", None)
    try:
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
            encoding="utf-8",
            errors="replace",
            **kwargs,
        )
        with c.status("[status]Running...[/status]"):
            while True:
                output = process.stdout.readline()
                if not output and process.poll() is not None:
                    break
                if output:
                    c.print(f"[dim]{output.rstrip()}[/dim]")

        if process.returncode != 0 and check:
            c.print(f"[error]Command failed with exit code {process.returncode}[/error]")
            sys.exit(process.returncode)
        return subprocess.CompletedProcess(cmd, process.returncode)
    except FileNotFoundError:
        c.print(f"[error]Command not found: {cmd[0]}[/error]")
        if check:
            sys.exit(1)
        raise


def _uv(*args: str, **kwargs) -> subprocess.CompletedProcess:
    return _run(["uv", "run", *args], **kwargs)


def _py(*args: str, **kwargs) -> subprocess.CompletedProcess:
    return _run([sys.executable, *args], **kwargs)


def _remove(path: Path):
    if not path.exists():
        return
    if path.is_dir():
        shutil.rmtree(path, ignore_errors=True)
    else:
        path.unlink(missing_ok=True)


def get_version() -> str:
    version_file = SRC_DIR / "version.py"
    content = version_file.read_text(encoding="utf-8")
    m = re.search(r"__version__\s*=\s*['\"]([^'\"]+)['\"]", content)
    if not m:
        raise ValueError(f"Cannot find __version__ in {version_file}")
    return m.group(1)


# ──────────────────────────────────────────────────────────────────
# Targets
# ──────────────────────────────────────────────────────────────────


def cmd_help():
    c = _get_console()
    c.rule("[info]PyTeXMK Build & Development Tasks[/info]")
    c.print(__doc__)
    c.print(f"[dim]Project root: {PROJECT_ROOT}[/dim]")
    c.print(f"[dim]Python: {sys.executable}[/dim]")
    c.print(f"[dim]Platform: {platform.system()} {platform.machine()}[/dim]")


def cmd_clean():
    c = _get_console()
    c.rule("[info]Cleaning build artifacts...[/info]")
    targets = [
        BUILD_DIR,
        DIST_DIR,
        PROJECT_ROOT / ".pytest_cache",
        PROJECT_ROOT / ".ruff_cache",
        SRC_DIR.parent / "pytexmk.egg-info",
        TESTS_DIR / "Build",
        TESTS_DIR / "Auxiliary",
    ]
    for p in targets:
        _remove(p)
        if not p.exists():
            c.log(f"Removed: {p.relative_to(PROJECT_ROOT)}")

    for pycache in PROJECT_ROOT.rglob("__pycache__"):
        _remove(pycache)
    for pyc in PROJECT_ROOT.rglob("*.pyc"):
        pyc.unlink(missing_ok=True)
    for p in PROJECT_ROOT.glob("build_temp.spec"):
        _remove(p)
    c.print("[success]Clean complete.[/success]")


def cmd_install():
    _get_console().rule("[info]Installing dependencies with uv...[/info]")
    _run(["uv", "sync", "--dev"], success_msg="依赖安装完成", error_msg="依赖安装失败")


def cmd_install_dev():
    cmd_install()


def cmd_test():
    _get_console().rule("[info]Running unit tests...[/info]")
    _uv("pytest", str(TESTS_DIR), "-v", "--tb=short", "-m", "not slow and not requires_latex",
        success_msg="单元测试通过", error_msg="单元测试失败")


def cmd_test_cov():
    _get_console().rule("[info]Running tests with coverage...[/info]")
    _uv(
        "pytest",
        str(TESTS_DIR),
        "-v",
        "--tb=short",
        "--cov=pytexmk",
        "--cov-report=term-missing",
        "-m",
        "not slow and not requires_latex",
        success_msg="覆盖率测试通过",
        error_msg="覆盖率测试失败",
    )


def cmd_test_integration():
    _get_console().rule("[info]Running integration tests (LaTeX required)...[/info]")
    _uv("pytest", str(TESTS_DIR / "integration"), "-v", "--tb=short", "-m", "requires_latex",
        success_msg="集成测试通过", error_msg="集成测试失败")


def cmd_lint():
    _get_console().rule("[info]Running ruff linter...[/info]")
    _uv("ruff", "check", "src/", "tests/", success_msg="Lint 检查通过", error_msg="Lint 检查有问题")


def cmd_lint_fix():
    _get_console().rule("[info]Running ruff linter with auto-fix...[/info]")
    _uv("ruff", "check", "--fix", "src/", "tests/", success_msg="Lint 修复完成", error_msg="Lint 修复失败")


def cmd_format():
    _get_console().rule("[info]Running ruff formatter...[/info]")
    _uv("ruff", "format", "src/", "tests/", success_msg="格式化完成", error_msg="格式化失败")


def cmd_format_check():
    _get_console().rule("[info]Checking formatting...[/info]")
    _uv("ruff", "format", "--check", "src/", "tests/", success_msg="格式检查通过", error_msg="代码格式不符合规范")


def cmd_build():
    c = _get_console()
    c.rule("[info]Building wheel & sdist...[/info]")
    _run(["uv", "build"], success_msg="wheel + sdist 构建完成", error_msg="构建失败")
    c.print("[success]Build complete. Artifacts in dist/[/success]")


def cmd_build_exe():
    _get_console().rule("[info]Building PyInstaller onedir distribution...[/info]")
    _py(str(TOOLS_DIR / "build.py"), "--no-rename",
        success_msg="PyInstaller onedir 构建完成", error_msg="PyInstaller onedir 构建失败")


def cmd_build_exe_onefile():
    _get_console().rule("[info]Building PyInstaller onefile distribution...[/info]")
    _py(str(TOOLS_DIR / "build.py"), "--onefile", "--no-rename",
        success_msg="PyInstaller onefile 构建完成", error_msg="PyInstaller onefile 构建失败")


def cmd_install_pkg():
    c = _get_console()
    c.rule("[info]Installing built wheel locally...[/info]")
    wheels = list(DIST_DIR.glob("*.whl"))
    if not wheels:
        c.print("[warning]No wheel found in dist/. Run `make build` first.[/warning]")
        sys.exit(1)
    _run([sys.executable, "-m", "pip", "install", "--force-reinstall", str(wheels[0])],
         success_msg=f"已安装: {wheels[0].name}", error_msg="安装失败")


def cmd_uninstall_pkg():
    _get_console().rule("[info]Uninstalling pytexmk...[/info]")
    _run([sys.executable, "-m", "pip", "uninstall", "-y", "pytexmk"], check=False,
         success_msg="pytexmk 卸载完成", error_msg="pytexmk 卸载失败")


def cmd_inswhl():
    """Install built wheel locally for testing (compatible with old tools naming)."""
    c = _get_console()
    c.rule("[info]📦 安装测试 PyTeXMK...[/info]")

    c.print("[status]卸载旧版 PyTeXMK...[/status]")
    _run(["uv", "pip", "uninstall", "pytexmk"], check=False,
         success_msg="旧版 PyTeXMK 卸载完成", error_msg="旧版 PyTeXMK 卸载失败")

    whl_files = list(DIST_DIR.glob("*.whl"))
    if not whl_files:
        c.print("[warning]dist 目录中没有找到 .whl 文件[/warning]")
        sys.exit(1)

    c.print("[status]安装测试版 PyTeXMK...[/status]")
    _run(["uv", "pip", "install", str(whl_files[0])],
         success_msg="测试 PyTeXMK 安装完成", error_msg="测试 PyTeXMK 安装失败")


def _get_i18n_modules() -> list[str]:
    modules = []
    skip = {"language", "__init__", "version", "constants", "cli"}
    for f in SRC_DIR.glob("*.py"):
        if f.stem in skip:
            continue
        content = f.read_text(encoding="utf-8")
        if re.search(r"^\s*_\s*=\s*set_language\(", content, re.MULTILINE):
            modules.append(f.stem)
    return sorted(modules)


def cmd_pot():
    c = _get_console()
    c.rule("[info]Generating .pot translation templates...[/info]")
    en_dir = LOCALE_DIR / "en"
    en_dir.mkdir(parents=True, exist_ok=True)
    lc_messages = en_dir / "LC_MESSAGES"
    lc_messages.mkdir(parents=True, exist_ok=True)
    modules = _get_i18n_modules()
    c.print(f"Found {len(modules)} modules with translations: {', '.join(modules)}")
    import tempfile

    for mod in modules:
        py_file = SRC_DIR / f"{mod}.py"
        pot_file = en_dir / f"{mod}.pot"
        with tempfile.NamedTemporaryFile(suffix=".pot", delete=False, mode="w", encoding="utf-8") as tmp:
            tmp_path = Path(tmp.name)
        try:
            try:
                result = _run(["xgettext", "-d", mod, "-o", str(tmp_path), str(py_file)], check=False)
                if result.returncode != 0:
                    c.print(f"[warning]xgettext failed for {mod}[/warning]")
                    continue
            except FileNotFoundError:
                c.print("[warning]xgettext not found. Install gettext to update translations.[/warning]")
                c.print("[dim]  Windows: scoop install gettext[/dim]")
                c.print("[dim]  macOS:   brew install gettext[/dim]")
                c.print("[dim]  Linux:   apt install gettext[/dim]")
                tmp_path.unlink(missing_ok=True)
                return
            if pot_file.exists():
                try:
                    _run(["msgmerge", "--update", "--backup=none", str(pot_file), str(tmp_path)], check=False)
                except FileNotFoundError:
                    c.print("[warning]msgmerge not found, overwriting .pot file[/warning]")
                    shutil.copy2(tmp_path, pot_file)
            else:
                shutil.copy2(tmp_path, pot_file)
        finally:
            tmp_path.unlink(missing_ok=True)
    c.print("[success].pot files generated.[/success]")


def cmd_mo():
    c = _get_console()
    c.rule("[info]Compiling .pot to .mo binary files...[/info]")
    en_dir = LOCALE_DIR / "en"
    lc_messages = en_dir / "LC_MESSAGES"
    lc_messages.mkdir(parents=True, exist_ok=True)
    modules = _get_i18n_modules()
    for mod in modules:
        pot_file = en_dir / f"{mod}.pot"
        mo_file = lc_messages / f"{mod}.mo"
        if not pot_file.exists():
            c.print(f"[warning]Skipping {mod}: {pot_file.name} not found[/warning]")
            continue
        try:
            _run(["msgfmt", "-o", str(mo_file), str(pot_file)], check=False)
        except FileNotFoundError:
            c.print("[warning]msgfmt not found. Install gettext.[/warning]")
            return
    c.print("[success].mo files compiled.[/success]")


def cmd_i18n_update():
    c = _get_console()
    c.rule("[info]Updating translations (pot + mo)...[/info]")
    cmd_pot()
    cmd_mo()


def cmd_poup():
    """Alias for i18n-update (pot + merge + mo). Compatible with old tools naming."""
    cmd_i18n_update()


def cmd_html():
    """Generate README.html from README.md using pandoc."""
    c = _get_console()
    c.rule("[info]Generating README.html from README.md...[/info]")
    readme_md = PROJECT_ROOT / "README.md"
    readme_html = PROJECT_ROOT / "README.html"
    target_dir = SRC_DIR / "data"
    target_dir.mkdir(parents=True, exist_ok=True)
    try:
        _run(["pandoc", str(readme_md), "-o", str(readme_html)], stream=True)
    except (FileNotFoundError, SystemExit):
        c.print("[warning]pandoc not found. Install pandoc to generate README.html.[/warning]")
        c.print("[dim]  Windows: scoop install pandoc[/dim]")
        c.print("[dim]  macOS:   brew install pandoc[/dim]")
        c.print("[dim]  Linux:   apt install pandoc[/dim]")
        return
    shutil.move(str(readme_html), str(target_dir / "README.html"))
    c.print(f"[success]README.html generated → {target_dir / 'README.html'}[/success]")


def cmd_version():
    print(get_version())


def cmd_dist():
    c = _get_console()
    c.rule("[info]Building full distribution (wheel + exe)...[/info]")
    cmd_build()
    cmd_build_exe()


def cmd_ci_test():
    c = _get_console()
    c.rule("[info]CI test pipeline (lint + test)[/info]")
    cmd_lint()
    cmd_test()
    c.print("[success]CI test pipeline passed.[/success]")


def cmd_ci_full():
    c = _get_console()
    c.rule("[info]CI full pipeline (lint + test + build)[/info]")
    cmd_lint()
    cmd_test()
    cmd_build()
    c.print("[success]CI full pipeline passed.[/success]")


def cmd_publish_tag():
    c = _get_console()
    version = get_version()
    tag = f"v{version}"
    c.rule(f"[info]📤 发布标签 {tag}...[/info]")

    c.print(f"[status]创建标签: {tag}[/status]")
    _run(["git", "tag", tag],
         success_msg=f"标签 {tag} 创建成功", error_msg=f"标签 {tag} 创建失败")

    c.print(f"[status]推送标签: {tag}[/status]")
    _run(["git", "push", "origin", tag],
         success_msg=f"标签 {tag} 推送成功", error_msg=f"标签 {tag} 推送失败")

    c.print("[success]成功上传标签并推送到远程仓库，发布到 GitHub[/success]")


# ──────────────────────────────────────────────────────────────────
# Dispatch
# ──────────────────────────────────────────────────────────────────

TARGETS = {
    "help": cmd_help,
    "clean": cmd_clean,
    "install": cmd_install,
    "install-dev": cmd_install_dev,
    "test": cmd_test,
    "test-cov": cmd_test_cov,
    "test-integration": cmd_test_integration,
    "lint": cmd_lint,
    "lint-fix": cmd_lint_fix,
    "format": cmd_format,
    "format-check": cmd_format_check,
    "build": cmd_build,
    "build-exe": cmd_build_exe,
    "build-exe-onefile": cmd_build_exe_onefile,
    "install-pkg": cmd_install_pkg,
    "uninstall-pkg": cmd_uninstall_pkg,
    "inswhl": cmd_inswhl,
    "pot": cmd_pot,
    "mo": cmd_mo,
    "i18n-update": cmd_i18n_update,
    "poup": cmd_poup,
    "html": cmd_html,
    "version": cmd_version,
    "dist": cmd_dist,
    "publish-tag": cmd_publish_tag,
    "ci-test": cmd_ci_test,
    "ci-full": cmd_ci_full,
}


def main():
    if len(sys.argv) < 2 or sys.argv[1] in ("-h", "--help", "help"):
        cmd_help()
        return

    target = sys.argv[1]
    if target not in TARGETS:
        c = _get_console()
        c.print(f"[error]Unknown target: {target}[/error]")
        c.print(f"Available targets: {', '.join(TARGETS.keys())}")
        sys.exit(1)

    TARGETS[target]()


if __name__ == "__main__":
    main()
