# -*- coding: utf-8 -*-
"""
实时文件监听与自动编译模块（PVC 模式，类似 latexmk -pvc）
"""

import os
import sys
import time
import subprocess
import threading
from pathlib import Path
from typing import Callable, Optional, Set, Any

from rich.console import Console
from watchdog.events import FileSystemEventHandler, FileSystemEvent
from watchdog.observers import Observer

from pytexmk.auxiliary_fun import is_shutdown_requested, setup_signal_handlers
from pytexmk.compile import CompileLaTeX
from pytexmk.additional import MoveRemoveOperation
from pytexmk.log_analysis import LogAnalysis
from pytexmk.language import set_language

_ = set_language("watcher")

console = Console(legacy_windows=False)

DEFAULT_WATCHED_EXTENSIONS: Set[str] = {
    ".tex",
    ".bib",
    ".bst",
    ".cls",
    ".sty",
    ".bbl",
    ".ist",
    ".idx",
    ".ind",
    ".gls",
    ".glo",
    ".nlo",
    ".nls",
    ".png",
    ".jpg",
    ".jpeg",
    ".pdf",
    ".eps",
    ".svg",
    ".tikz",
}

DEFAULT_EXCLUDE_DIRS: Set[str] = {
    "build",
    ".git",
    ".svn",
    "__pycache__",
    ".pytest_cache",
    "node_modules",
    ".venv",
}


def open_pdf_preview(pdf_path: Path, preview_command: Optional[str] = None) -> None:
    """
    跨平台打开 PDF 预览

    参数:
        pdf_path: PDF 文件路径
        preview_command: 自定义预览命令（可选）
    """
    pdf_path = Path(pdf_path)
    if not pdf_path.exists():
        console.print(_("[yellow]PDF 文件不存在，无法打开预览: %(path)s[/yellow]") % {"path": pdf_path})
        return

    try:
        if preview_command:
            cmd = preview_command.split()
            cmd.append(str(pdf_path))
            subprocess.Popen(cmd, shell=False)
        elif sys.platform == "win32":
            os.startfile(str(pdf_path))
        elif sys.platform == "darwin":
            subprocess.Popen(["open", str(pdf_path)])
        else:
            subprocess.Popen(["xdg-open", str(pdf_path)])
    except Exception as e:
        console.print(_("[yellow]打开预览失败: %(error)s[/yellow]") % {"error": e})


class FileChangeHandler(FileSystemEventHandler):
    """文件变更事件处理器，带防抖机制"""

    def __init__(
        self,
        project_root: Path,
        project_name: str,
        watched_extensions: Optional[Set[str]] = None,
        exclude_dirs: Optional[Set[str]] = None,
        compile_callback: Optional[Callable[[Path], Any]] = None,
        debounce_seconds: float = 1.0,
    ):
        """
        初始化文件变更处理器

        参数:
            project_root: 项目根目录
            project_name: 主文件名（不含 .tex）
            watched_extensions: 监听的文件后缀集合
            exclude_dirs: 排除的目录名集合
            compile_callback: 文件变更时的编译回调函数
            debounce_seconds: 防抖时间（秒）
        """
        super().__init__()
        self.project_root = Path(project_root).resolve()
        self.project_name = project_name
        self.watched_extensions = watched_extensions or DEFAULT_WATCHED_EXTENSIONS
        self.exclude_dirs = exclude_dirs or DEFAULT_EXCLUDE_DIRS
        self.compile_callback = compile_callback
        self.debounce_seconds = debounce_seconds

        self._last_event_time: float = 0.0
        self._pending_compile: bool = False
        self._timer: Optional[threading.Timer] = None
        self._timer_id: int = 0
        self._lock = threading.Lock()
        self._compiling: bool = False
        self._last_changed_file: Optional[Path] = None

    def on_any_event(self, event: FileSystemEvent) -> None:
        """
        处理所有文件系统事件

        参数:
            event: watchdog 文件系统事件
        """
        if event.is_directory:
            return

        event_path = Path(event.src_path).resolve()

        if not self._is_watched_file(event_path):
            return

        with self._lock:
            if self._compiling:
                self._pending_compile = True
                self._last_changed_file = event_path
                return

            if self._timer is not None:
                self._timer.cancel()
                self._timer = None

            self._last_changed_file = event_path
            self._timer_id += 1
            current_timer_id = self._timer_id
            self._timer = threading.Timer(self.debounce_seconds, self._trigger_compile, args=(current_timer_id,))
            self._timer.daemon = True
            self._timer.start()

    def _is_watched_file(self, file_path: Path) -> bool:
        """
        检查文件是否应该被监听

        参数:
            file_path: 文件路径

        返回:
            bool: 是否应该监听该文件
        """
        try:
            rel_path = file_path.relative_to(self.project_root)
        except ValueError:
            return False

        for part in rel_path.parts:
            if part in self.exclude_dirs:
                return False

        suffix = file_path.suffix.lower()
        return suffix in self.watched_extensions

    def _trigger_compile(self, timer_id: int = 0) -> None:
        """触发编译回调（防抖到期后执行）"""
        with self._lock:
            if timer_id != self._timer_id:
                return
            self._timer = None
            self._compiling = True
            changed_file = self._last_changed_file

        try:
            if self.compile_callback and changed_file:
                self.compile_callback(changed_file)
        except Exception as e:
            console.print(_("[bold red]编译回调异常: %(error)s[/bold red]") % {"error": e})
        finally:
            with self._lock:
                self._compiling = False
                if self._pending_compile:
                    self._pending_compile = False
                    self._timer_id += 1
                    current_timer_id = self._timer_id
                    self._timer = threading.Timer(
                        self.debounce_seconds, self._trigger_compile, args=(current_timer_id,)
                    )
                    self._timer.daemon = True
                    self._timer.start()

    def stop(self) -> None:
        """停止处理器，取消待执行的定时器"""
        with self._lock:
            if self._timer is not None:
                self._timer.cancel()
                self._timer = None


