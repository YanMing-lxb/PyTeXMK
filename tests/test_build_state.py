"""用例：BuildState —— 构建基线、源快照与收敛标记的持久化。

历史背景：收敛判定完全依赖进程内快照，进程一重启基线就没了，只能靠多编
一轮重新观察（即"确认轮"）。BuildState 把基线落到 pytexlogs 已经写过的
共享状态文件里，不新增任何辅助文件。
"""

from pathlib import Path

import pytest

from pytexmk.build_state import TRACKED_ARTIFACTS, BuildState


def _make_artifacts(root: Path, project: str = "main") -> None:
    """造一组辅助产物。"""
    for suffix, body in {
        ".aux": "\\relax\n\\bibcite{k}{{1}{}{{}}{{}}}\n",
        ".out": "\\BOOKMARK [1][-]{x}{T}{}\n",
        ".toc": "\\contentsline {section}{A}{1}\n",
    }.items():
        (root / f"{project}{suffix}").write_text(body, encoding="utf-8")


def test_no_state_file_means_no_baseline(tmp_path):
    tracker = BuildState(tmp_path, "main")
    assert tracker.load_baseline().is_empty()
    assert tracker.baseline_matches_current() is False


def test_save_and_reload_baseline(tmp_path):
    _make_artifacts(tmp_path)
    tracker = BuildState(tmp_path, "main")
    tracker.save_round(round_no=3, fingerprint="sha256:abc", dims={"aux": 0}, converged=True)

    reloaded = BuildState(tmp_path, "main").load_baseline()
    assert not reloaded.is_empty()
    assert reloaded.fingerprint == "sha256:abc"
    assert reloaded.hashes[".aux"] is not None


def test_baseline_matches_current_is_true_after_save(tmp_path):
    _make_artifacts(tmp_path)
    tracker = BuildState(tmp_path, "main")
    tracker.save_round(round_no=1, fingerprint="f", dims={"aux": 0})

    assert tracker.baseline_matches_current() is True


def test_baseline_matches_current_false_when_artifact_changed(tmp_path):
    _make_artifacts(tmp_path)
    tracker = BuildState(tmp_path, "main")
    tracker.save_round(round_no=1, fingerprint="f", dims={"aux": 0})

    (tmp_path / "main.aux").write_text("\\relax\nchanged\n", encoding="utf-8")
    assert tracker.baseline_matches_current() is False


def test_baseline_matches_current_false_when_artifact_deleted(tmp_path):
    _make_artifacts(tmp_path)
    tracker = BuildState(tmp_path, "main")
    tracker.save_round(round_no=1, fingerprint="f", dims={"aux": 0})

    (tmp_path / "main.aux").unlink()
    assert tracker.baseline_matches_current() is False


def test_tracked_artifacts_cover_the_stability_signals():
    """参与比对的后缀必须是实际决定收敛的那几类。"""
    assert set(TRACKED_ARTIFACTS) == {".aux", ".out", ".toc", ".nlo", ".bbl", ".nls"}


# ------------------------------------------------------------ 源快照


def test_sources_unchanged_roundtrip(tmp_path):
    (tmp_path / "main.tex").write_text("\\documentclass{article}", encoding="utf-8")
    (tmp_path / "chap.tex").write_text("\\section{A}", encoding="utf-8")

    tracker = BuildState(tmp_path, "main")
    sources = tracker.source_snapshot([tmp_path / "main.tex", tmp_path / "chap.tex"])
    tracker.save_round(round_no=1, fingerprint="f", dims={}, sources=sources)

    assert BuildState(tmp_path, "main").sources_unchanged(
        [tmp_path / "main.tex", tmp_path / "chap.tex"]
    ) is True


def test_sources_unchanged_false_after_edit(tmp_path):
    tex = tmp_path / "main.tex"
    tex.write_text("v1", encoding="utf-8")
    tracker = BuildState(tmp_path, "main")
    tracker.save_round(round_no=1, fingerprint="f", dims={}, sources=tracker.source_snapshot([tex]))

    tex.write_text("v2 changed", encoding="utf-8")
    assert BuildState(tmp_path, "main").sources_unchanged([tex]) is False


def test_sources_unchanged_false_when_file_added(tmp_path):
    """新增章节文件也算源码变动 —— 否则新增的 \\input 会被静默忽略。"""
    a = tmp_path / "main.tex"
    a.write_text("v1", encoding="utf-8")
    tracker = BuildState(tmp_path, "main")
    tracker.save_round(round_no=1, fingerprint="f", dims={}, sources=tracker.source_snapshot([a]))

    b = tmp_path / "new.tex"
    b.write_text("x", encoding="utf-8")
    assert BuildState(tmp_path, "main").sources_unchanged([a, b]) is False


def test_source_snapshot_skips_auxiliary_files(tmp_path):
    """产物文件不参与源快照，否则每次编译都会把自己判成"源码改动"。"""
    (tmp_path / "main.aux").write_text("x", encoding="utf-8")
    (tmp_path / "main.tex").write_text("y", encoding="utf-8")

    snapshot = BuildState(tmp_path, "main").source_snapshot(
        [tmp_path / "main.aux", tmp_path / "main.tex"]
    )
    assert list(snapshot) == [(tmp_path / "main.tex").as_posix()]


# ------------------------------------------------------------ 收敛标记


def test_converged_flag_roundtrip(tmp_path):
    tracker = BuildState(tmp_path, "main")
    assert tracker.was_converged() is False

    tracker.save_round(round_no=2, fingerprint="f", dims={}, converged=True)
    assert BuildState(tmp_path, "main").was_converged() is True


