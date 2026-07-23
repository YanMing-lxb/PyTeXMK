# -*- coding: utf-8 -*-
"""
test_log_analysis.py - LogAnalysis 类单元测试
"""

from pathlib import Path

from pytexmk.log_analysis import LogAnalysis, LatexLogParser


# ========================
# 辅助函数
# ========================


def write_log(tmp_path: Path, base_name: str, suffix: str, content: str) -> Path:
    """在临时目录写入日志文件"""
    log_file = tmp_path / f"{base_name}{suffix}"
    log_file.write_text(content, encoding="utf-8", errors="ignore")
    return log_file


def create_analyzer(tmp_path: Path, base_name: str = "test") -> LogAnalysis:
    """创建在临时目录工作的 LogAnalysis 实例"""
    return LogAnalysis(str(tmp_path / base_name))


# ========================
# 编译成功日志测试
# ========================


class TestCompilationSuccess:
    """测试编译成功场景"""

    def test_pdflatex_success(self, tmp_path):
        """测试 pdfLaTeX 编译成功"""
        log_content = r"""This is pdfTeX, Version 3.141592653-2.6-1.40.25 (TeX Live 2023)
entering extended mode
(./test.tex
LaTeX2e <2023-11-01> patch level 1
)
(./test.aux)
No file test.bbl.
[1
{C:/Users/test/AppData/Local/MiKTeX/fonts/map/pdftex/pdftex.map}]
Output written on test.pdf (1 page, 12345 bytes).
Transcript written on test.log.
"""
        write_log(tmp_path, "test", ".log", log_content)
        analyzer = create_analyzer(tmp_path)
        analyzer.parse_all()

        assert analyzer.compilation_success is True
        assert analyzer.engine_type == "pdflatex"
        assert analyzer.pages == 1
        assert analyzer.output_file == "test.pdf"
        assert analyzer.check_tex_error() == 0
        assert "test.bbl" in analyzer.missing_files

    def test_xelatex_success(self, tmp_path):
        """测试 XeLaTeX 编译成功"""
        log_content = r"""This is XeTeX, Version 3.141592653-2.6-0.999995 (TeX Live 2023)
entering extended mode
(./test.tex
LaTeX2e <2023-11-01> patch level 1
)
(./test.aux) [1]
Output written on test.pdf (2 pages, 45678 bytes).
Transcript written on test.log.
"""
        write_log(tmp_path, "test", ".log", log_content)
        analyzer = create_analyzer(tmp_path)
        analyzer.parse_all()

        assert analyzer.compilation_success is True
        assert analyzer.engine_type == "xelatex"
        assert analyzer.pages == 2

    def test_lualatex_success(self, tmp_path):
        """测试 LuaLaTeX 编译成功"""
        log_content = r"""This is LuaTeX, Version 1.17.0 (TeX Live 2023)
 restricted system commands enabled.
(./test.tex
LaTeX2e <2023-11-01> patch level 1
)
(./test.aux) [1{lualatex-cache}] [2]
Output written on test.pdf (2 pages).
Transcript written on test.log.
"""
        write_log(tmp_path, "test", ".log", log_content)
        analyzer = create_analyzer(tmp_path)
        analyzer.parse_all()

        assert analyzer.compilation_success is True
        assert analyzer.engine_type == "lualatex"
        assert analyzer.pages == 2

    def test_success_no_errors_warnings(self, tmp_path):
        """测试完全成功（无错误无警告）"""
        log_content = r"""This is pdfTeX, Version 3.14
(./test.tex) (./test.aux) [1]
Output written on test.pdf (1 page, 100 bytes).
Transcript written on test.log.
"""
        write_log(tmp_path, "test", ".log", log_content)
        analyzer = create_analyzer(tmp_path)
        analyzer.parse_all()

        assert analyzer.get_errors() == []
        summary = analyzer.get_compilation_summary()
        assert summary["success"] is True
        assert summary["tex_errors"] == 0


