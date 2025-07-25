import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path

from config import (
    CONFIG_DIR,
    DATA_DIR,
    ENTRY_POINT,
    ICON_FILE,
    PROJECT_NAME,
    REQUIREMENTS,
    SRCPYD_DIR,
    VENV_NAME,
    __team__,
    __version__,
)
from pydmk import pydmk
from utils import PerformanceTracker, console, delete_folder, get_venv_path, run_command

if sys.stdout.encoding != "UTF-8":
    sys.stdout.reconfigure(encoding="utf-8")


# -----------------------------------------------------------------------
# <<<<<<<<<<<<<<<<<<<<<<<<<<<<<<| 核心功能 |>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>
# -----------------------------------------------------------------------


def pre_check() -> bool:
    """
    打包前的环境检查，验证必要条件是否满足

    Returns
    -------
    bool
        所有检查项是否通过，`True` 表示环境符合要求，`False` 表示存在不满足条件的情况
    """
    # 定义需要检查的项目及其判断条件和失败提示信息
    check_items = {
        "Python版本": (sys.version_info >= (3, 8), "需要Python 3.8+"),
        "依赖文件": (Path(REQUIREMENTS).exists(), f"缺失依赖文件 {REQUIREMENTS}"),
    }

    console.print("🔍 开始环境检查", style="status")  # 提示开始检查
    all_ok = True  # 初始化检查结果状态

    # 遍历所有检查项
    for name, (condition, msg) in check_items.items():
        if not condition:
            # 如果某一项检查未通过，打印错误信息并将整体结果标记为失败
            console.print(f"✗ {name}检查失败: {msg}", style="error")
            all_ok = False

    return all_ok  # 返回检查总体结果


def check_pandoc_installed() -> bool:
    """
    检查系统是否已经安装了 pandoc。

    Returns
    -------
    bool
        - `True` 表示 pandoc 已安装；
        - `False` 表示未安装。
    """

    # 使用 run_command 执行 where pandoc 命令检查 pandoc 是否安装
    success = run_command(
        command=["where", "pandoc"],
        success_msg="pandoc 已安装",
        error_msg="pandoc 未安装或不在系统 PATH 中",
        process_name="检查 pandoc 安装",
    )

    return success


def check_venv_exists(venv_name: str = VENV_NAME) -> bool:
    """
    检查虚拟环境是否存在

    Parameters
    ----------
    venv_name : str, optional
        虚拟环境目录名称，默认使用全局配置的 [VENV_NAME]

    Returns
    -------
    bool
        - `True` 表示虚拟环境存在；
        - `False` 表示虚拟环境不存在。
    """
    venv_path = Path(venv_name)
    if not venv_path.exists():
        console.print(f"⚠️ 虚拟环境不存在：{venv_name}", style="warning")
        return False
    console.print(f"✓ 虚拟环境 [bold]{venv_name}[/] 已存在", style="success")
    return True


def create_virtual_environment(venv_name: str = VENV_NAME) -> bool:
    """
    创建隔离的Python虚拟环境

    Parameters
    ----------
    venv_name : str, optional
        虚拟环境目录名称，默认使用全局配置的 [VENV_NAME]

    Returns
    -------
    bool
        - `True` 表示创建成功；
        - `False` 表示创建失败。
    """
    console.print("🌱 开始创建虚拟环境", style="status")

    command = [sys.executable, "-m", "venv", venv_name]

    success = run_command(
        command=command,
        success_msg=f"虚拟环境 [bold]{venv_name}[/] 创建成功",
        error_msg="虚拟环境创建失败",
        process_name="创建虚拟环境",
    )

    if not success:
        console.print(
            "⚠️ 建议检查：\n1. Python环境是否正常\n2. 磁盘空间是否充足\n3. 权限是否足够",
            style="warning",
        )

    return success


