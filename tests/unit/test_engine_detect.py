# -*- coding: utf-8 -*-
"""engine_detect 智能引擎判定模块单元测试"""

from pytexmk.engine_detect import (
    detect_document_features,
    parse_magic_comments,
    select_engine,
    select_bib_tool,
    select_index_tool,
    auto_configure,
    _empty_features,
    _is_comment_line,
    _normalize_engine_name,
)
from pytexmk.toolchain import ToolchainManager


def _write_tex(tmp_path, content, name="test"):
    tex_path = tmp_path / (name + ".tex")
    tex_path.write_text(content, encoding="utf-8")
    return tex_path


class TestIsCommentLine:
    def test_comment_line_percent_start(self):
        assert _is_comment_line("% This is a comment") is True

    def test_comment_line_with_leading_space(self):
        assert _is_comment_line("   % indented comment") is True

    def test_non_comment_line(self):
        assert _is_comment_line("\\documentclass{article}") is False

    def test_empty_line_not_comment(self):
        assert _is_comment_line("") is False

    def test_whitespace_only_not_comment(self):
        assert _is_comment_line("   \t  ") is False


class TestNormalizeEngineName:
    def test_normalize_xelatex_variants(self):
        assert _normalize_engine_name("xelatex") == "xelatex"
        assert _normalize_engine_name("XeLaTeX") == "xelatex"
        assert _normalize_engine_name("XELATEX") == "xelatex"
        assert _normalize_engine_name("xetex") == "xelatex"

    def test_normalize_pdflatex_variants(self):
        assert _normalize_engine_name("pdflatex") == "pdflatex"
        assert _normalize_engine_name("PdfLaTeX") == "pdflatex"
        assert _normalize_engine_name("pdftex") == "pdflatex"

    def test_normalize_lualatex_variants(self):
        assert _normalize_engine_name("lualatex") == "lualatex"
        assert _normalize_engine_name("LuaLaTeX") == "lualatex"
        assert _normalize_engine_name("luatex") == "lualatex"

    def test_empty_string(self):
        assert _normalize_engine_name("") == ""

    def test_unknown_engine_passthrough(self):
        assert _normalize_engine_name("unknown") == "unknown"


class TestEmptyFeatures:
    def test_returns_expected_keys(self):
        f = _empty_features()
        expected_keys = {
            "has_chinese",
            "needs_unicode",
            "bib_engine",
            "index_engine",
            "has_glossaries",
            "has_nomencl",
            "detected_packages",
            "detected_documentclass",
        }
        assert set(f.keys()) == expected_keys
        assert f["has_chinese"] is False
        assert f["needs_unicode"] is False
        assert f["bib_engine"] is None
        assert f["index_engine"] is None
        assert f["has_glossaries"] is False
        assert f["has_nomencl"] is False
        assert f["detected_packages"] == []
        assert f["detected_documentclass"] is None


