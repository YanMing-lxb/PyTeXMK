"""投稿包 stage_bib 的去重契约。

``stage_bib`` 会把项目内所有 .bib 补进 staging；候选阶段已经收过的文件不能再
写一遍（重复 append 会让说明里的文件清单出现两次，也会多一次复制）。
"""
from pathlib import Path

from pytexmk.submission import _SubmissionStager


def _stager(tmp_path: Path) -> _SubmissionStager:
    root = tmp_path / "proj"
    root.mkdir()
    (root / "refs.bib").write_text("@book{a, title={A}}", encoding="utf-8")
    (root / "chapters").mkdir()
    (root / "chapters" / "extra.bib").write_text("@book{b}", encoding="utf-8")
    staging = tmp_path / "stage"
    staging.mkdir()
    return _SubmissionStager(root=root, staging=staging, sanitize=False)


def test_stage_bib_collects_all_bib_files(tmp_path):
    stager = _stager(tmp_path)
    stager.stage_bib("main")

    assert sorted(stager.staged) == ["chapters/extra.bib", "refs.bib"]
    assert (stager.staging / "refs.bib").is_file()
    assert (stager.staging / "chapters" / "extra.bib").is_file()


def test_stage_bib_is_idempotent(tmp_path):
    stager = _stager(tmp_path)
    stager.stage_bib("main")
    stager.stage_bib("main")

    assert sorted(stager.staged) == ["chapters/extra.bib", "refs.bib"]
    assert len(stager.staged) == len(set(stager.staged))


def test_stage_bib_respects_files_staged_by_candidate_phase(tmp_path):
    stager = _stager(tmp_path)
    # 候选阶段（.fls 记录）已经收过 refs.bib
    stager.staged.append("refs.bib")

    stager.stage_bib("main")

    assert stager.staged.count("refs.bib") == 1
    assert "chapters/extra.bib" in stager.staged
