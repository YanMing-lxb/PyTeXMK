"""检查 PyInstaller 产物（以及其中捆绑的动态库）要求的最高 glibc 版本。

CI 用它在构建完成后做"水位门禁"：any 产物里出现超过基线的 GLIBC_ 符号版本，
该产物就无法在基线及更老的 glibc 上启动，必须让构建失败而不是等用户报错。

用法：
    python tools/check_glibc.py 2.28 dist/pytexmk
"""

import argparse
import re
import subprocess
import sys
from pathlib import Path

ELF_MAGIC = b"\x7fELF"
GLIBC_VERSION_RE = re.compile(r"GLIBC_(\d+)\.(\d+)")


def is_elf(path: Path) -> bool:
    """通过文件头魔数判断是否为 ELF 文件。"""
    try:
        with path.open("rb") as fh:
            return fh.read(4) == ELF_MAGIC
    except OSError:
        return False


def required_glibc_versions(path: Path) -> set[tuple[int, int]]:
    """读取该 ELF 文件的动态符号表，返回其引用的全部 glibc 版本。"""
    result = subprocess.run(
        ["objdump", "-T", str(path)],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        raise RuntimeError(f"objdump 读取失败（{path}）：{result.stderr.strip()}")

    versions = {(int(major), int(minor)) for major, minor in GLIBC_VERSION_RE.findall(result.stdout)}
    return versions


def iter_elf_files(root: Path) -> list[Path]:
    """列出目录下所有 ELF 文件（不含目录、不含符号链接）。"""
    if root.is_file():
        return [root] if is_elf(root) else []
    files = []
    for path in sorted(root.rglob("*")):
        if path.is_file() and not path.is_symlink() and is_elf(path):
            files.append(path)
    return files


def format_version(version: tuple[int, int]) -> str:
    return f"{version[0]}.{version[1]}"


def main() -> int:
    parser = argparse.ArgumentParser(description="检查产物的 glibc 水位")
    parser.add_argument("baseline", help="允许的最高 glibc 版本，例如 2.28")
    parser.add_argument("paths", nargs="+", help="待检查的目录或文件")
    args = parser.parse_args()

    match = re.fullmatch(r"(\d+)\.(\d+)", args.baseline)
    if not match:
        print(f"✗ 基线格式不合法：{args.baseline}（应为 2.28 这类形式）")
        return 2
    baseline = (int(match.group(1)), int(match.group(2)))

    targets = [Path(p) for p in args.paths]
    missing = [str(p) for p in targets if not p.exists()]
    if missing:
        print(f"✗ 路径不存在：{', '.join(missing)}")
        return 2

    files = [elf for target in targets for elf in iter_elf_files(target)]
    if not files:
        print("✗ 未找到任何 ELF 文件，检查路径是否正确")
        return 2

    violations: list[tuple[Path, tuple[int, int]]] = []
    highest = (0, 0)
    for path in files:
        for version in required_glibc_versions(path):
            highest = max(highest, version)
            if version > baseline:
                violations.append((path, version))

    print(f"检查了 {len(files)} 个 ELF 文件，最高 glibc 需求：{format_version(highest) if highest != (0, 0) else '未识别'}")
    if violations:
        print(f"✗ 有 {len(violations)} 处超过基线 glibc {format_version(baseline)}：")
        for path, version in violations:
            print(f"   {path}: GLIBC_{format_version(version)}")
        return 1

    print(f"✓ 全部满足 glibc <= {format_version(baseline)}（基线下最老的发行版可运行）")
    return 0


if __name__ == "__main__":
    sys.exit(main())
