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

from config import WINGET_PACKAGE_IDENTIFIER, __version__
from utils import console

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
        check=False,
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
        check=False,  # 不抛异常，由调用方根据 returncode 自行判断成功与否
    )
    if result.stdout:
        console.print(_sanitize_log(result.stdout.rstrip()))
    if result.stderr:
        console.print(_sanitize_log(result.stderr.rstrip()))
    return result


def _should_fallback(result: subprocess.CompletedProcess) -> bool:
    combined = (result.stdout or "") + "\n" + (result.stderr or "")
    return any(marker in combined.lower() for marker in _FALLBACK_MARKERS)


# 匹配 wingetcreate 输出中 winget-pkgs 的 PR 链接
_PULL_URL_RE = re.compile(r"https://github\.com/microsoft/winget-pkgs/pull/[0-9]+")


def _write_pr_summary(result: subprocess.CompletedProcess) -> None:
    """解析 wingetcreate 输出中的 PR 链接，写入 GitHub Actions 的 Step Summary。
    便于人工（尤其首次审核）第一时间打开 PR 跟进。仅在 CI 环境（GITHUB_STEP_SUMMARY 存在）时生效。
    """
    summary = os.environ.get("GITHUB_STEP_SUMMARY")
    if not summary:
        return  # 本地运行，跳过
    combined = (result.stdout or "") + " " + (result.stderr or "")
    match = _PULL_URL_RE.search(combined)
    if not match:
        console.print(
            "⚠ 未能从 wingetcreate 输出解析到 PR 链接，可在日志中搜索 winget-pkgs",
            style="warning",
        )
        return
    try:
        Path(summary).write_text(
            f"### Winget-pkgs PR（待人工审核）\n\n- {match.group(0)}\n",
            encoding="utf-8",
        )
        console.print(f"✓ 已将 PR 链接写入 Step Summary: {match.group(0)}", style="info")
    except OSError as e:
        console.print(f"⚠ 写入 Step Summary 失败: {e}", style="warning")


def main() -> int:
    parser = argparse.ArgumentParser(description="PyTeXMK Winget 发布工具（基于官方 wingetcreate）")
    parser.add_argument(
        "--version", default=None,
        help='semver 版本号，不带 v 前缀；缺省自动使用 config.__version__（默认推荐）',
    )
    parser.add_argument(
        "--release-tag", default=None,
        help='GitHub Release tag，带 v 前缀；缺省自动为 v<version>',
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

    # 版本统一来源：默认自动取 config.__version__（由 src/pytexmk/version.py 定义），
    # 命令行参数仅作为显式覆盖手段，日常发布无需手动指定。
    version = args.version or __version__
    release_tag = args.release_tag or f"v{version}"
    console.print(f"版本: {version}  (来源: {args.version and '命令行' or 'config.__version__'})", style="info")

    if not args.dry_run:
        # 读取 token（仅在 argparse 之后执行，保证 --help 永远成功）
        _read_token()

    installer_url = (
        f"https://github.com/YanMing-lxb/PyTeXMK/releases/download/"
        f"{release_tag}/pytexmk-{version}-windows-x64.zip"
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
            except Exception as e:  # noqa: BLE001 - best-effort 安装，失败降级处理
                console.print(_sanitize_log(f"⚠ 安装 wingetcreate 异常: {e}"), style="warning")
                wingetcreate = None
            if wingetcreate is None:
                console.print("✗ 未找到 wingetcreate，发布中止", style="error")
                return 1

    # 优先 update（包已存在分支持续自动发布）；失败且命中未安装标记时，
    # 不再回退 new —— new 是交互式向导，无法在 CI 无人值守下完成首次提交，
    # 且 winget-pkgs 首次提交本就需人工审核。此时打印首次发布指引并温和退出。
    update_cmd = [
        wingetcreate, "update", WINGET_PACKAGE_IDENTIFIER,
        "-u", installer_url, "-v", version,
        "--submit", "--no-open",
    ]
    # 首次发布需手动执行；这里仅作提示用途，展示应如何使用 new。
    new_cmd = [
        wingetcreate, "new", installer_url, "--no-open",
    ]

    if args.dry_run:
        console.print("────────────────── dry-run（不执行）──────────────────", style="info")
        console.print(_sanitize_log(f"[dim]update: {' '.join(update_cmd)}[/]"))
        console.print(_sanitize_log(f"[dim]首次发布参考 (new): {' '.join(new_cmd)}[/]"))
        console.print("⚠ 真实发布需要：wingetcreate 可用 + WINGET_CREATE_GITHUB_TOKEN 注入", style="warning")
        return 0

    console.print(_sanitize_log(f"[dim]执行命令: {' '.join(update_cmd)}[/]"))
    result = _run(update_cmd)

    if result.returncode == 0:
        console.print("✓ winget 清单更新并提交成功 (wingetcreate update)", style="success")
        _write_pr_summary(result)
        return 0

    if not _should_fallback(result):
        console.print(f"✗ wingetcreate update 失败 (exit={result.returncode})", style="error")
        return result.returncode or 1

    # 首次发布：包在 winget-pkgs 尚不存在，update 无法定位。
    # new 是交互式向导，不适合在 CI 无人值守跑；首次提交还需 winget-pkgs 人工审核。
    # 因此这里明确引导用户走手动首次提交流程，并以非致命状态结束本次 winget 步骤。
    console.print(
        "⚠ 包在 winget-pkgs 中尚不存在（首次发布），update 无法定位现有清单。",
        style="warning",
    )
    console.print(
        "  首次提交需要手动执行 wingetcreate new 并在 PR 中回应人工审核。",
        style="info",
    )
    console.print(
        "  请参考仓库 docs/winget_publish.md（主题2：首次提交人工审核说明）完成首次手动提交。",
        style="info",
    )
    console.print(
        "  首次清单入库后，后续版本将由本 CI 的 update 步骤自动发布。",
        style="info",
    )
    return 78  # 非致命状态码（EX_CONFIG），表示“需要人工介入完成首次提交”


if __name__ == "__main__":
    sys.exit_code = 1
    try:
        sys.exit_code = main()
    except KeyboardInterrupt:
        console.print("\n⚠️ 用户中断操作 (Ctrl+C)，程序已终止", style="warning")
        sys.exit(1)
    except Exception as e:  # noqa: BLE001 - __main__ 最外层兜底，打印异常后退出
        console.print("\n💥 发生未知异常！", style="error")
        console.print(_sanitize_log(f"异常类型: {type(e).__name__}"), style="error")
        console.print(_sanitize_log(f"异常内容: {e!s}"), style="error")
        try:
            console.print_exception()
        except Exception as e:  # noqa: BLE001 - traceback 打印失败的防御性兜底
            console.print(_sanitize_log(f"(打印堆栈失败: {type(e).__name__}: {e})"), style="dim")
        sys.exit(1)
    sys.exit(sys.exit_code)