def test_stop_reason_roundtrip(tmp_path):
    tracker = BuildState(tmp_path, "main")
    tracker.save_round(round_no=2, fingerprint="f", dims={}, stop_reason="log_stalled")
    assert BuildState(tmp_path, "main").last_stop_reason() == "log_stalled"


# ------------------------------------------------------------ 清理


def test_discard_clears_build_but_keeps_refs(tmp_path):
    """-c 清理只能丢自己的基线，pytexlogs 的引用缓存必须留着。"""
    from pytexlogs import ProjectStateStore

    _make_artifacts(tmp_path)
    ProjectStateStore(tmp_path, "main").update_refs(keys=["keep"])
    tracker = BuildState(tmp_path, "main")
    tracker.save_round(round_no=1, fingerprint="f", dims={}, converged=True)

    assert tracker.discard() is True

    assert BuildState(tmp_path, "main").load_baseline().is_empty()
    assert ProjectStateStore(tmp_path, "main").get_refs()["keys"] == ["keep"]


def test_remove_state_file_if_empty(tmp_path):
    tracker = BuildState(tmp_path, "main")
    tracker.save_round(round_no=1, fingerprint="f", dims={})
    tracker.discard()

    assert tracker.remove_state_file_if_empty() is True
    assert not tracker._store.path.exists()


def test_remove_state_file_keeps_refs_payload(tmp_path):
    from pytexlogs import ProjectStateStore

    ProjectStateStore(tmp_path, "main").update_refs(keys=["a"])
    tracker = BuildState(tmp_path, "main")

    assert tracker.remove_state_file_if_empty() is False
    assert tracker._store.path.exists()


def test_state_uses_shared_file_not_a_new_one(tmp_path):
    """硬约束：只允许一个状态文件，不得新增辅助文件。"""
    _make_artifacts(tmp_path)
    BuildState(tmp_path, "main").save_round(round_no=1, fingerprint="f", dims={})

    dotfiles = sorted(p.name for p in tmp_path.iterdir() if p.name.startswith("."))
    assert dotfiles == [".pytexmk_refcache.json"]


@pytest.mark.parametrize("round_no", [1, 5, 9])
def test_save_round_records_dimensions(tmp_path, round_no):
    tracker = BuildState(tmp_path, "main")
    tracker.save_round(round_no=round_no, fingerprint="f", dims={"aux": 1, "log": 0})

    build = tracker._store.get_build()
    assert build["round"] == round_no
    assert build["dims"] == {"aux": 1, "log": 0}


# ------------------------------------------------------------ 源文件枚举口径


def _chdir(monkeypatch, path: Path) -> None:
    monkeypatch.chdir(path)


def test_iter_tex_sources_includes_main_and_chapters(tmp_path, monkeypatch):
    from pytexmk.compile_engine import _iter_tex_sources

    (tmp_path / "main.tex").write_text("m", encoding="utf-8")
    (tmp_path / "Section").mkdir()
    (tmp_path / "Section" / "S1.tex").write_text("s", encoding="utf-8")
    _chdir(monkeypatch, tmp_path)

    names = sorted(p.as_posix() for p in _iter_tex_sources("main"))
    assert names == ["Section/S1.tex", "main.tex"]


def test_iter_tex_sources_excludes_subprojects(tmp_path, monkeypatch):
    """带独立 .pytexmkrc 的子项目有自己的 PDF，改动它不该触发本项目重编译。"""
    from pytexmk.compile_engine import _iter_tex_sources

    (tmp_path / "main.tex").write_text("m", encoding="utf-8")
    (tmp_path / "Section").mkdir()
    (tmp_path / "Section" / "S1.tex").write_text("s", encoding="utf-8")
    cover = tmp_path / "Cover"
    cover.mkdir()
    (cover / ".pytexmkrc").write_text("[project]\n", encoding="utf-8")
    (cover / "Cover_Letter.tex").write_text("c", encoding="utf-8")
    _chdir(monkeypatch, tmp_path)

    names = [p.as_posix() for p in _iter_tex_sources("main")]
    assert "main.tex" in names
    assert "Section/S1.tex" in names
    assert not any(n.startswith("Cover/") for n in names)


def test_iter_tex_sources_excludes_output_dirs(tmp_path, monkeypatch):
    from pytexmk.compile_engine import _iter_tex_sources

    (tmp_path / "main.tex").write_text("m", encoding="utf-8")
    (tmp_path / "Build").mkdir()
    (tmp_path / "Build" / "copy.tex").write_text("x", encoding="utf-8")
    _chdir(monkeypatch, tmp_path)

    assert [p.as_posix() for p in _iter_tex_sources("main")] == ["main.tex"]


def test_iter_tex_sources_excludes_hidden_dirs(tmp_path, monkeypatch):
    from pytexmk.compile_engine import _iter_tex_sources

    (tmp_path / "main.tex").write_text("m", encoding="utf-8")
    (tmp_path / ".backup").mkdir()
    (tmp_path / ".backup" / "old.tex").write_text("x", encoding="utf-8")
    _chdir(monkeypatch, tmp_path)

    assert [p.as_posix() for p in _iter_tex_sources("main")] == ["main.tex"]


def test_iter_tex_sources_does_not_recurse_outside_cwd(tmp_path, monkeypatch):
    """子项目里编译时，不能把父项目的章节算进自己的源快照。"""
    from pytexmk.compile_engine import _iter_tex_sources

    (tmp_path / "main.tex").write_text("parent", encoding="utf-8")
    sub = tmp_path / "Review"
    sub.mkdir()
    (sub / "main.tex").write_text("child", encoding="utf-8")
    _chdir(monkeypatch, sub)

    assert [p.as_posix() for p in _iter_tex_sources("main")] == ["main.tex"]