class TestDetectDocumentFeatures:
    def test_nonexistent_file(self):
        result = detect_document_features("/nonexistent/file.tex")
        assert result["has_chinese"] is False
        assert result["bib_engine"] is None

    def test_plain_english_document(self, tmp_path):
        content = "\\documentclass{article}\n\\usepackage{geometry}\n\\usepackage{amsmath}\n\\begin{document}\nHello world.\n\\end{document}\n"
        tex = _write_tex(tmp_path, content)
        f = detect_document_features(tex)
        assert f["has_chinese"] is False
        assert f["needs_unicode"] is False
        assert f["bib_engine"] is None
        assert f["index_engine"] is None
        assert f["detected_documentclass"] == "article"
        assert "geometry" in f["detected_packages"]
        assert "amsmath" in f["detected_packages"]

    def test_ctex_package(self, tmp_path):
        content = "\\documentclass{article}\n\\usepackage{ctex}\n\\begin{document}\nHello\n\\end{document}\n"
        tex = _write_tex(tmp_path, content)
        f = detect_document_features(tex)
        assert f["has_chinese"] is True
        assert f["needs_unicode"] is True
        assert "ctex" in f["detected_packages"]

    def test_ctex_documentclass(self, tmp_path):
        content = "\\documentclass{ctexart}\n\\begin{document}\nTest\n\\end{document}\n"
        tex = _write_tex(tmp_path, content)
        f = detect_document_features(tex)
        assert f["has_chinese"] is True
        assert f["needs_unicode"] is True
        assert f["detected_documentclass"] == "ctexart"

    def test_xecjk_package(self, tmp_path):
        content = "\\documentclass{article}\n\\usepackage{xeCJK}\n\\begin{document}\nTest\n\\end{document}\n"
        tex = _write_tex(tmp_path, content)
        f = detect_document_features(tex)
        assert f["has_chinese"] is True
        assert f["needs_unicode"] is True
        assert "xeCJK" in f["detected_packages"]

    def test_fontspec_package_unicode(self, tmp_path):
        content = "\\documentclass{article}\n\\usepackage{fontspec}\n\\begin{document}\nTest\n\\end{document}\n"
        tex = _write_tex(tmp_path, content)
        f = detect_document_features(tex)
        assert f["needs_unicode"] is True
        assert f["has_chinese"] is False

    def test_luatexja_package(self, tmp_path):
        content = "\\documentclass{article}\n\\usepackage{luatexja}\n\\begin{document}\nTest\n\\end{document}\n"
        tex = _write_tex(tmp_path, content)
        f = detect_document_features(tex)
        assert f["has_chinese"] is True
        assert f["needs_unicode"] is True
        assert "luatexja" in f["detected_packages"]

    def test_biblatex_default_biber(self, tmp_path):
        content = "\\documentclass{article}\n\\usepackage{biblatex}\n\\begin{document}\nTest\n\\end{document}\n"
        tex = _write_tex(tmp_path, content)
        f = detect_document_features(tex)
        assert f["bib_engine"] == "biber"

    def test_biblatex_with_biber_backend(self, tmp_path):
        content = "\\documentclass{article}\n\\usepackage[backend=biber]{biblatex}\n\\begin{document}\nTest\n\\end{document}\n"
        tex = _write_tex(tmp_path, content)
        f = detect_document_features(tex)
        assert f["bib_engine"] == "biber"

    def test_biblatex_with_bibtex_backend(self, tmp_path):
        content = "\\documentclass{article}\n\\usepackage[backend=bibtex]{biblatex}\n\\begin{document}\nTest\n\\end{document}\n"
        tex = _write_tex(tmp_path, content)
        f = detect_document_features(tex)
        assert f["bib_engine"] == "bibtex"

    def test_bibtex_via_bibliography_command(self, tmp_path):
        content = "\\documentclass{article}\n\\begin{document}\n\\bibliography{refs}\n\\end{document}\n"
        tex = _write_tex(tmp_path, content)
        f = detect_document_features(tex)
        assert f["bib_engine"] == "bibtex"

    def test_imakeidx_xindy(self, tmp_path):
        content = "\\documentclass{article}\n\\usepackage[xindy]{imakeidx}\n\\makeindex\n\\begin{document}\nTest\n\\end{document}\n"
        tex = _write_tex(tmp_path, content)
        f = detect_document_features(tex)
        assert f["index_engine"] == "xindy"

    def test_imakeidx_default_makeindex(self, tmp_path):
        content = (
            "\\documentclass{article}\n\\usepackage{imakeidx}\n\\makeindex\n\\begin{document}\nTest\n\\end{document}\n"
        )
        tex = _write_tex(tmp_path, content)
        f = detect_document_features(tex)
        assert f["index_engine"] == "makeindex"

    def test_makeidx_package(self, tmp_path):
        content = (
            "\\documentclass{article}\n\\usepackage{makeidx}\n\\makeindex\n\\begin{document}\nTest\n\\end{document}\n"
        )
        tex = _write_tex(tmp_path, content)
        f = detect_document_features(tex)
        assert f["index_engine"] == "makeindex"

    def test_makeindex_command_only(self, tmp_path):
        content = "\\documentclass{article}\n\\makeindex\n\\begin{document}\nTest\n\\end{document}\n"
        tex = _write_tex(tmp_path, content)
        f = detect_document_features(tex)
        assert f["index_engine"] == "makeindex"

    def test_glossaries_xindy(self, tmp_path):
        content = (
            "\\documentclass{article}\n\\usepackage[xindy]{glossaries}\n\\begin{document}\nTest\n\\end{document}\n"
        )
        tex = _write_tex(tmp_path, content)
        f = detect_document_features(tex)
        assert f["has_glossaries"] is True
        assert f["index_engine"] == "xindy"

    def test_glossaries_default_makeindex(self, tmp_path):
        content = "\\documentclass{article}\n\\usepackage{glossaries}\n\\begin{document}\nTest\n\\end{document}\n"
        tex = _write_tex(tmp_path, content)
        f = detect_document_features(tex)
        assert f["has_glossaries"] is True
        assert f["index_engine"] == "makeindex"

    def test_nomencl_package(self, tmp_path):
        content = "\\documentclass{article}\n\\usepackage{nomencl}\n\\begin{document}\nTest\n\\end{document}\n"
        tex = _write_tex(tmp_path, content)
        f = detect_document_features(tex)
        assert f["has_nomencl"] is True
        assert f["index_engine"] == "makeindex"

    def test_comment_lines_skipped(self, tmp_path):
        content = "\\documentclass{article}\n% \\usepackage{ctex}\n% \\usepackage[biblatex]{backend=biber}\n% \\usepackage[xindy]{imakeidx}\n\\begin{document}\nHello\n\\end{document}\n"
        tex = _write_tex(tmp_path, content)
        f = detect_document_features(tex)
        assert f["has_chinese"] is False
        assert f["needs_unicode"] is False
        assert f["bib_engine"] is None
        assert f["index_engine"] is None
        assert "ctex" not in f["detected_packages"]

    def test_multiple_packages_in_one_usepackage(self, tmp_path):
        content = "\\documentclass{article}\n\\usepackage{amsmath,amssymb,graphicx}\n\\begin{document}\nTest\n\\end{document}\n"
        tex = _write_tex(tmp_path, content)
        f = detect_document_features(tex)
        assert "amsmath" in f["detected_packages"]
        assert "amssymb" in f["detected_packages"]
        assert "graphicx" in f["detected_packages"]