# ========================
# LaTeX 错误检测测试
# ========================


class TestLaTeXErrors:
    """测试 LaTeX 错误检测"""

    def test_bang_error(self, tmp_path):
        """测试 ! 开头的经典 LaTeX 错误"""
        log_content = r"""This is pdfTeX, Version 3.14
(./test.tex (./chapters/intro.tex
! Undefined control sequence.
l.42 \unkowncommand

The control sequence at the end of the top line
of your error message was never \def'ed.
)
! Emergency stop.
l.42 \unkowncommand

No pages of output.
Transcript written on test.log.
"""
        write_log(tmp_path, "test", ".log", log_content)
        analyzer = create_analyzer(tmp_path)
        analyzer.parse_all()

        assert analyzer.check_tex_error() >= 1
        assert analyzer.has_fatal_errors() is True
        assert analyzer.compilation_success is False

    def test_pdftex_error(self, tmp_path):
        """测试 !pdfTeX error: 前缀"""
        log_content = r"""This is pdfTeX, Version 3.14
(./test.tex)
!pdfTeX error: pdflatex.exe (file cmr10.pfb): cannot open Type 1 font file for reading
 ==> Fatal error occurred, no output PDF file produced!
Transcript written on test.log.
"""
        write_log(tmp_path, "test", ".log", log_content)
        analyzer = create_analyzer(tmp_path)
        analyzer.parse_all()

        assert analyzer.check_tex_error() >= 1
        assert analyzer.has_fatal_errors() is True

    def test_xetex_error(self, tmp_path):
        """测试 !XeTeX error: 前缀"""
        log_content = r"""This is XeTeX, Version 3.14
(./test.tex)
!XeTeX error: xelatex.exe: Could not find font
"""
        write_log(tmp_path, "test", ".log", log_content)
        analyzer = create_analyzer(tmp_path)
        analyzer.parse_all()

        assert analyzer.check_tex_error() >= 1

    def test_luatex_error(self, tmp_path):
        """测试 !LuaTeX error: 前缀"""
        log_content = r"""This is LuaTeX, Version 1.17
(./test.tex)
!LuaTeX error: cannot find font
"""
        write_log(tmp_path, "test", ".log", log_content)
        analyzer = create_analyzer(tmp_path)
        analyzer.parse_all()

        assert analyzer.check_tex_error() >= 1

    def test_emergency_stop(self, tmp_path):
        """测试 Emergency stop 检测"""
        log_content = r"""This is pdfTeX, Version 3.14
(./test.tex)
!  ==> Fatal error occurred, no output PDF file produced!
Emergency stop.
"""
        write_log(tmp_path, "test", ".log", log_content)
        analyzer = create_analyzer(tmp_path)
        analyzer.parse_all()

        assert analyzer.has_fatal_errors() is True

    def test_cant_use_error(self, tmp_path):
        """测试 You can't use 错误"""
        log_content = r"""This is pdfTeX, Version 3.14
(./test.tex)
You can't use `\macro' in vertical mode.
l.10 \macro
"""
        write_log(tmp_path, "test", ".log", log_content)
        analyzer = create_analyzer(tmp_path)
        analyzer.parse_all()

        assert analyzer.check_tex_error() >= 1

    def test_error_with_line_number(self, tmp_path):
        """测试错误行号提取"""
        log_content = r"""This is pdfTeX, Version 3.14
(./test.tex)
! Undefined control sequence.
l.123 \badcommand

Type <return> to continue.
"""
        write_log(tmp_path, "test", ".log", log_content)
        analyzer = create_analyzer(tmp_path)
        analyzer.parse_all()

        errors = analyzer.get_errors()
        assert len(errors) >= 1
        line_found = any(e.get("line", 0) == 123 for e in errors)
        assert line_found is True


# ========================
# 警告检测测试
# ========================


