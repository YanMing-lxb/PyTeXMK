"""``-r`` 按需报告与 Markdown 导出的回归测试。"""

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

from pytexmk import report_export
from pytexmk.diagnostics import generate_report_from_latest_log

_REPO = Path(__file__).resolve().parents[2]


def _env(tmp_path: Path) -> dict[str, str]:
    env = os.environ.copy()
    env["PYTHONPATH"] = str(_REPO / "src") + os.pathsep + env.get("PYTHONPATH", "")
    env["PYTEXMK_NO_UPDATE_CHECK"] = "1"
    env["USERPROFILE"] = str(tmp_path)
    env["HOME"] = str(tmp_path)
    return env


_SAMPLE_JSON = {
    "schema_version": 1,
    "jobname": "main",
    "root_file": "main.tex",
    "auxdir": "Auxiliary",
    "generated_at": "2026-11-23T00:00:00+00:00",
    "pytexmk_version": "1.2.18",
    "tool_results": [
        {
            "tool_name": "latex",
            "entries": [
                {
                    "level": "warning",
                    "file": "main.tex",
                    "line": 3,
                    "text": "Undefined reference `sec:missing`",
                },
                {
                    "level": "error",
                    "file": "main.tex",
                    "line": 9,
                    "text": "Emergency stop.",
                },
            ],
        }
    ],
}


def test_write_markdown_report_groups_levels_and_hints(tmp_path):
    json_path = tmp_path / "main.pytexmk-report.json"
    md_path = tmp_path / "main.pytexmk-report.md"
    json_path.write_text(json.dumps(_SAMPLE_JSON), encoding="utf-8")

    report_export.write_markdown_report_from_json(json_path, md_path)
    text = md_path.read_text(encoding="utf-8")

    assert "# PyTeXMK 诊断报告：main" in text
    assert "| 主文件 | `main.tex` |" in text
    assert "| 警告 | 1 |" in text and "| 错误 | 1 |" in text
    assert "## 错误（1）" in text and "## 警告（1）" in text
    assert "**`main.tex:3`** — Undefined reference" in text
    assert "> **建议**：" in text, "每条条目都应带一条可执行建议"
    assert "```bash" in text


def test_markdown_report_without_entries(tmp_path):
    json_path = tmp_path / "main.pytexmk-report.json"
    md_path = tmp_path / "main.pytexmk-report.md"
    data = dict(_SAMPLE_JSON, tool_results=[])
    json_path.write_text(json.dumps(data), encoding="utf-8")

    report_export.write_markdown_report_from_json(json_path, md_path)
    text = md_path.read_text(encoding="utf-8")

    assert "| **合计** | **0** |" in text
    assert "日志里没有解析出任何条目。" in text


def test_export_report_keeps_json_when_markdown_write_fails(tmp_path, monkeypatch):
    json_path = tmp_path / "report.json"
    json_path.write_text(json.dumps(_SAMPLE_JSON), encoding="utf-8")

    def _boom(*_args, **_kwargs):
        raise OSError("磁盘只读")

    monkeypatch.setattr(report_export, "atomic_write_text", _boom)
    result = report_export.export_report(json_path, tmp_path / "report.md")

    assert not result.ok
    assert result.json_path == json_path
    assert "磁盘只读" in result.error
    assert json_path.exists()


def test_export_report_reports_missing_json(tmp_path):
    result = report_export.export_report(tmp_path / "absent.json", tmp_path / "out.md")
    assert not result.ok
    assert str(tmp_path / "absent.json") in result.missing


def test_generate_report_requires_readable_log(tmp_path):
    path, reason = generate_report_from_latest_log(tmp_path / "Auxiliary", "main")
    assert path is None
    assert "main.log" in reason


def test_cli_r_generates_json_and_markdown(tmp_path):
    (tmp_path / "main.tex").write_text(
        "\\documentclass{article}\n\\begin{document}\nx\n\\end{document}\n",
        encoding="utf-8",
    )
    aux = tmp_path / "Auxiliary"
    aux.mkdir()
    (aux / "main.log").write_text(
        "This is XeTeX, Version 3.141592653\n"
        "(./main.tex\n"
        "LaTeX Warning: Reference `sec:missing' on page 1 undefined on input line 3.\n"
        ")\n",
        encoding="utf-8",
    )

    proc = subprocess.run(
        [sys.executable, "-m", "pytexmk", "-r"],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        encoding="utf-8",
        env=_env(tmp_path),
        timeout=60,
    )

    assert proc.returncode == 0, proc.stdout + proc.stderr
    json_path = aux / "main.pytexmk-report.json"
    md_path = aux / "main.pytexmk-report.md"
    assert json_path.exists() and md_path.exists()
    assert "**`main.tex:3`**" in md_path.read_text(encoding="utf-8")


def test_cli_r_without_log_exits_nonzero(tmp_path):
    (tmp_path / "main.tex").write_text(
        "\\documentclass{article}\n\\begin{document}x\\end{document}\n",
        encoding="utf-8",
    )

    proc = subprocess.run(
        [sys.executable, "-m", "pytexmk", "-r"],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        encoding="utf-8",
        env=_env(tmp_path),
        timeout=60,
    )

    assert proc.returncode == 1
    assert "无法从最近一次编译日志生成报告" in proc.stdout + proc.stderr


@pytest.mark.parametrize("flag", ["--report", "--fail-on", "--json"])
def test_removed_report_options_are_rejected(flag):
    from pytexmk.cli.cli_args import build_parser

    with pytest.raises(SystemExit) as exc:
        build_parser().parse_args([flag, "x"])
    assert exc.value.code == 2
