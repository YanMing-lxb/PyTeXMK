"""命令行开关契约：每个公开开关都必须出现在解析结果里。

只测"某个函数收到什么参数"发现不了开关本身被删/被改名（例如 -dr 改成 -dx
后全套测试仍绿）。这里把开关列成表：增删开关必须同步改表，否则本文件直接红。
"""
import pytest

from pytexmk.cli.cli_args import build_parser, parse_args

# 每个短/长开关至少出现一次；值为期望的 Namespace 字段。
FLAG_CASES = [
    ([], {"document": None}),
    (["main"], {"document": "main"}),
    (["-p"], {"PdfLaTeX": True}),
    (["--PdfLaTeX"], {"PdfLaTeX": True}),
    (["-x"], {"XeLaTeX": True}),
    (["--XeLaTeX"], {"XeLaTeX": True}),
    (["-l"], {"LuaLaTeX": True}),
    (["--LuaLaTeX"], {"LuaLaTeX": True}),
    (["-dr"], {"draft": True}),
    (["--draft"], {"draft": True}),
    (["-c"], {"clean": True}),
    (["--clean"], {"clean": True}),
    (["-C"], {"Clean": True}),
    (["--Clean"], {"Clean": True}),
    (["-ca"], {"clean_any": True}),
    (["--clean-any"], {"clean_any": True}),
    (["-Ca"], {"Clean_any": True}),
    (["--Clean-any"], {"Clean_any": True}),
    (["-nq"], {"non_quiet": True}),
    (["--non-quiet"], {"non_quiet": True}),
    (["--interaction", "batchmode"], {"interaction": "batchmode"}),
    (["--pass-arg=-8bit", "--pass-arg=foo"], {"extra_args": ["-8bit", "foo"]}),
    (["-sp"], {"submission_pack": True}),
    (["--submission-pack"], {"submission_pack": True}),
    (["--watch"], {"watch": True}),
    (["--explain"], {"explain": True}),
    (["--show-config"], {"show_config": True}),
    (["-A"], {"all_subprojects": True}),
    (["--all-subprojects"], {"all_subprojects": True}),
    (["--diff-style", "1"], {"diff_style": "1"}),
    (["-vb"], {"verbose": True}),
    (["--verbose"], {"verbose": True}),
    (["-pr"], {"pdf_repair": []}),
    (["-pr", "a.pdf", "b.pdf"], {"pdf_repair": ["a.pdf", "b.pdf"]}),
    (["--pdf-repair"], {"pdf_repair": []}),
    (["-fr"], {"force_rebuild": True}),
    (["--force-rebuild"], {"force_rebuild": True}),
    (["-pv"], {"pdf_preview": "preview after compile"}),
    (["-pv", "main.pdf"], {"pdf_preview": "main.pdf"}),
    (["--pdf-preview"], {"pdf_preview": "preview after compile"}),
    (["-s", "one"], {"subproject": "one"}),
    (["--subproject", "one"], {"subproject": "one"}),
    (["-ls"], {"list_subprojects": True}),
    (["--list-subprojects"], {"list_subprojects": True}),
    (["-i"], {"init": True}),
    (["--init"], {"init": True}),
    (["-iu"], {"init_user": True}),
    (["--init-user"], {"init_user": True}),
    (["-r"], {"report": True}),
    (["main", "-r"], {"report": True, "document": "main"}),
    # -d/-dc：省略文件名 → []；给两个 → [OLD, NEW]，document 被吸收
    (["-d"], {"LaTeXDiff": [], "document": None}),
    (["main", "-d"], {"LaTeXDiff": [], "document": "main"}),
    (["-d", "old.tex", "new.tex"], {"LaTeXDiff": ["old.tex", "new.tex"], "document": None}),
    (["-d", "old.tex"], {"LaTeXDiff": ["old.tex"]}),
    (["-dc"], {"LaTeXDiff_compile": []}),
    (["-dc", "old.tex", "new.tex"], {"LaTeXDiff_compile": ["old.tex", "new.tex"]}),
    (["--LaTeXDiff", "old.tex", "new.tex"], {"LaTeXDiff": ["old.tex", "new.tex"]}),
    (["--LaTeXDiff-compile"], {"LaTeXDiff_compile": []}),
]


@pytest.mark.parametrize(("argv", "expected"), FLAG_CASES)
def test_flag_parses_to_expected_field(argv, expected):
    args = parse_args(argv)
    for field, value in expected.items():
        assert getattr(args, field) == value, f"{argv} -> {field}"


def test_help_mentions_every_public_flag():
    """帮助页必须能找到每个开关；改短旗标时这里会立刻失败。"""
    help_text = build_parser().format_help()
    for flag in (
        "-p", "-x", "-l", "-d", "-dc", "-dr", "-c", "-C", "-ca", "-Ca",
        "-nq", "--interaction", "--pass-arg", "-sp", "--watch", "--explain",
        "--show-config", "-A", "--diff-style", "-vb", "-pr", "-fr", "-pv",
        "-s", "-ls", "-i", "-iu", "-r",
    ):
        assert flag in help_text, f"帮助页缺少 {flag}"


def test_unknown_flag_exits_with_usage_error():
    """未知开关必须是 argparse 的退出码 2，而不是被静默忽略。"""
    with pytest.raises(SystemExit) as exc:
        parse_args(["--no-such-flag"])
    assert exc.value.code == 2


@pytest.mark.parametrize("removed", [["--report", "custom.json"], ["--readme"]])
def test_removed_legacy_options_are_rejected(removed):
    """已删除的旧选项必须报参数错误，不能悄悄回退成新语义。"""
    with pytest.raises(SystemExit) as exc:
        parse_args(removed)
    assert exc.value.code == 2