class PvcMode:
    """PVC（Preview Continuous）模式：实时监听文件变更并自动编译"""

    def __init__(
        self,
        project_dir: str | Path,
        project_name: str,
        compile_callback: Optional[Callable[[Optional[Path]], bool]] = None,
        compiler_kwargs: Optional[dict] = None,
        auto_open_preview: bool = False,
        preview_command: Optional[str] = None,
    ):
        """
        初始化 PVC 模式

        参数:
            project_dir: 项目目录
            project_name: 主文件名（不含 .tex）
            compile_callback: 自定义编译回调函数（为 None 时使用默认）
            compiler_kwargs: 传递给默认编译器的参数
            auto_open_preview: 编译成功后是否自动打开 PDF 预览
            preview_command: 自定义预览命令
        """
        self.project_dir = Path(project_dir).resolve()
        self.project_name = project_name
        self.compile_callback = compile_callback
        self.compiler_kwargs = compiler_kwargs or {}
        self.auto_open_preview = auto_open_preview
        self.preview_command = preview_command

        self.observer: Optional[Observer] = None
        self.event_handler: Optional[FileChangeHandler] = None
        self._shutdown_requested = False

    def _get_pdf_path(self) -> Path:
        """获取输出 PDF 文件路径"""
        outdir = self.compiler_kwargs.get("outdir", "build")
        return self.project_dir / outdir / f"{self.project_name}.pdf"

    def _default_compile_callback(self, changed_file: Optional[Path] = None) -> bool:
        """
        默认编译回调函数

        参数:
            changed_file: 变更的文件路径（可选）

        返回:
            bool: 编译是否成功
        """
        if changed_file:
            console.print(
                _("[bold cyan]检测到文件变更: %(filename)s，开始重新编译...[/bold cyan]")
                % {"filename": changed_file.name}
            )
        else:
            console.print(_("[bold cyan]开始首次编译...[/bold cyan]"))

        old_cwd = os.getcwd()
        os.chdir(self.project_dir)

        outdir = self.compiler_kwargs.get("outdir", "Build")
        auxdir = self.compiler_kwargs.get("auxdir", "Auxiliary")

        suffixes_out = [".pdf", ".synctex.gz"]
        suffixes_aux = [
            ".log",
            ".blg",
            ".ilg",
            ".xlg",
            ".aux",
            ".bbl",
            ".xml",
            ".toc",
            ".lof",
            ".lot",
            ".out",
            ".bcf",
            ".idx",
            ".ind",
            ".nlo",
            ".nls",
            ".ist",
            ".glo",
            ".gls",
            ".bak",
            ".spl",
            ".ent-x",
            ".tmp",
            ".ltx",
            ".los",
            ".lol",
            ".loc",
            ".listing",
            ".gz",
            ".userbak",
            ".nav",
            ".snm",
            ".vrb",
            ".fls",
            ".xdv",
            ".fdb_latexmk",
            ".run.xml",
        ]

        out_files = [f"{self.project_name}{suffix}" for suffix in suffixes_out]
        aux_files = [f"{self.project_name}{suffix}" for suffix in suffixes_aux]

        MRO = MoveRemoveOperation()

        try:
            MRO.move_specific_files(aux_files, auxdir, ".")

            compiler = CompileLaTeX(project_name=self.project_name, **self.compiler_kwargs)
            compiler.compile_tex()

            try:
                log_analysis = LogAnalysis(self.project_name)
                log_analysis.parse_all()
                log_analysis.view_log()
            except Exception:
                pass

            Path(outdir).mkdir(parents=True, exist_ok=True)
            Path(auxdir).mkdir(parents=True, exist_ok=True)

            MRO.move_specific_files(out_files, ".", outdir)
            MRO.move_specific_files(aux_files, ".", auxdir)

            success = True
        except Exception as e:
            console.print(_("[bold red]编译失败: %(error)s[/bold red]") % {"error": e})
            success = False
        finally:
            os.chdir(old_cwd)

        if success and self.auto_open_preview:
            pdf_path = self._get_pdf_path()
            open_pdf_preview(pdf_path, self.preview_command)

        return success

    def _handle_file_change(self, changed_file: Path) -> None:
        """
        处理文件变更（供 FileChangeHandler 调用）

        参数:
            changed_file: 变更的文件路径
        """
        callback = self.compile_callback or self._default_compile_callback
        callback(changed_file)

    def start(self) -> None:
        """启动 PVC 模式：首次编译 + 开始文件监听"""
        setup_signal_handlers()

        console.print("\n" + "=" * 78, style="blue bold")
        console.print(
            _("[bold blue on white]| PyTeXMK PVC 模式（预览持续模式） |[/bold blue on white]"), justify="center"
        )
        console.print("=" * 78 + "\n", style="blue bold")

        callback = self.compile_callback or self._default_compile_callback
        callback(None)

        self.event_handler = FileChangeHandler(
            project_root=self.project_dir,
            project_name=self.project_name,
            compile_callback=self._handle_file_change,
        )

        self.observer = Observer()
        self.observer.schedule(self.event_handler, str(self.project_dir), recursive=True)
        self.observer.start()

        console.print(_("[bold green]PyTeXMK PVC 模式已启动，正在监听文件变更。按 Ctrl+C 停止...[/bold green]\n"))

        try:
            while not is_shutdown_requested() and not self._shutdown_requested:
                time.sleep(0.5)
        except KeyboardInterrupt:
            pass
        finally:
            self.stop()

    def stop(self) -> None:
        """停止 PVC 模式"""
        self._shutdown_requested = True

        if self.observer is not None:
            self.observer.stop()
            self.observer.join(timeout=5.0)
            self.observer = None

        if self.event_handler is not None:
            self.event_handler.stop()
            self.event_handler = None

        console.print("\n" + _("[bold yellow]PVC 模式已停止[/bold yellow]"))

    def __enter__(self):
        """上下文管理器入口"""
        self.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """上下文管理器出口"""
        self.stop()
        return False


