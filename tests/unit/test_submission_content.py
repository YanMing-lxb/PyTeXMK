"""投稿包的回归测试：导言区净化、非 ASCII 字符只报告不改写、诊断日志、产物检查。"""

import os
import zipfile
from pathlib import Path

from pytexmk.submission import build_pack, sanitize_preamble


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


def test_sanitize_preamble_keeps_line_breaks_when_dropping_package():
    """摘掉同行不兼容宏包时不能把下一行拼上来（曾丢换行）。"""
    text = (
        "\\documentclass{article}\n"
        "\\usepackage{fontspec,amsmath} % 说明文字\n"
        "\\usepackage{graphicx}\n"
        "\\begin{document}\n\\end{document}\n"
    )
    cleaned, _ = sanitize_preamble(text)
    assert "\\usepackage{amsmath} % 说明文字\n\\usepackage{graphicx}\n" in cleaned
    assert cleaned.count("\\usepackage{graphicx}") == 1


def test_sanitize_preamble_treats_usepackage_inside_iffalse_as_loaded():
    """``\\iffalse`` 块不再特殊识别：块里的 \\usepackage 按真实加载处理。

    块本就不参与排版，给它加注释前缀无害；换来的是永不因配对算错而漏掉整篇。
    """
    text = (
        "\\documentclass{article}\n"
        "\\iffalse\n\\usepackage{ctex}\n\\fi\n"
        "\\begin{document}\nx\n\\end{document}\n"
    )
    cleaned, notes = sanitize_preamble(text)
    assert "% [pytexmk] \\usepackage{ctex}" in cleaned
    assert any("ctex" in n for n in notes)


def test_sanitize_preamble_commented_hint_does_not_count_as_present():
    """注释里提到 fontenc / \\textdegree 不算已加载，仍需补齐。"""
    text = (
        "\\documentclass{article}\n"
        "% 记得加 \\usepackage{fontenc}\n"
        "\\begin{document}\nx % 25\\textdegree 见注释\n\\end{document}\n"
    )
    cleaned, notes = sanitize_preamble(text)
    assert "\\usepackage[T1]{fontenc}" in cleaned
    assert "\\usepackage{textcomp}" not in cleaned
    assert any("fontenc" in n for n in notes)


def test_sanitize_preamble_keeps_crlf_line_endings():
    text = (
        "\\documentclass{article}\r\n"
        "\\usepackage{ctex}\r\n"
        "\\begin{document}\r\nx\r\n\\end{document}\r\n"
    )
    cleaned, _ = sanitize_preamble(text)
    assert "\n" not in cleaned.replace("\r\n", "")
    assert "% [pytexmk] \\usepackage{ctex}\r\n" in cleaned


def test_non_ascii_chars_reported_with_locations(tmp_path):
    """正文非 ASCII 字符只报告（含位置），不改写提交副本。"""
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
    assert result.compat.non_ascii_chars.get("中", 0) >= 1
    assert result.compat.non_ascii_chars.get("α", 0) >= 1
    assert "main.tex:3" in result.compat.char_locations["中"]
    with zipfile.ZipFile(result.zip_path) as zf:
        notes = zf.read("pytexmk-submission-notes.txt").decode("utf-8")
        packed = zf.read("main.tex").decode("utf-8")
    assert "pdflatex 兼容性警告" in notes
    assert "非 ASCII 字符 中" in notes
    assert "中文 α" in packed  # 正文原样保留，不做自动转换
    assert "\\ensuremath" not in packed


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
    assert result.compat.non_ascii_chars == {}


def test_unicode_in_comment_and_verbatim_envs_are_not_blockers(tmp_path):
    """行注释与 comment/verbatim/lstlisting 环境内的中文不报告；正文非 ASCII 字符仍上报。"""
    root = tmp_path
    (root / "main.tex").write_text(
        "\\documentclass{article}\n"
        "% 行注释：换热器 板式 钎焊\n"
        "\\begin{comment}\n被注释正文：换热器 板式\n\\end{comment}\n"
        "\\begin{verbatim}\nverbatim 内：换热器\n\\end{verbatim}\n"
        "\\begin{lstlisting}\nlstlisting 内：换热器\n\\end{lstlisting}\n"
        "\\begin{document}\nSnowman ☃\n\\end{document}\n",
        encoding="utf-8",
    )
    aux = root / "Auxiliary"
    aux.mkdir()
    out = root / "Build"
    out.mkdir()
    (out / "main.pdf").write_bytes(b"%PDF-1.4 fake")

    result = build_pack(root, "main", out, aux, submit_dir=root / "Submission")
    assert result.compat.non_ascii_chars == {"☃": 1}
    assert "换" not in result.compat.non_ascii_chars
    assert "板" not in result.compat.non_ascii_chars


