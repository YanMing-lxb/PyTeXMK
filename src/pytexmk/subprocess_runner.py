import logging
import subprocess
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

    def run_command(
        self,
        command: list,
        out_files: str,
        aux_files: str,
        program_name: str = "执行命令",
        stdout_path: str | None = None,
    ) -> bool:
        stdout_lines = []
        try:
            console.print(_("[bold]运行命令: [/bold]") + f"[cyan]{' '.join(command)}")
            start_time = time.time()

            if stdout_path is not None:
                output_dir = Path(stdout_path).parent
                if not output_dir.exists():
                    output_dir.mkdir(parents=True, exist_ok=True)
                with open(stdout_path, "w", encoding="utf-8") as stdout_file:
                    process = subprocess.Popen(
                        command,
                        stdout=stdout_file,
                        stderr=subprocess.STDOUT,
                        text=True,
                        bufsize=1,
                        encoding="utf-8",
                    )
                    with console.status(f"[status]正在{program_name}..."):
                        process.wait()
            else:
                process = subprocess.Popen(
                    command,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                    bufsize=1,
                    encoding="utf-8",
                )
                with console.status(f"[status]正在{program_name}..."):
                    while True:
                        output = process.stdout.readline()
                        if not output and process.poll() is not None:
                            break
                        if output:
                            stdout_lines.append(output)
                            console.print(f"[dim]{output.strip()}[/]")

            if process.returncode == 0:
                console.print(
                    f"[√] 运行 {program_name} 成功 "
                    f"[time](耗时: {self._format_duration(time.time() - start_time)})[/]",
                    style="success",
                )
                return True

            else:
                raise subprocess.CalledProcessError(process.returncode, command)

        except subprocess.CalledProcessError as e:
            self.logger.error(
                _("%(args)s 编译失败,请查看日志文件以获取详细信息: ")
                % {"args": program_name}
                + f"{self.auxdir}{self.project_name + '.log' if not self.latexdiff else '/'}"
            )

            self.MRO.move_specific_files(aux_files, ".", self.auxdir)
            self.MRO.move_specific_files(out_files, ".", self.outdir)

            stdout = "".join(stdout_lines)
            raise SubprocessFailedError(
                command=command,
                exit_code=e.returncode,
                stdout=stdout,
                stderr="",
            )
