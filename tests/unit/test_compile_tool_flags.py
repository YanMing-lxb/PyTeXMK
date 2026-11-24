"""biber / bib2gls 的 quiet 旗标必须跟随 ``non_quiet``。

这两个工具的输出量很大，默认必须静音；``-nq`` 时才交给终端。
"""
import pytest

from pytexmk.compile import BibEngine, CompileLaTeX


def _model(tmp_path, non_quiet: bool) -> CompileLaTeX:
    return CompileLaTeX(
        "main",
        "XeLaTeX",
        [".pdf"],
        [".aux"],
        str(tmp_path / "Build"),
        str(tmp_path / "Auxiliary"),
        non_quiet,
        native=True,
    )


def _captured(model: CompileLaTeX, invoke) -> list[str]:
    calls: list[list[str]] = []
    model.MSP.run_command = lambda command, out_files, aux_files, program: calls.append(command)
    invoke(model)
    assert len(calls) == 1
    return calls[0]


@pytest.mark.parametrize("non_quiet", [False, True])
def test_biber_quiet_flag(tmp_path, non_quiet):
    command = _captured(
        _model(tmp_path, non_quiet), lambda m: m.compile_bib(BibEngine.BIBER)
    )
    assert ("-quiet" in command) is (not non_quiet)
    # biber 的输入目录必须指向 auxdir（.bcf 在那里）
    assert command[command.index("--input-directory") + 1] == str(tmp_path / "Auxiliary")


@pytest.mark.parametrize("non_quiet", [False, True])
def test_bib2gls_quiet_flag(tmp_path, non_quiet):
    command = _captured(_model(tmp_path, non_quiet), lambda m: m.compile_bib2gls())
    assert ("--quiet" in command) is (not non_quiet)
    assert f"--dir={(tmp_path / 'Auxiliary').resolve()}" in command


def test_bibtex_has_no_quiet_flag(tmp_path):
    command = _captured(
        _model(tmp_path, False), lambda m: m.compile_bib(BibEngine.BIBTEX)
    )
    assert command[0] == "bibtex"
    assert "-quiet" not in command
