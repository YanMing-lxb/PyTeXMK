# -*- coding: utf-8 -*-
"""MySubProcess 单元测试"""

import sys
import time
from unittest.mock import MagicMock

import pytest

from pytexmk.additional import MySubProcess
from pytexmk.exceptions import CompilationError, CompilationTimeoutError


class TestMySubProcess:
    """MySubProcess 类测试"""

    def test_run_command_success(self, mocker):
        """测试命令成功执行"""
        msp = MySubProcess()
        mock_popen = mocker.patch("subprocess.Popen")
        mock_process = MagicMock()
        mock_process.poll.side_effect = [None, 0]
        mock_process.returncode = 0
        mock_process.stdout.readline.side_effect = ["output line 1\n", ""]
        mock_popen.return_value = mock_process

        success, output = msp.run_command(["echo", "hello"], program_name="测试命令", timeout=5)

        assert success is True
        assert "output line 1" in output
        mock_popen.assert_called_once()

    def test_run_command_failure(self, mocker):
        """测试命令执行失败（非零返回码）"""
        msp = MySubProcess()
        error_callback = MagicMock()
        mock_popen = mocker.patch("subprocess.Popen")
        mock_process = MagicMock()
        mock_process.poll.side_effect = [None, 1]
        mock_process.returncode = 1
        mock_process.stdout.readline.side_effect = ["error output\n", ""]
        mock_popen.return_value = mock_process

        with pytest.raises(CompilationError) as exc_info:
            msp.run_command(["false"], program_name="失败命令", error_callback=error_callback)

        assert exc_info.value.returncode == 1
        error_callback.assert_called_once()

    def test_run_command_timeout(self, mocker):
        """测试命令执行超时"""
        msp = MySubProcess()
        error_callback = MagicMock()
        mock_terminate = mocker.patch.object(MySubProcess, "_terminate_process")
        mock_popen = mocker.patch("subprocess.Popen")
        mock_process = MagicMock()
        mock_process.poll.return_value = None
        mock_process.stdout.readline.return_value = ""
        mock_popen.return_value = mock_process

        start_time = time.time()
        with pytest.raises(CompilationTimeoutError) as exc_info:
            msp.run_command(
                [sys.executable, "-c", "import time; time.sleep(10)"],
                program_name="超时命令",
                timeout=0.5,
                error_callback=error_callback,
            )
        elapsed = time.time() - start_time

        assert exc_info.value.timeout == 0.5
        assert elapsed < 5.0
        mock_terminate.assert_called()
        error_callback.assert_called_once()

    def test_run_command_cwd_parameter(self, mocker):
        """测试 cwd 参数被正确传递"""
        msp = MySubProcess()
        mock_popen = mocker.patch("subprocess.Popen")
        mock_process = MagicMock()
        mock_process.poll.side_effect = [0]
        mock_process.returncode = 0
        mock_process.stdout.readline.return_value = ""
        mock_popen.return_value = mock_process

        msp.run_command(["pwd"], program_name="测试cwd", cwd="/tmp")

        call_kwargs = mock_popen.call_args[1]
        assert call_kwargs["cwd"] == "/tmp"

    def test_run_command_encoding_error_handling(self, mocker):
        """测试编码错误容错处理"""
        msp = MySubProcess()
        mock_popen = mocker.patch("subprocess.Popen")
        mock_process = MagicMock()
        mock_process.poll.side_effect = [None, 0]
        mock_process.returncode = 0
        mock_process.stdout.readline.side_effect = [
            UnicodeDecodeError("utf-8", b"\x80", 0, 1, "invalid start byte"),
            "valid line\n",
            "",
        ]
        mock_popen.return_value = mock_process

        success, output = msp.run_command(["echo", "test"], program_name="编码测试", timeout=5)

        assert success is True

    def test_no_self_attribute_error(self, mocker):
        """验证不再引用不存在的 self.compiled_program 等属性"""
        msp = MySubProcess()
        assert not hasattr(msp, "compiled_program")
        assert not hasattr(msp, "auxdir")
        assert not hasattr(msp, "project_name")
        assert not hasattr(msp, "aux_files")
        assert not hasattr(msp, "out_files")
        assert not hasattr(msp, "MRO")

        mock_popen = mocker.patch("subprocess.Popen")
        mock_process = MagicMock()
        mock_process.poll.side_effect = [None, 1]
        mock_process.returncode = 1
        mock_process.stdout.readline.side_effect = ["error\n", ""]
        mock_popen.return_value = mock_process

        with pytest.raises(CompilationError):
            msp.run_command(["false"], program_name="测试")

    def test_context_manager(self, mocker):
        """测试上下文管理器支持"""
        mock_cleanup = mocker.patch.object(MySubProcess, "_cleanup")
        with MySubProcess() as msp:
            assert isinstance(msp, MySubProcess)
        mock_cleanup.assert_called_once()

    def test_error_callback_not_called_on_success(self, mocker):
        """测试成功时不调用 error_callback"""
        msp = MySubProcess()
        error_callback = MagicMock()
        mock_popen = mocker.patch("subprocess.Popen")
        mock_process = MagicMock()
        mock_process.poll.side_effect = [None, 0]
        mock_process.returncode = 0
        mock_process.stdout.readline.side_effect = ["ok\n", ""]
        mock_popen.return_value = mock_process

        success, output = msp.run_command(["true"], program_name="成功命令", error_callback=error_callback)

        assert success is True
        error_callback.assert_not_called()
