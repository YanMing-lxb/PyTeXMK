"""``tex_source`` 的等长屏蔽与注释定位。

这个模块的输出会被直接切片回原文，长度或换行一变，调用方的行列号就全错。
"""
from pytexmk.tex_source import first_comment_index, mask_tex_noncode


def test_mask_keeps_length_and_newlines():
    text = "a % comment\nb\n"
    masked = mask_tex_noncode(text)
    assert len(masked) == len(text)
    assert masked.count("\n") == text.count("\n")


def test_comment_is_blanked_but_escaped_percent_is_kept():
    text = "value 50\\% % note\nnext"
    masked = mask_tex_noncode(text)
    assert "50\\%" in masked
    assert "note" not in masked
    assert masked.endswith("\nnext")


def test_verbatim_environment_is_fully_blanked():
    text = "before\n\\begin{verbatim}\n\\input{evil}\n\\end{verbatim}\nafter"
    masked = mask_tex_noncode(text)
    assert "evil" not in masked
    assert "verbatim" not in masked
    assert "before" in masked and "after" in masked


def test_verb_command_hides_its_content():
    text = "see \\verb|\\input{x}| end"
    masked = mask_tex_noncode(text)
    assert "\\input{x}" not in masked
    assert "end" in masked


def test_unterminated_verbatim_blanks_to_end_of_file():
    text = "\\begin{lstlisting}\ncode \\input{x}"
    masked = mask_tex_noncode(text)
    assert "code" not in masked
    assert len(masked) == len(text)


def test_ordinary_environment_is_not_masked():
    text = "\\begin{document}\n\\input{real}\n\\end{document}"
    assert mask_tex_noncode(text) == text


def test_escaped_backslash_before_percent_is_still_a_comment():
    # `\\` 是换行命令，后面的 `%` 仍是注释开始
    text = "line\\\\% tail"
    masked = mask_tex_noncode(text)
    assert "tail" not in masked


def test_first_comment_index_variants():
    assert first_comment_index("abc%def") == 3
    assert first_comment_index("abc\\%def") == len("abc\\%def")
    assert first_comment_index("no comment") == len("no comment")
    assert first_comment_index("\\\\%x") == 2
