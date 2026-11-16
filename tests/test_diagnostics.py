"""诊断展示层回归：0.5 参数直连、上下文建议、警告也显示建议。"""

from types import SimpleNamespace

from pytexmk import diagnostics


def _entry(level, text, *, file="main.tex", line=1):
    return SimpleNamespace(level=level, text=text, file=file, line=line)


def _report(*entries):
    return SimpleNamespace(tool_results=[SimpleNamespace(entries=list(entries))])


def test_run_pipeline_uses_pytexlogs_050_kwargs(monkeypatch):
    captured = {}

    def fake_run_pipeline(**kwargs):
        captured.update(kwargs)
        return object()

    monkeypatch.setattr("pytexlogs.run_pipeline", fake_run_pipeline)
    result = diagnostics._run_pipeline(
        jobname="main",
        auxdir="Build",
        root_file="main.tex",
        translate_fn=str,
        write_report=True,
        report_path="Build/report.json",
    )

    assert result is not None
    assert captured["write_report_file"] is True
    assert captured["report_path"] == "Build/report.json"
    assert "report" not in captured  # 旧参数名不再出现


def test_iter_entries_sorts_by_level_file_and_line():
    report = _report(
        _entry("warning", "w-late", line=9),
        _entry("error", "e-b", line=20),
        _entry("error", "e-a", line=2),
    )

    rows = diagnostics._iter_entries(report)

    assert [row[1].text for row in rows] == ["e-a", "e-b", "w-late"]


def test_entry_hint_fills_jobname_and_root_file():
    entry = _entry(
        "error",
        "LaTeX Warning: Citation `foo' on page 1 undefined on input line 10.",
    )

    hint = diagnostics._entry_hint(entry, jobname="main", root_file="main.tex")

    assert hint is not None
    assert "biber main" in hint.commands
    assert "bibtex main" in hint.commands


def test_report_success_shows_hint_for_warning(monkeypatch, capsys):
    warning = _entry(
        "warning",
        "LaTeX Warning: Citation `foo' on page 1 undefined on input line 10.",
    )
    report = _report(warning)
    monkeypatch.setattr(diagnostics, "_run_pipeline", lambda **kwargs: report)
    monkeypatch.setattr(diagnostics, "get_locale_lang", lambda: "en_US")

    count = diagnostics.report_success("main", "Build", "main.tex")

    out = capsys.readouterr().out
    assert count == 1
    assert "biber main" in out
    assert "引用键" not in out  # 英文 locale 下不应混入中文建议
    assert "Citation key `foo` is undefined" in out
