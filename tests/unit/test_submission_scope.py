"""投稿包依赖收集的目录/后缀边界测试。"""

from pytexmk.submission import _fallback_files, _fls_files


def test_fallback_includes_lua_but_excludes_build_and_bcf(tmp_path):
    root = tmp_path
    (root / "main.tex").write_text("x", encoding="utf-8")
    (root / "helper.lua").write_text("x", encoding="utf-8")
    (root / "main.bcf").write_text("x", encoding="utf-8")
    build = root / "nested" / "Build"
    build.mkdir(parents=True)
    (build / "ignored.tex").write_text("x", encoding="utf-8")
    hidden = root / ".hidden"
    hidden.mkdir()
    (hidden / "ignored.tex").write_text("x", encoding="utf-8")

    names = {path.name for path in _fallback_files(root)}
    assert "helper.lua" in names
    assert "main.bcf" not in names
    assert "ignored.tex" not in names


def test_fls_files_excludes_nested_build_regardless_of_depth(tmp_path):
    root = tmp_path
    keep = root / "figs" / "keep.png"
    skip = root / "nested" / "Build" / "skip.png"
    keep.parent.mkdir()
    skip.parent.mkdir(parents=True)
    keep.write_bytes(b"png")
    skip.write_bytes(b"png")
    fls = root / "main.fls"
    fls.write_text(f"INPUT {keep}\nINPUT {skip}\n", encoding="utf-8")

    paths = _fls_files(root, fls)
    assert keep in paths
    assert skip not in paths
