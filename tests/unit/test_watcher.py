# -*- coding: utf-8 -*-
"""watcher 文件监听模块单元测试"""

import time
from unittest.mock import MagicMock, patch

from pytexmk.watcher import (
    FileChangeHandler,
    PvcMode,
    open_pdf_preview,
    DEFAULT_WATCHED_EXTENSIONS,
    DEFAULT_EXCLUDE_DIRS,
    run_pvc_mode,
)


class MockEvent:
    """模拟 watchdog 文件系统事件"""

    def __init__(self, src_path: str, is_directory: bool = False):
        self.src_path = src_path
        self.is_directory = is_directory


class TestDefaultConstants:
    def test_default_watched_extensions(self):
        assert ".tex" in DEFAULT_WATCHED_EXTENSIONS
        assert ".bib" in DEFAULT_WATCHED_EXTENSIONS
        assert ".cls" in DEFAULT_WATCHED_EXTENSIONS
        assert ".sty" in DEFAULT_WATCHED_EXTENSIONS
        assert ".png" in DEFAULT_WATCHED_EXTENSIONS
        assert ".jpg" in DEFAULT_WATCHED_EXTENSIONS
        assert ".pdf" in DEFAULT_WATCHED_EXTENSIONS

    def test_default_exclude_dirs(self):
        assert "build" in DEFAULT_EXCLUDE_DIRS
        assert ".git" in DEFAULT_EXCLUDE_DIRS
        assert "__pycache__" in DEFAULT_EXCLUDE_DIRS
        assert ".venv" in DEFAULT_EXCLUDE_DIRS