class TestWarnings:
    """测试警告检测"""

    def test_package_warning(self, tmp_path):
        """测试 Package ... Warning:"""
        log_content = r"""This is pdfTeX, Version 3.14
(./test.tex
Package hyperref Warning: Token not allowed in a PDF string,
on input line 50.
)
Output written on test.pdf (1 page).
Transcript written on test.log.
"""
        write_log(tmp_path, "test", ".log", log_content)
        analyzer = create_analyzer(tmp_path)
        analyzer.parse_all()

        assert analyzer.check_warning() >= 1
        pkg_warnings = [w for w in analyzer.get_warnings() if "hyperref" in w["message"]]
        assert len(pkg_warnings) >= 1

    def test_class_warning(self, tmp_path):
        """测试 Class ... Warning:"""
        log_content = r"""This is pdfTeX, Version 3.14
(./test.tex
Class article Warning: Unknown document class option,
on input line 10.
)
Output written on test.pdf (1 page).
Transcript written on test.log.
"""
        write_log(tmp_path, "test", ".log", log_content)
        analyzer = create_analyzer(tmp_path)
        analyzer.parse_all()

        assert analyzer.check_warning() >= 1

    def test_latex_warning(self, tmp_path):
        """测试 LaTeX Warning:"""
        log_content = r"""This is pdfTeX, Version 3.14
(./test.tex)
LaTeX Warning: File `image.png' not found on input line 20.
Output written on test.pdf (1 page).
Transcript written on test.log.
"""
        write_log(tmp_path, "test", ".log", log_content)
        analyzer = create_analyzer(tmp_path)
        analyzer.parse_all()

        assert analyzer.check_warning() >= 1

    def test_pdftex_warning(self, tmp_path):
        """测试 pdfTeX warning:"""
        log_content = r"""This is pdfTeX, Version 3.14
(./test.tex) [1]
pdfTeX warning: pdflatex: has been referenced but does not exist
Output written on test.pdf (1 page).
Transcript written on test.log.
"""
        write_log(tmp_path, "test", ".log", log_content)
        analyzer = create_analyzer(tmp_path)
        analyzer.parse_all()

        assert analyzer.check_warning() >= 1


# ========================
# 未定义引用/参考文献测试
# ========================


class TestUndefinedRefs:
    """测试未定义引用和参考文献"""

    def test_undefined_citation(self, tmp_path):
        """测试未定义 citation"""
        log_content = r"""This is pdfTeX, Version 3.14
(./test.tex)
LaTeX Warning: Citation `Smith2023' on page 1 undefined on input line 15.
LaTeX Warning: Citation `Jones2022' on page 1 undefined on input line 16.
Output written on test.pdf (1 page).
Transcript written on test.log.
"""
        write_log(tmp_path, "test", ".log", log_content)
        analyzer = create_analyzer(tmp_path)
        analyzer.parse_all()

        citations = analyzer.get_undefined_citations()
        assert "Smith2023" in citations
        assert "Jones2022" in citations
        assert analyzer.has_citation_errors() is True
        assert analyzer.needs_recompile_bib() is True

    def test_undefined_reference(self, tmp_path):
        """测试未定义 reference"""
        log_content = r"""This is pdfTeX, Version 3.14
(./test.tex)
LaTeX Warning: Reference `fig:intro' on page 1 undefined on input line 25.
LaTeX Warning: Reference `tab:results' on page 2 undefined on input line 30.
Rerun to get cross-references right.
Output written on test.pdf (2 pages).
Transcript written on test.log.
"""
        write_log(tmp_path, "test", ".log", log_content)
        analyzer = create_analyzer(tmp_path)
        analyzer.parse_all()

        refs = analyzer.get_undefined_references()
        assert "fig:intro" in refs
        assert "tab:results" in refs
        assert analyzer.has_reference_errors() is True
        assert analyzer.needs_extra_pass() is True

    def test_no_file_bbl(self, tmp_path):
        """测试缺少 bbl 文件触发 bib 重编译"""
        log_content = r"""This is pdfTeX, Version 3.14
(./test.tex) (./test.aux)
No file test.bbl.
Output written on test.pdf (1 page).
Transcript written on test.log.
"""
        write_log(tmp_path, "test", ".log", log_content)
        analyzer = create_analyzer(tmp_path)
        analyzer.parse_all()

        assert analyzer.needs_recompile_bib() is True

    def test_rerun_to_get(self, tmp_path):
        """测试 Rerun to get 提示触发额外 pass"""
        log_content = r"""This is pdfTeX, Version 3.14
(./test.tex) (./test.aux)
LaTeX Warning: There were undefined references.
Rerun to get outlines right
Output written on test.pdf (1 page).
Transcript written on test.log.
"""
        write_log(tmp_path, "test", ".log", log_content)
        analyzer = create_analyzer(tmp_path)
        analyzer.parse_all()

        assert analyzer.needs_extra_pass() is True


