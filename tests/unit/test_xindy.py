"""xindy 在 Windows 项目目录报 Win32 267 时的兜底重试。"""

from pathlib import Path

import pytest

from pytexmk import compile as compile_module
from pytexmk.compile import (
    CompileLaTeX,
    absolutize_xindy_tokens,
    is_xindy_command,
    xindy_fallback_workdirs,
)
from pytexmk.subprocess_runner import SubprocessFailedError

BASE_TOKENS = [
    "xindy", "-L", "english", "-I", "xindy",
    "-M", "main.xdy", "-t", "main.glg", "-o", "main.gls", "main.glo",
]


def test_is_xindy_command():
    assert is_xindy_command(["xindy", "-L", "english"])
    assert is_xindy_command([r"C:\tex\bin\xindy.exe", "-L", "english"])
    assert is_xindy_command(["texindy", "-L", "english"])
    assert not is_xindy_command(["makeindex", "main.idx"])
    assert not is_xindy_command([])


def test_absolutize_xindy_tokens_keeps_flag_values(tmp_path):
    (tmp_path / "main.xdy").write_text("(define-attributes ())", encoding="utf-8")
    (tmp_path / "main.glo").write_text("(indexentry :tkey 1)", encoding="utf-8")
    result = absolutize_xindy_tokens(BASE_TOKENS, tmp_path)

    # -L/-I 的值不是路径，必须原样保留
    assert result[1:5] == ["-L", "english", "-I", "xindy"]
    # 文件参数全部变成绝对路径，print 时不会落到临时目录
    for token in ("-M", "-t", "-o"):
        index = result.index(token)
        assert Path(result[index + 1]).is_absolute()
    assert Path(result[-1]).is_absolute()
    assert Path(result[-1]).name == "main.glo"


def test_absolutize_xindy_tokens_keeps_missing_input_relative(tmp_path):
    result = absolutize_xindy_tokens(BASE_TOKENS, tmp_path)
    assert Path(result[result.index("-o") + 1]).is_absolute()
    # 输入文件不存在时保持相对，避免伪造路径
    assert result[-1] == "main.glo"


def test_xindy_fallback_workdirs_non_windows(monkeypatch):
    monkeypatch.setattr(compile_module.os, "name", "posix")
    assert xindy_fallback_workdirs() == []


def _make_compiler(auxdir: Path) -> CompileLaTeX:
    compiler = CompileLaTeX(
        "main", "XeLaTeX", ["main.pdf"], ["main.aux"], "Build", str(auxdir), True, native=True,
    )
    compiler.MSP = _FlakyMSP()
    return compiler


class _FlakyMSP:
    """第一次抛 267 失败，第二次成功；记录每次调用的 cwd 与参数。"""

    def __init__(self):
        self.calls = []

    def run_command(self, command, out_files, aux_files, program_name="执行命令",
                    stdout_path=None, cwd=None, log_hint=True):
        self.calls.append((list(command), Path(cwd) if cwd else None))
        if len(self.calls) == 1:
            raise SubprocessFailedError(
                command="xindy", exit_code=1,
                stdout="*** - Win32 error 267 (ERROR_DIRECTORY)\n", stderr="",
            )
        return True


def test_compile_index_retries_xindy_in_fallback_dir(monkeypatch, tmp_path):
    auxdir = tmp_path / "Auxiliary"
    auxdir.mkdir()
    (auxdir / "main.xdy").write_text("(define-attributes ())", encoding="utf-8")
    (auxdir / "main.glo").write_text("(indexentry :tkey 1)", encoding="utf-8")
    workdir = tmp_path / "fallback"
    workdir.mkdir()
    monkeypatch.setattr(compile_module, "xindy_fallback_workdirs", lambda: [workdir])
    monkeypatch.setattr(compile_module, "is_dir_writable", lambda path: True)

    compiler = _make_compiler(auxdir)
    compiler.compile_index(("glossaries (main, xindy)", " ".join(BASE_TOKENS)))

    assert len(compiler.MSP.calls) == 2, "第一次失败后必须重试一次"
    first_cmd, first_cwd = compiler.MSP.calls[0]
    assert first_cwd == auxdir
    assert first_cmd[0] == "xindy"
    retry_cmd, retry_cwd = compiler.MSP.calls[1]
    assert retry_cwd == workdir
    for token in ("-M", "-t", "-o"):
        assert Path(retry_cmd[retry_cmd.index(token) + 1]).is_absolute()
    assert Path(retry_cmd[-1]).is_absolute()


