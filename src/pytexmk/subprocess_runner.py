import logging
import queue
import shutil
import subprocess
import sys
import threading
import time
from contextlib import suppress
from pathlib import Path
from typing import Self

from rich.text import Text

from pytexmk.file_ops import FileMoveRemoveManager
from pytexmk.language import set_language
from pytexmk.runtime_env import child_env, ensure_writable_temp, external_process_scope
from pytexmk.timing import get_text_len, total_len
from pytexmk.ui_theme import console

_ = set_language("subprocess_runner")

#: “运行命令: ” 前缀。宽度按显示宽度算（中文按 2 格），见 pytexmk.timing.get_text_len。
_COMMAND_PREFIX = "运行命令: "

#: 需要加引号的字符：空白与双引号。加引号只是为了让“带空格的路径”在打印时一眼可辨，
#: 不承担任何 shell 转义职责（折行块仅供参考，不保证可粘贴执行）。
_NEED_QUOTE_CHARS = frozenset(' \t"')

#: 读取线程的轮询粒度：主线程靠它定期检查"子进程是否已退出 / 是否长时间没输出"。
_READER_POLL_SECONDS = 0.25
#: 输出队列上限。宽限期到点后主线程不再出队，读线程不能把孙进程的后续输出
#: 无限堆进内存；队列满时读线程自然阻塞，形成管道背压。
_OUTPUT_QUEUE_MAX = 1024
#: 连续多少秒没有任何输出，才提示一次"仍在运行"（安静模式下这是唯一的心跳）。
_STALL_NOTICE_SECONDS = 20.0
#: 子进程已退出、但输出管道仍未关闭（它派生的进程还握着写端）时，最多再等多久。
#: 两条执行路径（流式合并 / stdout 重定向）共用这个期限；计时从**检测到进程退出**
#: 开始，而不是从"第一次读空"开始，否则孙进程持续输出会把期限无限推迟。
_EOF_GRACE_SECONDS = 2.0


def _announce_running(program_name: str) -> None:
    """"正在跑"提示：一行静态文字，**不建** rich 的 Live/status。

    旧实现用 ``console.status()`` 打转圈：Live 有一条每 100ms 写一次终端的刷新
    线程，而它写终端时是持着 Live 的锁的。只要那次写被阻塞（Windows 控制台被
    鼠标选中进入标记模式、终端渲染被挂起、输出流卡住），主线程退出 spinner 时
    就会永远等锁 —— 现象正是"卡在正在编译、一个字节也不再输出"，且只有安静
    模式会踩到（非安静模式压根不建 Live）。这里改成普通的一行 print。
    """
    console.print(_("正在%(prog)s…") % {"prog": program_name}, style="status", markup=False)


def _pump_stream(stream, lines: queue.Queue[str | None]) -> None:
    """在独立线程里把 ``stream`` 逐行读进队列，读完后放一个 EOF 哨兵。

    流式路径传 ``process.stdout``，重定向路径传 ``process.stderr``；两者都可能被
    子进程派生的孙进程继承，因此读线程与主循环必须解耦，主循环才能按"进程是否已
    退出"独立做有界收尾。
    """
    try:
        for line in stream:
            lines.put(line)
    except OSError, ValueError:
        # 进程被终止 / 管道被关：当作 EOF，不把异常抛到线程外面去
        pass
    finally:
        lines.put(None)


def _quote_arg(arg) -> str:
    """给单个参数加引号（仅在需要时），让打印出来的命令不把路径切成两段。

    注意：这里只做**展示层**的加引号，不承担 shell 转义职责；折行块仅供阅读，
    不承诺可原样粘贴执行（见 ``format_command`` / ``wrap_command``）。
    """
    text = str(arg)
    if not text:
        return '""'
    if any(ch in _NEED_QUOTE_CHARS for ch in text):
        return '"' + text.replace('"', '\\"') + '"'
    return text


def _relative_to_cwd(value: str, cwd: Path) -> str:
    """把 cwd 之内的绝对路径缩成相对路径（只为打印省宽度，不改变实际执行参数）。"""
    if not value:
        return value
    try:
        path = Path(value)
    except OSError, ValueError:
        return value
    if not path.is_absolute():
        return value
    try:
        if path.is_relative_to(cwd):
            return path.relative_to(cwd).as_posix() or value
    except OSError, ValueError:
        return value
    return value


