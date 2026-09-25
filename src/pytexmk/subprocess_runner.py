import logging
import subprocess
import sys
import time
from pathlib import Path

from pytexmk.file_ops import FileMoveRemoveManager
from pytexmk.language import set_language
from pytexmk.ui_theme import console

_ = set_language("subprocess_runner")


class SubprocessFailedError(Exception):
    def __init__(self, command, exit_code, stdout, stderr):
        self.command = command
        self.exit_code = exit_code
        self.stdout = stdout
        self.stderr = stderr
        super().__init__(f"Command {command} failed with exit code {exit_code}")


class MySubProcess:
    def __init__(
        self, outdir, auxdir, project_name: str | None = None, latexdiff: bool = False
    ):
        self.logger = logging.getLogger(__name__)
        self.project_name = project_name
        self.latexdiff = latexdiff
        self.outdir = outdir
        self.auxdir = auxdir
        self.MRO = FileMoveRemoveManager()

    def _format_duration(self, seconds: float) -> str:
        if seconds > 60:
            return f"{seconds // 60:.0f}m {seconds % 60:.2f}s"
        return f"{seconds:.4f}s"

    @staticmethod
    def _terminate_process(proc: subprocess.Popen) -> None:
        """安全终止子进程及其后代，跨平台兼容。

        Windows: LaTeX 工具链（latexmk/biber/latexdiff）常产生子进程，
        单纯 proc.terminate() 只杀父进程，会留下孤儿进程。
        这里优先用 taskkill /T /F 杀掉整个进程树。
        POSIX: 先 SIGTERM，再 SIGKILL 兜底。
        """
        if proc.poll() is not None:
            return  # 已退出，无需处理

        try:
            if sys.platform == "win32":
                # taskkill 杀掉进程树，/F 强制
                subprocess.run(
                    ["taskkill", "/T", "/F", "/PID", str(proc.pid)],
                    capture_output=True,
                    timeout=5,
                    check=False,
                )
            else:
                # POSIX: 先温和终止，500ms 后仍存活则强杀
                proc.terminate()
                try:
                    proc.wait(timeout=0.5)
                except subprocess.TimeoutExpired:
                    proc.kill()
                    proc.wait(timeout=2)
        except (subprocess.TimeoutExpired, OSError):
            # 终止过程本身出错（进程已死、权限不足等），忽略
            try:
                proc.kill()
            except OSError:
                pass

    def run_command(
        self,
        command: list,
        out_files: str,
        aux_files: str,
        program_name: str = "执行命令",
        stdout_path: str | None = None,
    ) -> bool:
        stdout_text = ""
        start_time = time.time()
        process: subprocess.Popen | None = None
        try:
            console.print(_("[bold]运行命令: [/bold]") + f"[cyan]{' '.join(command)}")

            if stdout_path is not None:
                # 输出重定向到文件（latexdiff 等场景）
                output_dir = Path(stdout_path).parent
                if not output_dir.exists():
                    output_dir.mkdir(parents=True, exist_ok=True)
                with open(stdout_path, "w", encoding="utf-8") as stdout_file:
                    process = subprocess.Popen(
                        command,
                        stdout=stdout_file,
                        stderr=subprocess.STDOUT,
                        text=True,
                        encoding="utf-8",
                        errors="replace",
                        cwd=Path.cwd(),
                    )
                    try:
                        with console.status(f"[status]正在{program_name}..."):
                            process.wait()
                    except KeyboardInterrupt:
                        console.print()  # 换行避免覆盖 status spinner
                        console.print(
                            _("[yellow]收到中断信号，正在终止 %(prog)s...[/yellow]")
                            % {"prog": program_name}
                        )
                        self._terminate_process(process)
                        raise
                # 重定向模式：从文件读回 stdout 文本
                try:
                    stdout_text = Path(stdout_path).read_text(
                        encoding="utf-8", errors="replace"
                    )
                except OSError:
                    stdout_text = ""
            else:
                # 实时模式：stdout 合并 stderr 并实时显示
                process = subprocess.Popen(
                    command,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                    bufsize=1,
                    encoding="utf-8",
                    errors="replace",
                    cwd=Path.cwd(),
                )
                stdout_lines: list[str] = []
                try:
                    with console.status(f"[status]正在{program_name}..."):
                        while True:
                            output = process.stdout.readline()
                            if not output and process.poll() is not None:
                                break
                            if output:
                                stdout_lines.append(output)
                                console.print(f"[dim]{output.strip()}[/]")
                except KeyboardInterrupt:
                    console.print()  # 换行避免覆盖 status spinner
                    console.print(
                        _("[yellow]收到中断信号，正在终止 %(prog)s...[/yellow]")
                        % {"prog": program_name}
                    )
                    self._terminate_process(process)
                    # 尝试读尽剩余输出（避免 SIGINT 丢失最后几行）
                    try:
                        rest, _unused = process.communicate(timeout=2)
                        if rest:
                            stdout_lines.append(rest)
                    except (subprocess.TimeoutExpired, ValueError):
                        pass
                    stdout_text = "".join(stdout_lines)
                    raise
                stdout_text = "".join(stdout_lines)

            # 正常分支：按 returncode 判断成败
            if process.returncode == 0:
                console.print(
                    _("[√] 运行 %(prog)s 成功 [time](耗时: %(dur)s)[/]")
                    % {
                        "prog": program_name,
                        "dur": self._format_duration(time.time() - start_time),
                    },
                    style="success",
                )
                return True

            # 失败分支：统一处理
            self.MRO.move_specific_files(aux_files, ".", self.auxdir)
            self.MRO.move_specific_files(out_files, ".", self.outdir)

            if not self.latexdiff:
                log_path = Path(self.auxdir) / f"{self.project_name}.log"
                log_prompt = str(log_path)
                try:
                    if log_path.exists():
                        line_count = sum(1 for _ in log_path.open("rb"))
                        log_prompt = f"{log_prompt}:{line_count}"
                except OSError:
                    pass
            else:
                log_prompt = str(Path(self.auxdir))

            self.logger.error(
                _("%(prog)s 编译失败, 请查看日志文件以获取详细信息: %(log)s")
                % {"prog": program_name, "log": log_prompt}
            )
            raise SubprocessFailedError(
                command=command,
                exit_code=process.returncode,
                stdout=stdout_text,
                stderr="",
            )

        except SubprocessFailedError:
            raise
        except subprocess.TimeoutExpired:
            self.logger.error(_("%(prog)s 执行超时: ") % {"prog": program_name})
            if process is not None:
                self._terminate_process(process)
            raise SubprocessFailedError(
                command=command,
                exit_code=-1,
                stdout=stdout_text,
                stderr=_("执行超时"),
            )
        except OSError as e:
            self.logger.error(
                _("%(prog)s 无法启动: %(err)s") % {"prog": program_name, "err": str(e)}
            )
            raise SubprocessFailedError(
                command=command,
                exit_code=-1,
                stdout=stdout_text,
                stderr=str(e),
            )
