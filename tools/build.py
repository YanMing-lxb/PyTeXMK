#!/usr/bin/env python3
import argparse
import platform
import shutil
import subprocess
import sys
from pathlib import Path

TOOLS_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = TOOLS_DIR.parent
SRC_PATH = PROJECT_ROOT / "src" / "pytexmk"
DIST_DIR = PROJECT_ROOT / "dist"
BUILD_DIR = PROJECT_ROOT / "build"


def get_version() -> str:
    version_file = SRC_PATH / "version.py"
    version_ns = {}
    exec(version_file.read_text(encoding="utf-8"), version_ns)
    return version_ns["__version__"]


def get_platform_suffix() -> str:
    system = platform.system().lower()
    machine = platform.machine().lower()
    if machine in ("amd64", "x86_64"):
        arch = "amd64"
    elif machine in ("arm64", "aarch64"):
        arch = "arm64"
    elif machine.startswith("arm"):
        arch = "arm"
    else:
        arch = machine
    if system == "windows":
        return f"win_{arch}"
    elif system == "darwin":
        return f"macos_{arch}"
    elif system == "linux":
        return f"linux_{arch}"
    return f"{system}_{arch}"


def get_exe_suffix() -> str:
    return ".exe" if platform.system() == "Windows" else ""


def generate_spec(name: str = "pytexmk", mode: str = "onedir") -> Path:
    hiddenimports = [
        "rich_argparse",
        "watchdog.observers.polling",
        "watchdog.observers.api",
        "toml",
        "pypdf",
        "packaging",
        "packaging.version",
        "packaging.specifiers",
        "packaging.requirements",
    ]
    if platform.system() == "Windows":
        hiddenimports.append("watchdog.observers.winapi")
    elif platform.system() == "Darwin":
        hiddenimports.append("watchdog.observers.fsevents")
    else:
        hiddenimports.append("watchdog.observers.inotify")

    datas = [
        (str(SRC_PATH / "data" / "*"), "pytexmk/data"),
        (str(SRC_PATH / "locale" / "*"), "pytexmk/locale"),
        (str(SRC_PATH / "version.py"), "pytexmk"),
    ]

    collect_block = ""
    if mode == "onedir":
        exe_third_arg = "[]"
        collect_block = """
coll = COLLECT(
    exe, a.binaries, a.zipfiles, a.datas,
    strip=False, upx=True, upx_exclude=[], name='PyTeXMK'
)
"""
    else:
        exe_third_arg = "a.binaries, a.zipfiles, a.datas,"

    spec_content = f"""# -*- mode: python ; coding: utf-8 -*-
import sys
from pathlib import Path

block_cipher = None

project_root = Path(r'{PROJECT_ROOT}')
src_path = project_root / 'src' / 'pytexmk'

a = Analysis(
    [str(src_path / '__main__.py')],
    pathex=[str(project_root / 'src')],
    binaries=[],
    datas={datas!r},
    hiddenimports={hiddenimports!r},
    hookspath=[],
    hooksconfig={{}},
    runtime_hooks=[],
    excludes=[
        'tkinter', 'test', 'unittest', 'pip', 'setuptools', 'wheel',
        'distutils', 'pydoc', 'doctest', 'pdb', 'profile', 'pstats',
        'cProfile', 'trace', 'venv', 'ensurepip', 'lib2to3', 'idlelib',
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz, a.scripts, {exe_third_arg}
    name='{name}', debug=False, bootloader_ignore_signals=False,
    strip=False, upx=True, upx_exclude=[], runtime_tmpdir=None,
    console=True, disable_windowed_traceback=False, argv_emulation=False,
    target_arch=None, codesign_identity=None, entitlements_file=None,
)
{collect_block}
"""
    spec_path = BUILD_DIR / "temp.spec"
    BUILD_DIR.mkdir(parents=True, exist_ok=True)
    spec_path.write_text(spec_content, encoding="utf-8")
    return spec_path


def clean_build():
    """Clean build artifacts."""
    for dir_path in [BUILD_DIR, DIST_DIR]:
        if dir_path.exists():
            print(f"Cleaning {dir_path.relative_to(PROJECT_ROOT)}/...")
            shutil.rmtree(dir_path)


def run_pyinstaller(spec_path: Path) -> bool:
    """Run PyInstaller and return True on success."""
    cmd = [
        sys.executable,
        "-m",
        "PyInstaller",
        str(spec_path),
        "--clean",
        "--noconfirm",
        "--distpath",
        str(DIST_DIR),
        "--workpath",
        str(BUILD_DIR),
    ]
    print(f"Running: {' '.join(str(c) for c in cmd)}")
    print()
    result = subprocess.run(cmd, cwd=PROJECT_ROOT)
    return result.returncode == 0


