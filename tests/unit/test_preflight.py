"""preflight / latexdiff flatten / 清理安全 / 索引配置 的回归测试（3.2 / 3.5 / 3.8 / U6）。"""

import re
from pathlib import Path

from pytexmk.detection import (
    IndexSpec,
    _index_glossaries_cmd_builder_v2,
    _nomencl_cmd_builder,
    configure_index,
)
from pytexmk.file_ops import FileMoveRemoveManager
from pytexmk.latexdiff import LaTeXDiff_Aux
from pytexmk.preflight import check_project


def _write(path: Path, text: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


# --------------------------------------------------------------- 3.2 preflight


def test_preflight_ok(tmp_path):
    _write(tmp_path / "main.tex", "\\documentclass{article}\n\\begin{document}\nHi\n\\end{document}\n")
    report = check_project("main", tmp_path)
    assert report.ok
    assert report.issues == []


def test_preflight_missing_end_document(tmp_path):
    _write(tmp_path / "main.tex", "\\documentclass{article}\n\\begin{document}\nHi\n")
    report = check_project("main", tmp_path)
    assert not report.ok
    assert any("\\end{document}" in i.message for i in report.errors)


def test_preflight_missing_bib_and_graphic(tmp_path):
    _write(
        tmp_path / "main.tex",
        "\\documentclass{article}\n\\begin{document}\n"
        "\\bibliography{refs}\n\\includegraphics{fig/none}\n"
        "\\end{document}\n",
    )
    report = check_project("main", tmp_path)
    assert any("refs.bib" in i.message for i in report.errors)
    assert any("图片不存在" in i.message for i in report.warnings)


def test_preflight_graphicspath_is_honored(tmp_path):
    (tmp_path / "fig").mkdir()
    (tmp_path / "fig" / "plot.pdf").write_bytes(b"%PDF-1.4")
    _write(
        tmp_path / "main.tex",
        "\\documentclass{article}\n\\graphicspath{{fig/}}\n\\begin{document}\n"
        "\\includegraphics{plot}\n\\end{document}\n",
    )
    report = check_project("main", tmp_path)
    assert not any("图片不存在" in issue.message for issue in report.issues)


def test_preflight_child_inherits_main_graphicspath(tmp_path):
    """主文件前导区声明的 ``\\graphicspath`` 对 ``\\input`` 子文件同样生效；
    预检对子文件自身的声明做宽松合并，而不是覆盖继承目录。"""
    (tmp_path / "Pictures").mkdir()
    (tmp_path / "Pictures" / "plot.pdf").write_bytes(b"%PDF-1.4")
    (tmp_path / "Section" / "figs").mkdir(parents=True)
    (tmp_path / "Section" / "figs" / "local.pdf").write_bytes(b"%PDF-1.4")
    _write(
        tmp_path / "main.tex",
        "\\documentclass{article}\n\\graphicspath{{Pictures/}}\n\\begin{document}\n"
        "\\input{Section/Section2}\n\\end{document}\n",
    )
    _write(
        tmp_path / "Section" / "Section2.tex",
        "\\graphicspath{{Section/figs/}}\n"
        "\\includegraphics{plot.pdf}\n"
        "\\includegraphics{local.pdf}\n",
    )

    report = check_project("main", tmp_path)
    assert not any("图片不存在" in issue.message for issue in report.issues)


def test_preflight_graphicspath_comma_separated_ok(tmp_path):
    """模板常见的 ``\\graphicspath{{Pictures/},}``：逗号分隔、末项为空即当前目录。

    一次性正则要求“花括号组后紧跟 ``}``”，会把这条声明整条漏掉，导致
    ``Pictures/`` 下实际存在的图片全部误报为“图片不存在”。
    """
    (tmp_path / "Pictures").mkdir()
    (tmp_path / "Pictures" / "plot.pdf").write_bytes(b"%PDF-1.4")
    _write(
        tmp_path / "main.tex",
        "\\documentclass{article}\n\\graphicspath{{Pictures/},}  % 图片目录\n"
        "\\begin{document}\n\\input{Section/ch}\n\\end{document}\n",
    )
    _write(
        tmp_path / "Section" / "ch.tex",
        "\\includegraphics[width=0.5\\textwidth]{plot.pdf}\n",
    )

    report = check_project("main", tmp_path)
    assert not any("图片不存在" in issue.message for issue in report.issues)


def test_preflight_graphicspath_multiple_dir_and_missing(tmp_path):
    """逗号分隔的多目录都要生效；真的不在任何目录时才报缺失。"""
    for name in ("figs", "plots"):
        (tmp_path / name).mkdir()
    (tmp_path / "figs" / "a.pdf").write_bytes(b"%PDF-1.4")
    (tmp_path / "plots" / "b.png").write_bytes(b"png")
    _write(
        tmp_path / "main.tex",
        "\\documentclass{article}\n\\graphicspath{{figs/},{plots/},}\n"
        "\\begin{document}\n\\includegraphics{a}\n\\includegraphics{b}\n"
        "\\includegraphics{gone}\n\\end{document}\n",
    )

    report = check_project("main", tmp_path)
    missing = [i.message for i in report.warnings if "图片不存在" in i.message]
    assert missing == ["图片不存在: gone"]


def test_preflight_missing_input_and_bom(tmp_path):
    _write(tmp_path / "main.tex", "\ufeff\\documentclass{article}\n\\begin{document}\n\\input{sec/a}\n\\end{document}\n")
    report = check_project("main", tmp_path)
    assert any("BOM" in i.message for i in report.warnings)
    assert any("sec/a.tex" in i.message for i in report.errors)


def test_preflight_custom_inputsection_is_not_misparsed(tmp_path):
    """``\\inputsection{...}`` 不能被正则的 ``\\input`` 前缀误匹配。"""
    _write(
        tmp_path / "main.tex",
        "\\documentclass{article}\n\\begin{document}\n"
        "\\newcommand{\\inputsection}[1]{#1}\n"
        "\\inputsection{section}\n"
        "\\end{document}\n",
    )
    report = check_project("main", tmp_path)
    assert report.ok
    assert not any("section.tex" in issue.message for issue in report.issues)


def test_preflight_dynamic_input_path_is_skipped(tmp_path):
    """宏定义体里的动态 ``#1`` / ``\\langdir`` 路径不阻断。"""
    _write(
        tmp_path / "main.tex",
        "\\documentclass{article}\n\\begin{document}\n"
        "\\newcommand{\\inputsection}[1]{\\input{Section/\\langdir/#1.tex}}\n"
        "\\inputsection{section}\n"
        "\\end{document}\n",
    )
    report = check_project("main", tmp_path)
    assert report.ok
    assert not any("目标不存在" in issue.message for issue in report.errors)


def test_preflight_top_level_dynamic_path_warns_but_does_not_block(tmp_path):
    """顶层动态路径无法静态求值，只提示、不阻断。"""
    _write(
        tmp_path / "main.tex",
        "\\documentclass{article}\n\\begin{document}\n"
        "\\input{\\jobname/section}\n"
        "\\end{document}\n",
    )
    report = check_project("main", tmp_path)
    assert report.ok
    assert any("动态 \\input/\\include 路径" in issue.message for issue in report.warnings)


def test_preflight_macro_definition_body_is_not_checked(tmp_path):
    """宏定义体里的静态 \\input 只有宏被调用时才需要检查，定义阶段不阻断。"""
    _write(
        tmp_path / "main.tex",
        "\\documentclass{article}\n\\begin{document}\n"
        "\\newcommand{\\foo}{\\input{missing}}\n"
        "\\end{document}\n",
    )
    report = check_project("main", tmp_path)
    assert report.ok
    assert not any("missing" in issue.message for issue in report.errors)


def test_preflight_invalid_utf8(tmp_path):
    (tmp_path / "main.tex").write_bytes(b"\\documentclass{article}\n\xff\xfe\n")
    report = check_project("main", tmp_path)
    assert any("UTF-8" in i.message for i in report.errors)


# --------------------------------------------------------------- 3.5 flatten


def test_flatten_uses_file_handle_and_nested_inputs(tmp_path):
    _write(tmp_path / "main.tex", "DOC\n\\input{sec/a}\nEND\n")
    _write(tmp_path / "sec" / "a.tex", "A\n\\input{b}\n")
    _write(tmp_path / "sec" / "b.tex", "B\n")
    aux = LaTeXDiff_Aux(".", [], [], tmp_path)
    import os

    cwd = Path.cwd()
    os.chdir(tmp_path)
    try:
        stem = aux.flatten_Latex("main")
    finally:
        os.chdir(cwd)
    text = (tmp_path / f"{stem}.tex").read_text(encoding="utf-8")
    assert "DOC" in text and "A" in text and "B" in text and "END" in text
    assert not re.search(r"INFO|DEBUG|Flatten", text)


def test_flatten_detects_cycle(tmp_path):
    _write(tmp_path / "main.tex", "M\n\\input{a}\n")
    _write(tmp_path / "a.tex", "A\n\\input{main}\n")
    aux = LaTeXDiff_Aux(".", [], [], tmp_path)
    import os

    cwd = Path.cwd()
    os.chdir(tmp_path)
    try:
        stem = aux.flatten_Latex("main")
    finally:
        os.chdir(cwd)
    text = (tmp_path / f"{stem}.tex").read_text(encoding="utf-8")
    assert text.count("M") == 1
    assert text.count("A") == 1


# --------------------------------------------------------------- 3.8 / U6


def test_index_style_file_is_configurable():
    configure_index("custom.ist")
    try:
        spec = IndexSpec(ext_in="nlo", ext_out="nls")
        cmd = _nomencl_cmd_builder("proj", spec)
    finally:
        configure_index("nomencl.ist")
    assert "custom.ist" in cmd[1]


def test_glossaries_makeglossaries_tool_is_configurable():
    """多 glossary 项目可切到 makeglossaries；默认仍保持 makeindex。"""
    ctx = {"backend": {"backend": "makeindex", "lang": "english"}, "name": "main", "glg": "glg"}
    configure_index(glossaries_tool="makeglossaries")
    try:
        spec = IndexSpec(ext_in="glo", ext_out="gls", ctx=ctx)
        cmd = _index_glossaries_cmd_builder_v2("proj", spec)
    finally:
        configure_index(glossaries_tool="makeindex")
    assert cmd == ["makeglossaries", "makeglossaries proj"]


def test_clean_matched_files_skips_tests_and_examples(tmp_path):
    _write(tmp_path / "tests" / "main.aux", "x")
    _write(tmp_path / "examples" / "main.log", "x")
    _write(tmp_path / "main.aux", "x")
    manager = FileMoveRemoveManager()
    manager.remove_matched_files([re.compile(r".*\.(aux|log)$")], str(tmp_path))
    assert not (tmp_path / "main.aux").exists()
    assert (tmp_path / "tests" / "main.aux").exists()
    assert (tmp_path / "examples" / "main.log").exists()


# --------------------------------------------------------------- 3.1 / U4


def test_watch_snapshot_ignores_build_and_aux(tmp_path):
    from pytexmk.cli.cli_watch import _snapshot

    _write(tmp_path / "main.tex", "x")
    _write(tmp_path / "refs.bib", "x")
    _write(tmp_path / "Build" / "main.tex", "x")
    _write(tmp_path / "Auxiliary" / "main.aux", "x")
    snap = _snapshot(tmp_path)
    assert set(snap) == {"main.tex", "refs.bib"}
