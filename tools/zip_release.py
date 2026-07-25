import argparse
import shutil
import sys
import zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from config import PROJECT_NAME, ROOT_DIR, __version__
from utils import console


def get_executable_name(platform: str) -> str:
    if platform == "windows":
        return f"{PROJECT_NAME}.exe"
    return PROJECT_NAME


def format_size(size_bytes: int) -> str:
    for unit in ["B", "KB", "MB", "GB"]:
        if size_bytes < 1024.0:
            return f"{size_bytes:.2f} {unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.2f} TB"


def zip_release(platform: str) -> bool:
    dist_dir = ROOT_DIR / "dist" / PROJECT_NAME
    zip_name = f"pytexmk-{__version__}-{platform}-x64.zip"
    zip_path = ROOT_DIR / zip_name
    staging_dir = ROOT_DIR / "staging_release"
    staging_app_dir = staging_dir / PROJECT_NAME

    console.rule(f"[bold]📦 发布打包 - {platform}[/]")

    console.print(f"正在验证 dist 目录...", style="status")
    if not dist_dir.exists():
        console.print(f"✗ dist 目录不存在: {dist_dir}", style="error")
        return False
    console.print(f"✓ dist 目录已确认: {dist_dir}", style="success")

    console.print(f"正在验证可执行文件...", style="status")
    exe_name = get_executable_name(platform)
    exe_path = dist_dir / exe_name
    if not exe_path.exists():
        console.print(f"✗ 可执行文件不存在: {exe_path}", style="error")
        return False
    console.print(f"✓ 可执行文件已确认: {exe_path}", style="success")

    console.print(f"正在清理旧文件...", style="status")
    if zip_path.exists():
        zip_path.unlink()
        console.print(f"已删除旧的压缩包: {zip_path}", style="info")
    if staging_dir.exists():
        shutil.rmtree(staging_dir)
        console.print(f"已删除旧的临时目录: {staging_dir}", style="info")
    console.print(f"✓ 清理完成", style="success")

    console.print(f"正在创建临时目录...", style="status")
    staging_app_dir.mkdir(parents=True, exist_ok=True)
    console.print(f"✓ 临时目录已创建: {staging_app_dir}", style="success")

    console.print(f"正在复制文件...", style="status")
    shutil.copytree(dist_dir, staging_app_dir, dirs_exist_ok=True)
    console.print(f"✓ 文件复制完成", style="success")

    console.print(f"正在创建压缩包...", style="status")
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for file_path in staging_app_dir.rglob("*"):
            if file_path.is_file():
                arcname = file_path.relative_to(staging_dir)
                zf.write(file_path, arcname)
    console.print(f"✓ 压缩包已创建: {zip_path}", style="success")

    console.print(f"正在清理临时目录...", style="status")
    shutil.rmtree(staging_dir)
    console.print(f"✓ 临时目录已删除", style="success")

    file_size = zip_path.stat().st_size
    console.print(f"\n🎉 发布打包成功！", style="success")
    console.print(f"压缩包路径: {zip_path}", style="info")
    console.print(f"文件大小: {format_size(file_size)}", style="info")

    return True


def main():
    parser = argparse.ArgumentParser(description=f"PyTeXMK 发布打包工具 v{__version__}")
    parser.add_argument("platform", choices=["linux", "windows", "macos"], help="目标平台")
    args = parser.parse_args()

    try:
        success = zip_release(args.platform)
        if not success:
            sys.exit(1)
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
