"""用例 1 & 4：子项目发现排除规则/层深，以及 -ls 幂等写回并保留块外内容。"""
import pytest
from pytexmk.subproject_scanner import (
    discover_subprojects,
    entries_to_subprojects,
    write_subprojects_to_rc,
)


def _scan_config(depth=3):
    return {
        "project_scan": {"depth": depth, "exclude": []},
        "folder": {"outdir": "./Build/", "auxdir": "./Auxiliary/"},
    }


def _write_main(root, rel, text="\\documentclass{article}\n"):
    p = root / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text, encoding="utf-8")


def test_discover_excludes_pictures_and_hits_main(tmp_path):
    root = tmp_path / "root"
    root.mkdir()
    _write_main(root, "chap1/main.tex")
    _write_main(root, "Pictures/deco.tex")  # 即使含主 tex 也应被排除

    assert discover_subprojects(root, _scan_config(depth=3)) == [("chap1", "chap1")]


def test_discover_depth1_no_drill_into_hit_subdir(tmp_path):
    root = tmp_path / "root"
    root.mkdir()
    # 命中层子项目内部更深层的子项目：命中后不下钻（任何 depth 都应如此）
    _write_main(root, "subA/main.tex")
    _write_main(root, "subA/nested/other.tex")
    # 需 >depth 次递归才能触达的子项目：depth=1 时不下钻、不命中
    _write_main(root, "aaa/bbb/ccc/deep.tex")

    assert discover_subprojects(root, _scan_config(depth=1)) == [("subA", "subA")]
    # 放宽 depth=3 时能下钻命中，且 subA 命中后仍不下钻其 nested
    assert discover_subprojects(root, _scan_config(depth=3)) == [
        ("aaa/bbb/ccc", "aaa/bbb/ccc"),
        ("subA", "subA"),
    ]


def test_discover_depth1_reaches_level2_but_not_level3(tmp_path):
    root = tmp_path / "root"
    root.mkdir()
    # depth 下钻层数=1 时检查到 level=depth+1=2：level2 子项目应命中；
    # level3（a/m/n）超出检查范围，不识别（贴合原始递归语义）。
    _write_main(root, "a/b/x.tex")       # level2 → 命中
    _write_main(root, "a/m/n/deep.tex")  # level3 → 不命中

    assert discover_subprojects(root, _scan_config(depth=1)) == [("a/b", "a/b")]


def test_discover_sorted_results(tmp_path):
    root = tmp_path / "root"
    root.mkdir()
    _write_main(root, "b/main.tex")
    _write_main(root, "a/main.tex")

    assert discover_subprojects(root, _scan_config(depth=3)) == [("a", "a"), ("b", "b")]


def _sample_rc() -> str:
    return (
        "# file header comment\n"
        'owner = "me"\n'
        "\n"
        "[project_scan]\n"
        "depth = 2\n"
        "exclude = []\n"
        'keep_key = "untouched"\n'
        "\n"
        "[subprojects]\n"
        "# handwritten by user\n"
        '"manual" = "legacy/path"\n'
        "# interior comment\n"
        '"alpha" = "x"\n'
        "\n"
        "[other_section]\n"
        'keep = "this"\n'
        "# trailing comment\n"
    )


def test_write_subprojects_idempotent_and_sections_preserved(tmp_path):
    rc = tmp_path / ".pytexmkrc"
    rc.write_text(_sample_rc(), encoding="utf-8")

    entries = [("chap1", "chap1"), ("b", "b")]

    # 往返结果必须是 str，不能是 Path
    mapping = entries_to_subprojects(entries)
    assert all(isinstance(k, str) and isinstance(v, str) for k, v in mapping.items())

    assert write_subprojects_to_rc(rc, entries) is True
    text = rc.read_text(encoding="utf-8")

    # 新托管块整体替换旧 [subprojects]（手写项与块内注释全部消失）
    assert "[subprojects]\n" in text
    assert "# 子项目清单（由 pytexmk -ls 自动托管）：名称 = 相对路径\n" in text
    assert '"chap1" = "chap1"\n' in text and '"b" = "b"\n' in text
    assert "manual" not in text and "legacy/path" not in text
    assert "interior comment" not in text and "handwritten" not in text

    # [project_scan] 段逐字节不变
    assert '[project_scan]\ndepth = 2\nexclude = []\nkeep_key = "untouched"\n' in text

    # 块外片外注释与其它段逐字节不变
    assert text.startswith('# file header comment\nowner = "me"\n\n')
    assert '[other_section]\nkeep = "this"\n# trailing comment\n' in text

    # 幂等：同输入重复写回结果逐字节一致
    first = rc.read_text(encoding="utf-8")
    assert write_subprojects_to_rc(rc, entries) is True
    assert rc.read_text(encoding="utf-8") == first


def test_write_subprojects_missing_rc_returns_false(tmp_path):
    missing = tmp_path / "no_such" / ".pytexmkrc"
    assert write_subprojects_to_rc(missing, [("a", "a")]) is False
    assert not missing.exists()