"""2026-11-23 第二轮改进的回归测试。

覆盖递归清理、普通编译消费配置校验、-c 的真实删除清单、tool-pending 文案、
preflight/投稿扫描对注释与 verbatim 的处理。
"""

import os
import re
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

from pytexmk import lifecycle
from pytexmk.cli import cli_compile, cli_context, cli_workflow
from pytexmk.cli.cli_state import SUFFIXES_AUX
from pytexmk.compile_report import STOP_REASON_MESSAGES
from pytexmk.file_ops import FileMoveRemoveManager
from pytexmk.layout import AUX_SUFFIXES
from pytexmk.preflight import check_project
from pytexmk.submission import scan_compat

_REPO = Path(__file__).resolve().parents[2]


def _aux_patterns() -> list[re.Pattern[str]]:
    return [re.compile(rf".*{re.escape(suffix)}$") for suffix in SUFFIXES_AUX]


# ---------------------------------------------------------------- 递归清理所有权


def test_generic_xml_and_tmp_are_not_aux_artifacts():
    """`.xml`/`.tmp` 是通用用户文件；只有 `.run.xml` 是 biber 的真实产物。"""
    assert ".xml" not in AUX_SUFFIXES
    assert ".tmp" not in AUX_SUFFIXES
    assert ".run.xml" in AUX_SUFFIXES

    patterns = _aux_patterns()
    assert not any(p.match("records.xml") for p in patterns)
    assert not any(p.match("notes.tmp") for p in patterns)
    assert any(p.match("main.run.xml") for p in patterns)


def test_recursive_clean_keeps_user_xml_and_tmp(tmp_path, monkeypatch):
    """旧行为：`-ca` 递归删除 `data/records.xml` 与 `notes.tmp`。"""
    monkeypatch.chdir(tmp_path)
    (tmp_path / "data").mkdir()
    (tmp_path / "main.aux").write_text("aux", encoding="utf-8")
    (tmp_path / "main.run.xml").write_text("<run/>", encoding="utf-8")
    (tmp_path / "notes.tmp").write_text("用户临时文件", encoding="utf-8")
    (tmp_path / "data" / "records.xml").write_text("<records/>", encoding="utf-8")

    state = SimpleNamespace(
        aux_regex_files=_aux_patterns(),
        output_name="main",
        outdir="Build",
        out_files=["main.pdf"],
    )
    targets = cli_compile._recursive_clean_targets(
        SimpleNamespace(clean_recursive_out=False), state
    )
    names = {path.name for path in targets}
    assert names == {"main.aux", "main.run.xml"}


def test_resolve_clean_target_is_best_effort(tmp_path, monkeypatch):
    """有两个主文件且无 default_file 时，-ca 不退出，只把 jobname 留空。"""
    monkeypatch.chdir(tmp_path)

    class _Logger:
        def warning(self, *_a, **_k):
            pass

    args = SimpleNamespace(document=None)
    state = SimpleNamespace(
        main_files_in_root=["a", "b"],
        default_file="main",
        explicit_default=False,
        all_magic_comments={},
        logger=_Logger(),
        project_name="",
        output_name="main",
    )
    cli_context.resolve_clean_target(args, state)
    assert state.project_name == ""
    assert state.output_name == ""

    state.main_files_in_root = ["main"]
    cli_context.resolve_clean_target(args, state)
    assert (state.project_name, state.output_name) == ("main", "main")


