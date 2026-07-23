# -*- coding: utf-8 -*-
"""latexdiff 模块单元测试"""

import sys
from unittest.mock import patch, MagicMock
import subprocess

import pytest

from pytexmk.latexdiff import (
    LaTeXDiffTool,
    LaTeXDiff_Aux,
    parse_diff_args,
    run_diff_from_cli,
    get_version,
)
from pytexmk.exceptions import LaTeXDiffError, CompilationError


def _write_tex(tmp_path, content, name="test"):
    """辅助函数：创建临时 tex 文件"""
    tex_path = tmp_path / (name + ".tex")
    tex_path.write_text(content, encoding="utf-8")
    return tex_path


class TestLaTeXDiffToolInit:
    def test_init_default(self):
        tool = LaTeXDiffTool()
        assert tool.timeout == 300
        assert tool._compiler is None
        assert tool._toolchain_manager is None

    def test_init_with_timeout(self):
        tool = LaTeXDiffTool(timeout=600)
        assert tool.timeout == 600

    def test_init_with_toolchain_manager(self):
        mock_mgr = MagicMock()
        tool = LaTeXDiffTool(toolchain_manager=mock_mgr)
        assert tool._toolchain_manager is mock_mgr


class TestDetectAvailable:
    @patch("shutil.which")
    def test_detect_available_true(self, mock_which):
        mock_which.return_value = "/usr/bin/latexdiff"
        tool = LaTeXDiffTool()
        assert tool.detect_available() is True
        mock_which.assert_called_once_with("latexdiff")

    @patch("shutil.which")
    def test_detect_available_false(self, mock_which):
        mock_which.return_value = None
        tool = LaTeXDiffTool()
        assert tool.detect_available() is False


