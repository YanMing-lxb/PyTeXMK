"""投稿包深度处理（3.9）的回归测试：导言区净化、.bbl 转换、残留字符、verbatim 保护。"""

import zipfile

from pytexmk.submission import (
    build_pack,
    convert_text,
    sanitize_preamble,
)


def test_sanitize_preamble_comments_incompatible_and_injects_fontenc():
    text = (
        "\\documentclass{article}\n"
        "\\usepackage{fontspec}\n"
        "\\usepackage{amsmath,unicode-math}\n"
        "\\setmainfont{Times New Roman}\n"
        "\\begin{document}\nα\n\\end{document}\n"
    )
    cleaned, notes = sanitize_preamble(text)
    assert "% [pytexmk] \\usepackage{fontspec}" in cleaned
    assert "\\usepackage{amsmath}" in cleaned
    assert "unicode-math" not in cleaned.replace("% [pytexmk]", "")
    assert "% [pytexmk] \\setmainfont" in cleaned
    assert "\\usepackage[T1]{fontenc}" in cleaned
    assert "\\usepackage[utf8]{inputenc}" in cleaned
    assert cleaned.index("fontenc") < cleaned.index("\\begin{document}")
    assert any("fontspec" in n for n in notes)


def test_sanitize_preamble_adds_textcomp_for_degree():
    text = "\\documentclass{article}\n\\begin{document}\n25\\textdegree{}\n\\end{document}\n"
    cleaned, notes = sanitize_preamble(text)
    assert "\\usepackage{textcomp}" in cleaned
    assert any("textcomp" in n for n in notes)


def test_convert_text_protects_verbatim():
    text = "正文 α\n\\begin{verbatim}\nα ≤\n\\end{verbatim}\n\\verb|α| 结尾 β"
    converted, repl = convert_text(text)
    assert "\\begin{verbatim}\nα ≤\n\\end{verbatim}" in converted
    assert "\\verb|α|" in converted
    assert "\\ensuremath{\\alpha}" in converted
    assert "\\ensuremath{\\beta}" in converted


def test_convert_text_handles_fullwidth_and_ligature():
    converted, _ = convert_text("ＡＢＣ ﬁ ①")
    assert "ABC" in converted
    assert "fi" in converted
    assert "1" in converted


def test_bbl_is_also_converted(tmp_path):
    root = tmp_path
    (root / "main.tex").write_text(
        "\\documentclass{article}\\begin{document}x\\end{document}", encoding="utf-8"
    )
    aux = root / "Auxiliary"
    aux.mkdir()
    (aux / "main.bbl").write_text("Author α and β\n", encoding="utf-8")
    out = root / "Build"
    out.mkdir()
    (out / "main.pdf").write_bytes(b"%PDF-1.4 fake")

    result = build_pack(root, "main", out, aux, submit_dir=root / "Submission", include_bbl=True)
    with zipfile.ZipFile(result.zip_path) as zf:
        bbl = zf.read("main.bbl").decode("utf-8")
    assert "\\ensuremath{\\alpha}" in bbl
    assert "α" not in bbl


def test_jobname_bbl_falls_back_to_source_name(tmp_path):
    """--jobname 时 .bbl 仍必须叫 main.bbl，否则期刊用 main.tex 编译会缺文献。"""
    root = tmp_path
    (root / "main.tex").write_text(
        "\\documentclass{article}\\begin{document}x\\end{document}", encoding="utf-8"
    )
    aux = root / "Auxiliary"
    aux.mkdir()
    (aux / "alt.bbl").write_text("Author\n", encoding="utf-8")
    out = root / "Build"
    out.mkdir()
    (out / "alt.pdf").write_bytes(b"%PDF-1.4 fake")

    result = build_pack(
        root, "main", out, aux, pdf_name="alt", submit_dir=root / "Submission", include_bbl=True
    )
    with zipfile.ZipFile(result.zip_path) as zf:
        assert "main.bbl" in zf.namelist()
        assert "alt.bbl" not in zf.namelist()


def test_remaining_cjk_reported_with_locations(tmp_path):
    root = tmp_path
    (root / "main.tex").write_text(
        "\\documentclass{article}\n\\begin{document}\n中文 α\n\\end{document}\n", encoding="utf-8"
    )
    aux = root / "Auxiliary"
    aux.mkdir()
    out = root / "Build"
    out.mkdir()
    (out / "main.pdf").write_bytes(b"%PDF-1.4 fake")

    result = build_pack(root, "main", out, aux, submit_dir=root / "Submission")
    assert result.remaining_chars.get("中", 0) >= 1
    assert any("main.tex:" in item for item in result.remaining_locations)
    with zipfile.ZipFile(result.zip_path) as zf:
        notes = zf.read("pytexmk-submission-notes.txt").decode("utf-8")
    assert "仍无法用 pdflatex 处理" in notes
    assert "main.tex:3" in notes


def test_unicode_in_comments_is_not_a_blocker(tmp_path):
    root = tmp_path
    (root / "main.tex").write_text(
        "\\documentclass{article}\n% 中文注释 α 不会让 pdflatex 报错\n"
        "\\begin{document}\nEnglish only.\n\\end{document}\n",
        encoding="utf-8",
    )
    aux = root / "Auxiliary"
    aux.mkdir()
    out = root / "Build"
    out.mkdir()
    (out / "main.pdf").write_bytes(b"%PDF-1.4 fake")

    result = build_pack(root, "main", out, aux, submit_dir=root / "Submission")
    assert result.remaining_chars == {}


def test_default_pack_contains_bib_without_bbl(tmp_path):
    """默认只带源 .bib（全部），不含 .bbl；include_bbl=True 时才附 .bbl。"""
    root = tmp_path
    (root / "main.tex").write_text(
        "\\documentclass{article}\\begin{document}x\\end{document}", encoding="utf-8"
    )
    (root / "main.bib").write_text("@article{a, title={T}}", encoding="utf-8")
    (root / "extra.bib").write_text("@book{b, title={U}}", encoding="utf-8")
    aux = root / "Auxiliary"
    aux.mkdir()
    (aux / "main.bbl").write_text("% bbl\n", encoding="utf-8")
    out = root / "Build"
    out.mkdir()
    (out / "main.pdf").write_bytes(b"%PDF-1.4 fake")

    default = build_pack(root, "main", out, aux, submit_dir=root / "S1")
    with zipfile.ZipFile(default.zip_path) as zf:
        names = set(zf.namelist())
        notes = zf.read("pytexmk-submission-notes.txt").decode("utf-8")
    assert {"main.bib", "extra.bib"} <= names
    assert "main.bbl" not in names
    assert "包内未附 .bbl" in notes

    with_bbl = build_pack(
        root, "main", out, aux, submit_dir=root / "S2", include_bbl=True
    )
    with zipfile.ZipFile(with_bbl.zip_path) as zf:
        names = set(zf.namelist())
        notes = zf.read("pytexmk-submission-notes.txt").decode("utf-8")
    assert {"main.bib", "extra.bib", "main.bbl"} <= names
    assert "若包内含 .bbl" in notes
