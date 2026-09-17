"""
PyTeXMK Winget 发布工具（基于官方 wingetcreate）

统一入口：使用 wingetcreate 直接生成清单并提交 PR 到 microsoft/winget-pkgs。

用法（本项目通过 uv 运行）：
    uv run python tools/winget/publish.py --version <VERSION> --release-tag v<VERSION>
"""

import argparse
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from config import WINGET_PACKAGE_IDENTIFIER  # noqa: E402
from utils import console  # noqa: E402

_SANITIZE_PATTERNS = [
    re.compile(r"ghp_[A-Za-z0-9]{36}"),
    re.compile(r"github_pat_[A-Za-z0-9_]{82}"),
    re.compile(r"x-access-token:[^\s'\"]+"),
]

# winget 尚未安装该包时，update 会报这类错误，需回退走 new
_FALLBACK_MARKERS = ("not found", "could not find", "not installed", "不存在")


def _sanitize_log(msg: str) -> str:
    result = msg
    for pattern in _SANITIZE_PATTERNS:
        result = pattern.sub("<REDACTED>", result)
    return result


def _find_wingetcreate(explicit: str | None) -> str | None:
    if explicit:
        if Path(explicit).is_file() or shutil.which(explicit):
            return explicit
        console.print(f"⚠ 指定的 wingetcreate 路径不可用: {explicit}", style="warning")
    env_path = os.environ.get("WINGETCREATE_PATH")
    if env_path:
        if Path(env_path).is_file() or shutil.which(env_path):
            return env_path
        console.print(f"⚠ 环境变量 WINGETCREATE_PATH 指定的路径不可用: {env_path}", style="warning")
    return shutil.which("wingetcreate")


def _install_wingetcreate_best_effort() -> None:
    console.print("[status]已安装 wingetcreate...", style="info")
    result = subprocess.run(
        ["winget", "install", "--exact", "--id", "Microsoft.WingetCreate",
         "--silent", "--accept-package-agreements", "--accept-source-agreements"],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="ignore",
    )
    if result.returncode == 0:
        console.print("✓ wingetcreate 安装成功", style="success")
    else:
        console.print(
            _sanitize_log(f"⚠ wingetcreate 安装失败 (exit={result.returncode})，继续尝试已存在的命令"),
            style="warning",
        )


def _read_token() -> str:
    token = os.environ.get("WINGET_CREATE_GITHUB_TOKEN")
    if not token:
        console.print("✗ 环境变量 WINGET_CREATE_GITHUB_TOKEN 未设置", style="error")
        console.print("请在环境变量中注入 GitHub PAT（勿通过命令行参数传递）", style="error")
        sys.exit(1)
    return token


def _run(cmd: list[str]) -> subprocess.CompletedProcess:
    env = os.environ.copy()
    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="ignore",
        env=env,
    )
    if result.stdout:
        console.print(_sanitize_log(result.stdout.rstrip()))
    if result.stderr:
        console.print(_sanitize_log(result.stderr.rstrip()))
    return result


def _should_fallback(result: subprocess.CompletedProcess) -> bool:
    combined = (result.stdout or "") + "\n" + (result.stderr or "")
    return any(marker in combined.lower() for marker in _FALLBACK_MARKERS)


def main() -> int:
    parser = argparse.ArgumentParser(description="PyTeXMK Winget 发布工具（基于官方 wingetcreate）")
    parser.add_argument(
        "--version", required=True,
        help='semver 版本号，不带 v 前缀 (如 "1.3.0")',
    )
    parser.add_argument(
        "--release-tag", required=True,
        help='GitHub Release tag，带 v 前缀 (如 "v1.3.0")',
    )
    parser.add_argument(
        "--wingetcreate-path", type=str, default=None,
        help="wingetcreate 可执行文件路径（覆盖环境变量与 PATH）",
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="仅打印将要执行的命令，不实际调用 wingetcreate、不要求 TOKEN（供本地核对）",
    )
    args = parser.parse_args()

    if not args.dry_run:
        # 读取 token（仅在 argparse 之后执行，保证 --help 永远成功）
        _read_token()

    installer_url = (
        f"https://github.com/YanMing-lxb/PyTeXMK/releases/download/"
        f"{args.release_tag}/pytexmk-{args.version}-windows-x64.zip"
    )
    console.print(f"Installer URL: {installer_url}", style="info")

    wingetcreate = _find_wingetcreate(args.wingetcreate_path)
    if wingetcreate is None:
        if args.dry_run:
            console.print("⚠ dry-run：未找到 wingetcreate（正常流程会 best-effort 安装后重试）", style="warning")
            wingetcreate = "wingetcreate"
        else:
            console.print("[status]wingetcreate 未找到，尝试安装 (best-effort)...", style="info")
            try:
                _install_wingetcreate_best_effort()
                wingetcreate = _find_wingetcreate(args.wingetcreate_path)
            except Exception as e:
                console.print(_sanitize_log(f"⚠ 安装 wingetcreate 异常: {e}"), style="warning")
                wingetcreate = None
            if wingetcreate is None:
                console.print("✗ 未找到 wingetcreate，发布中止", style="error")
                return 1

    # 优先 update（包已存在）；失败且命中未安装标记时回退 new
    update_cmd = [
        wingetcreate, "update", WINGET_PACKAGE_IDENTIFIER,
        "-u", installer_url, "-v", args.version,
        "--submit", "--no-open",
    ]
    new_cmd = [
        wingetcreate, "new", installer_url,
        "-v", args.version, "--submit", "--no-open",
    ]

    if args.dry_run:
        console.print("────────────────── dry-run（不执行）──────────────────", style="info")
        console.print(_sanitize_log(f"[dim]update: {' '.join(update_cmd)}[/]"))
        console.print(_sanitize_log(f"[dim]fallback(new): {' '.join(new_cmd)}[/]"))
        console.print("⚠ 真实发布需要：wingetcreate 可用 + WINGET_CREATE_GITHUB_TOKEN 注入", style="warning")
        return 0

    console.print(_sanitize_log(f"[dim]执行命令: {' '.join(update_cmd)}[/]"))
    result = _run(update_cmd)

    if result.returncode == 0:
        console.print("✓ winget 清单更新并提交成功 (wingetcreate update)", style="success")
        return 0

    if not _should_fallback(result):
        console.print(f"✗ wingetcreate update 失败 (exit={result.returncode})", style="error")
        return result.returncode or 1

    console.print("⚠ update 提示包可能不存在，回退执行 wingetcreate new...", style="warning")
    console.print(_sanitize_log(f"[dim]执行命令: {' '.join(new_cmd)}[/]"))
    result = _run(new_cmd)

    if result.returncode == 0:
        console.print("✓ winget 清单创建并提交成功 (wingetcreate new)", style="success")
        return 0

    console.print(f"✗ wingetcreate 提交失败 (exit={result.returncode})", style="error")
    return result.returncode or 1


if __name__ == "__main__":
    sys.exit_code = 1
    try:
        sys.exit_code = main()
    except KeyboardInterrupt:
        console.print("\n⚠️ 用户中断操作 (Ctrl+C)，程序已终止", style="warning")
        sys.exit(1)
    except Exception as e:
        console.print("\n💥 发生未知异常！", style="error")
        console.print(_sanitize_log(f"异常类型: {type(e).__name__}"), style="error")
        console.print(_sanitize_log(f"异常内容: {e!s}"), style="error")
        try:
            console.print_exception()
        except Exception:
            pass
        sys.exit(1)
    sys.exit(sys.exit_code)