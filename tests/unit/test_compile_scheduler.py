# -*- coding: utf-8 -*-
"""
Unit tests for CompileLaTeX scheduler with fixed passes and smart recompilation
"""

from unittest.mock import MagicMock, patch

from pytexmk.compile import CompileLaTeX
from pytexmk.exceptions import CompilationError, CompilationTimeoutError


class TestCompileLaTeXInit:
    """Tests for CompileLaTeX initialization with new API"""

    @patch("pytexmk.compile.ToolchainManager")
    @patch("pytexmk.compile.MySubProcess")
    @patch("pytexmk.compile.MoveRemoveOperation")
    @patch("pytexmk.compile.MainFileOperation")
    def test_init_new_style_keywords(self, _MockMFO, _MockMRO, _MockMSP, MockTC):
        """Test initialization with new-style keyword arguments"""
        mock_tc = MockTC.return_value
        mock_engine = MagicMock()
        mock_engine.name = "xelatex"
        mock_tc.get_engine.return_value = mock_engine

        cl = CompileLaTeX(
            program="xelatex",
            run_count=3,
            outdir="output",
            auxdir="auxiliary",
            timeout=600,
        )

        assert cl.program == "xelatex"
        assert cl.run_count == 3
        assert cl.runs == 3
        assert cl.outdir == "output"
        assert cl.auxdir == "auxiliary"
        assert cl.timeout == 600
        assert cl.compiled_program == "xelatex"
        assert cl.max_extra_passes == 2
        assert cl._compat_mode is False
        mock_tc.detect_all.assert_called_once()

    @patch("pytexmk.compile.ToolchainManager")
    @patch("pytexmk.compile.MySubProcess")
    @patch("pytexmk.compile.MoveRemoveOperation")
    @patch("pytexmk.compile.MainFileOperation")
    def test_init_compat_mode_old_style(self, _MockMFO, _MockMRO, _MockMSP, MockTC):
        """Test backward compat: old positional args (project_name, program, ...)"""
        mock_tc = MockTC.return_value
        mock_engine = MagicMock()
        mock_engine.name = "xelatex"
        mock_tc.get_engine.return_value = mock_engine

        cl = CompileLaTeX(
            "myproject",
            "xelatex",
            ["myproject.pdf"],
            ["myproject.aux", "myproject.log"],
            "outdir",
            "auxdir",
            False,
        )

        assert cl._compat_mode is True
        assert cl.project_name == "myproject"
        assert cl.compiled_program == "xelatex"
        assert "myproject.pdf" in cl.out_files
        assert "myproject.aux" in cl.aux_files
        assert cl.outdir == "outdir"
        assert cl.auxdir == "auxdir"