# ========================
# Overfull/Underfull 测试
# ========================


class TestBadBoxes:
    """测试 Overfull/Underfull boxes"""

    def test_overfull_hbox(self, tmp_path):
        """测试 Overfull hbox 检测"""
        log_content = r"""This is pdfTeX, Version 3.14
(./test.tex)
Overfull \hbox (10.5pt too wide) in paragraph at lines 10--12
[]\OT1/cmr/m/n/10 This is some text that is too long and will overflow
Overfull \vbox (5.0pt too high) detected at line 20
Output written on test.pdf (1 page).
Transcript written on test.log.
"""
        write_log(tmp_path, "test", ".log", log_content)
        analyzer = create_analyzer(tmp_path)
        analyzer.parse_all()

        assert analyzer.overfull_boxes >= 1

    def test_underfull_hbox(self, tmp_path):
        """测试 Underfull hbox 检测"""
        log_content = r"""This is pdfTeX, Version 3.14
(./test.tex)
Underfull \hbox (badness 10000) in paragraph at lines 5--8
Underfull \vbox (badness 5000) detected at line 15
Output written on test.pdf (1 page).
Transcript written on test.log.
"""
        write_log(tmp_path, "test", ".log", log_content)
        analyzer = create_analyzer(tmp_path)
        analyzer.parse_all()

        assert analyzer.underfull_boxes >= 1


# ========================
# 缺少文件测试
# ========================


class TestMissingFiles:
    """测试缺少文件检测"""

    def test_no_file_various(self, tmp_path):
        """测试 No file ... 检测"""
        log_content = r"""This is pdfTeX, Version 3.14
(./test.tex) (./test.aux)
No file test.bbl.
No file test.ind.
No file chapters/chap1.aux.
Output written on test.pdf (1 page).
Transcript written on test.log.
"""
        write_log(tmp_path, "test", ".log", log_content)
        analyzer = create_analyzer(tmp_path)
        analyzer.parse_all()

        assert "test.bbl" in analyzer.missing_files
        assert "test.ind" in analyzer.missing_files
        assert analyzer.needs_recompile_index() is True


# ========================
# BibTeX 日志测试
# ========================