def test_trailing_comment_chars_are_ignored(tmp_path):
    """行尾注释里的中文不报告；正文里的 α/° 只上报、不被改写。"""
    root = tmp_path
    (root / "main.tex").write_text(
        "\\documentclass{article}\n"
        "\\begin{document}\n"
        "Body α °C % 换热器 板式 钎焊 bollocks\n"
        "\\end{document}\n",
        encoding="utf-8",
    )
    aux = root / "Auxiliary"
    aux.mkdir()
    out = root / "Build"
    out.mkdir()
    (out / "main.pdf").write_bytes(b"%PDF-1.4 fake")

    result = build_pack(root, "main", out, aux, submit_dir=root / "Submission")
    assert set(result.compat.non_ascii_chars) == {"α", "°"}
    with zipfile.ZipFile(result.zip_path) as zf:
        packed = zf.read("main.tex").decode("utf-8")
    assert "换热器 板式 钎焊 bollocks" in packed  # 注释原样保留
    assert "Body α °C" in packed  # 正文不转换
    assert "\\ensuremath" not in packed


def test_url_argument_percent_does_not_hide_trailing_text(tmp_path):
    """``\\url{...%20...}`` 里的 ``%`` 是正文，不能把同一行后面的字符一起吞掉。"""
    root = tmp_path
    (root / "main.tex").write_text(
        "\\documentclass{article}\n"
        "\\begin{document}\n"
        "See \\url{https://e.com/a%20b} 换热器\n"
        "\\end{document}\n",
        encoding="utf-8",
    )
    aux = root / "Auxiliary"
    aux.mkdir()
    out = root / "Build"
    out.mkdir()
    (out / "main.pdf").write_bytes(b"%PDF-1.4 fake")

    result = build_pack(root, "main", out, aux, submit_dir=root / "Submission")
    assert set(result.compat.non_ascii_chars) == {"换", "热", "器"}
    with zipfile.ZipFile(result.zip_path) as zf:
        packed = zf.read("main.tex").decode("utf-8")
    assert "\\url{https://e.com/a%20b}" in packed  # URL 原样保留


def test_iffalse_block_chars_are_reported(tmp_path):
    """``\\iffalse`` 块按正文统计：块内字符照报（宁可多报，不漏报整篇）。"""
    root = tmp_path
    (root / "main.tex").write_text(
        "\\documentclass{article}\n"
        "\\iffalse\n换热器 板式\n\\iffalse\n嵌套 内容\n\\fi\n仍在块内\n\\fi\n"
        "\\begin{document}\nSnowman ☃\n\\end{document}\n",
        encoding="utf-8",
    )
    aux = root / "Auxiliary"
    aux.mkdir()
    out = root / "Build"
    out.mkdir()
    (out / "main.pdf").write_bytes(b"%PDF-1.4 fake")

    result = build_pack(root, "main", out, aux, submit_dir=root / "Submission")
    assert set(result.compat.non_ascii_chars) == set("换热器板式嵌套内容仍在块☃")
    with zipfile.ZipFile(result.zip_path) as zf:
        packed = zf.read("main.tex").decode("utf-8")
    assert "换热器 板式" in packed  # \iffalse 块也原样保留


def test_default_pack_contains_bib_without_bbl(tmp_path):
    """投稿包只带源 .bib（全部），任何来源的 .bbl 都不进包。"""
    root = tmp_path
    (root / "main.tex").write_text(
        "\\documentclass{article}\\begin{document}x\\end{document}", encoding="utf-8"
    )
    (root / "main.bib").write_text("@article{a, title={T}}", encoding="utf-8")
    (root / "extra.bib").write_text("@book{b, title={U}}", encoding="utf-8")
    (root / "main.bbl").write_text("% hand-written root bbl\n", encoding="utf-8")
    aux = root / "Auxiliary"
    aux.mkdir()
    (aux / "main.bbl").write_text("% generated aux bbl\n", encoding="utf-8")
    out = root / "Build"
    out.mkdir()
    (out / "main.pdf").write_bytes(b"%PDF-1.4 fake")

    result = build_pack(root, "main", out, aux, submit_dir=root / "Submission")
    with zipfile.ZipFile(result.zip_path) as zf:
        names = set(zf.namelist())
        notes = zf.read("pytexmk-submission-notes.txt").decode("utf-8")
    assert {"main.bib", "extra.bib"} <= names
    assert not any(name.endswith(".bbl") for name in names)
    assert "包内未附 .bbl" in notes


