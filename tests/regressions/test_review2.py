"""第二轮全仓复审（2026-11-18）修复的回归测试。

覆盖报告第十一节 R1–R7：
* R1 stdout 落盘时 stderr 不能混进输出文件（否则产物第一行是告警，后续解析/
  编译直接报错）；
* R3 源目录不存在时 ``move_matched_files`` 返回 0 而不是抛 FileNotFoundError；
* R4 glossaries-extra + bib2gls 的识别不能依赖 biblatex/biber 标记；
* R5 ``.ist``/``.xdy`` 这类用户可能手写的样式文件不得被静默删除；
* R6 SyncTeX 缺产物用结构化标记，而不是匹配本地化文案；
* R7 ``[submission]`` 配置键确实被 ``-sp`` 使用，模板里的死键已清除。
"""

import re
import sys
import tomllib
from pathlib import Path
from types import SimpleNamespace

import pytexmk
from pytexmk import subprocess_runner, synctex
from pytexmk.cli import cli_compile
from pytexmk.config import DEFAULT_CONFIG
from pytexmk.detection import CompilationDetector
from pytexmk.file_ops import FileMoveRemoveManager

DATA_DIR = Path(pytexmk.__file__).parent / "data"


# ---------------------------------------------------------------------- R1


def test_redirect_stdout_file_excludes_stderr(tmp_path, monkeypatch):
    """重定向到文件的只有 stdout；stderr 进管道，不污染产物。"""
    import io

    from rich.console import Console

    from pytexmk import ui_theme

    monkeypatch.setattr(
        subprocess_runner,
        "console",
        Console(
            file=io.StringIO(),
            width=200,
            force_terminal=False,
            no_color=True,
            theme=ui_theme.custom_theme,
        ),
    )
    output = tmp_path / "tool-out.tex"
    command = [
        sys.executable,
        "-c",
        "import sys; print('DOC'); print('log4cxx: denied', file=sys.stderr)",
    ]
    process = subprocess_runner.MySubProcess(".", ".", "demo")
    assert process.run_command(command, [], [], "demo-tool", stdout_path=str(output)) is True

    text = output.read_text(encoding="utf-8")
    assert "DOC" in text
    assert "log4cxx" not in text


# ---------------------------------------------------------------------- R3


def test_move_matched_files_missing_source_is_noop(tmp_path):
    manager = FileMoveRemoveManager()
    assert manager.move_matched_files([re.compile(r".*")], str(tmp_path / "nope"), ".") == 0


# ---------------------------------------------------------------------- R4


def test_bib2gls_detected_without_biber_markers(tmp_path, monkeypatch):
    """record 模式只写 ``\\glsxtr@record``，不写 ``\\abx@aux@refcontext``。"""
    monkeypatch.chdir(tmp_path)
    (tmp_path / "main.aux").write_text(
        "\\@newglossary{main}{glg}{gls}{glo}\n"
        "\\glsxtr@record{alpha}{}{page}{glsnumberformat}{1}\n",
        encoding="utf-8",
    )
    detector = CompilationDetector(
        "main",
        "XeLaTeX",
        ["main.pdf"],
        ["main.aux"],
        "Build",
        "Auxiliary",
        False,
        FileMoveRemoveManager(),
        jobname="main",
        native=False,
    )
    engine, times, _target = detector.bib_judgment({})

    assert detector.bib2gls_mode is True
    assert engine is None  # 纯 bib2gls 项目没有 biber
    assert times == 2  # bib2gls 之后还要两轮 LaTeX 才能把术语表排进 PDF


def test_bib2gls_flag_lives_on_detector_not_detection_result():
    """``DetectionResult`` 只装聚合结果，没有 ``bib2gls_mode``。

    这条断言就是 R4 的成因备忘：引擎若再写回
    ``getattr(detection, "bib2gls_mode", False)``，会静默失效。
    """
    from pytexmk.detection import DetectionResult

    assert "bib2gls_mode" not in DetectionResult._fields


# ---------------------------------------------------------------------- R5