class TestGenerateDiff:
    @patch.object(LaTeXDiffTool, "detect_available", return_value=False)
    def test_generate_diff_raises_when_unavailable(self, mock_detect, tmp_path):
        tool = LaTeXDiffTool()
        old = _write_tex(tmp_path, "old content", "old")
        new = _write_tex(tmp_path, "new content", "new")
        out = tmp_path / "diff.tex"
        with pytest.raises(LaTeXDiffError, match="未检测到 latexdiff"):
            tool.generate_diff(old, new, out)

    @patch("subprocess.run")
    @patch.object(LaTeXDiffTool, "detect_available", return_value=True)
    def test_generate_diff_basic(self, mock_detect, mock_run, tmp_path):
        old_content = r"\documentclass{article}\begin{document}Old\end{document}"
        new_content = r"\documentclass{article}\begin{document}New\end{document}"
        old = _write_tex(tmp_path, old_content, "old")
        new = _write_tex(tmp_path, new_content, "new")
        out = tmp_path / "diff.tex"

        expected_diff = r"\documentclass{article}\begin{document}\DIFdel{Old}\DIFadd{New}\end{document}"
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = expected_diff
        mock_result.stderr = ""
        mock_run.return_value = mock_result

        tool = LaTeXDiffTool()
        result = tool.generate_diff(old, new, out)

        assert result == out.resolve()
        assert out.exists()
        assert out.read_text(encoding="utf-8") == expected_diff

        cmd = mock_run.call_args[0][0]
        assert "latexdiff" in cmd
        assert "--encoding=utf8" in cmd
        assert "--flatten" not in cmd
        assert "--fast" not in cmd
        assert "--only-changes" not in cmd

    @patch("subprocess.run")
    @patch.object(LaTeXDiffTool, "detect_available", return_value=True)
    def test_generate_diff_with_options(self, mock_detect, mock_run, tmp_path):
        old = _write_tex(tmp_path, "old", "old")
        new = _write_tex(tmp_path, "new", "new")
        out = tmp_path / "diff.tex"

        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "diff content"
        mock_result.stderr = ""
        mock_run.return_value = mock_result

        tool = LaTeXDiffTool()
        tool.generate_diff(
            old,
            new,
            out,
            flatten=True,
            fast=True,
            only_changes=True,
            encoding="latin1",
            extra_args=["--type=UNDERLINE"],
        )

        cmd = mock_run.call_args[0][0]
        assert "--flatten" in cmd
        assert "--fast" in cmd
        assert "--only-changes" in cmd
        assert "--encoding=latin1" in cmd
        assert "--type=UNDERLINE" in cmd

    @patch("subprocess.run")
    @patch.object(LaTeXDiffTool, "detect_available", return_value=True)
    def test_generate_diff_command_failure(self, mock_detect, mock_run, tmp_path):
        old = _write_tex(tmp_path, "old", "old")
        new = _write_tex(tmp_path, "new", "new")
        out = tmp_path / "diff.tex"

        mock_result = MagicMock()
        mock_result.returncode = 1
        mock_result.stdout = ""
        mock_result.stderr = "latexdiff error message"
        mock_run.return_value = mock_result

        tool = LaTeXDiffTool()
        with pytest.raises(LaTeXDiffError, match="latexdiff error message"):
            tool.generate_diff(old, new, out)

    @patch("subprocess.run")
    @patch.object(LaTeXDiffTool, "detect_available", return_value=True)
    def test_generate_diff_timeout(self, mock_detect, mock_run, tmp_path):
        old = _write_tex(tmp_path, "old", "old")
        new = _write_tex(tmp_path, "new", "new")
        out = tmp_path / "diff.tex"

        mock_run.side_effect = subprocess.TimeoutExpired(cmd="latexdiff", timeout=300)

        tool = LaTeXDiffTool()
        with pytest.raises(LaTeXDiffError, match="超时"):
            tool.generate_diff(old, new, out)

    @patch.object(LaTeXDiffTool, "detect_available", return_value=True)
    def test_generate_diff_old_file_not_found(self, mock_detect, tmp_path):
        new = _write_tex(tmp_path, "new", "new")
        out = tmp_path / "diff.tex"
        old_missing = tmp_path / "nonexistent.tex"

        tool = LaTeXDiffTool()
        with pytest.raises(FileNotFoundError):
            tool.generate_diff(old_missing, new, out)

    @patch.object(LaTeXDiffTool, "detect_available", return_value=True)
    def test_generate_diff_new_file_not_found(self, mock_detect, tmp_path):
        old = _write_tex(tmp_path, "old", "old")
        out = tmp_path / "diff.tex"
        new_missing = tmp_path / "nonexistent.tex"

        tool = LaTeXDiffTool()
        with pytest.raises(FileNotFoundError):
            tool.generate_diff(old, new_missing, out)

    @patch("subprocess.run")
    @patch.object(LaTeXDiffTool, "detect_available", return_value=True)
    def test_generate_diff_adds_tex_suffix(self, mock_detect, mock_run, tmp_path):
        old = _write_tex(tmp_path, "old", "old")
        new = _write_tex(tmp_path, "new", "new")
        out_no_suffix = tmp_path / "diff"

        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "content"
        mock_result.stderr = ""
        mock_run.return_value = mock_result

        tool = LaTeXDiffTool()
        result = tool.generate_diff(
            str(old.with_suffix("")),
            str(new.with_suffix("")),
            str(out_no_suffix),
        )

        assert result.suffix == ".tex"
        cmd = mock_run.call_args[0][0]
        assert str(old) in cmd
        assert str(new) in cmd


