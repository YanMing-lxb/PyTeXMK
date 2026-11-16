"""`--watch` 轮询监视（3.1，不引入 watchdog 依赖）。

用 mtime+size 快照判断源码是否变化；每次变化后等待 400ms 去抖，避免编辑器
“先删后写”导致连续触发。轮询间隔 1s，CPU 开销可忽略。
"""

from __future__ import annotations

import time
from pathlib import Path

from ..language import set_language
from ..ui_theme import console

_ = set_language("cli_workflow")

_SOURCE_SUFFIXES = {".tex", ".bib", ".bst", ".cls", ".sty", ".def", ".clo", ".cfg", ".ist", ".tikz", ".bbx", ".cbx"}
_SKIP_DIRS = {"Build", "Auxiliary", "Submission", ".git", ".venv", "node_modules"}


def _snapshot(root: Path) -> dict[str, tuple[int, int]]:
    """记录源码文件的 (mtime_ns, size)。"""
    result: dict[str, tuple[int, int]] = {}
    for path in root.rglob("*"):
        if not path.is_file() or path.suffix.lower() not in _SOURCE_SUFFIXES:
            continue
        parts = set(path.relative_to(root).parts[:-1])
        if parts & _SKIP_DIRS or any(p.startswith(".") for p in parts):
            continue
        try:
            stat = path.stat()
        except OSError:
            continue
        result[path.relative_to(root).as_posix()] = (stat.st_mtime_ns, stat.st_size)
    return result


def watch_loop(args) -> None:
    """先编译一次，然后阻塞监视；Ctrl+C 退出。"""
    from .cli_workflow import run_workflow

    args.watch = False  # 防止递归进入 watch
    root = Path.cwd()
    while True:
        try:
            run_workflow(args)
        except SystemExit:
            # 编译失败/参数错误不应终止 watch；修好文件后还能继续
            pass
        snapshot = _snapshot(root)
        console.print("[dim]" + _("监视中：修改源文件后自动重编译（Ctrl+C 退出）") + "[/dim]")
        while True:
            time.sleep(1)
            current = _snapshot(root)
            if current != snapshot:
                time.sleep(0.4)  # 去抖：等编辑器把文件写完
                console.print("[green]" + _("检测到源文件变化，重新编译…") + "[/green]")
                break
