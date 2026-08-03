import argparse
import glob
import os
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from config import (
    ICON_FILE,
    PROJECT_NAME,
    ROOT_DIR,
    SRC_DATA_DIR,
    SRC_ENTRY_POINT,
    SRC_LOCALE_DIR,
    TOOLS_DIR,
    __team__,
    __version__,
)
from utils import PerformanceTracker, console, delete_folder, run_command

tracker = PerformanceTracker()


def check_icon():
    if not ICON_FILE.exists():
        console.print(f"⚠️ 图标文件不存在: {ICON_FILE}", style="warning")
        try:
            from generate_icon import main as generate_icon_main
            console.print("正在生成图标文件...", style="status")
            generate_icon_main()
        except Exception:
            console.print("请先运行 generate_icon.py 生成图标文件", style="warning")
            return False
    return ICON_FILE.exists()


def get_binary_path(dist_dir: Path) -> Path:
    if sys.platform == "win32":
        bin_name = f"{PROJECT_NAME}.exe"
    else:
        bin_name = PROJECT_NAME
    return dist_dir / PROJECT_NAME / bin_name


def pack_app(entry_point: Path, data_dir: Path, config_dir: Path, locale_dir: Path) -> bool:
    dist_dir = ROOT_DIR / "dist"
    work_dir = ROOT_DIR / "build"
    sep = os.pathsep

    for directory in [data_dir, locale_dir]:
        if directory and not directory.exists():
            console.print(f"⚠️ 数据目录不存在: {directory}", style="warning")

    if config_dir and not config_dir.exists():
        console.print(f"⚠️ 配置目录不存在: {config_dir}", style="warning")

    args = [
        "pyinstaller",
        "--noconfirm",
        "--clean",
        "--name", PROJECT_NAME,
        "--distpath", str(dist_dir),
        "--workpath", str(work_dir),
        "--onedir",
    ]

    if sys.platform == "darwin":
        args.append("--noupx")
        console.print("ℹ️ macOS 平台已禁用 UPX 压缩", style="info")

    icon_exists = check_icon()
    if icon_exists:
        args.append(f"--icon={ICON_FILE.resolve()}")

    if data_dir and data_dir.exists():
        args.append(f"--add-data={data_dir.resolve()}{sep}data")
    if config_dir and config_dir.exists():
        args.append(f"--add-data={config_dir.resolve()}{sep}{config_dir.name}")
    if locale_dir and locale_dir.exists():
        args.append(f"--add-data={locale_dir.resolve()}{sep}locale")

    args.extend([
        "--hidden-import=tomllib",
        "--hidden-import=tomli_w",
        f"--paths={str(ROOT_DIR)}",
        str(entry_point.resolve()),
    ])

    delete_folder(dist_dir)
    delete_folder(work_dir)

    success = run_command(
        command=args,
        success_msg="打包成功",
        error_msg="打包失败",
        process_name="打包应用",
    )

    return False


def clean_build():
    delete_folder(ROOT_DIR / "build")
    delete_folder(ROOT_DIR / "dist")
    delete_folder(ROOT_DIR / "staging")
    for spec in glob.glob(str(ROOT_DIR / "*.spec")):
        os.remove(spec)
        console.print(f"已删除 spec 文件: {spec}")
    return True


def pack():
    parser = argparse.ArgumentParser(description=f"{__team__} - {PROJECT_NAME} 打包工具 v{__version__}")
    parser.add_argument("mode", nargs="?", default="pack", choices=["pack", "clean"], help="运行模式: pack(打包程序), clean(清理构建文件)")
    args = parser.parse_args()

    if args.mode == "clean":
        clean_result, clean_data = tracker.execute_with_timing(clean_build, "清理构建文件")
        tracker.add_record(clean_data)
        tracker.generate_report()
        if clean_result:
            console.print("\n🎉 清理完成！", style="success")
        else:
            console.print("\n⚠️ 清理过程中出现问题，请检查上方日志", style="warning")
            sys.exit(1)
        return

    os.chdir(ROOT_DIR)

    steps_result = []

    console.rule("[bold]📦 打包模式 (onedir)[/]")
    entry_point = SRC_ENTRY_POINT
    data_dir = SRC_DATA_DIR
    config_dir = None
    locale_dir = SRC_LOCALE_DIR

    if not entry_point.exists():
        console.print(f"✗ 入口文件不存在: {entry_point}", style="error")
        sys.exit(1)

    mode_str = "源码"
    console.print(f"打包模式: onedir 目录 ({mode_str})", style="info")
    console.print(f"入口文件: {entry_point}", style="info")

    pack_result, pack_data = tracker.execute_with_timing(
        lambda: pack_app(entry_point, data_dir, config_dir, locale_dir),
        "打包程序"
    )
    tracker.add_record(pack_data)
    steps_result.append(pack_result)

    tracker.generate_report()

    if steps_result and all(steps_result):
        console.print("\n🎉 所有操作成功完成！", style="success")
    else:
        console.print("\n⚠️ 部分操作失败，请检查上方日志", style="warning")
        sys.exit(1)


def main():
    try:
        pack()
    except KeyboardInterrupt:
        console.print("\n⚠️ 用户中断操作 (Ctrl+C)，程序已终止", style="warning")
        sys.exit(1)
    except Exception as e:
        console.print("\n💥 发生未知异常！", style="error")
        console.print(f"异常类型: {type(e).__name__}", style="error")
        console.print(f"异常内容: {e!s}", style="error")
        console.print_exception()
        sys.exit(1)


if __name__ == "__main__":
    main()
