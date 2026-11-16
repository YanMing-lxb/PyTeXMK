"""Shell 补全脚本生成的回归测试。"""

from pytexmk.cli.cli_completion import completion_text


def test_completion_contains_new_options():
    for shell in ("bash", "zsh", "fish", "powershell"):
        text = completion_text(shell)
        assert "jobname" in text
        assert "synctex-check" in text
        assert "report" in text


def test_bash_completion_has_register_line():
    text = completion_text("bash")
    assert "complete -F _pytexmk_complete pytexmk" in text


def test_powershell_completion_registers_native():
    text = completion_text("powershell")
    assert "Register-ArgumentCompleter -Native" in text
