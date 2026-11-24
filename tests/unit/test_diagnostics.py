"""诊断展示层回归：0.5 参数直连、上下文建议、警告也显示建议。"""

from types import SimpleNamespace

from pytexmk import diagnostics
from pytexmk.timing import get_text_len

# 0.6.3 的 diagnose 展示层契约：等级顺序取自库、hint 带 tool_name 作用域、
# JSON issue 带稳定 rule_id、报告路径以实际落盘结果为准、摘要宽度跟随 78 列横幅。


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


def test_report_summary_shows_hint_for_warning(monkeypatch, capsys):
    warning = _entry(
        "warning",
        "LaTeX Warning: Citation `foo' on page 1 undefined on input line 10.",
    )
    report = _report(warning)
    monkeypatch.setattr(diagnostics, "_run_pipeline", lambda **kwargs: report)
    monkeypatch.setattr(diagnostics, "get_locale_lang", lambda: "en_US")

    summary = diagnostics.report_summary("main", "Build", "main.tex")

    out = capsys.readouterr().out
    assert summary.warn_total == 1
    assert "引用键" not in out  # 英文 locale 下不应混入中文建议
    assert "Citation key `foo` is undefined" in out
    if diagnostics._has_pytexlogs_footer():
        # 0.6.4+：hint 默认 brief，不再带 biber/bibtex 命令，并在最后给页脚。
        assert "biber main" not in out
        assert "Next: check the warnings above" in out


def test_report_failure_uses_pytexlogs_grouped_layout(monkeypatch, capsys, tmp_path):
    """失败摘要走 PyTeXLogs 的 ``[E]`` + ``+-- [分类]`` 分组版式。"""
    entry = _entry("error", "! Undefined control sequence.", file="main.tex", line=10)
    entry.error_pos_text = "\\badcmd"
    tool = SimpleNamespace(
        tool_name="lualatex",
        category="compile",
        importance="high",
        source_path=None,
        entries=[entry],
    )
    report = SimpleNamespace(tool_results=[tool])
    monkeypatch.setattr(diagnostics, "_run_pipeline", lambda **kwargs: report)
    monkeypatch.setattr(diagnostics, "log_readable", lambda *args, **kwargs: True)
    monkeypatch.setattr(diagnostics, "get_locale_lang", lambda: "zh_CN")

    summary = diagnostics.report_failure("main", str(tmp_path), "main.tex")

    out = capsys.readouterr().out
    assert summary.errors == 1
    assert "[E]" in out
    assert "+-- [一般编译]" in out
    assert "✗" not in out  # 旧版手写列表不再出现
    assert "↳" in out  # 分组版式仍保留可执行建议
    # 0.6.3 起版式宽度可配：横幅必须与 PyTeXMK 自己的 78 列分隔线同宽，
    # 不能落回库默认的 74 列（按显示列数比较，中文按 2 列）。
    banner = next(line for line in out.splitlines() if "错误汇总" in line)
    assert get_text_len(banner) == diagnostics.total_len


def test_print_failure_groups_passes_total_len_width(monkeypatch):
    """0.6.3 的 ``print_summary(width=)`` 必须显式收到 PyTeXMK 的横幅宽度。"""
    captured = {}

    def fake_print_summary(logs, **kwargs):
        captured["logs"] = logs
        captured.update(kwargs)
        return ""

    monkeypatch.setattr("pytexlogs.print_summary", fake_print_summary)
    entry = _entry("error", "! Undefined control sequence.")
    entry.error_pos_text = "\\badcmd"
    tool = SimpleNamespace(tool_name="xelatex", category="compile", importance="high", source_path=None)

    diagnostics._print_failure_groups([(0, entry, tool)], jobname="main", root_file="main.tex")

    assert captured["width"] == diagnostics.total_len
    assert captured["show_hints"] is True
    assert len(captured["logs"]) == 1

def test_report_summary_uses_pytexlogs_grouped_layout(monkeypatch, capsys, tmp_path):
    """成功摘要也走 ``==== 警告汇总 ====`` + ``+-- [分类]`` 分组版式。

    PyTeXMK 不再自己手写 ``! file:line`` 紧凑列表：两套版式会让同一次编译的
    警告长得不一样，用户也无法把输出和 ``pytexlogs summary`` 对照。
    """
    warnings = [
        _entry("warning", f"LaTeX Warning: Reference `r{i}' undefined on input line {i}.", line=i)
        for i in range(1, diagnostics.MAX_SUCCESS_WARNINGS + 3)
    ]
    monkeypatch.setattr(diagnostics, "_run_pipeline", lambda **kwargs: _report(*warnings))
    monkeypatch.setattr(diagnostics, "log_readable", lambda *args, **kwargs: True)
    monkeypatch.setattr(diagnostics, "get_locale_lang", lambda: "zh_CN")

    diagnostics.report_summary("main", str(tmp_path), "main.tex")

    out = capsys.readouterr().out
    assert "警告汇总" in out
    assert "+-- [一般编译]" in out
    assert "↳" in out  # 分组版式仍保留可执行建议
    assert "提示：" not in out  # 旧版自写的“提示：N 个警告”不再出现
    # 横幅宽度必须和 PyTeXMK 的 78 列分隔线一致，不能落回库默认的 74 列。
    banner = next(line for line in out.splitlines() if "警告汇总" in line)
    assert get_text_len(banner) == diagnostics.total_len