class TestBibTeX:
    """测试 BibTeX 日志解析"""

    def test_bibtex_error(self, tmp_path):
        """测试 BibTeX 错误"""
        blg_content = r"""This is BibTeX, Version 0.99d
The top-level auxiliary file: test.aux
I found no \bibdata command---while reading file test.aux
Warning--I didn't find a database entry for "test"
"""
        write_log(tmp_path, "test", ".blg", blg_content)
        analyzer = create_analyzer(tmp_path)
        analyzer.parse_all()

        assert analyzer.check_bib_error() >= 1
        bib_errors = [e for e in analyzer.get_errors() if e["source"] == "bibtex"]
        assert len(bib_errors) >= 1

    def test_bibtex_fatal(self, tmp_path):
        """测试 BibTeX 致命错误"""
        blg_content = r"""Fatal error: aux file not found
Aborted."""
        write_log(tmp_path, "test", ".blg", blg_content)
        analyzer = create_analyzer(tmp_path)
        analyzer.parse_all()

        assert analyzer.check_bib_error() >= 1

    def test_biber_error(self, tmp_path):
        """测试 Biber 错误"""
        blg_content = r"""INFO - This is Biber 2.19
INFO - Logfile is 'test.blg'
ERROR - Cannot find 'test.bcf'!
WARN - I didn't find a database entry for 'MissingKey'
FATAL - Caught signal
"""
        write_log(tmp_path, "test", ".blg", blg_content)
        analyzer = create_analyzer(tmp_path)
        analyzer.parse_all()

        assert analyzer.check_bib_error() >= 1
        biber_errors = [e for e in analyzer.get_errors() if e["source"] == "biber"]
        assert len(biber_errors) >= 1
        biber_warns = [w for w in analyzer.get_warnings() if w["source"] == "biber"]
        assert len(biber_warns) >= 1


# ========================
# Makeindex 日志测试
# ========================


class TestMakeindex:
    """测试 Makeindex 日志解析"""

    def test_makeindex_bang_error(self, tmp_path):
        """测试 Makeindex !! 错误"""
        ilg_content = r"""This is makeindex, version 2.16
Scanning input file test.idx...
!! Input index error extra '}' at line 5
!! Output file not written.
"""
        write_log(tmp_path, "test", ".ilg", ilg_content)
        analyzer = create_analyzer(tmp_path)
        analyzer.parse_all()

        assert analyzer.check_index_error() >= 1
        idx_errors = [e for e in analyzer.get_errors() if e["source"] == "makeindex"]
        assert len(idx_errors) >= 1

    def test_makeindex_notfound(self, tmp_path):
        """测试 Makeindex 输入文件未找到"""
        ilg_content = r"""This is makeindex, version 2.16
Input index file test.idx not found.
Usage: makeindex ...
"""
        write_log(tmp_path, "test", ".ilg", ilg_content)
        analyzer = create_analyzer(tmp_path)
        analyzer.parse_all()

        assert analyzer.check_index_error() >= 1
        assert analyzer.needs_recompile_index() is True

    def test_makeindex_warning(self, tmp_path):
        """测试 Makeindex 警告"""
        ilg_content = r"""This is makeindex, version 2.16
Scanning input file test.idx....done (3 entries accepted, 0 rejected).
## Warning: input file style not found, using defaults.
Sorting entries....done
Output written on test.ind (3 entries).
"""
        write_log(tmp_path, "test", ".ilg", ilg_content)
        analyzer = create_analyzer(tmp_path)
        analyzer.parse_all()

        idx_warns = [w for w in analyzer.get_warnings() if w["source"] == "makeindex"]
        assert len(idx_warns) >= 1


# ========================
# Xindy 日志测试
# ========================


class TestXindy:
    """测试 Xindy 日志解析"""

    def test_xindy_xlg_error(self, tmp_path):
        """测试 .xlg 文件中的 xindy 错误"""
        xlg_content = r"""xindy release: 2.5.1
xindy script version: 1.17
ERROR: Missing index file!
Cannot open input file test.idx: No such file or directory
WARNING: Some entries may be out of order.
"""
        write_log(tmp_path, "test", ".xlg", xlg_content)
        analyzer = create_analyzer(tmp_path)
        analyzer.parse_all()

        assert analyzer.check_index_error() >= 1
        xindy_errors = [e for e in analyzer.get_errors() if e["source"] == "xindy"]
        assert len(xindy_errors) >= 1
        xindy_warns = [w for w in analyzer.get_warnings() if w["source"] == "xindy"]
        assert len(xindy_warns) >= 1
        assert analyzer.needs_recompile_index() is True

    def test_xindy_in_ilg(self, tmp_path):
        """测试在 .ilg 中的 xindy 日志"""
        ilg_content = r"""xindy release: 2.5.1
xindy script version: 1.17
ERROR: Cannot read style file `mystyle.xdy'
"""
        write_log(tmp_path, "test", ".ilg", ilg_content)
        analyzer = create_analyzer(tmp_path)
        analyzer.parse_all()

        assert analyzer.check_index_error() >= 1
        xindy_errors = [e for e in analyzer.get_errors() if e["source"] == "xindy"]
        assert len(xindy_errors) >= 1

    def test_xindy_fatal(self, tmp_path):
        """测试 xindy 致命错误"""
        xlg_content = r"""xindy release: 2.5.1
FATAL error: xindy failed
"""
        write_log(tmp_path, "test", ".xlg", xlg_content)
        analyzer = create_analyzer(tmp_path)
        analyzer.parse_all()

        assert analyzer.check_index_error() >= 1
        fatal_errors = [e for e in analyzer.get_errors() if e.get("level") == "fatal"]
        assert len(fatal_errors) >= 1