class TestCompileLaTeXScheduling:
    """Tests for compilation scheduling with fixed passes and smart extra passes"""

    def _make_compiler(self, run_count=2, program="xelatex"):
        """Helper to create a CompileLaTeX with mocked dependencies"""
        with (
            patch("pytexmk.compile.ToolchainManager") as MockTC,
            patch("pytexmk.compile.MySubProcess") as MockMSP,
            patch("pytexmk.compile.MoveRemoveOperation"),
            patch("pytexmk.compile.MainFileOperation"),
            patch("pytexmk.compile.LogAnalysis") as MockLA,
        ):
            mock_tc = MockTC.return_value
            mock_engine = MagicMock()
            mock_engine.name = program
            mock_engine.build_command.return_value = [program, "-interaction=nonstopmode", "main.tex"]
            mock_tc.get_engine.return_value = mock_engine

            mock_bib = MagicMock()
            mock_bib.name = "bibtex"
            mock_bib.build_command.return_value = ["bibtex", "main"]
            mock_tc.get_bib_tool.return_value = mock_bib

            mock_index = MagicMock()
            mock_index.name = "makeindex"
            mock_index.build_command.return_value = ["makeindex", "main.idx"]
            mock_tc.get_index_tool.return_value = mock_index

            mock_dvipdfmx = MagicMock()
            mock_dvipdfmx.available = False
            mock_dvipdfmx.build_command.return_value = ["dvipdfmx", "main.xdv"]
            mock_tc.dvipdfmx = mock_dvipdfmx

            mock_msp = MockMSP.return_value
            mock_msp.run_command.return_value = (True, "This is XeTeX, Version 3.14...")

            cl = CompileLaTeX(program=program, run_count=run_count, auto_detect=False)
            cl.project_name = "main"
            cl.bib_tool = mock_bib
            cl.index_tool_instance = mock_index
            cl.dvipdfmx_tool = mock_dvipdfmx

            return cl, mock_msp, mock_engine, mock_bib, MockLA

    def _make_path_mock(self, existing_files=None):
        """Create a Path mock that returns exists()=True only for specified files"""
        if existing_files is None:
            existing_files = {"main.tex"}

        def path_side_effect(path_str):
            mock_path = MagicMock()
            mock_path.__str__ = MagicMock(return_value=str(path_str))
            file_name = str(path_str)
            mock_path.exists.return_value = file_name in existing_files
            return mock_path

        return path_side_effect

    def test_fixed_2_passes_normal_flow_xelatex(self):
        """Test: fixed 2-pass compilation with XeLaTeX, all success
        - First pass: no_pdf=True
        - Second pass: no_pdf=False
        """
        cl, mock_msp, mock_engine, _, _ = self._make_compiler(run_count=2, program="xelatex")

        with (
            patch("pytexmk.compile.Path", side_effect=self._make_path_mock({"main.tex"})),
            patch.object(cl, "_check_exist", return_value=True),
            patch.object(cl, "_analyze_logs") as mock_analyze,
            patch.object(cl, "_analyze_logs_update_state"),
            patch.object(cl, "_view_log_current"),
            patch.object(cl, "_move_files"),
            patch.object(cl, "_finalize"),
        ):
            mock_log = MagicMock()
            mock_log.has_fatal_errors.return_value = False
            mock_log.needs_recompile_bib.return_value = False
            mock_log.needs_recompile_index.return_value = False
            mock_log.needs_extra_pass.return_value = False
            mock_analyze.return_value = mock_log

            cl._compile_tex_full()

            assert mock_msp.run_command.call_count == 2

            call_args_list = mock_engine.build_command.call_args_list
            assert len(call_args_list) == 2
            assert call_args_list[0][1].get("no_pdf") is True
            assert call_args_list[1][1].get("no_pdf") is False

    def test_fixed_3_passes_with_bib(self):
        """Test: fixed 3-pass compilation: tex -> bib -> tex -> tex"""
        cl, mock_msp, mock_engine, mock_bib, _ = self._make_compiler(run_count=3, program="xelatex")
        cl.bib_tool = mock_bib

        analyze_call = [0]

        def mock_analyze():
            analyze_call[0] += 1
            mock_log = MagicMock()
            mock_log.has_fatal_errors.return_value = False
            if analyze_call[0] == 1:
                mock_log.needs_recompile_bib.return_value = True
                mock_log.needs_recompile_index.return_value = False
                mock_log.needs_extra_pass.return_value = False
                cl.bib_needed = True
            else:
                mock_log.needs_recompile_bib.return_value = False
                mock_log.needs_recompile_index.return_value = False
                mock_log.needs_extra_pass.return_value = False
                cl.bib_needed = False
            return mock_log

        with (
            patch("pytexmk.compile.Path", side_effect=self._make_path_mock({"main.tex"})),
            patch.object(cl, "_check_exist", return_value=True),
            patch.object(cl, "_analyze_logs", side_effect=mock_analyze),
            patch.object(cl, "_analyze_logs_update_state"),
            patch.object(cl, "_view_log_current"),
            patch.object(cl, "_move_files"),
            patch.object(cl, "_finalize"),
        ):
            cl._compile_tex_full()

            tex_calls = 0
            bib_calls = 0
            for c in mock_msp.run_command.call_args_list:
                cmd = c[0][0]
                if "xelatex" in str(cmd[0]):
                    tex_calls += 1
                if "bibtex" in str(cmd[0]):
                    bib_calls += 1

            assert tex_calls == 3
            assert bib_calls == 1

    def test_first_compile_failure_stops_flow(self):
        """Test: if first tex compilation fails, stop and return False"""
        cl, mock_msp, mock_engine, _, _ = self._make_compiler(run_count=2, program="xelatex")
        mock_msp.run_command.side_effect = CompilationError(message="Fatal error!", returncode=1)

        with (
            patch("pytexmk.compile.Path", side_effect=self._make_path_mock({"main.tex"})),
            patch.object(cl, "_check_exist", return_value=True),
            patch.object(cl, "_analyze_logs_update_state"),
            patch.object(cl, "_view_log_current"),
            patch.object(cl, "_error_callback"),
            patch.object(cl, "_move_files"),
            patch.object(cl, "_finalize"),
        ):
            cl._compile_tex_full()

            assert mock_msp.run_command.call_count == 1

    def test_smart_extra_pass_for_undefined_citation(self):
        """Test: after fixed passes, if undefined citations -> bib + tex extra pass"""
        cl, mock_msp, mock_engine, mock_bib, _ = self._make_compiler(run_count=2, program="xelatex")
        cl.bib_tool = mock_bib

        analyze_call = [0]

        def mock_analyze():
            analyze_call[0] += 1
            mock_log = MagicMock()
            mock_log.has_fatal_errors.return_value = False
            if analyze_call[0] <= 2:
                mock_log.needs_recompile_bib.return_value = True
                mock_log.needs_recompile_index.return_value = False
                mock_log.needs_extra_pass.return_value = False
            else:
                mock_log.needs_recompile_bib.return_value = False
                mock_log.needs_recompile_index.return_value = False
                mock_log.needs_extra_pass.return_value = False
            return mock_log

        with (
            patch("pytexmk.compile.Path", side_effect=self._make_path_mock({"main.tex"})),
            patch.object(cl, "_check_exist", return_value=True),
            patch.object(cl, "_analyze_logs", side_effect=mock_analyze),
            patch.object(cl, "_analyze_logs_update_state"),
            patch.object(cl, "_view_log_current"),
            patch.object(cl, "_move_files"),
            patch.object(cl, "_finalize"),
        ):
            cl._compile_tex_full()

            tex_calls = 0
            bib_calls = 0
            for c in mock_msp.run_command.call_args_list:
                cmd = c[0][0]
                if "xelatex" in str(cmd[0]):
                    tex_calls += 1
                if "bibtex" in str(cmd[0]):
                    bib_calls += 1

            assert tex_calls >= 3
            assert bib_calls >= 1

    def test_smart_extra_pass_for_undefined_reference(self):
        """Test: after fixed passes, if undefined references -> extra tex pass"""
        cl, mock_msp, mock_engine, _, _ = self._make_compiler(run_count=2, program="xelatex")

        analyze_call = [0]

        def mock_analyze():
            analyze_call[0] += 1
            mock_log = MagicMock()
            mock_log.has_fatal_errors.return_value = False
            if analyze_call[0] <= 2:
                mock_log.needs_recompile_bib.return_value = False
                mock_log.needs_recompile_index.return_value = False
                mock_log.needs_extra_pass.return_value = True
            else:
                mock_log.needs_recompile_bib.return_value = False
                mock_log.needs_recompile_index.return_value = False
                mock_log.needs_extra_pass.return_value = False
            return mock_log

        with (
            patch("pytexmk.compile.Path", side_effect=self._make_path_mock({"main.tex"})),
            patch.object(cl, "_check_exist", return_value=True),
            patch.object(cl, "_analyze_logs", side_effect=mock_analyze),
            patch.object(cl, "_analyze_logs_update_state"),
            patch.object(cl, "_view_log_current"),
            patch.object(cl, "_move_files"),
            patch.object(cl, "_finalize"),
        ):
            cl._compile_tex_full()

            tex_calls = sum(1 for c in mock_msp.run_command.call_args_list if "xelatex" in str(c[0][0]))
            assert tex_calls >= 3

    def test_max_extra_passes_enforced(self):
        """Test: extra passes do not exceed max_extra_passes (2)"""
        cl, mock_msp, mock_engine, _, _ = self._make_compiler(run_count=2, program="xelatex")

        def mock_analyze():
            mock_log = MagicMock()
            mock_log.has_fatal_errors.return_value = False
            mock_log.needs_recompile_bib.return_value = False
            mock_log.needs_recompile_index.return_value = False
            mock_log.needs_extra_pass.return_value = True
            return mock_log

        with (
            patch("pytexmk.compile.Path", side_effect=self._make_path_mock({"main.tex"})),
            patch.object(cl, "_check_exist", return_value=True),
            patch.object(cl, "_analyze_logs", side_effect=mock_analyze),
            patch.object(cl, "_analyze_logs_update_state"),
            patch.object(cl, "_view_log_current"),
            patch.object(cl, "_move_files"),
            patch.object(cl, "_finalize"),
        ):
            cl._compile_tex_full()

            tex_calls = sum(1 for c in mock_msp.run_command.call_args_list if "xelatex" in str(c[0][0]))
            assert tex_calls <= 2 + cl.max_extra_passes
            assert tex_calls == 4

    def test_fatal_error_stops_extra_passes(self):
        """Test: fatal errors prevent extra passes"""
        cl, mock_msp, mock_engine, _, _ = self._make_compiler(run_count=2, program="xelatex")

        analyze_call = [0]

        def mock_analyze():
            analyze_call[0] += 1
            mock_log = MagicMock()
            if analyze_call[0] <= 1:
                mock_log.has_fatal_errors.return_value = False
                mock_log.needs_recompile_bib.return_value = False
                mock_log.needs_recompile_index.return_value = False
                mock_log.needs_extra_pass.return_value = False
            else:
                mock_log.has_fatal_errors.return_value = True
                mock_log.needs_recompile_bib.return_value = True
                mock_log.needs_recompile_index.return_value = True
                mock_log.needs_extra_pass.return_value = True
            return mock_log

        with (
            patch("pytexmk.compile.Path", side_effect=self._make_path_mock({"main.tex"})),
            patch.object(cl, "_check_exist", return_value=True),
            patch.object(cl, "_analyze_logs", side_effect=mock_analyze),
            patch.object(cl, "_analyze_logs_update_state"),
            patch.object(cl, "_view_log_current"),
            patch.object(cl, "_move_files"),
            patch.object(cl, "_finalize"),
        ):
            cl._compile_tex_full()

            tex_calls = sum(1 for c in mock_msp.run_command.call_args_list if "xelatex" in str(c[0][0]))
            assert tex_calls == 2

    def test_pdflatex_no_no_pdf_param(self):
        """Test: PdfLaTeX does NOT receive no_pdf parameter"""
        cl, mock_msp, mock_engine, _, _ = self._make_compiler(run_count=2, program="pdflatex")

        with (
            patch("pytexmk.compile.Path", side_effect=self._make_path_mock({"main.tex"})),
            patch.object(cl, "_check_exist", return_value=True),
            patch.object(cl, "_analyze_logs") as mock_analyze,
            patch.object(cl, "_analyze_logs_update_state"),
            patch.object(cl, "_view_log_current"),
            patch.object(cl, "_move_files"),
            patch.object(cl, "_finalize"),
        ):
            mock_log = MagicMock()
            mock_log.has_fatal_errors.return_value = False
            mock_log.needs_recompile_bib.return_value = False
            mock_log.needs_recompile_index.return_value = False
            mock_log.needs_extra_pass.return_value = False
            mock_analyze.return_value = mock_log

            cl._compile_tex_full()

            for c in mock_engine.build_command.call_args_list:
                assert "no_pdf" not in c[1] or c[1].get("no_pdf") is None

    def test_timeout_error_handling(self):
        """Test: CompilationTimeoutError is caught and handled"""
        cl, mock_msp, mock_engine, _, _ = self._make_compiler(run_count=2, program="xelatex")
        mock_msp.run_command.side_effect = CompilationTimeoutError(timeout=300)

        with (
            patch("pytexmk.compile.Path", side_effect=self._make_path_mock({"main.tex"})),
            patch.object(cl, "_check_exist", return_value=True),
            patch.object(cl, "_analyze_logs_update_state"),
            patch.object(cl, "_view_log_current"),
            patch.object(cl, "_error_callback"),
            patch.object(cl, "_move_files"),
            patch.object(cl, "_finalize"),
        ):
            cl._compile_tex_full()

            assert mock_msp.run_command.call_count == 1

    def test_compat_mode_compile_tex_single(self):
        """Test: _compat_mode uses old single-compile path"""
        with (
            patch("pytexmk.compile.ToolchainManager") as MockTC,
            patch("pytexmk.compile.MySubProcess") as MockMSP,
            patch("pytexmk.compile.MoveRemoveOperation"),
            patch("pytexmk.compile.MainFileOperation"),
        ):
            mock_tc = MockTC.return_value
            mock_engine = MagicMock()
            mock_engine.name = "xelatex"
            mock_engine.build_command.return_value = ["xelatex", "main.tex"]
            mock_tc.get_engine.return_value = mock_engine
            mock_msp = MockMSP.return_value
            mock_msp.run_command.return_value = (True, "output")

            cl = CompileLaTeX("main", "xelatex")
            assert cl._compat_mode is True

            cl.compile_tex()
            mock_msp.run_command.assert_called_once()

    def test_move_files_called_on_completion(self):
        """Test: _move_files method exists and can be called externally (file moving is handled by caller now)"""
        cl, mock_msp, mock_engine, _, _ = self._make_compiler(run_count=2, program="xelatex")

        with (
            patch("pytexmk.compile.Path", side_effect=self._make_path_mock({"main.tex"})),
            patch.object(cl, "_check_exist", return_value=True),
            patch.object(cl, "_analyze_logs") as mock_analyze,
            patch.object(cl, "_analyze_logs_update_state"),
            patch.object(cl, "_view_log_current"),
            patch.object(cl, "_move_files") as mock_move,
            patch.object(cl, "_finalize"),
        ):
            mock_log = MagicMock()
            mock_log.has_fatal_errors.return_value = False
            mock_log.needs_recompile_bib.return_value = False
            mock_log.needs_recompile_index.return_value = False
            mock_log.needs_extra_pass.return_value = False
            mock_analyze.return_value = mock_log

            cl._compile_tex_full()
            mock_move.assert_not_called()
            cl._move_files()
            mock_move.assert_called_once()