def shorten_command(command, cwd: Path) -> list[str]:
    """把 ``cwd`` 内的绝对路径参数改成相对形式，供“运行命令”展示。

    只做展示层缩写：``-output-directory=C:\\proj\\Auxiliary`` → ``-output-directory=Auxiliary``。
    相对路径只有在用户**在项目根目录**执行时与绝对路径等价，因此仅当实际运行目录
    就是当前目录时才启用（``cwd`` 与 ``Path.cwd()`` 一致），其余情况仍打印绝对路径。
    """
    try:
        if Path(cwd).resolve() != Path.cwd().resolve():
            return [str(part) for part in command]
    except OSError:
        return [str(part) for part in command]

    shortened: list[str] = []
    for part in command:
        text = str(part)
        if text.startswith("-") and "=" in text:
            # 形如 -output-directory=<path> / --dir=<path>：只缩右半边的路径
            flag, _, value = text.partition("=")
            shortened.append(f"{flag}={_relative_to_cwd(value, Path.cwd())}")
        else:
            shortened.append(_relative_to_cwd(text, Path.cwd()))
    return shortened


def format_command(command) -> str:
    """把 argv 列表拼成一条可读命令（只为展示，不做任何 shell 转义）。

    带空格或双引号的参数加双引号，避免“路径里的空格”把一条参数看成两个。
    """
    parts = [_quote_arg(part) for part in command]
    return " ".join(parts)


def _split_command(text: str) -> list[str]:
    """按空格切分命令，但保留双引号内部的空格（引号本身留在分片里）。"""
    parts: list[str] = []
    buf: list[str] = []
    in_quote = False
    for ch in text:
        if ch == '"':
            in_quote = not in_quote
            buf.append(ch)
        elif ch == " " and not in_quote:
            if buf:
                parts.append("".join(buf))
                buf.clear()
        else:
            buf.append(ch)
    if buf:
        parts.append("".join(buf))
    return parts


def _split_by_width(text: str, width: int) -> list[str]:
    """把一段文本按显示宽度切成若干片（超长参数专用的兜底手段）。

    优先在路径分隔符（``\\`` / ``/``）后断开，避免把目录名或中文词切成两半；
    找不到位置合适的断点时，才按显示宽度硬切。
    """
    chunks: list[str] = []
    buf: list[str] = []
    used = 0
    last_sep = -1
    for ch in text:
        char_width = get_text_len(ch)
        if buf and used + char_width > width:
            cut = len(buf)
            if last_sep > 0:
                head_width = sum(get_text_len(c) for c in buf[: last_sep + 1])
                if head_width >= width // 2:  # 断点太靠前就放弃，免得切出碎片行
                    cut = last_sep + 1
            chunks.append("".join(buf[:cut]))
            buf = buf[cut:]
            used = sum(get_text_len(c) for c in buf)
            last_sep = max((i for i, c in enumerate(buf) if c in "\\/"), default=-1)
        buf.append(ch)
        used += char_width
        if ch in "\\/":
            last_sep = len(buf) - 1
    if buf:
        chunks.append("".join(buf))
    return chunks


def wrap_command(text: str, width: int, indent: str) -> list[str]:
    """按显示宽度把命令折行，保证每行不超过 ``width`` 列。

    优先在参数之间断行；只有某个参数本身就超过可用宽度时（例如跨盘/深层绝对路径），
    才按显示宽度把该参数切成几片——折行块只用于阅读和对齐，不承诺可粘贴执行。
    ``indent`` 的宽度即首行前缀宽度，因此首行拼上前缀后同样不超过 ``width``。

    返回的行里，首行不带缩进（调用方自己拼接前缀），其余行已带 ``indent``。
    """
    parts = _split_command(text)
    if not parts:
        return [text]

    indent_width = get_text_len(indent)
    room = max(width - indent_width, 1)
    rows: list[str] = []
    current = ""
    for part in parts:
        candidate = f"{current} {part}" if current else part
        if get_text_len(candidate) <= room:
            current = candidate
            continue
        if current:
            rows.append(current)
            current = ""
        for chunk in _split_by_width(part, room):
            if current:
                rows.append(current)
            current = chunk
    if current:
        rows.append(current)
    return [rows[0]] + [indent + row for row in rows[1:]]