# ========================
# Glossaries 日志测试
# ========================


class TestGlossaries:
    """测试 Glossaries 日志解析"""

    def test_glg_error(self, tmp_path):
        """测试 .glg 错误"""
        glg_content = r"""This is makeglossaries version 4.50
!! No file test.glo.
Error: Cannot find glossary input file.
"""
        write_log(tmp_path, "test", ".glg", glg_content)
        analyzer = create_analyzer(tmp_path)
        analyzer.parse_all()

        assert analyzer.check_index_error() >= 1
        glg_errors = [e for e in analyzer.get_errors() if e["source"] == "glossaries"]
        assert len(glg_errors) >= 1


# ========================
# Nomencl 日志测试
# ========================


class TestNomencl:
    """测试 Nomencl 日志解析"""

    def test_nlg_error(self, tmp_path):
        """测试 .nlg 错误"""
        nlg_content = r"""This is makeindex, version 2.16 (nomencl).
!! Input file test.nlo not found.
"""
        write_log(tmp_path, "test", ".nlg", nlg_content)
        analyzer = create_analyzer(tmp_path)
        analyzer.parse_all()

        assert analyzer.check_index_error() >= 1
        nlg_errors = [e for e in analyzer.get_errors() if e["source"] == "nomencl"]
        assert len(nlg_errors) >= 1


# ========================
# 结构化查询方法测试
# ========================