class TestFlattenTex:
    def test_flatten_tex_basic(self, tmp_path):
        sub_content = "This is content from sub file.\n"
        _write_tex(tmp_path, sub_content, "sub")

        main_content = (
            r"\documentclass{article}"
            "\n\\begin{document}\n"
            r"\input{sub}"
            "\n\\end{document}\n"
        )
        main = _write_tex(tmp_path, main_content, "main")
        out = tmp_path / "flattened.tex"

        tool = LaTeXDiffTool()
        result = tool.flatten_tex(main, out)

        assert result == out.resolve()
        flattened = out.read_text(encoding="utf-8")
        assert "This is content from sub file." in flattened
        assert r"\documentclass{article}" in flattened
        assert r"\end{document}" in flattened

    def test_flatten_tex_include(self, tmp_path):
        chap_content = "Chapter content here.\n"
        _write_tex(tmp_path, chap_content, "chap1")

        main_content = (
            r"\documentclass{article}"
            "\n\\begin{document}\n"
            r"\include{chap1}"
            "\n\\end{document}\n"
        )
        main = _write_tex(tmp_path, main_content, "main")
        out = tmp_path / "flattened.tex"

        tool = LaTeXDiffTool()
        tool.flatten_tex(main, out)

        flattened = out.read_text(encoding="utf-8")
        assert "Chapter content here." in flattened

    def test_flatten_tex_nested_input(self, tmp_path):
        subsub_content = "Deepest content.\n"
        _write_tex(tmp_path, subsub_content, "subsub")

        sub_content = "Sub file starts.\n\\input{subsub}\nSub file ends.\n"
        _write_tex(tmp_path, sub_content, "sub")

        main_content = (
            r"\documentclass{article}"
            "\n\\begin{document}\n"
            r"\input{sub}"
            "\n\\end{document}\n"
        )
        main = _write_tex(tmp_path, main_content, "main")
        out = tmp_path / "flattened.tex"

        tool = LaTeXDiffTool()
        tool.flatten_tex(main, out)

        flattened = out.read_text(encoding="utf-8")
        assert "Deepest content." in flattened
        assert "Sub file starts." in flattened
        assert "Sub file ends." in flattened

    def test_flatten_tex_commented_input_not_expanded(self, tmp_path):
        sub_content = "SHOULD NOT APPEAR\n"
        _write_tex(tmp_path, sub_content, "secret")

        main_content = (
            r"\documentclass{article}"
            "\n\\begin{document}\n"
            r"% \input{secret}"
            "\nVisible content.\n"
            r"\end{document}"
            "\n"
        )
        main = _write_tex(tmp_path, main_content, "main")
        out = tmp_path / "flattened.tex"

        tool = LaTeXDiffTool()
        tool.flatten_tex(main, out)

        flattened = out.read_text(encoding="utf-8")
        assert "SHOULD NOT APPEAR" not in flattened
        assert "Visible content." in flattened
        assert r"% \input{secret}" in flattened

    def test_flatten_tex_inline_comment_after_input(self, tmp_path):
        sub_content = "This is included content.\n"
        _write_tex(tmp_path, sub_content, "chap")

        main_content = (
            r"\documentclass{article}"
            "\n\\begin{document}\n"
            r"\input{chap} % this is a comment after input"
            "\n\\end{document}\n"
        )
        main = _write_tex(tmp_path, main_content, "main")
        out = tmp_path / "flattened.tex"

        tool = LaTeXDiffTool()
        tool.flatten_tex(main, out)

        flattened = out.read_text(encoding="utf-8")
        assert "This is included content." in flattened

    def test_flatten_tex_file_not_found(self, tmp_path):
        main = tmp_path / "nonexistent.tex"
        out = tmp_path / "out.tex"

        tool = LaTeXDiffTool()
        with pytest.raises(CompilationError, match="不存在"):
            tool.flatten_tex(main, out)

    def test_flatten_tex_missing_subfile(self, tmp_path):
        main_content = (
            r"\documentclass{article}"
            "\n\\begin{document}\n"
            r"\input{missing_subfile}"
            "\n\\end{document}\n"
        )
        main = _write_tex(tmp_path, main_content, "main")
        out = tmp_path / "flattened.tex"

        tool = LaTeXDiffTool()
        with pytest.raises(CompilationError, match="不存在"):
            tool.flatten_tex(main, out)

    def test_flatten_tex_restores_stdout_on_exception(self, tmp_path):
        original_stdout = sys.stdout
        main_content = (
            r"\documentclass{article}"
            "\n\\begin{document}\n"
            r"\input{does_not_exist}"
            "\n\\end{document}\n"
        )
        main = _write_tex(tmp_path, main_content, "main")
        out = tmp_path / "out.tex"

        tool = LaTeXDiffTool()
        try:
            tool.flatten_tex(main, out)
        except CompilationError:
            pass

        assert sys.stdout is original_stdout

    def test_flatten_tex_adds_tex_suffix(self, tmp_path):
        sub_content = "Sub content\n"
        _write_tex(tmp_path, sub_content, "sub")

        main_content = r"\documentclass{article}\begin{document}\input{sub}\end{document}"
        main = _write_tex(tmp_path, main_content, "main")
        out_no_suffix = tmp_path / "flattened"

        tool = LaTeXDiffTool()
        result = tool.flatten_tex(
            str(main.with_suffix("")),
            str(out_no_suffix),
        )

        assert result.suffix == ".tex"
        flattened = result.read_text(encoding="utf-8")
        assert "Sub content" in flattened

    def test_flatten_tex_circular_reference_detection(self, tmp_path):
        a_content = r"\documentclass{article}\begin{document}\input{b}\end{document}"
        b_content = r"\input{a}"
        _write_tex(tmp_path, a_content, "a")
        _write_tex(tmp_path, b_content, "b")
        out = tmp_path / "flattened.tex"

        tool = LaTeXDiffTool()
        result = tool.flatten_tex(tmp_path / "a.tex", out)

        assert result.exists()


