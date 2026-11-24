import sys

from rich.console import Console
from rich.theme import Theme

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


class _SwappableStream:
    """rich Console 只持有一个流引用；``--json`` 时要整体切到 stderr。

    ``Console`` 在构造时就固定了 ``file``，事后给 ``console.file`` 赋值没有 setter，
    所以这里包一层代理：所有模块共享同一个 ``console``，切目标只改代理内部引用。

    没有显式切换时按 ``sys.stdout`` **动态**解析：rich 原本就是写时取 ``sys.stdout``，
    若在导入期就钉住真实流，``contextlib.redirect_stdout`` / pytest ``capsys`` 之类
    重定向会全部失效（rich 输出跑到原始终端，调用方拿不到）。
    """

    def __init__(self, override=None):
        self._override = override

    @property
    def _target(self):
        return self._override if self._override is not None else sys.stdout

    def switch_to(self, target) -> None:
        self._override = target

    def restore(self) -> None:
        """回到“跟随 ``sys.stdout``”的默认状态。"""
        self._override = None

    def write(self, text) -> None:
        self._target.write(text)

    def flush(self) -> None:
        self._target.flush()

    def isatty(self) -> bool:
        return bool(getattr(self._target, "isatty", lambda: False)())

    def fileno(self) -> int:
        return self._target.fileno()

    @property
    def encoding(self) -> str:
        return getattr(self._target, "encoding", "utf-8") or "utf-8"

    @property
    def errors(self) -> str:
        return getattr(self._target, "errors", "strict") or "strict"

    def close(self) -> None:  # rich 退出时可能调用，代理本身不能关掉真实流
        return None


console_stream = _SwappableStream()
console = Console(theme=custom_theme, legacy_windows=False, file=console_stream)

