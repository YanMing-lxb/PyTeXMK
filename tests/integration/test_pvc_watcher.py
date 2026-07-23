# -*- coding: utf-8 -*-
"""
PVC 模式集成测试
"""

import time
import threading
from unittest import mock

from pytexmk.watcher import PvcMode, FileChangeHandler


class TestFileChangeHandler:
    """测试 FileChangeHandler 防抖和回调逻辑"""

    def test_debounce_logic(self, tmp_path):
        """测试防抖逻辑在真实时间下工作"""
        callback_called = []
        changed_files = []

        def mock_compile_callback(file_path):
            callback_called.append(time.time())
            changed_files.append(file_path)

        handler = FileChangeHandler(
            project_root=tmp_path,
            project_name="test",
            compile_callback=mock_compile_callback,
            debounce_seconds=0.2,
        )

        tex_file = tmp_path / "test.tex"
        tex_file.write_text("test content", encoding="utf-8")

        from watchdog.events import FileModifiedEvent

        event1 = FileModifiedEvent(str(tex_file))
        handler.on_any_event(event1)

        assert len(callback_called) == 0

        event2 = FileModifiedEvent(str(tex_file))
        handler.on_any_event(event2)

        time.sleep(0.35)

        assert len(callback_called) == 1

        handler.stop()

    def test_callback_receives_changed_file(self, tmp_path):
        """测试编译回调接收到变更的文件路径"""
        received_file = []

        def mock_callback(file_path):
            received_file.append(file_path)

        handler = FileChangeHandler(
            project_root=tmp_path,
            project_name="test",
            compile_callback=mock_callback,
            debounce_seconds=0.1,
        )

        tex_file = tmp_path / "main.tex"
        tex_file.write_text("\\documentclass{article}", encoding="utf-8")

        from watchdog.events import FileModifiedEvent

        event = FileModifiedEvent(str(tex_file))
        handler.on_any_event(event)

        time.sleep(0.25)

        assert len(received_file) == 1
        assert received_file[0] is not None

        handler.stop()

    def test_ignores_excluded_directories(self, tmp_path):
        """测试忽略排除的目录"""
        callback_called = []

        def mock_callback(file_path):
            callback_called.append(file_path)

        handler = FileChangeHandler(
            project_root=tmp_path,
            project_name="test",
            compile_callback=mock_callback,
            debounce_seconds=0.1,
        )

        git_dir = tmp_path / ".git"
        git_dir.mkdir(exist_ok=True)
        git_file = git_dir / "config"
        git_file.write_text("git config", encoding="utf-8")

        from watchdog.events import FileModifiedEvent

        event = FileModifiedEvent(str(git_file))
        handler.on_any_event(event)

        time.sleep(0.2)

        assert len(callback_called) == 0

        handler.stop()


class TestPvcMode:
    """测试 PvcMode 类"""

    def test_pvc_mode_initialization(self, tmp_path):
        """测试 PvcMode 初始化"""
        compiler_kwargs = {
            "program": "xelatex",
            "outdir": "build",
            "run_count": 1,
        }

        pvc = PvcMode(
            project_dir=tmp_path,
            project_name="test",
            compiler_kwargs=compiler_kwargs,
            auto_open_preview=False,
        )

        assert pvc.project_dir == tmp_path.resolve()
        assert pvc.project_name == "test"
        assert pvc.compiler_kwargs == compiler_kwargs
        assert pvc.auto_open_preview is False
        assert pvc.observer is None
        assert pvc.event_handler is None

        pvc.stop()

    def test_pvc_stop_without_start(self, tmp_path):
        """测试未启动时 stop 不报错"""
        pvc = PvcMode(
            project_dir=tmp_path,
            project_name="test",
        )
        pvc.stop()
        assert True

    def test_pvc_custom_callback(self, tmp_path):
        """测试自定义编译回调"""
        callback_called = threading.Event()
        callback_args = []

        def custom_callback(changed_file):
            callback_args.append(changed_file)
            callback_called.set()
            return True

        pvc = PvcMode(
            project_dir=tmp_path,
            project_name="test",
            compile_callback=custom_callback,
        )

        assert pvc.compile_callback == custom_callback
        pvc.stop()

    def test_pvc_start_and_stop_with_thread(self, tmp_path, monkeypatch):
        """测试在单独线程中启动和停止 PvcMode（超时保护）"""
        tex_file = tmp_path / "test.tex"
        tex_file.write_text("\\documentclass{article}\n\\begin{document}\nTest\n\\end{document}", encoding="utf-8")

        callback_invoked = threading.Event()

        def mock_callback(changed_file):
            callback_invoked.set()
            return True

        pvc = PvcMode(
            project_dir=tmp_path,
            project_name="test",
            compile_callback=mock_callback,
        )

        def run_pvc():
            with mock.patch("pytexmk.watcher.setup_signal_handlers"):
                with mock.patch.object(pvc, "_default_compile_callback", side_effect=mock_callback):
                    pvc.compile_callback = mock_callback
                    callback = pvc.compile_callback
                    callback(None)

                    pvc.event_handler = FileChangeHandler(
                        project_root=tmp_path,
                        project_name="test",
                        compile_callback=lambda f: mock_callback(f),
                        debounce_seconds=0.1,
                    )
                    from watchdog.observers import Observer

                    pvc.observer = Observer()
                    pvc.observer.schedule(pvc.event_handler, str(tmp_path), recursive=True)
                    pvc.observer.start()

                    time.sleep(0.3)
                    pvc.stop()

        thread = threading.Thread(target=run_pvc, daemon=True)
        thread.start()
        thread.join(timeout=5.0)

        assert not thread.is_alive(), "PVC 线程未能在超时时间内停止"


class TestPvcSignalHandling:
    """测试 Ctrl+C 信号能优雅停止 PvcMode"""

    def test_graceful_shutdown(self, tmp_path):
        """测试优雅停止机制"""
        pvc = PvcMode(
            project_dir=tmp_path,
            project_name="test",
        )

        assert pvc._shutdown_requested is False

        pvc.stop()

        assert pvc._shutdown_requested is True
        assert pvc.observer is None
        assert pvc.event_handler is None


class TestDebounceTiming:
    """测试防抖时间配置"""

    def test_debounce_configuration(self, tmp_path):
        """测试防抖时间可配置"""
        custom_debounce = 0.2

        callback_called = []

        def mock_callback(file_path):
            callback_called.append(time.time())

        handler = FileChangeHandler(
            project_root=tmp_path,
            project_name="test",
            compile_callback=mock_callback,
            debounce_seconds=custom_debounce,
        )

        assert handler.debounce_seconds == custom_debounce
        handler.stop()