class TestQueryMethods:
    """测试公开查询方法"""

    def test_get_errors_returns_list(self, tmp_path):
        """测试 get_errors() 返回 list"""
        log_content = r"""This is pdfTeX, Version 3.14
(./test.tex)
! Undefined control sequence.
l.5 \bad
Output written on test.pdf (1 page).
"""
        write_log(tmp_path, "test", ".log", log_content)
        analyzer = create_analyzer(tmp_path)
        analyzer.parse_all()

        errors = analyzer.get_errors()
        assert isinstance(errors, list)
        assert len(errors) >= 1
        for e in errors:
            assert "file" in e
            assert "line" in e
            assert "message" in e
            assert "source" in e

    def test_get_warnings_returns_list(self, tmp_path):
        """测试 get_warnings() 返回 list"""
        log_content = r"""This is pdfTeX, Version 3.14
(./test.tex)
Package foo Warning: test warning on input line 10.
Output written on test.pdf (1 page).
"""
        write_log(tmp_path, "test", ".log", log_content)
        analyzer = create_analyzer(tmp_path)
        analyzer.parse_all()

        warnings = analyzer.get_warnings()
        assert isinstance(warnings, list)

    def test_get_undefined_returns_set(self, tmp_path):
        """测试 get_undefined_citations/references 返回 set"""
        log_content = r"""This is pdfTeX, Version 3.14
(./test.tex)
LaTeX Warning: Citation `a' undefined.
LaTeX Warning: Reference `b' undefined.
Output written on test.pdf (1 page).
"""
        write_log(tmp_path, "test", ".log", log_content)
        analyzer = create_analyzer(tmp_path)
        analyzer.parse_all()

        assert isinstance(analyzer.get_undefined_citations(), set)
        assert isinstance(analyzer.get_undefined_references(), set)
        assert isinstance(analyzer.get_missing_files(), set)

    def test_get_compilation_summary(self, tmp_path):
        """测试 get_compilation_summary() 返回结构正确"""
        log_content = r"""This is XeTeX, Version 3.14
(./test.tex) (./test.aux)
LaTeX Warning: Citation `key' undefined.
Output written on test.pdf (3 pages).
"""
        write_log(tmp_path, "test", ".log", log_content)
        analyzer = create_analyzer(tmp_path)
        summary = analyzer.get_compilation_summary()

        assert isinstance(summary, dict)
        assert "success" in summary
        assert "engine" in summary
        assert "pages" in summary
        assert "tex_errors" in summary
        assert "bib_errors" in summary
        assert "index_errors" in summary
        assert "warnings" in summary
        assert "needs_recompile_bib" in summary
        assert "needs_extra_pass" in summary
        assert summary["engine"] == "xelatex"
        assert summary["pages"] == 3

    def test_has_methods_return_bool(self, tmp_path):
        """测试 has_* 方法返回 bool"""
        log_content = r"""This is pdfTeX, Version 3.14
(./test.tex)
Output written on test.pdf (1 page).
"""
        write_log(tmp_path, "test", ".log", log_content)
        analyzer = create_analyzer(tmp_path)
        analyzer.parse_all()

        assert isinstance(analyzer.has_citation_errors(), bool)
        assert isinstance(analyzer.has_reference_errors(), bool)
        assert isinstance(analyzer.has_index_errors(), bool)
        assert isinstance(analyzer.has_fatal_errors(), bool)
        assert isinstance(analyzer.needs_recompile_bib(), bool)
        assert isinstance(analyzer.needs_recompile_index(), bool)
        assert isinstance(analyzer.needs_extra_pass(), bool)


# ========================
# 向后兼容测试
# ========================


class TestBackwardCompatibility:
    """测试旧接口向后兼容"""

    def test_latexlogparser_exists(self):
        """测试 LatexLogParser 类存在且可导入"""
        assert LatexLogParser is not None
        parser = LatexLogParser(root_file="test.tex")
        assert parser is not None

    def test_latexlogparser_parse(self):
        """测试 LatexLogParser.parse() 方法"""
        log_text = r"""This is pdfTeX, Version 3.14
(./test.tex)
! Undefined control sequence.
l.1 \badcommand
Type H for help.
)
Output written on test.pdf (1 page).
"""
        parser = LatexLogParser(root_file="test.tex")
        entries = parser.parse(log_text)
        assert isinstance(entries, list)

    def test_check_methods_return_int(self, tmp_path):
        """测试 check_* 方法返回 int"""
        log_content = r"""This is pdfTeX, Version 3.14
(./test.tex)
Output written on test.pdf (1 page).
"""
        write_log(tmp_path, "test", ".log", log_content)
        analyzer = create_analyzer(tmp_path)
        analyzer.parse_all()

        assert isinstance(analyzer.check_tex_error(), int)
        assert isinstance(analyzer.check_bib_error(), int)
        assert isinstance(analyzer.check_index_error(), int)
        assert isinstance(analyzer.check_warning(), int)

    def test_parse_all_chainable(self, tmp_path):
        """测试 parse_all() 可链式调用"""
        log_content = r"""This is pdfTeX, Version 3.14
(./test.tex)
Output written on test.pdf (1 page).
"""
        write_log(tmp_path, "test", ".log", log_content)
        analyzer = create_analyzer(tmp_path)
        result = analyzer.parse_all()
        assert result is analyzer


# ========================
# 空文件/不存在文件测试
# ========================