class TestParseMagicComments:
    def test_parse_program_magic_comment(self, tmp_path):
        content = "% !TEX program = xelatex\n\\documentclass{article}\n"
        tex = _write_tex(tmp_path, content)
        result = parse_magic_comments(tex)
        assert result.get("program") == "xelatex"

    def test_parse_outdir_auxdir(self, tmp_path):
        content = "% !TeX outdir = ./Output/\n% !TEX auxdir = ./Aux/\n\\documentclass{article}\n"
        tex = _write_tex(tmp_path, content)
        result = parse_magic_comments(tex)
        assert result.get("outdir") == "./Output/"
        assert result.get("auxdir") == "./Aux/"

    def test_parse_bib_index_options(self, tmp_path):
        content = "% !TEX bib = biber\n% !TEX index = xindy\n% !TEX options = -shell-escape\n\\documentclass{article}\n"
        tex = _write_tex(tmp_path, content)
        result = parse_magic_comments(tex)
        assert result.get("bib") == "biber"
        assert result.get("index") == "xindy"
        assert result.get("options") == "-shell-escape"

    def test_nonexistent_file_returns_empty(self, tmp_path):
        result = parse_magic_comments(tmp_path / "nonexistent.tex")
        assert result == {}

    def test_no_magic_comments(self, tmp_path):
        content = "\\documentclass{article}\n\\begin{document}\nTest\n\\end{document}\n"
        tex = _write_tex(tmp_path, content)
        result = parse_magic_comments(tex)
        assert result == {}

    def test_magic_comment_without_tex_suffix(self, tmp_path):
        content = "% !TEX program = lualatex\n\\documentclass{article}\n"
        _write_tex(tmp_path, content, name="mydoc")
        stem_path = tmp_path / "mydoc"
        result = parse_magic_comments(stem_path)
        assert result.get("program") == "lualatex"