def copy_additional_files(dist_dir: Path, mode: str = "onedir"):
    files_to_copy = ["README.md", "README.en.md", "LICENSE", "CHANGELOG.md"]
    if mode == "onedir":
        target_dir = dist_dir / "PyTeXMK"
    else:
        target_dir = dist_dir
    target_dir.mkdir(parents=True, exist_ok=True)
    for filename in files_to_copy:
        src = PROJECT_ROOT / filename
        if src.exists():
            shutil.copy2(src, target_dir / filename)
            print(f"Copied: {filename}")


def rename_output(version: str, mode: str = "onedir") -> Path:
    plat = get_platform_suffix()
    exe_suffix = get_exe_suffix()
    if mode == "onedir":
        orig_dir = DIST_DIR / "PyTeXMK"
        new_name = f"PyTeXMK_v{version}_{plat}"
        new_dir = DIST_DIR / new_name
        if orig_dir.exists():
            if new_dir.exists():
                shutil.rmtree(new_dir)
            orig_dir.rename(new_dir)
            return new_dir
        return orig_dir
    else:
        orig_exe = DIST_DIR / f"pytexmk{exe_suffix}"
        new_name = f"PyTeXMK_v{version}_{plat}{exe_suffix}"
        new_exe = DIST_DIR / new_name
        if orig_exe.exists():
            if new_exe.exists():
                new_exe.unlink()
            orig_exe.rename(new_exe)
            return new_exe
        return orig_exe


def get_dir_size(path: Path) -> int:
    total = 0
    if path.is_file():
        return path.stat().st_size
    for item in path.rglob("*"):
        if item.is_file():
            total += item.stat().st_size
    return total


def format_size(size: int) -> str:
    for unit in ["B", "KB", "MB", "GB"]:
        if size < 1024:
            return f"{size:.1f} {unit}"
        size /= 1024
    return f"{size:.1f} TB"


def main():
    parser = argparse.ArgumentParser(description="PyTeXMK Build Script (PyInstaller)")
    mode_group = parser.add_mutually_exclusive_group()
    mode_group.add_argument("--onedir", action="store_true", default=True, help="Build as onedir (directory, default)")
    mode_group.add_argument("--onefile", action="store_true", help="Build as onefile (single executable)")
    parser.add_argument("--no-rename", action="store_true", help="Don't rename output with version")
    parser.add_argument("--version", action="version", version=f"PyTeXMK Build {get_version()}")
    args = parser.parse_args()

    mode = "onefile" if args.onefile else "onedir"
    version = get_version()

    print("=" * 60)
    print("  PyTeXMK PyInstaller Build Script")
    print("=" * 60)
    print(f"Version: {version}")
    print(f"Platform: {platform.system()} {platform.machine()}")
    print(f"Mode: {mode}")
    print(f"Python: {sys.executable}")
    print()

    print("Cleaning previous builds...")
    clean_build()
    print("Clean complete.")
    print()

    print("Generating PyInstaller spec...")
    spec_path = generate_spec(mode=mode)
    print(f"Spec generated: {spec_path.relative_to(PROJECT_ROOT)}")
    print()

    print("Running PyInstaller...")
    success = run_pyinstaller(spec_path)
    spec_path.unlink(missing_ok=True)

    if not success:
        print()
        print("=" * 60)
        print("  Build FAILED!")
        print("=" * 60)
        sys.exit(1)

    print()
    print("Copying additional files...")
    copy_additional_files(DIST_DIR, mode=mode)

    output_path = None
    if not args.no_rename:
        print()
        print("Renaming output...")
        output_path = rename_output(version, mode=mode)
    else:
        if mode == "onedir":
            output_path = DIST_DIR / "PyTeXMK"
        else:
            output_path = DIST_DIR / f"pytexmk{get_exe_suffix()}"

    print()
    print("=" * 60)
    print("  Build completed successfully!")
    print("=" * 60)
    print()

    if output_path and output_path.exists():
        size = get_dir_size(output_path)
        rel = output_path.relative_to(PROJECT_ROOT)
        if mode == "onedir":
            print(f"Output directory: {rel}/")
            exe_name = f"pytexmk{get_exe_suffix()}"
            print(f"Executable: {rel / exe_name}")
        else:
            print(f"Executable: {rel}")
        print(f"Size: {format_size(size)}")
    print()


if __name__ == "__main__":
    main()
