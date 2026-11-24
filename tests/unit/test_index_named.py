"""多索引系统回归：命名索引、xindy 后端、辅助文件归位。

覆盖的现场问题：
  * imakeidx 的 ``\\makeindex[name=author]`` 产出 ``author.idx``，旧实现只按
    jobname 拼文件名，命名索引永远不被调度（``\\printindex[author]`` 空白）。
  * glossaries 的 xindy 后端会把 ``.xdy`` 写进 auxdir，旧实现只在 CWD 找它，
    结果误判为 makeindex 后端，于是拿不存在的 ``.ist`` 去跑 makeindex 并失败。
  * 切换过 ``--no-native`` 的项目根目录会残留同名 ``.ind``，TeX 找输入时根目录
    优先，旧实现没有清理，``\\printindex`` 一直读到旧索引。
"""

from pathlib import Path
from types import SimpleNamespace

from pytexmk.cli.cli_compile import _collect_named_index_aux, _sweep_stale_root_aux
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
        native=True,
    )


def _state(auxdir: str = AUX, output_name: str = "main") -> SimpleNamespace:
    return SimpleNamespace(
        auxdir=auxdir,
        output_name=output_name,
        aux_files=[f"{output_name}.aux", f"{output_name}.idx", f"{output_name}.ind"],
    )


# ---------------------------------------------------------------- 命名索引


def test_named_imakeidx_is_discovered(tmp_path, monkeypatch):
    """`\\makeindex[name=author]` 生成的 author.idx 必须各自跑一次 makeindex。"""
    monkeypatch.chdir(tmp_path)
    (tmp_path / AUX).mkdir()
    (tmp_path / AUX / "main.aux").write_text("", encoding="utf-8")
    (tmp_path / AUX / "main.idx").write_text("\\indexentry{alpha}{1}\n", encoding="utf-8")
    (tmp_path / AUX / "author.idx").write_text("\\indexentry{beta}{1}\n", encoding="utf-8")

    commands = _detector().index_judgment({})
    assert [c[1] for c in commands] == ["makeindex author.idx", "makeindex main.idx"]
    # 命名索引在时长表里带主干名，避免两条都显示 "makeidx"
    assert [c[0] for c in commands] == ["makeidx (author)", "makeidx"]


def test_named_imakeidx_rerun_only_when_its_idx_changes(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / AUX).mkdir()
    (tmp_path / AUX / "main.aux").write_text("", encoding="utf-8")
    (tmp_path / AUX / "main.idx").write_text("\\indexentry{alpha}{1}\n", encoding="utf-8", newline="\n")
    (tmp_path / AUX / "main.ind").write_text("alpha 1\n", encoding="utf-8", newline="\n")
    (tmp_path / AUX / "author.idx").write_text("\\indexentry{beta}{1}\n", encoding="utf-8", newline="\n")
    (tmp_path / AUX / "author.ind").write_text("beta 1\n", encoding="utf-8", newline="\n")
    snapshot = {
        "main.idx": (tmp_path / AUX / "main.idx").read_text(encoding="utf-8"),
        "author.idx": "\\indexentry{gamma}{2}\n",
    }
    commands = _detector().index_judgment(snapshot)
    assert [c[1] for c in commands] == ["makeindex author.idx"]


def test_named_idx_in_cwd_is_ignored_in_favour_of_auxdir(tmp_path, monkeypatch):
    """切换过 --no-native 后根目录残留同名 idx，不能让 native 构建读到旧内容。"""
    monkeypatch.chdir(tmp_path)
    (tmp_path / AUX).mkdir()
    (tmp_path / AUX / "main.aux").write_text("", encoding="utf-8")
    (tmp_path / "author.idx").write_text("\\indexentry{old}{1}\n", encoding="utf-8")
    (tmp_path / AUX / "author.idx").write_text("\\indexentry{new}{1}\n", encoding="utf-8")
    (tmp_path / AUX / "author.ind").write_text("new 1\n", encoding="utf-8")

    snapshot = {"author.idx": "\\indexentry{new}{1}\n"}
    assert _detector().index_judgment(snapshot) == []