def _make_mock_manager(available_engines=None):
    mgr = ToolchainManager()
    mgr._detected = True
    available = available_engines or {"xelatex", "lualatex", "pdflatex"}
    for name in mgr.engines:
        mgr.engines[name].available = name in available
    return mgr


def _make_mock_bib_manager(bibtex_available=True, biber_available=True):
    mgr = ToolchainManager()
    mgr._detected = True
    mgr.bib_tools["bibtex"].available = bibtex_available
    mgr.bib_tools["biber"].available = biber_available
    return mgr


def _make_mock_index_manager(makeindex_available=True, xindy_available=True):
    mgr = ToolchainManager()
    mgr._detected = True
    mgr.index_tools["makeindex"].available = makeindex_available
    mgr.index_tools["xindy"].available = xindy_available
    return mgr


class TestSelectEngine:
    def test_cli_takes_highest_priority(self):
        mgr = _make_mock_manager()
        engine, reason = select_engine(
            cli_engine="pdflatex",
            magic_comment_engine="xelatex",
            config_default="lualatex",
            toolchain_manager=mgr,
        )
        assert engine == "pdflatex"
        assert "CLI" in reason

    def test_magic_comment_overrides_config(self):
        mgr = _make_mock_manager()
        engine, reason = select_engine(
            cli_engine=None,
            magic_comment_engine="lualatex",
            config_default="pdflatex",
            toolchain_manager=mgr,
        )
        assert engine == "lualatex"
        assert "魔法注释" in reason

    def test_config_default_used(self):
        mgr = _make_mock_manager()
        engine, reason = select_engine(
            cli_engine=None,
            magic_comment_engine=None,
            config_default="pdflatex",
            toolchain_manager=mgr,
        )
        assert engine == "pdflatex"
        assert "配置文件" in reason

    def test_auto_select_xelatex_for_plain_english(self):
        mgr = _make_mock_manager()
        features = {"needs_unicode": False, "has_chinese": False, "detected_packages": []}
        engine, reason = select_engine(
            cli_engine=None,
            magic_comment_engine=None,
            config_default=None,
            doc_features=features,
            toolchain_manager=mgr,
        )
        assert engine == "xelatex"
        assert "自动选择" in reason

    def test_auto_select_xelatex_for_ctex(self):
        mgr = _make_mock_manager()
        features = {
            "needs_unicode": True,
            "has_chinese": True,
            "detected_packages": ["ctex"],
        }
        engine, reason = select_engine(
            doc_features=features,
            toolchain_manager=mgr,
        )
        assert engine == "xelatex"
        assert "ctex" in reason

    def test_auto_select_lualatex_for_luatexja(self):
        mgr = _make_mock_manager()
        features = {
            "needs_unicode": True,
            "has_chinese": True,
            "detected_packages": ["luatexja"],
        }
        engine, reason = select_engine(
            doc_features=features,
            toolchain_manager=mgr,
        )
        assert engine == "lualatex"
        assert "luatexja" in reason

    def test_auto_select_xelatex_for_fontspec(self):
        mgr = _make_mock_manager()
        features = {
            "needs_unicode": True,
            "has_chinese": False,
            "detected_packages": ["fontspec"],
        }
        engine, reason = select_engine(
            doc_features=features,
            toolchain_manager=mgr,
        )
        assert engine == "xelatex"
        assert "fontspec" in reason

    def test_fallback_when_preferred_unavailable(self):
        mgr = _make_mock_manager(available_engines={"lualatex", "pdflatex"})
        features = {
            "needs_unicode": True,
            "has_chinese": True,
            "detected_packages": ["ctex"],
        }
        engine, reason = select_engine(
            doc_features=features,
            toolchain_manager=mgr,
        )
        assert engine == "lualatex"
        assert "降级" in reason

    def test_default_xelatex_when_no_info(self):
        mgr = _make_mock_manager()
        engine, reason = select_engine(toolchain_manager=mgr)
        assert engine == "xelatex"

    def test_case_insensitive_engine_names(self):
        mgr = _make_mock_manager()
        engine, _ = select_engine(cli_engine="XeLaTeX", toolchain_manager=mgr)
        assert engine == "xelatex"
        engine, _ = select_engine(cli_engine="PDFLATEX", toolchain_manager=mgr)
        assert engine == "pdflatex"

    def test_no_toolchain_manager_no_fallback_check(self):
        engine, reason = select_engine(cli_engine="xelatex", toolchain_manager=None)
        assert engine == "xelatex"