class TestEdgeCases:
    """测试边界情况"""

    def test_no_log_file(self, tmp_path):
        """测试没有日志文件时不崩溃"""
        analyzer = create_analyzer(tmp_path, "nonexistent")
        analyzer.parse_all()

        assert analyzer.compilation_success is False
        assert analyzer.check_tex_error() == 0
        assert analyzer.get_errors() == []
        assert analyzer.get_warnings() == []

    def test_empty_log_file(self, tmp_path):
        """测试空日志文件"""
        write_log(tmp_path, "test", ".log", "")
        analyzer = create_analyzer(tmp_path)
        analyzer.parse_all()

        assert analyzer.compilation_success is False

    def test_multiple_parse_all_calls(self, tmp_path):
        """测试多次调用 parse_all() 重置状态"""
        log_content1 = r"""This is pdfTeX, Version 3.14
(./test.tex)
! Undefined control sequence.
l.1 \bad
Output written on test.pdf (1 page).
"""
        write_log(tmp_path, "test", ".log", log_content1)
        analyzer = create_analyzer(tmp_path)
        analyzer.parse_all()
        assert analyzer.check_tex_error() >= 1

        log_content2 = r"""This is pdfTeX, Version 3.14
(./test.tex)
Output written on test.pdf (1 page).
"""
        write_log(tmp_path, "test", ".log", log_content2)
        analyzer.parse_all()
        assert analyzer.check_tex_error() == 0
        assert analyzer.compilation_success is True

    def test_loaded_files_tracking(self, tmp_path):
        """测试加载文件列表"""
        log_content = r"""This is pdfTeX, Version 3.14
(./test.tex
(/usr/share/texlive/texmf-dist/tex/latex/article.cls
Document Class: article
)
(/usr/share/texlive/texmf-dist/tex/latex/hyperref/hyperref.sty
)
)
Output written on test.pdf (1 page).
"""
        write_log(tmp_path, "test", ".log", log_content)
        analyzer = create_analyzer(tmp_path)
        analyzer.parse_all()

        assert "article.cls" in " ".join(analyzer.loaded_files) or "hyperref.sty" in " ".join(analyzer.loaded_files)


# ========================
# 综合场景测试
# ========================


class TestComplexScenarios:
    """测试综合场景"""

    def test_full_compile_cycle_with_bib(self, tmp_path):
        """测试带参考文献的完整编译周期判断"""
        log_content = r"""This is pdfTeX, Version 3.14
(./test.tex) (./test.aux)
LaTeX Warning: Citation `Doe2024' undefined.
No file test.bbl.
Overfull \hbox (5pt too wide) in paragraph at lines 10--12
[1]
Output written on test.pdf (1 page, 12345 bytes).
Transcript written on test.log.
"""
        blg_content = r"""This is BibTeX, Version 0.99d
The top-level auxiliary file: test.aux
The style file: plain.bst
Database file #1: refs.bib
Warning--empty journal in Doe2024
"""
        write_log(tmp_path, "test", ".log", log_content)
        write_log(tmp_path, "test", ".blg", blg_content)
        analyzer = create_analyzer(tmp_path)
        summary = analyzer.get_compilation_summary()

        assert summary["needs_recompile_bib"] is True
        assert summary["undefined_citations"] == 1
        assert summary["overfull_boxes"] >= 1

    def test_index_scenario(self, tmp_path):
        """测试索引场景判断"""
        log_content = r"""This is pdfTeX, Version 3.14
(./test.tex) (./test.aux)
No file test.ind.
[1]
Output written on test.pdf (1 page).
"""
        ilg_content = r"""This is makeindex, version 2.16
Input index file test.idx not found.
"""
        write_log(tmp_path, "test", ".log", log_content)
        write_log(tmp_path, "test", ".ilg", ilg_content)
        analyzer = create_analyzer(tmp_path)
        analyzer.parse_all()

        assert analyzer.needs_recompile_index() is True
        assert analyzer.check_index_error() >= 1