def install_dependencies(venv_name: str = VENV_NAME) -> bool:
    """
    在指定的虚拟环境中安装项目依赖

    Parameters
    ----------
    venv_name : str, optional
        虚拟环境目录名称，默认使用全局配置的 [VENV_NAME]

    Returns
    -------
    bool
        - `True` 表示安装成功；
        - `False` 表示安装失败。
    """
    pip_path = get_venv_path("pip", venv_name)

    console.print("📦 开始安装依赖", style="status")

    dep_success = run_command(
        command=[str(pip_path), "install", "--no-cache-dir", "-r", REQUIREMENTS],
        success_msg="项目依赖安装完成",
        error_msg="项目依赖安装失败",
        process_name="安装项目依赖",
    )

    run_command(
        command=[str(pip_path), "install", "--no-cache-dir", "pyinstaller"],
        success_msg="PyInstaller 安装完成",
        error_msg="PyInstaller 安装失败",
        process_name="安装 PyInstaller",
    )

    run_command(
        command=[str(pip_path), "install", "--no-cache-dir", "cython"],
        success_msg="Cython 安装完成",
        error_msg="Cython 安装失败",
        process_name="安装 Cython",
    )

    return dep_success


def run_pyinstaller(venv_name: str = VENV_NAME) -> bool:
    """
    使用 PyInstaller 将 Python 项目打包为可执行应用程序

    Parameters
    ----------
    venv_name : str, optional
        虚拟环境目录名称，默认使用全局配置的 [VENV_NAME]

    Returns
    -------
    bool
        打包过程是否成功完成，`True` 表示成功，`False` 表示失败
    """
    # 获取 pyinstaller 可执行文件路径
    pyinstaller_path = get_venv_path("pyinstaller", venv_name)

    # 构建打包命令参数列表
    args = [
        str(pyinstaller_path),  # PyInstaller 可执行文件的路径
        "--name",
        PROJECT_NAME,  # 指定生成的应用程序名称
        "--workpath",
        "build",  # 设置构建过程中使用的临时工作目录
        "--distpath",
        "dist",  # 设置最终生成的可执行文件存放目录
        "--specpath",
        ".",  # 设置 .spec 文件的存放目录（当前目录）
        "--noconfirm",  # 不提示确认覆盖输出目录，避免交互式操作中断自动化流程
        "--clean",  # 构建前清理缓存，确保构建环境干净
        "--add-data",
        f"{DATA_DIR.resolve()}{os.pathsep}data",  # 添加数据文件 assets 目录到打包中，供运行时使用
        "--add-data",
        f"{CONFIG_DIR.resolve()}{os.pathsep}config",  # 添加配置文件 config 目录到打包中
        "--icon",
        str(ICON_FILE.resolve()),  # 指定程序图标文件
        "--company-name",
        __team__,  # 设置公司或团队名称，显示在文件属性中
        "--file-description",
        PROJECT_NAME,  # 设置文件描述信息
        "--product-version",
        __version__,  # 设置产品版本号，用于标识软件版本
        "--file-version",
        __version__,  # 设置文件版本号，通常与产品版本一致
        # 💄 ✨ "--windowed",  # GUI 程序必须添加此选项，防止出现控制台窗口
        str(ENTRY_POINT.resolve()),  # 入口脚本路径，指定打包的主程序
    ]

    # 执行打包命令并获取结果
    success = run_command(
        command=args,
        success_msg=f"PyInstaller 打包成功 → [bold underline]dist/{PROJECT_NAME}[/]",
        error_msg="打包失败",
        process_name="打包应用程序",
    )

    return success


def clean_up():
    """
    清理打包过程中生成的临时文件和目录，保持项目环境整洁

    Returns
    -------
    bool
        清理操作是否成功完成：
        - `True` 表示清理顺利完成；
        - `False` 表示清理过程中发生错误。

    Notes
    -----
    当前清理内容包括：
    1. 目录：`build`, `__pycache__`, 和虚拟环境目录（默认为 [venv_rhs]）
    2. 文件：所有 `.spec` 打包配置文件
    """
    try:
        # 遍历并删除主要打包产物目录
        for artifact in ["build", "__pycache__"]:
            if Path(artifact).exists():
                shutil.rmtree(artifact)  # 删除目录及其内容
                console.print(f"✓ 删除打包产物: {artifact}", style="info")

        # 查找并删除所有 .spec 文件
        for spec_file in Path().glob("*.spec"):
            spec_file.unlink()  # 删除单个文件
            console.print(f"✓ 删除spec文件: {spec_file}", style="info")

        # 提示用户环境清理已完成
        console.print("✓ 环境清理完成", style="success")
        return True

    except Exception as e:
        # 捕获并打印异常信息，返回清理失败状态
        console.print(f"✗ 清理失败: {e}", style="error")
        return False