def test_report_summary_passes_max_entries_per_group(monkeypatch):
    """折叠上限通过 0.6.3 的 ``max_entries=`` 交给库，而不是在本地截断条目。"""
    captured = {}

    def fake_print_summary(logs, **kwargs):
        captured["logs"] = logs
        captured.update(kwargs)
        return ""

    monkeypatch.setattr("pytexlogs.print_summary", fake_print_summary)
    warnings = [_entry("warning", f"LaTeX Warning: Reference `r{i}' undefined on input line {i}.", line=i)
                for i in range(1, 5)]
    monkeypatch.setattr(diagnostics, "_run_pipeline", lambda **kwargs: _report(*warnings))
    monkeypatch.setattr(diagnostics, "log_readable", lambda *args, **kwargs: True)

    diagnostics.report_summary("main", "Auxiliary", "main.tex")

    assert captured["max_entries"] == diagnostics.MAX_SUCCESS_WARNINGS
    assert captured["width"] == diagnostics.total_len
    assert captured["show_hints"] is True
    # 条目全量交给库（组标题里的计数才是真实总数），折叠由 max_entries 负责。
    assert sum(len(plog.entries) for plog in captured["logs"]) == len(warnings)


def test_log_looks_truncated_detects_mid_shipout(tmp_path):
    """日志停在 [1 且没有 Output written，判定为写出 PDF 前被中断。"""
    log = tmp_path / "main.log"
    log.write_text("This is XeTeX...\n[1", encoding="utf-8")
    assert diagnostics._log_looks_truncated(log) is True

    log.write_text("... [1\nOutput written on main.pdf (1 page).\n", encoding="utf-8")
    assert diagnostics._log_looks_truncated(log) is False

    log.write_text("LaTeX Warning: undefined references\n", encoding="utf-8")
    assert diagnostics._log_looks_truncated(log) is False


def test_log_looks_truncated_handles_missing_file(tmp_path):
    """日志不存在时不做推断，避免掩盖真正的编译失败。"""
    assert diagnostics._log_looks_truncated(tmp_path / "absent.log") is False


def test_iter_entries_follows_pytexlogs_severity_order():
    """0.6.1 起 INFO 在 TYPESET 之前，展示层不能再写死旧顺序。"""
    report = _report(
        _entry("typesetting", "t-1", line=3),
        _entry("font", "f-1", line=4),
        _entry("info", "i-1", line=2),
        _entry("error", "e-1", line=1),
    )

    rows = diagnostics._iter_entries(report)

    assert [row[1].text for row in rows] == ["e-1", "i-1", "t-1", "f-1"]


def test_report_summary_counts_typesetting_by_name(monkeypatch):
    """TYPESET 只计入 typesetting，不再靠枚举序号猜测。"""
    report = _report(
        _entry("info", "i-1"),
        _entry("typesetting", "t-1"),
        _entry("font", "f-1"),
    )
    monkeypatch.setattr(diagnostics, "_run_pipeline", lambda **kwargs: report)
    summary = diagnostics.report_summary("main", "Build", "main.tex")

    assert summary.typesetting == 1
    assert summary.warnings == 0
    assert summary.errors == 0


def test_entry_hint_forwards_tool_name_scope(monkeypatch):
    """0.6.2 的 hint 按工具作用域匹配，展示层必须把 tool_name 透传下去。"""
    captured = {}

    def fake_hint_for_entry(entry, **kwargs):
        captured.update(kwargs)
        return None

    monkeypatch.setattr("pytexlogs.hint_for_entry", fake_hint_for_entry)

    diagnostics._entry_hint(
        _entry("warning", "WARN - something"),
        jobname="main",
        root_file="main.tex",
        tool_name="biber",
    )

    assert captured["tool_name"] == "biber"
    assert captured["jobname"] == "main"


def test_entry_issue_carries_stable_rule_id():
    """JSON issue 带 0.6.2 的 rule_id，编辑器据此映射规则而不依赖文案。"""
    entry = _entry("error", "! Undefined control sequence.")
    entry.error_pos_text = "\\badcmd"

    issue = diagnostics._entry_issue(
        entry, jobname="main", root_file="main.tex", tool_name="xelatex"
    )

    assert issue["rule_id"] == "undefined_control"
    assert issue["level"] == "error"


def test_entry_issue_omits_rule_id_without_hint():
    entry = _entry("warning", "普通警告：没有任何规则命中")

    issue = diagnostics._entry_issue(entry, jobname="main", root_file="main.tex")

    assert "rule_id" not in issue


def test_log_summary_reports_actual_report_path(monkeypatch):
    report = SimpleNamespace(
        tool_results=[],
        custom_fields={"_report_path": "Build/main.pytexmk-report.json"},
    )
    monkeypatch.setattr(diagnostics, "_run_pipeline", lambda **kwargs: report)

    summary = diagnostics.report_summary("main", "Build", "main.tex")

    assert summary.report_path == "Build/main.pytexmk-report.json"
    assert summary.report_error is None


def test_log_summary_surfaces_report_write_error(monkeypatch):
    """0.6.2 写盘失败不抛异常，只留 _report_write_error，必须显式暴露。"""
    report = SimpleNamespace(
        tool_results=[],
        custom_fields={"_report_write_error": "OSError: disk full"},
    )
    monkeypatch.setattr(diagnostics, "_run_pipeline", lambda **kwargs: report)

    summary = diagnostics.report_summary("main", "Build", "main.tex")

    assert summary.report_path is None
    assert summary.report_error == "OSError: disk full"