class TestCompileLaTeXBackwardCompat:
    """Tests for backward-compatible methods"""

    def _make_simple_compiler(self):
        with (
            patch("pytexmk.compile.ToolchainManager") as MockTC,
            patch("pytexmk.compile.MySubProcess") as MockMSP,
            patch("pytexmk.compile.MoveRemoveOperation"),
            patch("pytexmk.compile.MainFileOperation"),
        ):
            mock_tc = MockTC.return_value
            mock_engine = MagicMock()
            mock_engine.name = "xelatex"
            mock_tc.get_engine.return_value = mock_engine
            mock_msp = MockMSP.return_value
            mock_msp.run_command.return_value = (True, "ok")

            cl = CompileLaTeX(program="xelatex", run_count=2)
            cl.project_name = "main"
            return cl, mock_msp, mock_tc

    def test_compile_bib_backward_compat(self):
        """Test: compile_bib(bib_engine) still works"""
        cl, mock_msp, mock_tc = self._make_simple_compiler()
        mock_bib = MagicMock()
        mock_bib.name = "bibtex"
        mock_bib.build_command.return_value = ["bibtex", "main"]
        mock_tc.get_bib_tool.return_value = mock_bib

        cl.compile_bib("bibtex")
        mock_msp.run_command.assert_called_once()

    def test_compile_xdv_backward_compat(self):
        """Test: compile_xdv() still works"""
        cl, mock_msp, mock_tc = self._make_simple_compiler()
        mock_dvipdfmx = MagicMock()
        mock_dvipdfmx.build_command.return_value = ["dvipdfmx", "main.xdv"]
        mock_tc.dvipdfmx = mock_dvipdfmx

        cl.compile_xdv()
        mock_msp.run_command.assert_called_once()

    def test_compile_index_backward_compat(self):
        """Test: compile_index(cmd) with shlex-split command still works"""
        cl, mock_msp, _ = self._make_simple_compiler()

        cl.compile_index(["makeidx", "makeindex main.idx"])
        mock_msp.run_command.assert_called_once()

    def test_set_methods_exist(self):
        """Test: setters exist and update attributes"""
        cl, _, _ = self._make_simple_compiler()

        cl.set_outdir("my_out")
        cl.set_auxdir("my_aux")
        cl.set_non_quiet(True)
        cl.set_run_count(4)
        cl.set_timeout(120)

        assert cl.outdir == "my_out"
        assert cl.auxdir == "my_aux"
        assert cl.non_quiet is True
        assert cl.run_count == 4
        assert cl.runs == 4
        assert cl.timeout == 120
