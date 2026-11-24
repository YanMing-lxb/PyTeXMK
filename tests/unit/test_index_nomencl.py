"""索引系统触发/重跑判定：nomencl 与 makeidx 在原生构建下的可见性。

1.2.17 的 ``_make_extension_trigger`` 只在**当前目录**找 ``.nlo`` / ``.idx``，
而默认 ``native=auto`` 会把辅助文件直接写进 ``Auxiliary/``，于是
``\\printnomenclature`` 在默认配置下永远不触发 makeindex——用户看到的现象
就是"nomencl 没有编译"。这里把两种布局、以及"已收敛不重跑"都锁住。
"""

import pytest

from pytexmk.detection import CompilationDetector
from pytexmk.file_ops import FileMoveRemoveManager

AUX = "Auxiliary"


def _detector(auxdir: str = AUX) -> CompilationDetector:
    return CompilationDetector(
        project_name="main",
        compiled_program="XeLaTeX",
        out_files=["main.pdf"],
        aux_files=["main.aux", "main.log"],
        outdir="Build",
        auxdir=auxdir,
        non_quiet=False,
        MRO=FileMoveRemoveManager(),
        jobname="main",
    )


@pytest.fixture
def project(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / AUX).mkdir()
    (tmp_path / "main.aux").write_text("", encoding="utf-8")
    (tmp_path / AUX / "main.aux").write_text("", encoding="utf-8")
    return tmp_path


def test_nomencl_triggers_when_nlo_only_in_auxdir(project):
    """native 构建：.nlo 落在 Auxiliary，nomencl 仍必须被调度。"""
    (project / AUX / "main.nlo").write_text("\\entry{A}{1}\n", encoding="utf-8")
    commands = _detector().index_judgment({})
    assert [c[0] for c in commands] == ["nomencl"]
    assert "makeindex -s nomencl.ist" in commands[0][1]
    assert "main.nlo" in commands[0][1] and "main.nls" in commands[0][1]


def test_nomencl_triggers_when_nlo_in_cwd(project):
    """传统构建：.nlo 留在根目录，同样必须被调度。"""
    (project / "main.nlo").write_text("\\entry{A}{1}\n", encoding="utf-8")
    commands = _detector().index_judgment({})
    assert [c[0] for c in commands] == ["nomencl"]


def test_nomencl_skipped_when_no_nlo(project):
    assert _detector().index_judgment({}) == []


def test_nomencl_not_rerun_when_output_matches_snapshot(project):
    """输入内容与快照一致、且 .nls 已生成时不再重复调用 makeindex。"""
    nlo = project / AUX / "main.nlo"
    # newline="\n"：Windows 上文本写入默认把 \n 换成 \r\n，会让快照与读取结果假性不一致
    nlo.write_text("\\entry{A}{1}\n", encoding="utf-8", newline="\n")
    (project / AUX / "main.nls").write_text("A 1\n", encoding="utf-8", newline="\n")
    snapshot = {"main.nlo": nlo.read_text(encoding="utf-8")}
    assert _detector().index_judgment(snapshot) == []


def test_nomencl_rerun_when_input_changed(project):
    (project / AUX / "main.nlo").write_text("\\entry{B}{2}\n", encoding="utf-8")
    (project / AUX / "main.nls").write_text("A 1\n", encoding="utf-8")
    assert [c[0] for c in _detector().index_judgment({"main.nlo": "\\entry{A}{1}\n"})] == [
        "nomencl"
    ]


def test_makeidx_triggers_when_idx_in_auxdir(project):
    (project / AUX / "main.idx").write_text("\\indexentry{x}{1}\n", encoding="utf-8")
    commands = _detector().index_judgment({})
    assert [c[0] for c in commands] == ["makeidx"]
    assert commands[0][1] == "makeindex main.idx"


def test_configured_style_file_reaches_command(project, monkeypatch):
    """``[index] index_style_file`` 必须真的进到 makeindex 的 -s 参数。"""
    from pytexmk import detection

    (project / AUX / "main.nlo").write_text("\\entry{A}{1}\n", encoding="utf-8")
    monkeypatch.setattr(detection, "_INDEX_OPTIONS", {"nomencl_ist": r"C:\tex dir\nomencl.ist", "glossaries_tool": "makeindex"})
    commands = _detector().index_judgment({})
    assert '-s "C:\\tex dir\\nomencl.ist"' in commands[0][1]