class TestSelectBibTool:
    def test_cli_bib_takes_priority(self):
        mgr = _make_mock_bib_manager()
        tool, reason = select_bib_tool(
            cli_bib="bibtex", magic_bib="biber", doc_features={"bib_engine": "biber"}, toolchain_manager=mgr
        )
        assert tool == "bibtex"
        assert "CLI" in reason

    def test_magic_bib_overrides_features(self):
        mgr = _make_mock_bib_manager()
        tool, reason = select_bib_tool(magic_bib="bibtex", doc_features={"bib_engine": "biber"}, toolchain_manager=mgr)
        assert tool == "bibtex"
        assert "魔法注释" in reason

    def test_auto_detect_biber_from_features(self):
        mgr = _make_mock_bib_manager()
        tool, reason = select_bib_tool(doc_features={"bib_engine": "biber"}, toolchain_manager=mgr)
        assert tool == "biber"
        assert "文档特征" in reason

    def test_auto_detect_bibtex_from_features(self):
        mgr = _make_mock_bib_manager()
        tool, reason = select_bib_tool(doc_features={"bib_engine": "bibtex"}, toolchain_manager=mgr)
        assert tool == "bibtex"

    def test_no_bib_needed_returns_none(self):
        mgr = _make_mock_bib_manager()
        tool, reason = select_bib_tool(doc_features={"bib_engine": None}, toolchain_manager=mgr)
        assert tool is None
        assert "未检测到" in reason

    def test_biber_unavailable_fallback_to_bibtex(self):
        mgr = _make_mock_bib_manager(biber_available=False, bibtex_available=True)
        tool, reason = select_bib_tool(doc_features={"bib_engine": "biber"}, toolchain_manager=mgr)
        assert tool == "bibtex"
        assert "回退" in reason

    def test_no_toolchain_manager(self):
        tool, reason = select_bib_tool(cli_bib="biber", toolchain_manager=None)
        assert tool == "biber"


class TestSelectIndexTool:
    def test_cli_index_takes_priority(self):
        mgr = _make_mock_index_manager()
        tool, reason = select_index_tool(
            cli_index="xindy",
            magic_index="makeindex",
            doc_features={"index_engine": "makeindex"},
            toolchain_manager=mgr,
        )
        assert tool == "xindy"
        assert "CLI" in reason

    def test_magic_index_overrides_features(self):
        mgr = _make_mock_index_manager()
        tool, reason = select_index_tool(
            magic_index="xindy", doc_features={"index_engine": "makeindex"}, toolchain_manager=mgr
        )
        assert tool == "xindy"
        assert "魔法注释" in reason

    def test_auto_detect_xindy(self):
        mgr = _make_mock_index_manager()
        tool, reason = select_index_tool(doc_features={"index_engine": "xindy"}, toolchain_manager=mgr)
        assert tool == "xindy"

    def test_auto_detect_makeindex(self):
        mgr = _make_mock_index_manager()
        tool, reason = select_index_tool(doc_features={"index_engine": "makeindex"}, toolchain_manager=mgr)
        assert tool == "makeindex"

    def test_default_makeindex(self):
        mgr = _make_mock_index_manager()
        tool, reason = select_index_tool(doc_features={"index_engine": None}, toolchain_manager=mgr)
        assert tool == "makeindex"
        assert "默认" in reason

    def test_xindy_unavailable_fallback_to_makeindex(self):
        mgr = _make_mock_index_manager(makeindex_available=True, xindy_available=False)
        tool, reason = select_index_tool(doc_features={"index_engine": "xindy"}, toolchain_manager=mgr)
        assert tool == "makeindex"
        assert "回退" in reason

    def test_no_toolchain_manager(self):
        tool, reason = select_index_tool(cli_index="xindy", toolchain_manager=None)
        assert tool == "xindy"


