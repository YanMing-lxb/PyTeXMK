import os
import queue
import shutil
import signal
import subprocess
import sys
import threading
import time
from collections.abc import Callable
from pathlib import Path
from platform import system
from typing import Any

from rich.console import Console
from rich.table import Table
from rich.theme import Theme

if sys.stdout.encoding != "UTF-8":
    sys.stdout.reconfigure(encoding="utf-8")

# -----------------------------------------------------------------------
# <<<<<<<<<<<<<<<<<<<<<<<<<<<<| 主题与样式配置 |>>>>>>>>>>>>>>>>>>>>>>>>>>>>
# -----------------------------------------------------------------------
custom_theme = Theme(
    {
        "success": "bold green",
        "warning": "bold yellow",
        "error": "bold red",
        "info": "bold blue",
        "status": "bold cyan",
        "time": "bold magenta",
    }
)
console = Console(theme=custom_theme)


# -----------------------------------------------------------------------
# <<<<<<<<<<<<<<<<<<<<<<<<<<<<<| 性能统计模块 |>>>>>>>>>>>>>>>>>>>>>>>>>>>>>
# -----------------------------------------------------------------------
class PerformanceTracker:
    """
    用于跟踪和记录性能数据的类。

    该类可以记录多个步骤的执行时间，并生成一个可视化的性能报告，
    报告内容包括每个步骤的名称、耗时和状态（成功/失败/异常）。
    """

    def __init__(self):
        """初始化一个空列表用于存储性能记录"""
        self.records = []

    def add_record(self, performance_data: dict[str, Any]) -> None:
        """
        添加一条性能记录。

        Parameters
        ----------
        performance_data : dict
            包含以下键的字典：
            - 'name' (str): 步骤名称；
            - 'duration' (str): 耗时字符串（格式如 "1m 30.5s" 或 "45.2s"）；
            - 'status' (str): 状态信息（如 "成功", "失败", "异常"）。
        """
        self.records.append(
            {
                "name": performance_data.get("name"),
                "duration": performance_data.get("duration"),  # 解析并转换为秒数
                "status": performance_data.get("status"),
            }
        )

    def execute_with_timing(self, func: Callable[..., Any], step_name: str) -> tuple:
        """
        执行指定函数并记录其执行时间及状态。

        该函数用于封装其他函数的执行过程，并记录执行耗时和结果状态。如果被调用的函数成功完成，
        则返回结果和包含执行信息的字典；如果发生异常，则捕获异常并返回失败的状态信息。

        Parameters
        ----------
        func : function
            要执行的目标函数对象。该函数应该不接受任何参数并且返回一个布尔值表示执行是否成功。
        step_name : str
            当前正在执行的步骤名称，用于日志输出和性能报告中的标识。

        Returns
        -------
        tuple
            包含两个元素的元组：
            - 第一个元素是目标函数的执行结果（布尔值）。
            - 第二个元素是一个字典，包含以下键：
                * 'name' (str): 步骤名称；
                * 'duration' (float): 步骤执行耗时（秒）；
                * 'status' (str): 状态，可以是 "成功"、"失败" 或 "异常"。
        """

        start_time = time.time()  # 记录开始时间戳
        try:
            result = func()  # 执行传入的函数

            duration = time.time() - start_time  # 计算执行耗时
            status = "成功" if result else "失败"  # 根据函数返回值判断执行结果

            # 返回函数执行结果和执行详情
            return result, {"name": step_name, "duration": duration, "status": status}

        except Exception as e:
            # 捕获所有异常，并计算耗时
            duration = time.time() - start_time

            # 输出异常信息
            console.print(f"❌ [{step_name}] 执行异常 - 耗时: {duration}, 错误: {e!s}")

            # 返回 False 和异常状态
            return False, {"name": step_name, "duration": duration, "status": "异常"}

    def generate_report(self) -> None:
        """
        生成可视化性能报告，并输出到控制台。

        使用 rich.Table 创建一个表格，显示所有记录的步骤名、耗时和状态，
        并在最后显示总耗时。
        """
        table = Table(title="性能报告")

        table.add_column("步骤", justify="left", style="cyan")
        table.add_column("耗时(秒)", justify="right", style="magenta")
        table.add_column("状态", justify="center")

        total_time = sum(record["duration"] for record in self.records)

        for record in self.records:
            table.add_row(
                record["name"],
                f"{record['duration']:.2f}s",
                f"[{'green' if record['status'] == '成功' else 'red' if record['status'] == '失败' else 'yellow'}]{record['status']}[/]",
            )

        table.add_row("总耗时", f"{total_time:.2f}s", "")

        console.print(table)


# ======================
# 工具函数
# ======================


