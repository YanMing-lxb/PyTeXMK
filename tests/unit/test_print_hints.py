"""打印信息审计整改的回归：可执行命令串、--fail-on 分级、doctor 配置检查。"""

from types import SimpleNamespace

from pytexmk import diagnostics
from pytexmk.config import ConfigParser
from pytexmk.diagnostics import LogSummary


def _entry(level, text, *, file="main.tex", line=1):
    return SimpleNamespace(level=level, text=text, file=file, line=line)


def _report(*entries):
    return SimpleNamespace(tool_results=[SimpleNamespace(entries=list(entries))])


# ------------------------------------------------------- 可执行的 PyTeXLogs 命令


def test_pytexlogs_command_uses_subcommand_and_quotes_spaces():
    assert diagnostics._pytexlogs_command("export", "Build/main.log", "--format", "json") == (
        "pytexlogs export Build/main.log --format json"
    )
    quoted = diagnostics._pytexlogs_command("summary", "Auxiliary/main dir/main.log", "--max-entries", "0")
    assert quoted == 'pytexlogs summary "Auxiliary/main dir/main.log" --max-entries 0'


def test_failure_hint_prints_executable_export_command(monkeypatch, capsys):
    many = [_entry("error", f"Undefined control sequence {i}", line=i) for i in range(diagnostics.MAX_FAILURE_ERRORS + 2)]
    monkeypatch.setattr(diagnostics, "_run_pipeline", lambda **kwargs: _report(*many))
    monkeypatch.setattr(diagnostics, "get_locale_lang", lambda: "en_US")

    diagnostics.report_failure("main", "Auxiliary", "main.tex")

    out = capsys.readouterr().out
    assert "pytexlogs export" in out
    assert "--format json" in out
    # 不能出现旧的、argparse 会拒绝的形态
    assert "pytexlogs main.log --format" not in out


def test_success_hint_prints_executable_summary_command(monkeypatch, capsys):
    many = [_entry("warning", f"LaTeX Warning: Reference `r{i}' undefined on input line {i}.", line=i)
            for i in range(diagnostics.MAX_SUCCESS_WARNINGS + 2)]
    monkeypatch.setattr(diagnostics, "_run_pipeline", lambda **kwargs: _report(*many))
    monkeypatch.setattr(diagnostics, "get_locale_lang", lambda: "en_US")

    diagnostics.report_summary("main", "Auxiliary", "main.tex")

    out = capsys.readouterr().out
    assert "pytexlogs summary" in out
    assert "--max-entries 0" in out


# ------------------------------------------------------------- 分级计数与阈值


def test_report_summary_counts_levels(monkeypatch):
    report = _report(
        _entry("error", "Undefined control sequence"),
        _entry("warning", "LaTeX Warning: Reference `a' undefined on input line 2."),
        _entry("warning", "LaTeX Warning: Reference `b' undefined on input line 3."),
        _entry("typesetting", "Overfull \\hbox (3pt too wide) in paragraph at lines 4--5"),
    )
    monkeypatch.setattr(diagnostics, "_run_pipeline", lambda **kwargs: report)
    monkeypatch.setattr(diagnostics, "get_locale_lang", lambda: "en_US")

    summary = diagnostics.report_summary("main", "Auxiliary", "main.tex")

    assert isinstance(summary, LogSummary)
    assert (summary.errors, summary.warnings, summary.typesetting) == (1, 2, 1)
    assert summary.warn_total == 3


# ---------------------------------------------------------------- 配置错误记录


def test_config_records_toml_parse_error(tmp_path):
    project = tmp_path / "proj"
    project.mkdir()
    (project / ".pytexmkrc").write_text('default_file = "main"\n= 1\n', encoding="utf-8")

    cp = ConfigParser()
    cp.user_config_path = None  # 隔离用户级配置
    cp.load_config(project)

    assert (project / ".pytexmkrc") in cp.load_errors


def test_config_clears_errors_between_loads(tmp_path):
    project = tmp_path / "proj"
    project.mkdir()
    rc = project / ".pytexmkrc"
    rc.write_text('= 1\n', encoding="utf-8")

    cp = ConfigParser()
    cp.user_config_path = None
    cp.load_config(project)
    assert cp.load_errors

    rc.write_text('default_file = "main"\n', encoding="utf-8")
    cp.load_config(project)
    assert cp.load_errors == {}