def test_compat_scan_covers_only_packed_tex(tmp_path):
    """只有进包的 .tex 才参与字符告警：另一语种稿件不该被检查。"""
    root = tmp_path
    (root / "main.tex").write_text(
        "\\documentclass{article}\n\\input{Section/en}\n\\begin{document}\nClean text\n\\end{document}\n",
        encoding="utf-8",
    )
    section = root / "Section"
    section.mkdir()
    (section / "en.tex").write_text("English section.\n", encoding="utf-8")
    (root / "main-cn.tex").write_text(
        "\\documentclass{article}\n\\begin{document}\n板式换热器\n\\end{document}\n",
        encoding="utf-8",
    )
    (section / "cn.tex").write_text("紧凑型钎焊板式换热器\n", encoding="utf-8")
    aux = root / "Auxiliary"
    aux.mkdir()
    (aux / "main.fls").write_text(
        f"INPUT {(root / 'main.tex').as_posix()}\nINPUT {(section / 'en.tex').as_posix()}\n",
        encoding="utf-8",
    )
    out = root / "Build"
    out.mkdir()
    (out / "main.pdf").write_bytes(b"%PDF-1.4 fake")

    result = build_pack(root, "main", out, aux, submit_dir=root / "Submission")
    assert result.compat.non_ascii_chars == {}
    assert sorted(path.name for path in result.compat.tex_files) == ["en.tex", "main.tex"]
    # .fls 在且 PDF 不旧于源码 → 产物检查无告警
    assert result.used_fls is True
    assert result.stale_sources == []
    with zipfile.ZipFile(result.zip_path) as zf:
        names = set(zf.namelist())
    assert "main-cn.tex" not in names
    assert "Section/cn.tex" not in names
    log = result.log_path.read_text(encoding="utf-8")
    assert "板" not in log
    assert "main-cn.tex" not in log
    # 干净包不写兼容性小节，避免空标题误导
    assert "pdflatex 兼容性" not in log


def test_build_pack_writes_diagnostic_log_beside_zip(tmp_path):
    """明细（逐字计数、文件:行号、宏包原因）写进 <包名>.log，且不进 zip。"""
    root = tmp_path
    (root / "main.tex").write_text(
        "\\documentclass{article}\n"
        "\\usepackage{ctex}\n"
        "\\begin{document}\n"
        "板式换热器 α\n"
        "% 注释里的 换热器 不计入\n"
        "\\end{document}\n",
        encoding="utf-8",
    )
    aux = root / "Auxiliary"
    aux.mkdir()
    out = root / "Build"
    out.mkdir()
    (out / "main.pdf").write_bytes(b"%PDF-1.4 fake")

    result = build_pack(root, "main", out, aux, submit_dir=root / "Submission")
    assert result.log_path == result.zip_path.with_suffix(".log")
    log = result.log_path.read_text(encoding="utf-8")
    assert "PyTeXMK 投稿包诊断日志" in log
    assert result.sha256 in log
    assert "## 导言区净化" in log
    assert "## pdflatex 兼容性（正文仅报告；导言区按需净化；注释已跳过）" in log
    assert "提交副本已注释，无需手改" in log
    assert "ctex: ctex 依赖" in log
    assert "板 (U+677F) × 1：main.tex:4" in log  # 逐字计数 + 位置
    assert "注释里的" not in log  # 注释内字符不参与统计
    assert "Unicode → LaTeX 转换清单" not in log  # 不再有自动转换清单
    with zipfile.ZipFile(result.zip_path) as zf:
        assert "main-submission.log" not in zf.namelist()


def test_pack_reports_missing_fls_as_fallback(tmp_path):
    """没有 .fls 时照常出包，但结果要标记“用了后缀兜底”，日志写明原因。"""
    root = tmp_path
    (root / "main.tex").write_text(
        "\\documentclass{article}\\begin{document}x\\end{document}\n", encoding="utf-8"
    )
    (root / "figs").mkdir()
    (root / "figs" / "unused.png").write_bytes(b"x")  # 没被引用也会被兜底收进来
    aux = root / "Auxiliary"
    aux.mkdir()
    out = root / "Build"
    out.mkdir()
    (out / "main.pdf").write_bytes(b"%PDF-1.4 fake")

    result = build_pack(root, "main", out, aux, submit_dir=root / "Submission")
    assert result.used_fls is False
    assert result.fls_path == Path("Auxiliary") / "main.fls"
    log = result.log_path.read_text(encoding="utf-8")
    assert "## 产物检查" in log
    assert "按后缀白名单兜底收集" in log
    assert "建议先编译一次再打包" in log


def test_pack_reports_pdf_older_than_sources(tmp_path):
    """源文件比 PDF 新时必须标记出来：用户核对的 PDF 与包内源码不是同一版。"""
    root = tmp_path
    (root / "main.tex").write_text(
        "\\documentclass{article}\\begin{document}x\\end{document}\n", encoding="utf-8"
    )
    aux = root / "Auxiliary"
    aux.mkdir()
    (aux / "main.fls").write_text(
        f"INPUT {(root / 'main.tex').as_posix()}\n", encoding="utf-8"
    )
    out = root / "Build"
    out.mkdir()
    pdf = out / "main.pdf"
    pdf.write_bytes(b"%PDF-1.4 fake")
    pdf_mtime = pdf.stat().st_mtime
    os.utime(root / "main.tex", (pdf_mtime + 120, pdf_mtime + 120))

    result = build_pack(root, "main", out, aux, submit_dir=root / "Submission")
    assert result.stale_sources == ["main.tex"]
    log = result.log_path.read_text(encoding="utf-8")
    assert "PDF 早于 main.tex" in log
    assert "建议重新编译后再提交" in log