def run_pvc_mode(
    project_dir: str | Path,
    project_name: str,
    engine: Optional[str] = None,
    run_count: Optional[int] = None,
    outdir: Optional[str] = None,
    auxdir: Optional[str] = None,
    auto_open_preview: bool = False,
    preview_command: Optional[str] = None,
    **kwargs,
) -> None:
    """
    便捷函数：创建并启动 PVC 模式

    参数:
        project_dir: 项目目录
        project_name: 主文件名（不含 .tex）
        engine: LaTeX 引擎（如 'xelatex', 'pdflatex', 'lualatex'）
        run_count: 编译次数
        outdir: 输出目录
        auxdir: 辅助文件目录
        auto_open_preview: 是否自动打开预览
        preview_command: 自定义预览命令
        **kwargs: 其他传递给 CompileLaTeX 的参数
    """
    compiler_kwargs = {}
    if engine is not None:
        compiler_kwargs["program"] = engine
    if run_count is not None:
        compiler_kwargs["run_count"] = run_count
    if outdir is not None:
        compiler_kwargs["outdir"] = outdir
    if auxdir is not None:
        compiler_kwargs["auxdir"] = auxdir
    compiler_kwargs.update(kwargs)

    pvc = PvcMode(
        project_dir=project_dir,
        project_name=project_name,
        compiler_kwargs=compiler_kwargs,
        auto_open_preview=auto_open_preview,
        preview_command=preview_command,
    )

    try:
        pvc.start()
    except KeyboardInterrupt:
        pass
    finally:
        pvc.stop()