def test_sweep_keeps_user_style_files(tmp_path, monkeypatch):
    """同名但内容不同的 .xdy/.ist 是用户手写样式，必须保留。"""
    monkeypatch.chdir(tmp_path)
    (tmp_path / "Auxiliary").mkdir()
    (tmp_path / "main.xdy").write_text(";; user style", encoding="utf-8")
    (tmp_path / "Auxiliary" / "main.xdy").write_text(";; generated", encoding="utf-8")
    (tmp_path / "main.ist").write_text(";; user makeindex style", encoding="utf-8")

    state = SimpleNamespace(auxdir="Auxiliary", aux_files=["main.ist", "main.xdy"])
    cli_compile._sweep_stale_root_aux(state)

    assert (tmp_path / "main.xdy").exists()
    assert (tmp_path / "main.ist").exists()


def test_sweep_removes_identical_root_copy(tmp_path, monkeypatch):
    """内容完全一致时，根目录那份只是旧副本，可以安全删除。"""
    monkeypatch.chdir(tmp_path)
    (tmp_path / "Auxiliary").mkdir()
    (tmp_path / "main.xdy").write_text(";; same", encoding="utf-8")
    (tmp_path / "Auxiliary" / "main.xdy").write_text(";; same", encoding="utf-8")

    state = SimpleNamespace(auxdir="Auxiliary", aux_files=["main.xdy"])
    cli_compile._sweep_stale_root_aux(state)

    assert not (tmp_path / "main.xdy").exists()


def test_index_artifact_suffixes_exclude_user_inputs():
    """`.ist` 是 makeindex 的输入样式文件，不能进"自动删除"清单。"""
    assert ".ist" not in cli_compile.INDEX_ARTIFACT_SUFFIXES


# ---------------------------------------------------------------------- R6


def test_synctex_missing_artifact_is_structured(tmp_path):
    report = synctex.check(tmp_path / "missing.pdf", tmp_path / "main.tex")
    assert report.missing_artifact == "pdf"
    assert report.ok is False


# ---------------------------------------------------------------------- R7


def test_submission_pack_uses_config_flags(tmp_path, monkeypatch):
    from pytexmk import submission

    captured: dict = {}
    pack = tmp_path / "pack.zip"
    pack.write_bytes(b"x")

    class FakeResult:
        zip_path = pack
        files = ["main.tex"]
        pdf_pages = 3
        pdf_bytes = 1024
        rounds = 1
        sanitized = []
        sha256 = ""
        log_path = None
        used_fls = True
        fls_path = None
        stale_sources: list[str] = []
        sanitize = True
        compat = SimpleNamespace(
            ok=True,
            non_ascii_chars={},
            incompatible_packages={},
            char_locations={},
        )

    def fake_build_pack(*args, **kwargs):
        captured.update(kwargs)
        return FakeResult()

    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(submission, "build_pack", fake_build_pack)

    state = SimpleNamespace(
        project_name="main",
        outdir="Build",
        auxdir="Auxiliary",
        output_name="main",
        submission_reproducible=False,
        submission_output_dir="./Out/",
        submission_keep_preamble=True,
    )
    args = SimpleNamespace()
    cli_compile._submission_pack(args, state)

    assert "convert_unicode" not in captured
    assert captured["reproducible"] is False
    assert captured["submit_dir"] == "./Out/"
    assert captured["sanitize"] is False


def test_templates_and_defaults_agree_on_submission_section():
    submission_keys = set(DEFAULT_CONFIG["submission"])
    assert {"reproducible", "output_dir", "keep_preamble"} == submission_keys
    # 输入/输出后缀由 detection 注册表管理，配置层不再暴露死键
    assert "input_suffix" not in DEFAULT_CONFIG["index"]
    assert "output_suffix" not in DEFAULT_CONFIG["index"]

    for file_name in ("default_project_config.toml", "default_user_config.toml"):
        data = tomllib.loads((DATA_DIR / file_name).read_text(encoding="utf-8"))
        assert set(data["submission"]) == submission_keys
        assert data["preflight"]["enabled"] is True
        assert "input_suffix" not in data["index"]
        assert "output_suffix" not in data["index"]