class TestParseDiffArgs:
    def test_parse_diff_args_default(self):
        args = {}
        config = parse_diff_args(args)
        assert config["enabled"] is False
        assert config["old_file"] is None
        assert config["new_file"] is None
        assert config["flatten"] is False
        assert config["fast"] is False
        assert config["output"] is None
        assert config["engine"] is None
        assert config["do_compile"] is True

    def test_parse_diff_args_all_options(self):
        args = {
            "diff": True,
            "diff_old": "old.tex",
            "diff_new": "new.tex",
            "diff_flatten": True,
            "diff_fast": True,
            "diff_output": "mydiff.tex",
            "diff_engine": "lualatex",
        }
        config = parse_diff_args(args)
        assert config["enabled"] is True
        assert config["old_file"] == "old.tex"
        assert config["new_file"] == "new.tex"
        assert config["flatten"] is True
        assert config["fast"] is True
        assert config["output"] == "mydiff.tex"
        assert config["engine"] == "lualatex"


class TestRunDiffFromCli:
    def test_run_diff_disabled(self):
        assert run_diff_from_cli({}) is False

    @patch.object(LaTeXDiffTool, "detect_available", return_value=False)
    def test_run_diff_latexdiff_not_available(self, mock_detect, capsys):
        args = {"diff": True, "diff_old": "a.tex", "diff_new": "b.tex"}
        assert run_diff_from_cli(args) is False

    def test_run_diff_missing_old_new_args(self, capsys):
        args = {"diff": True}
        assert run_diff_from_cli(args) is False
        captured = capsys.readouterr()
        assert "--diff-old" in captured.out or "--diff-old" in captured.err


