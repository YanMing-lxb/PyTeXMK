"""PythonTeX 自动调度：.pytxcode 探测、工作目录与后置 LaTeX 轮次。"""

from pathlib import Path

from pytexmk.compile import CompileLaTeX
from pytexmk.compile_engine import _run_pythontex_if_present


def _model(tmp_path: Path, *, native: bool = True) -> CompileLaTeX:
    aux = tmp_path / "Auxiliary"
    aux.mkdir()
    return CompileLaTeX(
        "main",
        "XeLaTeX",
        [],
        [],
        str(tmp_path / "Build"),
        str(aux),
        False,
        native=native,
    )


def test_pythontex_code_is_detected_in_auxdir(tmp_path):
    model = _model(tmp_path)
    code = Path(model.auxdir) / "main.pytxcode"
    code.write_text("", encoding="utf-8")

    assert model.has_pythontex_code() is True
    assert model._pythontex_code_path() == code


def test_compile_pythontex_runs_in_code_directory(tmp_path):
    model = _model(tmp_path)
    (Path(model.auxdir) / "main.pytxcode").write_text("", encoding="utf-8")
    calls = []

    def fake_run(command, out_files, aux_files, program_name, **kwargs):
        calls.append((command, program_name, kwargs))
        return True

    model.MSP.run_command = fake_run
    model.compile_pythontex()

    assert calls[0][0] == ["pythontex", "main"]
    assert calls[0][1] == "pythontex"
    assert calls[0][2]["cwd"] == Path(model.auxdir).resolve()


def test_run_pythontex_then_recompiles(monkeypatch):
    events = []

    class FakeModel:
        def has_pythontex_code(self):
            return True

        def compile_pythontex(self):
            events.append("pythontex")

        def compile_tex(self):
            events.append("latex")

    runtime = {}
    assert _run_pythontex_if_present(FakeModel(), runtime, "XeLaTeX") is True
    assert events == ["pythontex", "latex"]
    assert "pythontex" in runtime
    # timings 的键是稳定 slug（显示名在 time_print 里按语言翻译）
    assert "latex_after_pythontex" in runtime
