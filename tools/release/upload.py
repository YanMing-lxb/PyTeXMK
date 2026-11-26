"""
 =======================================================================
 ····Y88b···d88P················888b·····d888·d8b·······················
 ·····Y88b·d88P·················8888b···d8888·Y8P·······················
 ······Y88o88P··················88888b·d88888···························
 ·······Y888P··8888b···88888b···888Y88888P888·888·88888b·····d88b·······
 ········888······"88b·888·"88b·888·Y888P·888·888·888·"88b·d88P"88b·····
 ········888···d888888·888··888·888··Y8P··888·888·888··888·888··888·····
 ········888··888··888·888··888·888···"···888·888·888··888·Y88b·888·····
 ········888··"Y888888·888··888·888·······888·888·888··888··"Y88888·····
 ·······························································888·····
 ··························································Y8b·d88P·····
 ···························································"Y88P"······
 =======================================================================

 -----------------------------------------------------------------------
Author       : 焱铭
Date         : 2025-07-16 20:53:22 +0800
LastEditTime : 2025-07-16 20:53:53 +0800
Github       : https://github.com/YanMing-lxb/
FilePath     : /PyTeXMK/tools/release/upload.py
Description  :
 -----------------------------------------------------------------------
"""

import re
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from shared.utils import console, run_command


def _get_version():
    version_file = Path("src/pytexmk/version.py")
    if not version_file.exists():
        raise FileNotFoundError(f"文件 {version_file} 不存在")

    with open(version_file, encoding="utf-8") as file:
        content = file.read()

    version_match = re.search(r"__version__\s*=\s*['\"]([^'\"]+)['\"]", content)
    if not version_match:
        raise ValueError(f"无法在 {version_file} 中找到 __version__ 变量")

    return version_match.group(1)


def upload():
    version = _get_version()
    tag_name = f"v{version}"

    # 创建标签；已存在且指向当前 HEAD 时视为可重试的成功（例如上次推送中断）。
    existing = subprocess.run(
        ["git", "tag", "-l", tag_name],
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=False,
    )
    if existing.returncode != 0:
        console.print(f"✗ 检查标签 {tag_name} 失败: {existing.stderr.strip()}", style="error")
        sys.exit(1)

    if existing.stdout.strip():
        head = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            capture_output=True,
            text=True,
            encoding="utf-8",
            check=False,
        )
        tag_sha = subprocess.run(
            ["git", "rev-list", "-n", "1", tag_name],
            capture_output=True,
            text=True,
            encoding="utf-8",
            check=False,
        )
        if (
            head.returncode != 0
            or tag_sha.returncode != 0
            or head.stdout.strip() != tag_sha.stdout.strip()
        ):
            console.print(
                f"✗ 标签 {tag_name} 已存在且不指向当前 HEAD，拒绝覆盖；"
                f"请先确认版本号或手动处理旧标签",
                style="error",
            )
            sys.exit(1)
        console.print(f"ℹ️ 标签 {tag_name} 已存在并指向当前 HEAD，跳过创建", style="info")
    else:
        created = run_command(
            command=["git", "tag", tag_name],
            success_msg=f"标签 {tag_name} 创建成功",
            error_msg=f"标签 {tag_name} 创建失败",
            process_name="创建标签",
        )
        if not created:
            console.print(f"✗ 标签 {tag_name} 创建失败，已停止发布", style="error")
            sys.exit(1)

    # 推送标签
    pushed = run_command(
        command=["git", "push", "origin", tag_name],
        success_msg=f"标签 {tag_name} 推送成功",
        error_msg=f"标签 {tag_name} 推送失败",
        process_name="推送标签",
    )
    if not pushed:
        console.print(f"✗ 标签 {tag_name} 推送失败，已停止发布", style="error")
        sys.exit(1)

    console.log(f"已上传标签并推送到远程仓库，发布到 GitHub: {tag_name}")


def main():
    targets = {
        "upload": upload,
    }

    if len(sys.argv) < 2 or sys.argv[1] not in targets:
        console.log(f"用法: {sys.argv[0]} <目标>")
        console.log("可用目标:", ", ".join(targets.keys()))
        sys.exit(1)

    target = sys.argv[1]
    try:
        targets[target]()
    except subprocess.CalledProcessError as e:
        console.log(f"执行命令时出错: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