def delete_dist_project_folder():
    """
    删除 dist 目录下的项目文件夹

    Returns
    -------
    bool
        - `True` 表示删除成功或文件夹不存在；
        - `False` 表示删除失败。
    """
    dist_project_path = Path("dist") / PROJECT_NAME  # 构建目标路径

    if not dist_project_path.exists():
        console.print(f"⚠️ 文件夹不存在：{dist_project_path}", style="warning")
        return True  # 如果文件夹不存在，认为删除成功

    try:
        shutil.rmtree(dist_project_path)  # 删除目录及其内容
        console.print(
            f"✓ 删除 dist 下的项目文件夹: {dist_project_path}", style="success"
        )
        return True
    except Exception as e:
        console.print(f"✗ 删除 dist 下的项目文件夹失败：{e}", style="error")
        return False


# ==========================================================
#                         PyPi 发布
# ==========================================================


def build_whl(venv_name):
    pip_path = get_venv_path("pip", venv_name)

    console.print("📦 开始构建 PyTeXMK 轮子", style="status")

    whl_success = run_command(
        command=[str(pip_path), "python", "-m", "build"],
        success_msg="PyTeXMK 轮子构建完成",
        error_msg="PyTeXMK 轮子构建失败",
        process_name="构建 PyTeXMK 轮子",
    )

    return whl_success


def inswhl(venv_name):
    pip_path = get_venv_path("pip", venv_name)

    console.print("📦 开始安装依赖", style="status")

    uninstall_success = run_command(
        command=[str(pip_path), "pip", "uninstall", "-y", "pytexmk"],
        success_msg="旧版 PyTeXMK 卸载完成",
        error_msg="旧版 PyTeXMK 卸载失败",
        process_name="卸载旧版 PyTeXMK",
    )

    whl_files = list(Path("dist").glob("*.whl"))
    if not whl_files:
        raise FileNotFoundError("dist 目录中没有找到 .whl 文件")
    install_success = run_command(
        command=[str(pip_path), "pip", "install", str(whl_files[0])],
        success_msg="测试 PyTeXMK 安装完成",
        error_msg="测试 PyTeXMK 安装失败",
        process_name="安装测试版 PyTeXMK",
    )
    return uninstall_success and install_success


# ==========================================================
#                          辅助程序
# ==========================================================
def build_html():
    console.print("📦 开始转换 Readme 文件格式", style="status")
    readme_md = Path("README.md")
    readme_html = Path("README.html")
    html_success = run_command(
        command=["pandoc", readme_md, "-o", readme_html],
        success_msg="Readme 文件格式转换完成",
        error_msg="Readme 文件格式转换失败",
        process_name="转换 Readme 文件格式",
    )

    if not DATA_DIR.exists():
        DATA_DIR.mkdir(parents=True)
        console.log(f"已创建目录: {DATA_DIR}")

    target_html = DATA_DIR / "README.html"
    shutil.move(str(readme_html), str(target_html))
    console.log(f"生成 HTML 并移动到 {target_html}")

    return html_success


