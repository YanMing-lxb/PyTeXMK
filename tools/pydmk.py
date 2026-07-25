import locale
import shutil
import sys
import sysconfig
from pathlib import Path

from config import ROOT_DIR, SRC_DIR, SRCPYD_DIR
from utils import PerformanceTracker, console, run_command

ext_suffix = sysconfig.get_config_var("EXT_SUFFIX")
ext_final = Path(ext_suffix).suffix


def move_src_to_srcpyd(src_dir: Path, srcpyd_dir: Path) -> bool:
    """将 src 文件夹中的所有内容移动到 srcpyd 文件夹中"""
    if not src_dir.exists():
        console.print(f"✗ 源目录不存在: {src_dir}", style="error")
        return False

    try:
        srcpyd_dir.mkdir(parents=True, exist_ok=True)
        for item in src_dir.iterdir():
            dest_item = srcpyd_dir / item.name
            if item.is_dir():
                if dest_item.exists():
                    shutil.rmtree(dest_item)
                shutil.copytree(item, dest_item)
            else:
                shutil.copy2(item, dest_item)
        console.print(f"✓ 已复制源文件到: {srcpyd_dir}", style="success")
        return True
    except Exception as e:
        console.print(f"✗ 复制源文件失败: {e}", style="error")
        return False


def should_exclude(file_path: Path, exclude_files: list) -> bool:
    """判断文件是否需要排除"""
    return file_path.name in exclude_files


def encrypt_py_to_pyd(py_file: Path) -> bool:
    """使用 Cython 编译单个 .py 文件为扩展模块"""
    try:
        # 使用 cythonize 命令编译 py 文件为 pyd
        command = ["cythonize", "-3", "-i", "-j", "8", str(py_file)]
        success = run_command(
            command=command,
            success_msg=f"加密成功: {py_file.name}",
            error_msg=f"加密失败: {py_file.name}",
            process_name="Cython 编译",
            encoding=locale.getpreferredencoding(False),
        )
        return success
    except Exception as e:
        console.print(f"✗ 加密异常: {py_file}, 错误: {e}", style="error")
        return False


def rename_pyd_file(pyd_file: Path, original_name: Path) -> Path:
    """将生成的编译文件重命名为原始名称"""
    pattern = f"{original_name.stem}{ext_suffix}"
    for file in pyd_file.parent.glob(pattern):
        new_name = f"{original_name.stem}{ext_final}"
        renamed_file = file.parent / new_name
        file.rename(renamed_file)
        console.print(f"✓ 重命名: {file.name} → {renamed_file.name}", style="info")
        return renamed_file
    console.print(f"⚠️ 未找到匹配的编译文件: {pattern}", style="warning")
    return None


def clean_cython_artifacts(directory: Path) -> bool:
    """删除 cython 编译过程中生成的中间文件"""
    try:
        # 删除 C 文件
        c_files = list(directory.glob("**/*.c"))
        for c_file in c_files:
            c_file.unlink()
            console.print(f"✓ 删除中间文件: {c_file}", style="info")

        # 删除对象文件（跨平台）
        obj_exts = [".o", ".obj"]  # Linux/Mac 和 Windows
        for ext in obj_exts:
            for obj_file in directory.glob(f"**/*{ext}"):
                obj_file.unlink(missing_ok=True)
                console.print(f"✓ 删除对象文件: {obj_file}", style="info")

        return True
    except Exception as e:
        console.print(f"✗ 清理中间文件失败: {e}", style="error")
        return False


def process_directory(srcpyd_dir: Path, exclude_files: list) -> bool:
    """遍历 srcpyd 文件夹，对非排除的 .py 文件进行加密处理"""
    all_success = True

    for py_file in srcpyd_dir.rglob("*.py"):
        if should_exclude(py_file, exclude_files):
            console.print(f"⚠️ 跳过排除文件: {py_file}", style="warning")
            continue

        console.print(f"🔒 正在加密: {py_file.relative_to(ROOT_DIR)}", style="status")

        # 加密文件
        encrypt_success = encrypt_py_to_pyd(py_file)

        if encrypt_success:
            # 重命名并删除原文件
            renamed_file = rename_pyd_file(py_file, py_file)
            if renamed_file and renamed_file.exists():
                py_file.unlink()  # 删除原 .py 文件
                console.print(f"✓ 已删除原文件: {py_file.name}", style="info")
            else:
                console.print(
                    f"⚠️ 未找到重命名后的文件: {py_file.stem}*{ext_final}", style="warning"
                )
                all_success = False
        else:
            all_success = False

    return all_success


def pydmk():
    """主函数，处理加密流程"""
    tracker = PerformanceTracker()
    exclude_files = {"main.py", "__main__.py"}

    try:
        console.rule("[bold]🔐 加密系统[/]")

        # 步骤1: 复制源文件到加密目录
        copy_result, copy_data = tracker.execute_with_timing(
            lambda: move_src_to_srcpyd(SRC_DIR, SRCPYD_DIR), "复制源文件"
        )
        tracker.add_record(copy_data)

        if not copy_result:
            console.rule("[bold red]❌ 复制源文件失败，加密终止！[/]")
            sys.exit(1)

        # 步骤2: 加密文件
        encrypt_result, encrypt_data = tracker.execute_with_timing(
            lambda: process_directory(SRCPYD_DIR, exclude_files), "加密文件"
        )
        tracker.add_record(encrypt_data)

        # 步骤3: 清理中间文件
        clean_result, clean_data = tracker.execute_with_timing(
            lambda: clean_cython_artifacts(SRCPYD_DIR), "清理中间文件"
        )
        tracker.add_record(clean_data)

        if encrypt_result and clean_result:
            console.rule("[bold green]✅ 加密完成！[/]")
            console.print(f"加密后的文件位于: [bold underline]{SRCPYD_DIR}[/]")
        else:
            console.rule("[bold yellow]⚠️ 加密部分完成，但存在错误[/]")

        # 返回性能数据
        return tracker.records

    except KeyboardInterrupt:
        console.print("\n⚠️ 用户中断操作 (Ctrl+C)，程序已终止", style="warning")
        sys.exit(1)

    except Exception as e:
        console.rule("[bold red]💥 发生未知异常！[/]")
        console.print(f"异常类型: {type(e).__name__}", style="error")
        console.print(f"异常内容: {e!s}", style="error")
        console.print_exception()
        sys.exit(1)


if __name__ == "__main__":
    pydmk()