class TestFileChangeHandler:
    def setup_method(self):
        self.callback_mock = MagicMock()

    def _make_handler(self, tmp_path, debounce=0.1):
        return FileChangeHandler(
            project_root=tmp_path,
            project_name="main",
            compile_callback=self.callback_mock,
            debounce_seconds=debounce,
        )

    def test_init_default_values(self, tmp_path):
        handler = FileChangeHandler(
            project_root=tmp_path,
            project_name="main",
        )
        assert handler.watched_extensions == DEFAULT_WATCHED_EXTENSIONS
        assert handler.exclude_dirs == DEFAULT_EXCLUDE_DIRS
        assert handler.compile_callback is None
        assert handler.debounce_seconds == 1.0

    def test_init_custom_values(self, tmp_path):
        custom_exts = {".tex", ".bib"}
        custom_dirs = {"custom_build"}
        handler = FileChangeHandler(
            project_root=tmp_path,
            project_name="main",
            watched_extensions=custom_exts,
            exclude_dirs=custom_dirs,
            compile_callback=self.callback_mock,
            debounce_seconds=0.5,
        )
        assert handler.watched_extensions == custom_exts
        assert handler.exclude_dirs == custom_dirs
        assert handler.compile_callback == self.callback_mock
        assert handler.debounce_seconds == 0.5

    def test_is_watched_file_valid_extension(self, tmp_path):
        handler = self._make_handler(tmp_path)

        tex_file = tmp_path / "main.tex"
        assert handler._is_watched_file(tex_file) is True

        bib_file = tmp_path / "refs.bib"
        assert handler._is_watched_file(bib_file) is True

        sty_file = tmp_path / "mypackage.sty"
        assert handler._is_watched_file(sty_file) is True

    def test_is_watched_file_invalid_extension(self, tmp_path):
        handler = self._make_handler(tmp_path)

        log_file = tmp_path / "main.log"
        assert handler._is_watched_file(log_file) is False

        aux_file = tmp_path / "main.aux"
        assert handler._is_watched_file(aux_file) is False

        tmp_file = tmp_path / "temp.tmp"
        assert handler._is_watched_file(tmp_file) is False

    def test_is_watched_file_exclude_dirs(self, tmp_path):
        handler = self._make_handler(tmp_path)
        build_dir = tmp_path / "build"
        build_dir.mkdir()
        git_dir = tmp_path / ".git"
        git_dir.mkdir()
        pycache_dir = tmp_path / "__pycache__"
        pycache_dir.mkdir()

        build_file = build_dir / "main.tex"
        build_file.write_text("", encoding="utf-8")
        assert handler._is_watched_file(build_file) is False

        git_file = git_dir / "config"
        git_file.write_text("", encoding="utf-8")
        assert handler._is_watched_file(git_file) is False

        pycache_file = pycache_dir / "test.pyc"
        pycache_file.write_text("", encoding="utf-8")
        assert handler._is_watched_file(pycache_file) is False

    def test_is_watched_file_outside_project_root(self, tmp_path):
        handler = self._make_handler(tmp_path)
        outside_file = tmp_path.parent / "other" / "file.tex"
        outside_file.parent.mkdir(exist_ok=True)
        outside_file.write_text("", encoding="utf-8")
        assert handler._is_watched_file(outside_file) is False

    def test_on_any_event_ignores_directory(self, tmp_path):
        handler = self._make_handler(tmp_path)
        subdir = tmp_path / "subdir"
        subdir.mkdir()
        event = MockEvent(str(subdir), is_directory=True)
        handler.on_any_event(event)
        time.sleep(0.2)
        self.callback_mock.assert_not_called()

    def test_on_any_event_ignores_unwatched_extension(self, tmp_path):
        handler = self._make_handler(tmp_path)
        log_file = tmp_path / "main.log"
        log_file.write_text("", encoding="utf-8")
        event = MockEvent(str(log_file))
        handler.on_any_event(event)
        time.sleep(0.2)
        self.callback_mock.assert_not_called()

    def test_on_any_event_ignores_excluded_dir(self, tmp_path):
        handler = self._make_handler(tmp_path)
        build_dir = tmp_path / "build"
        build_dir.mkdir()
        tex_in_build = build_dir / "main.tex"
        tex_in_build.write_text("", encoding="utf-8")
        event = MockEvent(str(tex_in_build))
        handler.on_any_event(event)
        time.sleep(0.2)
        self.callback_mock.assert_not_called()

    def test_on_any_event_triggers_callback_after_debounce(self, tmp_path):
        handler = self._make_handler(tmp_path)
        tex_file = tmp_path / "main.tex"
        tex_file.write_text("", encoding="utf-8")
        event = MockEvent(str(tex_file))
        handler.on_any_event(event)

        assert self.callback_mock.call_count == 0

        time.sleep(0.2)
        self.callback_mock.assert_called_once()
        call_args = self.callback_mock.call_args[0][0]
        assert call_args == tex_file.resolve()

    def test_debounce_multiple_rapid_events_only_one_callback(self, tmp_path):
        handler = self._make_handler(tmp_path)
        tex_file = tmp_path / "main.tex"
        tex_file.write_text("", encoding="utf-8")
        ch_file = tmp_path / "chapter1.tex"
        ch_file.write_text("", encoding="utf-8")

        event1 = MockEvent(str(tex_file))
        event2 = MockEvent(str(ch_file))
        event3 = MockEvent(str(tex_file))

        handler.on_any_event(event1)
        time.sleep(0.05)
        handler.on_any_event(event2)
        time.sleep(0.05)
        handler.on_any_event(event3)

        time.sleep(0.2)
        assert self.callback_mock.call_count == 1

    def test_stop_cancels_pending_timer(self, tmp_path):
        handler = self._make_handler(tmp_path)
        tex_file = tmp_path / "main.tex"
        tex_file.write_text("", encoding="utf-8")
        event = MockEvent(str(tex_file))
        handler.on_any_event(event)

        handler.stop()
        time.sleep(0.2)
        self.callback_mock.assert_not_called()

    def test_compile_callback_exception_does_not_crash(self, tmp_path):
        error_callback = MagicMock(side_effect=Exception("编译错误"))
        handler = FileChangeHandler(
            project_root=tmp_path,
            project_name="main",
            compile_callback=error_callback,
            debounce_seconds=0.05,
        )

        tex_file = tmp_path / "main.tex"
        tex_file.write_text("", encoding="utf-8")
        event = MockEvent(str(tex_file))
        handler.on_any_event(event)
        time.sleep(0.15)
        error_callback.assert_called_once()

    def test_pending_compile_during_compilation(self, tmp_path):
        handler = self._make_handler(tmp_path, debounce=0.05)

        with handler._lock:
            handler._compiling = True

        tex_file = tmp_path / "main.tex"
        tex_file.write_text("", encoding="utf-8")
        event = MockEvent(str(tex_file))
        handler.on_any_event(event)

        assert handler._pending_compile is True
        self.callback_mock.assert_not_called()


