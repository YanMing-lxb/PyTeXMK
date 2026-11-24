"""`--watch` 轮询监视（3.1，不引入 watchdog 依赖）。

用 mtime+size 快照判断源码是否变化；每次变化后等待 400ms 去抖，避免编辑器
“先删后写”导致连续触发。轮询间隔 1s，CPU 开销可忽略。

修订点：
* **每轮都从原始调用目录重新解析目标**。`run_workflow` 会 ``os.chdir`` 到
  子项目目录，旧实现下一轮就在子项目目录里找 ``-s`` 别名，必然报“未找到子项目”；
* 快照覆盖构建依赖（图片、``.bib``、``.pytexmkrc``），不只盯 ``.tex``；
* 编译**期间**发生的保存也要被发现：编译前后各取一次快照，不一致就立刻再编，
  而不是等下一轮轮询时才看到。
"""

import contextlib
import time
from pathlib import Path

from ..language import set_language
from ..layout import (
    DEPENDENCY_SUFFIXES,
    OUT_SUFFIXES,
    SOURCE_SNAPSHOT_EXCLUDED_SUFFIXES,
    SOURCE_SUFFIXES,
    WATCH_SKIP_DIRS,
)
from ..ui_theme import console
from .cli_state import WorkflowState

_ = set_language("cli_workflow")

#: 轮询监控的文件后缀：源码 + 构建依赖（图片/文献/样式），外加项目配置。
#: 只监控 .tex 会漏掉“换了一张图”“改了参考文献”这类必须重编的变化。
_MONITOR_SUFFIXES = (SOURCE_SUFFIXES | DEPENDENCY_SUFFIXES) - SOURCE_SNAPSHOT_EXCLUDED_SUFFIXES
_SKIP_DIRS = WATCH_SKIP_DIRS


def _snapshot(
    root: Path, excluded: frozenset[Path] = frozenset()
) -> dict[str, tuple[int, int]]:
    """记录源/依赖文件的 (mtime_ns, size)。"""
    result: dict[str, tuple[int, int]] = {}
    for path in root.rglob("*"):
        if not path.is_file():
            continue
        name = path.name
        if name != ".pytexmkrc" and path.suffix.lower() not in _MONITOR_SUFFIXES:
            continue
        parts = set(path.relative_to(root).parts[:-1])
        if parts & _SKIP_DIRS or any(p.startswith(".") for p in parts):
            continue
        try:
            if excluded and path.resolve() in excluded:
                continue
            stat = path.stat()
        except OSError:
            continue
        result[path.relative_to(root).as_posix()] = (stat.st_mtime_ns, stat.st_size)
    return result


def _generated_outputs(state: WorkflowState) -> frozenset[Path]:
    """只排除实际目标产物，同一目录中的 PDF 图片仍可触发重编。"""
    name = state.diff_tex_file if state.is_latexdiff else state.output_name
    source = Path(state.auxdir if state.native_build else ".")
    outputs = {
        (folder / f"{name}{suffix}").resolve()
        for folder in (source, Path(state.outdir))
        for suffix in OUT_SUFFIXES
    }
    if state.is_latexdiff:
        outputs.add(Path(f"{name}.tex").resolve())
    return frozenset(outputs)


def watch_loop(args) -> None:
    """先编译一次，然后阻塞监视；Ctrl+C 退出。"""
    from .cli_workflow import run_workflow

    args.watch = False  # 防止递归进入 watch
    root = Path.cwd()
    excluded: frozenset[Path] = frozenset()
    baseline = _snapshot(root)

    def before_build(state: WorkflowState) -> None:
        nonlocal baseline, excluded
        excluded = _generated_outputs(state)
        baseline = _snapshot(root, excluded)

    def _compile_once() -> None:
        """回到原始调用目录编译一次；失败/参数错误不终止 watch。"""
        with contextlib.chdir(root), contextlib.suppress(SystemExit):
            run_workflow(args, before_build=before_build)

    try:
        while True:
            _compile_once()
            current = _snapshot(root, excluded)
            if current != baseline:
                # 编译过程中用户又保存了文件：直接再编一轮，别等下一次轮询。
                baseline = current
                console.print("[green]" + _("编译期间检测到新的源文件变化，立即重新编译…") + "[/green]")
                continue

            console.print("[dim]" + _("监视中：修改源文件后自动重编译（Ctrl+C 退出）") + "[/dim]")
            while True:
                time.sleep(1)
                current = _snapshot(root, excluded)
                if current == baseline:
                    continue
                time.sleep(0.4)  # 去抖：等编辑器把文件写完
                baseline = _snapshot(root, excluded)
                console.print("[green]" + _("检测到源文件变化，重新编译…") + "[/green]")
                break
    except KeyboardInterrupt:
        console.print("[dim]" + _("已退出监视模式") + "[/dim]")