def _kill_process_tree(pid: int) -> None:
    try:
        if system() == "Windows":
            subprocess.run(
                ["taskkill", "/F", "/T", "/PID", str(pid)],
                capture_output=True,
                timeout=5,
            )
        else:
            try:
                import psutil

                parent = psutil.Process(pid)
                for child in parent.children(recursive=True):
                    try:
                        child.kill()
                    except (psutil.NoSuchProcess, psutil.AccessDenied):
                        pass
                try:
                    parent.kill()
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    pass
            except ImportError:
                try:
                    os.kill(pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
    except Exception:
        pass


def run_command(
    command: list,
    success_msg: str,
    error_msg: str,
    process_name: str = "执行命令",
    encoding: str = "utf-8",
    timeout: int | None = None,
    cwd: str | None = None,
    env_extra: dict[str, str] | None = None,
) -> bool:
    """
    通用命令执行函数，用于运行系统命令并提供友好的控制台输出和状态提示

    Parameters
    ----------
    command : list
        要执行的命令，以列表形式提供（如：["cmd", "arg1"]）
    success_msg : str
        命令执行成功时显示的消息
    error_msg : str
        命令执行失败时显示的错误消息前缀
    process_name : str, optional
        正在执行的操作名称，用于状态栏显示, by default "执行命令"
    timeout : int, optional
        超时时间（秒），None 表示不限制, by default None
    cwd : str, optional
        子进程工作目录, by default None
    env_extra : dict[str, str], optional
        额外的环境变量，会与当前环境合并, by default None

    Returns
    -------
    bool
        命令是否成功执行完成

    Raises
    ------
    subprocess.CalledProcessError
        当子进程返回非零退出码时抛出此异常
    """
    env = None
    if env_extra is not None:
        env = os.environ.copy()
        env.update(env_extra)

    try:
        console.print(f"[dim]执行命令: {' '.join(command)}[/]")
        start_time = time.time()

        process = subprocess.Popen(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
            encoding=encoding,
            errors="ignore",
            cwd=cwd,
            env=env,
        )

        q: queue.Queue[str | None] = queue.Queue()

        def _reader():
            try:
                for line in process.stdout:
                    q.put(line)
            finally:
                q.put(None)

        reader_thread = threading.Thread(target=_reader, daemon=True)
        reader_thread.start()

        deadline = None
        if timeout is not None:
            deadline = time.monotonic() + timeout

        timed_out = False
        with console.status(f"[status]正在{process_name}..."):
            while True:
                remaining = None
                if deadline is not None:
                    remaining = deadline - time.monotonic()
                    if remaining <= 0:
                        timed_out = True
                        break
                try:
                    line = q.get(timeout=0.1 if remaining is None else min(0.1, remaining))
                except queue.Empty:
                    if process.poll() is not None and q.empty():
                        break
                    continue
                if line is None:
                    break
                if line:
                    console.print(f"[dim]{line.strip()}[/]")

        if timed_out:
            try:
                _kill_process_tree(process.pid)
            except Exception:
                try:
                    process.kill()
                except Exception:
                    pass
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                pass
            reader_thread.join(timeout=2)
            console.print(
                f"✗ {error_msg}: 命令执行超时 / Command timed out after {timeout}s",
                style="error",
            )
            return False

        reader_thread.join(timeout=2)
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            pass

        if process.returncode == 0:
            duration = time.time() - start_time
            if duration > 60:
                format_duration = (
                    f"{duration // 60:.0f}m {duration % 60:.1f}s"
                )
            else:
                format_duration = f"{duration:.2f}s"
            console.print(
                f"✓ {success_msg} [time](耗时: {format_duration})[/]", style="success"
            )
            return True

        raise subprocess.CalledProcessError(
            process.returncode, command, f"退出码: {process.returncode}"
        )

    except subprocess.CalledProcessError as e:
        console.print(f"✗ {error_msg}: {e}", style="error")
        return False


def delete_folder(folder_path):
    """
    删除指定文件夹及其所有内容

    Parameters
    ----------
    folder_path : str or Path
        要删除的文件夹路径

    Returns
    -------
    bool
        - `True` 表示删除成功；
        - `False` 表示删除失败。
    """
    path = Path(folder_path)

    if not path.exists():
        print(f"⚠️ 文件夹不存在：{path}")
        return True  # 不存在也视为“已删除”

    try:
        shutil.rmtree(path)  # 删除整个目录树
        print(f"✓ 已删除文件夹：{path}")
        return True
    except Exception as e:
        print(f"✗ 删除失败：{e}")
        return False


if __name__ == "__main__":
    if len(sys.argv) > 1:
        command = sys.argv[1]
        if command == "clean":
            delete_folder("dist")