class TestOpenPdfPreview:
    @patch("pytexmk.watcher.sys.platform", "win32")
    @patch("pytexmk.watcher.os.startfile")
    def test_windows_open_pdf(self, mock_startfile, tmp_path):
        pdf_file = tmp_path / "test.pdf"
        pdf_file.write_text("%PDF-1.4", encoding="utf-8")

        open_pdf_preview(pdf_file)
        mock_startfile.assert_called_once_with(str(pdf_file))

    @patch("pytexmk.watcher.sys.platform", "darwin")
    @patch("pytexmk.watcher.subprocess.Popen")
    def test_macos_open_pdf(self, mock_popen, tmp_path):
        pdf_file = tmp_path / "test.pdf"
        pdf_file.write_text("%PDF-1.4", encoding="utf-8")

        open_pdf_preview(pdf_file)
        mock_popen.assert_called_once_with(["open", str(pdf_file)])

    @patch("pytexmk.watcher.sys.platform", "linux")
    @patch("pytexmk.watcher.subprocess.Popen")
    def test_linux_open_pdf(self, mock_popen, tmp_path):
        pdf_file = tmp_path / "test.pdf"
        pdf_file.write_text("%PDF-1.4", encoding="utf-8")

        open_pdf_preview(pdf_file)
        mock_popen.assert_called_once_with(["xdg-open", str(pdf_file)])

    @patch("pytexmk.watcher.subprocess.Popen")
    def test_custom_preview_command(self, mock_popen, tmp_path):
        pdf_file = tmp_path / "test.pdf"
        pdf_file.write_text("%PDF-1.4", encoding="utf-8")

        open_pdf_preview(pdf_file, preview_command="evince")
        mock_popen.assert_called_once_with(["evince", str(pdf_file)], shell=False)

    def test_nonexistent_pdf_does_not_crash(self, tmp_path):
        pdf_file = tmp_path / "nonexistent.pdf"
        open_pdf_preview(pdf_file)


class TestPvcMode:
    @patch("pytexmk.watcher.FileChangeHandler")
    @patch("pytexmk.watcher.Observer")
    def test_init_default_values(self, mock_observer_class, mock_handler_class, tmp_path):
        pvc = PvcMode(
            project_dir=tmp_path,
            project_name="main",
        )
        assert pvc.project_dir == tmp_path.resolve()
        assert pvc.project_name == "main"
        assert pvc.compile_callback is None
        assert pvc.compiler_kwargs == {}
        assert pvc.auto_open_preview is False
        assert pvc.preview_command is None
        assert pvc.observer is None
        assert pvc.event_handler is None

    @patch("pytexmk.watcher.FileChangeHandler")
    @patch("pytexmk.watcher.Observer")
    def test_init_custom_values(self, mock_observer_class, mock_handler_class, tmp_path):
        custom_callback = MagicMock()
        compiler_kwargs = {"program": "lualatex", "run_count": 2}
        pvc = PvcMode(
            project_dir=tmp_path,
            project_name="main",
            compile_callback=custom_callback,
            compiler_kwargs=compiler_kwargs,
            auto_open_preview=True,
            preview_command="okular",
        )
        assert pvc.compile_callback == custom_callback
        assert pvc.compiler_kwargs == compiler_kwargs
        assert pvc.auto_open_preview is True
        assert pvc.preview_command == "okular"

    @patch("pytexmk.watcher.FileChangeHandler")
    @patch("pytexmk.watcher.Observer")
    @patch("pytexmk.watcher.is_shutdown_requested", return_value=True)
    def test_start_calls_initial_compile(self, mock_shutdown, mock_observer_class, mock_handler_class, tmp_path):
        mock_observer_instance = mock_observer_class.return_value
        mock_handler_instance = mock_handler_class.return_value

        callback_mock = MagicMock()
        pvc = PvcMode(
            project_dir=tmp_path,
            project_name="main",
            compile_callback=callback_mock,
        )
        pvc.start()

        callback_mock.assert_called_once_with(None)
        mock_observer_instance.schedule.assert_called_once()
        mock_observer_instance.start.assert_called_once()
        mock_observer_instance.stop.assert_called_once()
        mock_handler_instance.stop.assert_called_once()

    @patch("pytexmk.watcher.FileChangeHandler")
    @patch("pytexmk.watcher.Observer")
    @patch("pytexmk.watcher.is_shutdown_requested", return_value=True)
    def test_stop_cleans_up_resources(self, mock_shutdown, mock_observer_class, mock_handler_class, tmp_path):
        mock_observer_instance = mock_observer_class.return_value
        mock_handler_instance = mock_handler_class.return_value

        callback_mock = MagicMock()
        pvc = PvcMode(
            project_dir=tmp_path,
            project_name="main",
            compile_callback=callback_mock,
        )
        pvc.start()

        pvc.stop()
        mock_observer_instance.stop.assert_called()
        mock_handler_instance.stop.assert_called()
        assert pvc.observer is None
        assert pvc.event_handler is None

    @patch("pytexmk.watcher.FileChangeHandler")
    @patch("pytexmk.watcher.Observer")
    @patch("pytexmk.watcher.is_shutdown_requested", return_value=True)
    def test_context_manager(self, mock_shutdown, mock_observer_class, mock_handler_class, tmp_path):
        callback_mock = MagicMock()

        with PvcMode(
            project_dir=tmp_path,
            project_name="main",
            compile_callback=callback_mock,
        ) as pvc:
            assert pvc is not None

        callback_mock.assert_called()

    def test_get_pdf_path(self, tmp_path):
        pvc = PvcMode(
            project_dir=tmp_path,
            project_name="main",
            compiler_kwargs={"outdir": "output"},
        )
        expected = tmp_path.resolve() / "output" / "main.pdf"
        assert pvc._get_pdf_path() == expected

    def test_get_pdf_path_default_outdir(self, tmp_path):
        pvc = PvcMode(
            project_dir=tmp_path,
            project_name="main",
        )
        expected = tmp_path.resolve() / "build" / "main.pdf"
        assert pvc._get_pdf_path() == expected

    @patch("pytexmk.watcher.CompileLaTeX")
    @patch("pytexmk.watcher.FileChangeHandler")
    @patch("pytexmk.watcher.Observer")
    @patch("pytexmk.watcher.is_shutdown_requested", return_value=True)
    def test_default_compile_callback(
        self, mock_shutdown, mock_observer_class, mock_handler_class, mock_compile_class, tmp_path
    ):
        mock_compiler_instance = mock_compile_class.return_value

        pvc = PvcMode(
            project_dir=tmp_path,
            project_name="main",
        )

        result = pvc._default_compile_callback(None)
        assert result is True
        mock_compiler_instance.compile_tex.assert_called_once()

    @patch("pytexmk.watcher.CompileLaTeX")
    @patch("pytexmk.watcher.FileChangeHandler")
    @patch("pytexmk.watcher.Observer")
    @patch("pytexmk.watcher.is_shutdown_requested", return_value=True)
    def test_default_compile_callback_with_changed_file(
        self, mock_shutdown, mock_observer_class, mock_handler_class, mock_compile_class, tmp_path
    ):
        mock_compiler_instance = mock_compile_class.return_value
        changed_file = tmp_path / "chapter1.tex"

        pvc = PvcMode(
            project_dir=tmp_path,
            project_name="main",
        )

        result = pvc._default_compile_callback(changed_file)
        assert result is True
        mock_compiler_instance.compile_tex.assert_called_once()

    @patch("pytexmk.watcher.CompileLaTeX")
    @patch("pytexmk.watcher.FileChangeHandler")
    @patch("pytexmk.watcher.Observer")
    @patch("pytexmk.watcher.is_shutdown_requested", return_value=True)
    def test_default_compile_callback_handles_exception(
        self, mock_shutdown, mock_observer_class, mock_handler_class, mock_compile_class, tmp_path
    ):
        mock_compiler_instance = mock_compile_class.return_value
        mock_compiler_instance.compile_tex.side_effect = Exception("编译失败")

        pvc = PvcMode(
            project_dir=tmp_path,
            project_name="main",
        )

        result = pvc._default_compile_callback(None)
        assert result is False


