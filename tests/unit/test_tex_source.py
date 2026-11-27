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


def test_iffalse_block_is_treated_as_body():
    """``\\iffalse`` 不做特殊识别：条件块配对极易算错，漏屏蔽会静默放过整篇正文。

    块内字符按正文统计（宁可多报），因此 ``\\input`` 与字符都保留在屏蔽结果里。
    """
    text = "before\n\\iffalse\n\\input{evil} 中文\n\\fi\nafter"
    assert mask_tex_noncode(text) == text


def test_ifthenelse_does_not_swallow_following_text():
    """宏式条件（``\\ifthenelse{}``）不需要 ``\\fi``，不能让它吞掉后续正文。"""
    text = "\\iffalse\n\\ifthenelse{1>0}{yes}{no}\n\\fi\nBody α\n"
    masked = mask_tex_noncode(text)
    assert "Body" in masked and "α" in masked


def test_comment_inside_iffalse_does_not_swallow_text():
    """``\\iffalse`` 块的注释里出现 ``\\if…`` 时，后续正文也不能被屏蔽。"""
    text = "\\iffalse\n% 旧写法：\\ifnum 1>0\n\\fi\nBody α\n"
    masked = mask_tex_noncode(text)
    assert "Body" in masked and "α" in masked


def test_url_argument_percent_is_not_a_comment():
    # \url 按字面读取参数，%20 是 URL 内容，不能吞掉同一行后面的正文
    text = "见 \\url{https://e.com/a%20b} 正文\n"
    masked = mask_tex_noncode(text)
    assert masked.endswith(" 正文\n")
    assert "https://e.com/a%20b" not in masked


def test_href_protects_url_argument_only():
    text = "\\href{https://e.com/a%20b}{链接 文本 %注释}\n"
    masked = mask_tex_noncode(text)
    # 首个参数被屏蔽，第二个参数里的 % 仍按注释处理
    assert "https://e.com" not in masked
    assert "链接 文本" in masked
    assert "注释" not in masked


def test_path_and_nolinkurl_keep_percent_literal():
    for command in ("path", "nolinkurl"):
        text = f"\\{command}{{a%20b}} 正文\n"
        masked = mask_tex_noncode(text)
        assert masked.endswith(" 正文\n")


def test_url_with_optional_argument_and_escaped_braces():
    text = "\\url[hyphens]{http://a%7Bb%7Dc} 后\n\\url{x}"
    masked = mask_tex_noncode(text)
    assert masked.endswith(" 后\n\\url{ }")
    assert "a%7Bb" not in masked
    assert len(masked) == len(text)


def test_unterminated_url_argument_does_not_swallow_next_line():
    text = "\\url{http://a%20b\n下一行\n"
    masked = mask_tex_noncode(text)
    assert masked.endswith("\n下一行\n")


def test_lstinline_content_is_blanked_in_all_forms():
    for text in (
        "\\lstinline|a%b| 后面\n",
        "\\lstinline{x%y} 后面\n",
        "\\lstinline[language=C]!b%2;! 后面\n",
    ):
        masked = mask_tex_noncode(text)
        assert masked.endswith(" 后面\n")
        assert len(masked) == len(text)


def test_lstinline_without_argument_keeps_body():
    # 没有分隔符时它不是代码片段，后面的正文仍要参与扫描
    text = "\\lstinline 正文 %注释\n"
    assert mask_tex_noncode(text) == text.replace("%注释", "   ")