def _make_all_available_manager(all_available=True):
    mgr = ToolchainManager()
    mgr._detected = True
    for name, eng in mgr.engines.items():
        eng.available = all_available
    for name, tool in mgr.bib_tools.items():
        tool.available = all_available
    for name, tool in mgr.index_tools.items():
        tool.available = all_available
    return mgr


class TestAutoConfigure:
    def test_auto_configure_with_ctex_document(self, tmp_path):
        content = "% !TEX program = xelatex\n\\documentclass{ctexart}\n\\usepackage[backend=biber]{biblatex}\n\\usepackage[xindy]{imakeidx}\n\\makeindex\n\\begin{document}\nHello\n\\printbibliography\n\\printindex\n\\end{document}\n"
        _write_tex(tmp_path, content)
        import os

        old_cwd = os.getcwd()
        os.chdir(tmp_path)
        try:
            mgr = _make_all_available_manager()
            cli_args = {}
            config = {"compiled_program": None, "folder": {"outdir": None, "auxdir": None}}
            result = auto_configure(
                project_name="test",
                cli_args=cli_args,
                config=config,
                toolchain_manager=mgr,
            )
            assert result["engine"] == "xelatex"
            assert result["bib_tool"] == "biber"
            assert result["index_tool"] == "xindy"
            assert result["doc_features"]["has_chinese"] is True
            assert result["doc_features"]["bib_engine"] == "biber"
            assert result["doc_features"]["index_engine"] == "xindy"
        finally:
            os.chdir(old_cwd)

    def test_auto_configure_cli_overrides_magic(self, tmp_path):
        content = "% !TEX program = xelatex\n\\documentclass{article}\n"
        _write_tex(tmp_path, content)
        import os

        old_cwd = os.getcwd()
        os.chdir(tmp_path)
        try:
            mgr = _make_all_available_manager()
            cli_args = {"PdfLaTeX": True}
            config = {}
            result = auto_configure(
                project_name="test",
                cli_args=cli_args,
                config=config,
                toolchain_manager=mgr,
            )
            assert result["engine"] == "pdflatex"
        finally:
            os.chdir(old_cwd)

    def test_auto_configure_returns_expected_keys(self, tmp_path):
        content = "\\documentclass{article}\n\\begin{document}\nTest\n\\end{document}\n"
        _write_tex(tmp_path, content)
        import os

        old_cwd = os.getcwd()
        os.chdir(tmp_path)
        try:
            mgr = _make_all_available_manager()
            result = auto_configure(
                project_name="test",
                cli_args={},
                config={},
                toolchain_manager=mgr,
            )
            expected_keys = {
                "engine",
                "engine_display",
                "bib_tool",
                "index_tool",
                "engine_reason",
                "bib_reason",
                "index_reason",
                "magic_comments",
                "doc_features",
                "outdir",
                "auxdir",
                "extra_options",
            }
            assert set(result.keys()) == expected_keys
            assert result["engine_display"] in ("XeLaTeX", "PdfLaTeX", "LuaLaTeX")
            assert result["outdir"] is not None
            assert result["auxdir"] is not None
        finally:
            os.chdir(old_cwd)

    def test_auto_configure_pre_parsed_magic_comments(self, tmp_path):
        content = "\\documentclass{article}\n"
        _write_tex(tmp_path, content)
        import os

        old_cwd = os.getcwd()
        os.chdir(tmp_path)
        try:
            mgr = _make_all_available_manager()
            pre_parsed = {"program": "lualatex", "bib": "biber", "index": "xindy"}
            result = auto_configure(
                project_name="test",
                cli_args={},
                config={},
                toolchain_manager=mgr,
                magic_comments=pre_parsed,
            )
            assert result["engine"] == "lualatex"
            assert result["bib_tool"] == "biber"
            assert result["index_tool"] == "xindy"
        finally:
            os.chdir(old_cwd)