def print_command(command, cwd: Path | None = None) -> None:
    """打印本次运行命令：按 ``total_len`` 对齐折行，每行都不超过横幅宽度。

    折行块仅供阅读定位用（例如复制到日志里讨论），不保证可原样粘贴执行。
    ``cwd`` 为本条命令的实际工作目录：仅当它就是当前目录时，才把参数里的绝对路径
    缩成相对路径（否则打印出来的相对路径在别处不可用，宁可保持绝对路径）。
    """
    display = shorten_command(command, cwd or Path.cwd())
    text = format_command(display)
    rows = wrap_command(text, total_len, " " * get_text_len(_COMMAND_PREFIX))

    first = Text(_COMMAND_PREFIX, style="bold")
    first.append(rows[0], style="cyan")
    console.print(first)
    for row in rows[1:]:
        console.print(Text(row, style="cyan"))


class SubprocessFailedError(Exception):
    def __init__(
        self, command, exit_code, stdout, stderr, output_truncated: bool = False
    ):
        self.command = command
        self.exit_code = exit_code
        self.stdout = stdout
        self.stderr = stderr
        #: 是否因为孙进程握着管道而提前停止读取（此时 stdout/stderr 可能不完整）。
        self.output_truncated = output_truncated
        super().__init__(f"Command {command} failed with exit code {exit_code}")

    @classmethod
    def launch_failed(cls, command: list, stdout: str, error: OSError) -> Self:
        """子进程无法启动（命令不存在、权限不足等）。"""
        return cls(command=command, exit_code=-1, stdout=stdout, stderr=str(error))


