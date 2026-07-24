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
FilePath     : /PyTeXMK/tools/make1.py
Description  :
 -----------------------------------------------------------------------
"""

import re
import shutil
import subprocess
import sys
from pathlib import Path

from utils import console, run_command


def _get_version():
    version_file = Path("src/pytexmk/version.py")
    if not version_file.exists():
        raise FileNotFoundError(f"文件 {version_file} 不存在")

    with open(version_file, "r", encoding="utf-8") as file:
        content = file.read()

    version_match = re.search(r"__version__\s*=\s*['\"]([^'\"]+)['\"]", content)
    if not version_match:
        raise ValueError(f"无法在 {version_file} 中找到 __version__ 变量")

    return version_match.group(1)


def inswhl():
    console.print("📦 开始安装测试 PyTeXMK", style="status")

    uninstall_success = run_command(
        command=["uv", "pip", "uninstall", "pytexmk"],
        success_msg="旧版 PyTeXMK 卸载完成",
        error_msg="旧版 PyTeXMK 卸载失败",
        process_name="卸载旧版 PyTeXMK",
    )

    whl_files = list(Path("dist").glob("*.whl"))
    if not whl_files:
        raise FileNotFoundError("dist 目录中没有找到 .whl 文件")
    install_success = run_command(
        command=["uv", "pip", "install", str(whl_files[0])],
        success_msg="测试 PyTeXMK 安装完成",
        error_msg="测试 PyTeXMK 安装失败",
        process_name="安装测试版 PyTeXMK",
    )
    return uninstall_success and install_success


def upload():
    version = _get_version()
    tag_name = f"v{version}"

    # 创建标签
    run_command(
        command=["git", "tag", tag_name],
        success_msg=f"标签 {tag_name} 创建成功",
        error_msg=f"标签 {tag_name} 创建失败",
        process_name="创建标签",
    )
    console.log(f"创建标签: {tag_name}")

    # 推送标签
    run_command(
        command=["git", "push", "origin", tag_name],
        success_msg=f"标签 {tag_name} 推送成功",
        error_msg=f"标签 {tag_name} 推送失败",
        process_name="推送标签",
    )
    console.log(f"推送标签: {tag_name}")

    console.log("成功上传标签和推送到远程仓库，发布到 github")


def html():
    readme_md = Path("README.md")
    readme_html = Path("README.html")
    target_dir = Path("src/pytexmk/data")

    run_command(
        command=["pandoc", str(readme_md), "-o", str(readme_html)],
        success_msg="README.html 生成成功",
        error_msg="README.html 生成失败",
        process_name="生成 README.html",
    )

    if not target_dir.exists():
        target_dir.mkdir(parents=True)
        console.log(f"已创建目录: {target_dir}")

    target_html = target_dir / "README.html"
    shutil.move(str(readme_html), str(target_html))
    console.log(f"生成 HTML 并移动到 {target_html}")


def main():
    targets = {
        "upload": upload,
        "inswhl": inswhl,
        "html": html,
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
