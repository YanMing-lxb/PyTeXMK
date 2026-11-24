"""退出码与退出提示：0 静默，非 0 必须说明原因。"""
from types import SimpleNamespace

import pytest

from pytexmk import lifecycle


def test_zero_exits_silently(capsys):
    with pytest.raises(SystemExit) as exc:
        lifecycle.exit_pytexmk(0)
    assert exc.value.code == 0
    out, err = capsys.readouterr()
    assert "退出" not in out + err


@pytest.mark.parametrize(
    ("code", "reason"),
    [
        (lifecycle.EXIT_ERROR, "遇到错误"),
        (lifecycle.EXIT_PROJECT_NOT_FOUND, "未找到"),
        (lifecycle.EXIT_CONFIG_ERROR, "配置文件错误"),
        (lifecycle.EXIT_COMPILE_FAILED, "编译失败"),
        (lifecycle.EXIT_REPORT_FAILED, "报告导出失败"),
    ],
)
def test_each_error_code_has_reason(code, reason, capsys):
    with pytest.raises(SystemExit) as exc:
        lifecycle.exit_pytexmk(code)
    assert exc.value.code == code
    assert reason in capsys.readouterr().out


def test_unknown_code_gets_generic_reason(capsys):
    with pytest.raises(SystemExit) as exc:
        lifecycle.exit_pytexmk(77)
    assert exc.value.code == 77
    assert "异常退出" in capsys.readouterr().out


def test_console_failure_falls_back_to_stderr(monkeypatch, capsys):
    def boom(*args, **kwargs):
        raise RuntimeError("控制台不可用")

    monkeypatch.setattr(lifecycle, "console", SimpleNamespace(print=boom))
    with pytest.raises(SystemExit):
        lifecycle.exit_pytexmk(lifecycle.EXIT_COMPILE_FAILED)
    assert "编译失败" in capsys.readouterr().err