class TestRunPvcMode:
    @patch("pytexmk.watcher.PvcMode")
    def test_run_pvc_mode_creates_and_starts(self, mock_pvc_class, tmp_path):
        mock_pvc_instance = mock_pvc_class.return_value

        run_pvc_mode(
            project_dir=tmp_path,
            project_name="main",
            engine="xelatex",
            run_count=3,
            outdir="build",
            auto_open_preview=True,
        )

        mock_pvc_class.assert_called_once()
        call_kwargs = mock_pvc_class.call_args[1]
        assert call_kwargs["project_dir"] == tmp_path
        assert call_kwargs["project_name"] == "main"
        assert call_kwargs["compiler_kwargs"]["program"] == "xelatex"
        assert call_kwargs["compiler_kwargs"]["run_count"] == 3
        assert call_kwargs["compiler_kwargs"]["outdir"] == "build"
        assert call_kwargs["auto_open_preview"] is True
        mock_pvc_instance.start.assert_called_once()
        mock_pvc_instance.stop.assert_called_once()

    @patch("pytexmk.watcher.PvcMode")
    def test_run_pvc_mode_with_keyboard_interrupt(self, mock_pvc_class, tmp_path):
        mock_pvc_instance = mock_pvc_class.return_value
        mock_pvc_instance.start.side_effect = KeyboardInterrupt()

        run_pvc_mode(
            project_dir=tmp_path,
            project_name="main",
        )

        mock_pvc_instance.stop.assert_called_once()