class MySubProcess:
    def __init__(
        self,
        outdir,
        auxdir,
        project_name: str | None = None,
        stream_output: bool = True,
    ):
        self.logger = logging.getLogger(__name__)
        self.project_name = project_name
        # ``-nq`` 的唯一职责：把子进程（TeX/biber/makeindex…）的输出实时打到终端。
        # 安静模式只留一行“运行命令”与成功/失败结论，输出仍会被读完并留存，
        # 失败诊断照样能拿到全文（不能因为不显示就停止读取，否则管道会阻塞）。
        self.stream_output = stream_output
        self.outdir = outdir
        self.auxdir = auxdir
        self.MRO = FileMoveRemoveManager()
        #: 上一次外部命令是否因为"进程已退出、管道仍被握着"而提前停止读取。
        #: 成功/失败两条路径都可读；失败时会带进 SubprocessFailedError。
        self.last_output_truncated = False

    def _format_duration(self, seconds: float) -> str:
        if seconds > 60:
            return f"{seconds // 60:.0f}m {seconds % 60:.2f}s"
        return f"{seconds:.4f}s"

    @staticmethod
    def _terminate_process(proc: subprocess.Popen) -> None:
        """安全终止子进程及其后代，跨平台兼容。

        Windows: LaTeX 工具链（latexmk/biber/makeindex）常产生子进程，
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
        except subprocess.TimeoutExpired, OSError:
            # 终止过程本身出错（进程已死、权限不足等），忽略
            with suppress(OSError):
                proc.kill()

    def run_command(
        self,
        command: list,
        out_files: list[str],
        aux_files: list[str],
        program_name: str = "执行命令",
        stdout_path: str | None = None,
        cwd: Path | None = None,
        log_hint: bool = True,
    ) -> bool:
        """执行外部命令。

        ``log_hint``：失败时是否提示"查看 LaTeX .log"。索引工具（makeindex /
        xindy / makeglossaries）的错误只出现在它们自己的输出里，不会进 .log，
        对它们提示 .log 会把真正原因藏起来，调用方应传 False。
        """
        start_time = time.time()
        run_cwd = cwd or Path.cwd()
        self.last_output_truncated = False
        # 外部程序（TeX 引擎等）必须拿到净化后的环境，否则打包目录里的同名库
        # 会被优先加载（见 pytexmk.runtime_env 的说明）。
        env = child_env()
        # 部分受限环境里 Python 与它启动的 TeX 工具都写不了 %TEMP%：xelatex 会在
        # shipout 阶段被杀掉（日志截断在 `[1`、留下 main.synctex(busy)），xindy 也会
        # 因为建不出临时文件报 Win32 267。这里探测一次，不可写就改用项目内目录。
        env, _temp_override = ensure_writable_temp(env, run_cwd / ".pytexmk-tmp")
        temp_fallback = Path(_temp_override) if _temp_override else None
        if _temp_override:
            self.logger.warning(
                _("系统临时目录不可写，本次编译改用 %(dir)s")
                % {"dir": _temp_override}
            )
        try:
            print_command(command, run_cwd)
            if stdout_path is not None:
                process, stdout_text, stderr_text = self._execute_redirected(
                    command, run_cwd, env, stdout_path, program_name
                )
            else:
                process, stdout_text, stderr_text = self._execute_streaming(
                    command, run_cwd, env, program_name
                )

            exit_code = process.returncode
            if exit_code == 0:
                console.print(
                    _("[√] 运行 %(prog)s 成功 [time](耗时: %(dur)s)[/]")
                    % {
                        "prog": program_name,
                        "dur": self._format_duration(time.time() - start_time),
                    },
                    style="success",
                )
                return True

            self._raise_failure(
                command=command,
                program_name=program_name,
                out_files=out_files,
                aux_files=aux_files,
                log_hint=log_hint,
                stdout_text=stdout_text,
                stderr_text=stderr_text,
                # 子进程在兜底等待内仍未退出时 returncode 是 None：按 -1 报失败，
                # 不要把 "None" 拼进提示里。
                returncode=-1 if exit_code is None else exit_code,
            )
        except SubprocessFailedError:
            raise
        except OSError as e:
            self.logger.error(
                _("%(prog)s 无法启动: %(err)s") % {"prog": program_name, "err": str(e)}
            )
            raise SubprocessFailedError.launch_failed(command, "", e) from e
        finally:
            # 兜底目录是本工具创建的临时工作区；每次外部命令结束后清掉，
            # 避免受限环境里越积越多。用户系统自己的 TEMP 不归我们清理。
            if temp_fallback is not None:
                shutil.rmtree(temp_fallback, ignore_errors=True)

    def _execute_redirected(
        self,
        command: list,
        run_cwd: Path,
        env: dict,
        stdout_path: str,
        program_name: str,
    ) -> tuple[subprocess.Popen, str, str]:
        """stdout 重定向到文件、stderr 走管道的执行分支。"""
        # 输出重定向到文件（调用方要求把工具 stdout 落盘时）。
        # 关键：stderr **不能**并入这个文件。stdout 往往是工具产出的正式内容
        # （源码/清单），而 MiKTeX 的 log4cxx 告警（数据目录不可写时必有）走
        # stderr；一旦合并，产物第一行就是 "log4cxx: ..."，后续编译/解析立即报错。
        # 这里改成单独收 stderr 到管道，既不污染产物，又能在失败时把真正原因
        # 带进异常。
        output_dir = Path(stdout_path).parent
        if not output_dir.exists():
            output_dir.mkdir(parents=True, exist_ok=True)
        target = Path(stdout_path)
        # 先写同目录临时文件，成功后再原子替换目标：旧实现直接以 "w" 打开目标，
        # 若目标恰好是某个输入文件（输出==输入）或进程中途失败，原文件已经被
        # 截断成 0 字节，无法恢复。
        tmp_path = target.with_name(f".{target.name}.{time.time_ns()}.tmp")
        stdout_text = ""
        stderr_text = ""
        try:
            with tmp_path.open("w", encoding="utf-8") as stdout_file:
                with external_process_scope():
                    process = subprocess.Popen(
                        command,
                        stdout=stdout_file,
                        stderr=subprocess.PIPE,
                        text=True,
                        encoding="utf-8",
                        errors="replace",
                        cwd=run_cwd,
                        env=env,
                    )
                try:
                    _announce_running(program_name)
                    # stdout 已重定向到文件，stderr 用与流式路径同一套有界收尾：
                    # 子进程退出后，孙进程即使继续握着 stderr 也不能无限等。
                    stderr_text, _truncated = self._drain_stream(
                        process,
                        process.stderr,
                        program_name,
                        display=False,
                        heartbeat=True,
                    )
                except KeyboardInterrupt:
                    self._interrupt_process(process, program_name)
                    raise
            # 重定向模式：从文件读回 stdout 文本
            try:
                stdout_text = tmp_path.read_text(encoding="utf-8", errors="replace")
            except OSError:
                stdout_text = ""
            if process.returncode == 0:
                try:
                    self._publish_redirected(tmp_path, target)
                except OSError as exc:
                    message = _("无法发布重定向输出: ") + f"{target}: {exc}"
                    self.logger.error(message)
                    raise SubprocessFailedError(
                        command, -1, stdout_text, message
                    ) from exc
            if stderr_text.strip():
                # 只进 debug 通道：正常流程不必把工具噪声打到终端，
                # 但 -vb 之外的排查（日志文件）仍能看到完整原因。
                self.logger.debug("%s stderr:\n%s", program_name, stderr_text.strip())
            return process, stdout_text, stderr_text
        finally:
            # 成功发布后 tmp 已被 replace；失败、Ctrl+C、任意异常时
            # 这里兜底清掉半成品，输出目录不会留下 .<name>.<ns>.tmp。
            with suppress(OSError):
                tmp_path.unlink(missing_ok=True)

    @staticmethod
    def _publish_redirected(source: Path, target: Path) -> None:
        """发布完整文件，Windows 后台进程仍持有 stdout 时用独立副本。"""
        try:
            source.replace(target)
            return
        except OSError as exc:
            if getattr(exc, "winerror", None) != 32:
                raise

        # Windows 上后台进程可能仍持有源文件句柄。先复制到另一个同目录
        # 临时文件，最终仍以原子替换发布，避免覆盖写截断上一次的结果。
        staged = source.with_suffix(".publish.tmp")
        try:
            shutil.copyfile(source, staged)
            staged.replace(target)
        finally:
            with suppress(OSError):
                staged.unlink(missing_ok=True)

    def _execute_streaming(
        self, command: list, run_cwd: Path, env: dict, program_name: str
    ) -> tuple[subprocess.Popen, str, str]:
        """stdout 合并 stderr：非安静模式逐行显示，安静模式只留一行静态提示。"""
        with external_process_scope():
            process = subprocess.Popen(
                command,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
                encoding="utf-8",
                errors="replace",
                cwd=run_cwd,
                env=env,
            )
        if not self.stream_output:
            _announce_running(program_name)
        stdout_text, _truncated = self._drain_stream(
            process,
            process.stdout,
            program_name,
            display=self.stream_output,
        )
        return process, stdout_text, ""

    def _drain_stream(
        self,
        process: subprocess.Popen,
        stream,
        program_name: str,
        *,
        display: bool,
        heartbeat: bool = True,
    ) -> tuple[str, bool]:
        """把子进程输出读干净，但**不允许**无限期地等下去。

        旧写法只在"这一轮队列为空"时才检查 ``process.poll()``：只要子进程派生的
        孙进程持续写 stdout，主线程就一直命中"有新行"分支，永远看不到父进程已经
        退出；``_EOF_GRACE_SECONDS`` 的钟也就永远不启动。现在把两件事解耦：

          * 每一轮（无论有没有新行）都先检查进程是否退出，退出即开始计宽限期；
          * 宽限期到点就停止读取，即使队列里还有孙进程写来的行；
          * 只有**进程仍在运行**且长时间没输出时才打心跳，已退出的进程不再伪造
            "仍在运行"的提示；
          * 流式（stdout 合并 stderr）与重定向（只读 stderr）共用这套收尾逻辑。

        返回 ``(已收集文本, 是否因宽限期截断)``；截断状态同时写入
        ``self.last_output_truncated``，失败时会带进 ``SubprocessFailedError``。
        """
        lines: queue.Queue[str | None] = queue.Queue(maxsize=_OUTPUT_QUEUE_MAX)
        threading.Thread(
            target=_pump_stream,
            args=(stream, lines),
            name="pytexmk-output",
            daemon=True,
        ).start()

        collected: list[str] = []
        last_output = time.monotonic()
        exited_at: float | None = None
        next_notice = _STALL_NOTICE_SECONDS
        eof = False
        truncated = False
        empty = object()
        try:
            while True:
                try:
                    item = lines.get(timeout=_READER_POLL_SECONDS)
                except queue.Empty:
                    item = empty

                # 关键次序：先看进程是否已退出，再决定要不要消费新行。
                # 孙进程持续输出时，旧实现会把这里拖到管道真正 EOF。
                now = time.monotonic()
                if exited_at is None and process.poll() is not None:
                    exited_at = now
                # EOF 是真正的终点：即使恰好跨过宽限点，也不应该误报截断。
                if item is None:  # 读线程读到 EOF
                    eof = True
                    break
                if (
                    exited_at is not None
                    and now - exited_at >= _EOF_GRACE_SECONDS
                ):
                    truncated = True
                    break
                if item is not empty:
                    collected.append(item)
                    last_output = now
                    if display:
                        console.print(item.rstrip("\n"), style="dim", markup=False)
                    continue

                # 本轮没有任何新输出
                if exited_at is not None:
                    continue
                idle = now - last_output
                if heartbeat and idle >= next_notice:
                    console.print(
                        _("已 %(sec)d 秒没有输出，%(prog)s 仍在运行（加 -nq 可看实时日志）")
                        % {"sec": int(idle), "prog": program_name},
                        style="warning",
                        markup=False,
                    )
                    next_notice = idle + _STALL_NOTICE_SECONDS
        except KeyboardInterrupt:
            self._interrupt_process(process, program_name)
            self._drain_after_interrupt(lines, collected)
            raise

        if not eof:
            self.last_output_truncated = True
            self.logger.debug("%s: 子进程已退出但输出管道未关闭，停止等待", program_name)
            console.print(
                _(
                    "%(prog)s 已结束，但输出管道仍未关闭（可能派生了后台进程），"
                    "已停止等待；后续输出可能未收集"
                )
                % {"prog": program_name},
                style="warning",
                markup=False,
            )
        # EOF 之后子进程通常已经退出；这里补一次有界 wait，确保 returncode 有值，
        # 但绝不无条件阻塞（管道被第三方持有时不代表进程还在跑）。
        try:
            process.wait(timeout=_EOF_GRACE_SECONDS)
        except subprocess.TimeoutExpired:
            pass
        return "".join(collected), truncated

    def _drain_after_interrupt(
        self, lines: queue.Queue[str | None], collected: list[str]
    ) -> None:
        """Ctrl+C 收尾：把已经缓冲的输出取完，最多等 ``_EOF_GRACE_SECONDS``。"""
        deadline = time.monotonic() + _EOF_GRACE_SECONDS
        while time.monotonic() < deadline:
            try:
                item = lines.get(timeout=0.2)
            except queue.Empty:
                continue
            if item is None:
                return
            collected.append(item)

    def _interrupt_process(self, process: subprocess.Popen, program_name: str) -> None:
        """Ctrl+C 的统一处理：换行、提示并终止进程树。"""
        console.print()  # 换行，避免与上一行提示挤在一起
        console.print(
            _("[yellow]收到中断信号，正在终止 %(prog)s...[/yellow]")
            % {"prog": program_name}
        )
        self._terminate_process(process)

    def _raise_failure(
        self,
        *,
        command: list,
        program_name: str,
        out_files: list[str],
        aux_files: list[str],
        log_hint: bool,
        stdout_text: str,
        stderr_text: str,
        returncode: int,
    ) -> None:
        """失败分支：搬回产物、拼日志提示并抛 SubprocessFailedError。"""
        self.MRO.move_specific_files(aux_files, ".", self.auxdir)
        self.MRO.move_specific_files(out_files, ".", self.outdir)

        if log_hint:
            log_path = Path(self.auxdir) / f"{self.project_name}.log"
            log_prompt = str(log_path)
            try:
                if log_path.exists():
                    # 3.15：Path.read_bytes() + bytes.count()，一次读入代替逐行 next()，
                    # 大日志（编译失败时常见几十万行）下速度更快，也无须手动管理文件句柄。
                    line_count = log_path.read_bytes().count(b"\n") + 1
                    log_prompt = f"{log_prompt}:{line_count}"
            except OSError:
                pass
        else:
            log_prompt = str(Path(self.auxdir))

        if log_hint:
            self.logger.error(
                _("%(prog)s 编译失败, 请查看日志文件以获取详细信息: %(log)s")
                % {"prog": program_name, "log": log_prompt}
            )
        else:
            # 索引类工具没有 LaTeX 日志可看，只留程序名与退出码
            self.logger.error(
                _("%(prog)s 执行失败 (退出码 %(code)s)")
                % {"prog": program_name, "code": returncode}
            )
        raise SubprocessFailedError(
            command=command,
            exit_code=returncode,
            stdout=stdout_text,
            stderr=stderr_text,
            output_truncated=self.last_output_truncated,
        )