# ---------------------------------------------------------------- xindy


def test_glossaries_xindy_detected_from_xdy_in_auxdir(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / AUX).mkdir()
    (tmp_path / AUX / "main.aux").write_text(
        "\\@newglossary{main}{glg}{gls}{glo}\n", encoding="utf-8"
    )
    (tmp_path / AUX / "main.xdy").write_text(";; xindy style\n", encoding="utf-8")
    (tmp_path / AUX / "main.glo").write_text("\\glossaryentry{alpha}{1}\n", encoding="utf-8")
    (tmp_path / AUX / "main.log").write_text(
        "Package babel Info: Using the language definitions for `english'.\n", encoding="utf-8"
    )

    commands = _detector().index_judgment({})
    assert commands[0][1].startswith("xindy -L english -I xindy")
    assert "main.xdy" in commands[0][1]


def test_glossaries_makeindex_when_only_ist_present(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / AUX).mkdir()
    (tmp_path / AUX / "main.aux").write_text(
        "\\@newglossary{main}{glg}{gls}{glo}\n", encoding="utf-8"
    )
    (tmp_path / AUX / "main.ist").write_text(";; makeindex style\n", encoding="utf-8")
    (tmp_path / AUX / "main.glo").write_text("\\glossaryentry{alpha}{1}\n", encoding="utf-8")
    (tmp_path / AUX / "main.log").write_text("", encoding="utf-8")

    commands = _detector().index_judgment({})
    assert commands[0][1].startswith("makeindex -s main.ist")


# ---------------------------------------------------------------- 辅助文件归位


def test_collect_named_index_aux_adds_stems(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / AUX).mkdir()
    (tmp_path / "author.idx").write_text("x", encoding="utf-8")
    (tmp_path / AUX / "main.idx").write_text("x", encoding="utf-8")
    state = _state()
    _collect_named_index_aux(state)
    assert "author.idx" in state.aux_files
    assert "author.ind" in state.aux_files
    assert "author.ilg" in state.aux_files
    # 与 jobname 同名的那份不重复添加
    assert state.aux_files.count("main.idx") == 1


def test_sweep_stale_root_aux_removes_shadowed_copies(tmp_path, monkeypatch):
    """auxdir 已有同名索引产物时，根目录旧副本必须删掉，否则 TeX 会读旧的。"""
    monkeypatch.chdir(tmp_path)
    (tmp_path / AUX).mkdir()
    (tmp_path / "main.ind").write_text("old\n", encoding="utf-8")
    (tmp_path / AUX / "main.ind").write_text("new\n", encoding="utf-8")
    state = _state()
    _sweep_stale_root_aux(state)
    assert not (tmp_path / "main.ind").exists()
    assert (tmp_path / AUX / "main.ind").read_text(encoding="utf-8") == "new\n"


def test_sweep_stale_root_aux_moves_orphan_copies(tmp_path, monkeypatch):
    """auxdir 没有同名文件时，根目录那份应被搬进 auxdir 而不是删除。"""
    monkeypatch.chdir(tmp_path)
    (tmp_path / AUX).mkdir()
    (tmp_path / "author.idx").write_text("keep\n", encoding="utf-8")
    state = _state()
    state.aux_files.append("author.idx")
    _sweep_stale_root_aux(state)
    assert not (tmp_path / "author.idx").exists()
    assert (tmp_path / AUX / "author.idx").read_text(encoding="utf-8") == "keep\n"


def test_sweep_stale_root_aux_leaves_unrelated_files(tmp_path, monkeypatch):
    """只清理索引类后缀，用户自己的 .bbl/.aux 不在此列。"""
    monkeypatch.chdir(tmp_path)
    (tmp_path / AUX).mkdir()
    (tmp_path / "main.bbl").write_text("user bbl\n", encoding="utf-8")
    (tmp_path / AUX / "main.bbl").write_text("generated\n", encoding="utf-8")
    state = _state()
    state.aux_files.append("main.bbl")
    _sweep_stale_root_aux(state)
    assert Path("main.bbl").exists()