class TestLaTeXDiff_AuxBackwardCompat:
    def test_aux_class_inherits_from_tool(self):
        assert issubclass(LaTeXDiff_Aux, LaTeXDiffTool)

    def test_init_creates_expected_attrs(self, tmp_path):
        suffixes = [".aux", ".log", ".out"]
        auxdir = tmp_path / "aux"
        auxdir.mkdir()
        with pytest.warns(DeprecationWarning, match="LaTeXDiff_Aux 类已弃用"):
            aux = LaTeXDiff_Aux(suffixes, str(auxdir))
        assert aux.suffixes_aux == suffixes
        assert aux.auxdir == auxdir

    def test_check_aux_files_true(self, tmp_path):
        auxdir = tmp_path / "aux"
        auxdir.mkdir()
        (auxdir / "test.aux").write_text("", encoding="utf-8")
        with pytest.warns(DeprecationWarning):
            aux = LaTeXDiff_Aux([".aux", ".log"], str(auxdir))
        assert aux.check_aux_files("test") is True

    def test_check_aux_files_false(self, tmp_path):
        auxdir = tmp_path / "aux"
        auxdir.mkdir()
        with pytest.warns(DeprecationWarning):
            aux = LaTeXDiff_Aux([".aux", ".log"], str(auxdir))
        assert aux.check_aux_files("nonexistent") is False

    def test_aux_files_both_exist_true(self, tmp_path):
        import os

        old_cwd = os.getcwd()
        os.chdir(tmp_path)
        try:
            (tmp_path / "a.bbl").write_text("", encoding="utf-8")
            (tmp_path / "b.bbl").write_text("", encoding="utf-8")
            with pytest.warns(DeprecationWarning):
                aux = LaTeXDiff_Aux([".aux"], str(tmp_path))
            result = aux.aux_files_both_exist("a", "b", ".bbl")
            assert result == ".bbl"
        finally:
            os.chdir(old_cwd)

    def test_aux_files_both_exist_false(self, tmp_path):
        import os

        old_cwd = os.getcwd()
        os.chdir(tmp_path)
        try:
            (tmp_path / "a.bbl").write_text("", encoding="utf-8")
            with pytest.warns(DeprecationWarning):
                aux = LaTeXDiff_Aux([".aux"], str(tmp_path))
            result = aux.aux_files_both_exist("a", "b", ".bbl")
            assert result is None
        finally:
            os.chdir(old_cwd)

    @patch.object(LaTeXDiffTool, "generate_diff")
    def test_compile_LaTeXDiff_calls_generate_diff(self, mock_generate, tmp_path):
        import os

        old_cwd = os.getcwd()
        os.chdir(tmp_path)
        try:
            _write_tex(tmp_path, "old", "old")
            _write_tex(tmp_path, "new", "new")
            with pytest.warns(DeprecationWarning):
                aux = LaTeXDiff_Aux([".aux"], str(tmp_path))
            with pytest.warns(DeprecationWarning, match="compile_LaTeXDiff 方法已弃用"):
                aux.compile_LaTeXDiff("old", "new", "diff", ".tex")
            mock_generate.assert_called_once()
            call_kwargs = mock_generate.call_args[1]
            assert call_kwargs["encoding"] == "utf8"
        finally:
            os.chdir(old_cwd)

    @patch.object(LaTeXDiffTool, "flatten_tex")
    def test_flatten_Latex_calls_flatten_tex(self, mock_flatten, tmp_path):
        import os

        old_cwd = os.getcwd()
        os.chdir(tmp_path)
        try:
            _write_tex(tmp_path, "main content", "main")
            with pytest.warns(DeprecationWarning):
                aux = LaTeXDiff_Aux([".aux"], str(tmp_path))
            with pytest.warns(DeprecationWarning, match="flatten_Latex 方法已弃用"):
                result = aux.flatten_Latex("main")
            assert result == "main-flatten"
            mock_flatten.assert_called_once()
        finally:
            os.chdir(old_cwd)


class TestGetVersion:
    @patch("shutil.which", return_value=None)
    def test_get_version_git_not_available(self, mock_which, tmp_path):
        assert get_version(str(tmp_path / "test.tex")) is None

    @patch("subprocess.run")
    @patch("shutil.which", return_value="/usr/bin/git")
    def test_get_version_success(self, mock_which, mock_run, tmp_path):
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "abc1234\n"
        mock_run.return_value = mock_result
        result = get_version(str(tmp_path / "test.tex"))
        assert result == "abc1234"

    @patch("subprocess.run")
    @patch("shutil.which", return_value="/usr/bin/git")
    def test_get_version_failure(self, mock_which, mock_run, tmp_path):
        mock_result = MagicMock()
        mock_result.returncode = 128
        mock_run.return_value = mock_result
        assert get_version(str(tmp_path / "test.tex")) is None