def test_compile_index_does_not_retry_makeindex(monkeypatch, tmp_path):
    compiler = _make_compiler(tmp_path)
    calls = {"count": 0}

    def fail_once(command, *args, **kwargs):
        calls["count"] += 1
        raise SubprocessFailedError(
            command="makeindex", exit_code=1, stdout="", stderr="",
        )

    compiler.MSP.run_command = fail_once
    monkeypatch.setattr(compile_module, "xindy_fallback_workdirs", lambda: [tmp_path])
    with pytest.raises(SystemExit):
        compiler.compile_index(("makeidx (main)", "makeindex main.idx"))
    assert calls["count"] == 1, "非 xindy 命令不应进入兜底重试"


def test_xindy_does_not_retry_on_non_startup_error(monkeypatch, tmp_path):
    """样式文件缺失等真实错误重试也没用，不应把报错刷掉。"""
    compiler = _make_compiler(tmp_path)
    calls = {"count": 0}

    def fail_once(command, *args, **kwargs):
        calls["count"] += 1
        raise SubprocessFailedError(
            command="xindy", exit_code=1,
            stdout="Cannot find main.xdy\n", stderr="",
        )

    compiler.MSP.run_command = fail_once
    monkeypatch.setattr(compile_module, "xindy_fallback_workdirs", lambda: [tmp_path])
    with pytest.raises(SystemExit):
        compiler.compile_index(("glossaries (main, xindy)", " ".join(BASE_TOKENS)))
    assert calls["count"] == 1, "非 267 的 xindy 错误不应重试"


class _LauncherLogFailureMSP:
    """模拟 MiKTeX 启动器写不了 xindy.log：原始 xindy 失败，perl 重试成功。"""

    def __init__(self):
        self.calls = []

    def run_command(self, command, out_files, aux_files, program_name="执行命令",
                    stdout_path=None, cwd=None, log_hint=True):
        self.calls.append((list(command), Path(cwd) if cwd else None))
        if len(self.calls) == 1:
            raise SubprocessFailedError(
                command="xindy", exit_code=1,
                stdout="log4cxx: IO Exception : status code = 720005(拒绝访问。)\n"
                       "Sorry, but xindy did not succeed.\n",
                stderr="",
            )
        return True


def test_compile_index_falls_back_to_perl_on_launcher_log_failure(monkeypatch, tmp_path):
    """启动器日志不可写（720005）时改用 perl xindy.pl，从原目录开始试。"""
    auxdir = tmp_path / "Auxiliary"
    auxdir.mkdir()
    (auxdir / "main.xdy").write_text("(define-attributes ())", encoding="utf-8")
    (auxdir / "main.glo").write_text("(indexentry :tkey 1)", encoding="utf-8")
    perl_command = ["perl", "/tex/xindy.pl", *BASE_TOKENS[1:]]
    monkeypatch.setattr(compile_module, "xindy_perl_command", lambda tokens: perl_command)
    monkeypatch.setattr(compile_module, "xindy_fallback_workdirs", lambda: [])
    monkeypatch.setattr(compile_module, "is_dir_writable", lambda path: True)

    compiler = _make_compiler(auxdir)
    compiler.MSP = _LauncherLogFailureMSP()
    compiler.compile_index(("glossaries (main, xindy)", " ".join(BASE_TOKENS)))

    assert len(compiler.MSP.calls) == 2
    retry_cmd, retry_cwd = compiler.MSP.calls[1]
    assert retry_cmd[:2] == ["perl", "/tex/xindy.pl"]
    assert retry_cwd == auxdir.resolve(), "perl 形态应从项目辅助目录先试一次"


def test_xindy_perl_command_prefers_install_script(monkeypatch, tmp_path):
    """按可执行文件位置推导 scripts/xindy/xindy.pl，缺 perl 时返回 None。"""
    executable = tmp_path / "texmfs" / "install" / "miktex" / "bin" / "x64" / "xindy.exe"
    executable.parent.mkdir(parents=True)
    script = tmp_path / "texmfs" / "install" / "scripts" / "xindy" / "xindy.pl"
    script.parent.mkdir(parents=True)
    script.write_text("#", encoding="utf-8")
    monkeypatch.setattr(compile_module.shutil, "which", lambda name: {
        "xindy": str(executable), "perl": "/usr/bin/perl",
    }.get(name))

    command = compile_module.xindy_perl_command(BASE_TOKENS)
    assert command is not None
    assert command[0] == "/usr/bin/perl"
    assert command[1] == str(script)
    assert command[2:] == BASE_TOKENS[1:]

    monkeypatch.setattr(compile_module.shutil, "which", lambda name: str(executable) if name == "xindy" else None)
    assert compile_module.xindy_perl_command(BASE_TOKENS) is None