# ======================
# 主流程
# ======================
def main():
    """主函数，处理打包流程"""
    parser = argparse.ArgumentParser(description="Python 项目打包工具")
    parser.add_argument(
        "mode",
        choices=["pack", "pydmk", "whl"],
        help="打包模式: pack (打包程序), setup (构建安装包), pydmk (生成pyd文件)",
    )
    parser.add_argument(
        "--pack-tool",
        "-t",
        default="flet",
        choices=["flet", "pyinstaller"],
        help="指定打包工具，默认使用 flet",
    )
    parser.add_argument(
        "--clean", "-c", action="store_true", help="清理 Cython 编译源码目录 SRCPYD_DIR"
    )
    args = parser.parse_args()

    tracker = PerformanceTracker()

    try:
        console.rule(f"[bold]🚀 {PROJECT_NAME} 打包系统[/]")

        # 预检查步骤
        pre_check_result, pre_check_performance_data = tracker.execute_with_timing(
            pre_check, "预检查"
        )
        tracker.add_record(pre_check_performance_data)

        if not pre_check_result:
            console.rule("[bold red]❌ 预检查失败，打包终止！[/]")
            sys.exit(1)

        steps = []
        if not args.clean and args.mode != "setup":
            # PACK 模式：需要虚拟环境 + 依赖 + 打包 + 验证
            # 删除 dist 下的项目文件夹
            delete_result, delete_performance_data = tracker.execute_with_timing(
                delete_dist_project_folder, "删除旧打包"
            )
            tracker.add_record(delete_performance_data)

            if not delete_result:
                console.print("✗ 删除旧打包失败，无法继续", style="error")
                sys.exit(1)

        # ====== 根据 mode 分支处理 ======
        if args.mode == "pack":
            if not Path(ENTRY_POINT).exists():
                console.print(
                    f"✗ 找不到入口文件：{ENTRY_POINT}, 可能没运行 生成 pyd 文件",
                    style="error",
                )
                sys.exit(1)

                # ✨ 添加打包与验证步骤
                pack_result, pack_performance_data = tracker.execute_with_timing(
                    run_pyinstaller, "PyInstaller 打包"
                )

                tracker.add_record(pack_performance_data)

                steps.extend([pack_result])
            else:
                console.print("✗ 安装或更新依赖失败", style="error")
                sys.exit(1)

        elif args.mode == "pydmk":
            if args.clean:  # 新增判断
                clean_result, clean_data = tracker.execute_with_timing(
                    lambda: delete_folder(SRCPYD_DIR), "清理源码目录"
                )
                tracker.add_record(clean_data)
                if not clean_result:
                    console.print("✗ 清理 SRCPYD_DIR 失败", style="error")
            else:
                pydmk_records = pydmk()

                for record in pydmk_records:
                    tracker.add_record(record)

        # ====== 统一执行步骤 ======
        success = all(steps)

        if success:
            if args.mode == "pack":
                console.rule("[bold green]✅ 程序打包成功！[/]")
                console.print(
                    f"生成的可执行文件位于：[bold underline]dist/{PROJECT_NAME}[/]"
                )
                _, clean_up_performance_data = tracker.execute_with_timing(
                    clean_up, "环境清理"
                )
                tracker.add_record(clean_up_performance_data)
            elif args.mode == "setup":
                console.rule("[bold green]✅ 安装包构建成功！[/]")
                console.print(
                    f"安装包位于：[bold underline]dist/{PROJECT_NAME}-{__version__}-setup.exe[/]"
                )
            elif args.mode == "pydmk":
                console.rule("[bold green]✅ pyd 文件生成完成！[/]")
        else:
            console.rule("[bold red]❌ 构建失败！[/]")
            console.print("部分步骤未完成，请查看上方详细错误信息。")

        # 生成性能报告
        tracker.generate_report()

    except PermissionError as e:
        console.print(f"✗ 权限错误: {e}", style="error")
        console.print("建议：尝试以管理员权限运行本脚本", style="warning")

    except FileNotFoundError as e:
        console.print(f"✗ 文件或路径不存在: {e}", style="error")
        console.print("请确认相关文件是否完整或路径是否正确", style="warning")

    except subprocess.CalledProcessError as e:
        console.print(f"✗ 子进程调用失败: {e}", style="error")
        console.print("命令执行中断，请检查依赖环境或系统资源", style="warning")

    except IOError as e:
        console.print(f"✗ IO 错误: {e}", style="error")
        console.print("可能原因：磁盘空间不足、文件锁定或权限问题", style="warning")

    except KeyboardInterrupt:
        console.print("\n⚠️ 用户中断操作 (Ctrl+C)，程序已终止", style="warning")
        sys.exit(1)

    except Exception as e:
        console.rule("[bold red]💥 发生未知异常！[/]")
        console.print_exception(show_locals=True)
        console.print(f"异常类型: {type(e).__name__}")
        console.print(f"异常内容: {str(e)}")
        console.print("请联系开发者并附上以上异常信息以便排查问题", style="warning")
        sys.exit(1)


if __name__ == "__main__":
    main()