def test_clean_recursive_works_without_a_main_file(tmp_path):
    """真实 CLI：没有主文件时 -ca 仍递归清理辅助产物并以 0 结束。"""
    (tmp_path / "chapter.tex").write_text("chapter", encoding="utf-8")
    (tmp_path / "orphan.aux").write_text("aux", encoding="utf-8")
    result = subprocess.run(
        [sys.executable, "-m", "pytexmk", "-ca"],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        env=_cli_env(tmp_path),
        timeout=30,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert not (tmp_path / "orphan.aux").exists()


# ---------------------------------------------------------------- 配置校验


def _cli_env(tmp_path: Path) -> dict[str, str]:
    env = os.environ.copy()
    env["PYTHONPATH"] = str(_REPO / "src") + os.pathsep + env.get("PYTHONPATH", "")
    env["PYTEXMK_NO_UPDATE_CHECK"] = "1"
    # 隔离真实用户配置，避免 home 下的 .pytexmkrc 干扰
    env["USERPROFILE"] = str(tmp_path)
    env["HOME"] = str(tmp_path)
    return env


def test_bad_section_type_exits_with_config_error_not_traceback(tmp_path):
    """旧行为：`build = "oops"` 进入普通编译后抛 AttributeError traceback。"""
    (tmp_path / "main.tex").write_text(
        "\\documentclass{article}\n\\begin{document}x\\end{document}\n",
        encoding="utf-8",
    )
    (tmp_path / ".pytexmkrc").write_text('build = "oops"\n', encoding="utf-8")
    result = subprocess.run(
        [sys.executable, "-m", "pytexmk"],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        env=_cli_env(tmp_path),
        timeout=30,
    )
    output = result.stdout + result.stderr
    assert result.returncode == 4, output
    assert "配置校验失败" in output
    assert "Traceback" not in output


def test_config_errors_accepts_scrollmode(tmp_path):
    """配置层支持 scrollmode，语义检查集合不能漏掉它。"""
    from pytexmk.cli.cli_config import config_errors
    from pytexmk.config import ConfigParser

    (tmp_path / ".pytexmkrc").write_text(
        '[build]\ninteraction = "scrollmode"\n', encoding="utf-8"
    )
    cp = ConfigParser()
    cp.user_config_path = tmp_path / "user.toml"
    assert config_errors(cp.load_config(tmp_path), cp.load_errors) == []


# ---------------------------------------------------------------- 诊断与 JSON


def test_tool_pending_has_its_own_conclusion_text():
    message = STOP_REASON_MESSAGES["tool-pending"]
    assert "未完全收敛" in message
    assert "额外编译预算" in message


def test_clean_short_flag_does_not_recurse(tmp_path):
    """`-c` 只清辅助目录；子目录里的孤立产物不在其范围内。"""
    import subprocess
    import sys

    (tmp_path / "main.tex").write_text(
        "\\documentclass{article}\n\\begin{document}\nmain\n\\end{document}",
        encoding="utf-8",
    )
    (tmp_path / "Auxiliary").mkdir()
    (tmp_path / "Auxiliary" / "main.bbl").write_text("bbl", encoding="utf-8")
    (tmp_path / "chapters").mkdir()
    (tmp_path / "chapters" / "orphan.aux").write_text("aux", encoding="utf-8")

    proc = subprocess.run(
        [sys.executable, "-m", "pytexmk", "-c"],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=120,
        env=_cli_env(tmp_path),
    )
    assert proc.returncode == 0, proc.stderr[-2000:]
    assert not (tmp_path / "Auxiliary" / "main.bbl").exists()
    assert (tmp_path / "chapters" / "orphan.aux").exists()


def test_clean_returns_actual_removals(tmp_path, monkeypatch):
    """-c/-C 也要把 .bbl/.xdv 当作辅助产物清理，而不是只删 .aux/.log。"""
    monkeypatch.chdir(tmp_path)
    (tmp_path / "main.aux").write_text("aux", encoding="utf-8")
    (tmp_path / "main.bbl").write_text("bbl", encoding="utf-8")
    (tmp_path / "main.xdv").write_text("xdv", encoding="utf-8")
    state = SimpleNamespace(
        auxdir=".",
        output_name="main",
        aux_files=["main.aux", "main.log", "main.bbl", "main.xdv"],
        out_files=["main.pdf"],
        runtime_dict={},
        mro=FileMoveRemoveManager(),
    )
    args = SimpleNamespace(clean_out=False)

    removed, failed = cli_compile._clean(args, state)
    assert failed == []
    assert {path.name for path in removed} == {"main.aux", "main.bbl", "main.xdv"}
    assert not (tmp_path / "main.aux").exists()
    assert not (tmp_path / "main.bbl").exists()
    assert not (tmp_path / "main.xdv").exists()


def test_all_subprojects_does_not_inherit_watch(tmp_path, monkeypatch):
    """`-ap -w` 必须关掉子项目的 watch，否则第一个子项目永远不返回。"""
    from pytexmk.config import ConfigParser
    from pytexmk.lifecycle import EXIT_OK

    monkeypatch.chdir(tmp_path)
    (tmp_path / ".pytexmkrc").write_text(
        '[subprojects]\none = "one/paper.tex"\n', encoding="utf-8"
    )
    cp = ConfigParser()
    cp.user_config_path = tmp_path / "user.toml"

    seen: list[bool] = []
    monkeypatch.setattr(
        cli_workflow, "run_workflow", lambda sub_args: seen.append(sub_args.watch)
    )

    def _stop(code=0):
        raise SystemExit(code)

    monkeypatch.setattr(lifecycle, "exit_pytexmk", _stop)
    args = SimpleNamespace(
        watch=True,
        subproject=None,
        all_subprojects=True,
        document=None,
    )
    logger = SimpleNamespace(exception=lambda *_a: None, error=lambda *_a: None)

    with pytest.raises(SystemExit) as exc:
        cli_workflow._run_all_subprojects(args, cp, logger)
    assert exc.value.code == EXIT_OK
    assert seen == [False]


# ---------------------------------------------------------------- preflight / 投稿


def test_preflight_ignores_input_in_verbatim(tmp_path):
    (tmp_path / "main.tex").write_text(
        "\\documentclass{article}\n"
        "\\begin{document}\n"
        "\\begin{verbatim}\n"
        "\\input{not-a-real-file}\n"
        "\\end{verbatim}\n"
        "\\end{document}\n",
        encoding="utf-8",
    )
    report = check_project("main", tmp_path)
    assert report.errors == []
    assert report.warnings == []


def test_compat_scan_ignores_commented_package(tmp_path):
    (tmp_path / "main.tex").write_text(
        "\\documentclass{article}\n"
        "% \\usepackage{fontspec}\n"
        "\\begin{document}x\\end{document}\n",
        encoding="utf-8",
    )
    report = scan_compat(tmp_path, [tmp_path / "main.tex"])
    assert report.incompatible_packages == {}


def test_unknown_legacy_key_only_fails_strict_validation():
    """普通编译只拦会崩溃的类型错误；旧版遗留段只在严格校验里报警。"""
    import copy

    from pytexmk.cli.cli_config import DEFAULT_CONFIG, config_errors

    config = copy.deepcopy(DEFAULT_CONFIG)
    config["main"] = {"latex_compiled_program": "XeLaTeX"}

    assert any("未知配置项" in error for error in config_errors(config, strict=True))
    assert config_errors(config, strict=False) == []

