"""子项目发现排除规则/层深，以及显式同步时保留手写条目与次序。"""
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

    # 托管块整体替换 [subprojects]，但段内注释保留
    assert "[subprojects]\n" in text
    assert "# 子项目清单（由 pytexmk -ls 维护）：名称 = 相对路径\n" in text
    assert 'chap1 = "chap1"\n' in text and 'b = "b"\n' in text
    # 旧条目指向的路径已不存在：条目淘汰，但用户注释不删
    assert '"manual" = "legacy/path"' not in text
    assert '"alpha" = "x"' not in text
    assert "interior comment" in text and "handwritten" in text

    # [project_scan] 段逐字节不变
    assert '[project_scan]\ndepth = 2\nexclude = []\nkeep_key = "untouched"\n' in text

    # 块外片外注释与其它段逐字节不变
    assert text.startswith('# file header comment\nowner = "me"\n\n')
    assert '[other_section]\nkeep = "this"\n# trailing comment\n' in text

    # 幂等：同输入重复写回结果逐字节一致
    first = rc.read_text(encoding="utf-8")
    assert write_subprojects_to_rc(rc, entries) is True
    assert rc.read_text(encoding="utf-8") == first


def test_write_subprojects_returns_false_on_write_error(monkeypatch, tmp_path):
    """配置只读/被占用时返回 False，让 CLI 以 4 退出而不是抛 traceback。"""
    rc = tmp_path / ".pytexmkrc"
    rc.write_text("[subprojects]\n", encoding="utf-8")

    def _fail(*_args, **_kwargs):
        raise OSError("read-only")

    monkeypatch.setattr("pytexmk.subproject_scanner.atomic_write_text", _fail)
    assert write_subprojects_to_rc(rc, []) is False


def test_write_subprojects_missing_rc_returns_false(tmp_path):
    missing = tmp_path / "no_such" / ".pytexmkrc"
    assert write_subprojects_to_rc(missing, [("a", "a")]) is False
    assert not missing.exists()


def test_write_subprojects_preserves_manual_entry_with_existing_path(tmp_path):
    """显式同步不应清掉仍指向真实路径的手写别名。"""
    manual = tmp_path / "manual_dir"
    manual.mkdir()
    rc = tmp_path / ".pytexmkrc"
    rc.write_text(
        '[subprojects]\n"manual" = "manual_dir"\n',
        encoding="utf-8",
    )
    assert write_subprojects_to_rc(rc, [("auto", "auto")]) is True
    text = rc.read_text(encoding="utf-8")
    assert '"manual" = "manual_dir"' in text
    assert 'auto = "auto"' in text


def test_write_subprojects_accepts_header_comment(tmp_path):
    """`[subprojects] # 手写说明` 是合法 TOML，同步后不能出现第二个同名表。"""
    (tmp_path / "manual").mkdir()
    rc = tmp_path / ".pytexmkrc"
    rc.write_text(
        '[subprojects]  # hand note\nalias = "manual"\n',
        encoding="utf-8",
    )

    assert write_subprojects_to_rc(rc, []) is True
    text = rc.read_text(encoding="utf-8")
    assert text.count("[subprojects]") == 1
    assert "[subprojects]  # hand note" in text
    assert 'alias = "manual"' in text


def test_write_subprojects_prefers_manual_alias_over_same_discovered_dir(tmp_path):
    """手写别名指向自动发现的目录时，保留别名并去掉同路径自动项，避免双编译。"""
    (tmp_path / "chap1").mkdir()
    (tmp_path / "chap1" / "main.tex").write_text(
        "\\documentclass{article}\n", encoding="utf-8"
    )
    rc = tmp_path / ".pytexmkrc"
    rc.write_text('[subprojects]\nalias = "chap1"\n', encoding="utf-8")

    assert write_subprojects_to_rc(rc, [("chap1", "chap1")]) is True
    text = rc.read_text(encoding="utf-8")
    assert 'alias = "chap1"' in text
    assert "\nchap1 = " not in text
    assert write_subprojects_to_rc(rc, [("chap1", "chap1")]) is True
    assert rc.read_text(encoding="utf-8") == text


def test_write_subprojects_dedupes_same_dir_with_dot_slash(tmp_path):
    """`./chap1` 与 `chap1` 是同一目录，不能同时保留。"""
    (tmp_path / "chap1").mkdir()
    (tmp_path / "chap1" / "main.tex").write_text(
        "\\documentclass{article}\n", encoding="utf-8"
    )
    rc = tmp_path / ".pytexmkrc"
    rc.write_text('[subprojects]\nalias = "./chap1"\n', encoding="utf-8")

    assert write_subprojects_to_rc(rc, [("chap1", "chap1")]) is True
    text = rc.read_text(encoding="utf-8")
    assert 'alias = "./chap1"' in text
    assert "\nchap1 = " not in text
    assert write_subprojects_to_rc(rc, [("chap1", "chap1")]) is True
    assert rc.read_text(encoding="utf-8") == text


def test_write_subprojects_preserves_inline_comment_and_quoted_key(tmp_path):
    """手写行的行尾注释、含等号的引号键都要原样保留。"""
    (tmp_path / "manual").mkdir()
    rc = tmp_path / ".pytexmkrc"
    rc.write_text(
        '[subprojects]\n"alias=x" = "manual"  # keep me\n',
        encoding="utf-8",
    )

    assert write_subprojects_to_rc(rc, []) is True
    text = rc.read_text(encoding="utf-8")
    assert '"alias=x" = "manual"  # keep me' in text


def test_write_subprojects_preserves_order_and_raw_key_style(tmp_path):
    """手写条目与自动条目都按原次序保留，裸键不补引号。"""
    for name in ("a", "b", "manual"):
        (tmp_path / name).mkdir()
        (tmp_path / name / "main.tex").write_text(
            "\\documentclass{article}\n", encoding="utf-8"
        )
    rc = tmp_path / ".pytexmkrc"
    rc.write_text(
        "[subprojects]\n"
        '# keep alias first\n'
        'alias = "manual"\n'
        '"b" = "b"\n'
        'a = "a"\n',
        encoding="utf-8",
    )

    # 扫描结果按名称排序：a、b；但写回后必须保持 alias、b、a 的原次序
    assert write_subprojects_to_rc(rc, [("a", "a"), ("b", "b")]) is True
    text = rc.read_text(encoding="utf-8")
    order = [
        line.split("=")[0].strip().strip('"')
        for line in text.splitlines()
        if "=" in line and not line.lstrip().startswith("#")
    ]
    assert order == ["alias", "b", "a"]
    assert 'alias = "manual"' in text
    assert '"b" = "b"' in text
    assert 'a = "a"' in text
    assert "# keep alias first" in text


def test_write_subprojects_appends_new_entries_in_scan_order(tmp_path):
    """新发现的项目追加在末尾，不插队、不重排已有条目。"""
    for name in ("a", "b", "manual"):
        (tmp_path / name).mkdir()
    rc = tmp_path / ".pytexmkrc"
    rc.write_text('[subprojects]\nalias = "manual"\n', encoding="utf-8")

    assert write_subprojects_to_rc(rc, [("a", "a"), ("b", "b")]) is True
    text = rc.read_text(encoding="utf-8")
    assert text.count("alias") == 1
    assert text.index('alias = "manual"') < text.index('a = "a"')
    assert text.index('a = "a"') < text.index('b = "b"')
