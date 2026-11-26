"""命令行开关契约：每个公开开关都必须出现在解析结果里。

只测"某个函数收到什么参数"发现不了开关本身被删/被改名（例如 -dr 改成 -d
后全套测试仍绿）。这里把开关列成表：增删开关必须同步改表，否则本文件直接红。

1.2.18 起短开关以单字符为主，多字符短开关只在确有语义时保留
（-nq / -ca / -Ca / -pa / -sp / -vb / -pv / -iu / -ls / -sc / -ap / -rp）。
"""
import pytest

from pytexmk.cli.cli_args import build_parser, parse_args

# 每个短/长开关至少出现一次；值为期望的 Namespace 字段。
FLAG_CASES = [
    ([], {"document": None}),
    (["main"], {"document": "main"}),
    (["-p"], {"pdflatex": True}),
    (["--pdflatex"], {"pdflatex": True}),
    (["-x"], {"xelatex": True}),
    (["--xelatex"], {"xelatex": True}),
    (["-l"], {"lualatex": True}),
    (["--lualatex"], {"lualatex": True}),
    (["-d"], {"draft": True}),
    (["--draft"], {"draft": True}),
    (["-c"], {"clean": True}),
    (["--clean"], {"clean": True}),
    (["-C"], {"clean_out": True}),
    (["--clean-out"], {"clean_out": True}),
    (["-ca"], {"clean_recursive": True}),
    (["--clean-recursive"], {"clean_recursive": True}),
    (["-Ca"], {"clean_recursive_out": True}),
    (["--clean-recursive-out"], {"clean_recursive_out": True}),
    (["-nq"], {"non_quiet": True}),
    (["--non-quiet"], {"non_quiet": True}),
    (["-pa=-8bit", "-pa=foo"], {"extra_args": ["-8bit", "foo"]}),
    (["--pass-arg=-8bit"], {"extra_args": ["-8bit"]}),
    (["-sp"], {"submission_pack": True}),
    (["--submission-pack"], {"submission_pack": True}),
    (["-w"], {"watch": True}),
    (["--watch"], {"watch": True}),
    (["-e"], {"explain": True}),
    (["--explain"], {"explain": True}),
    (["-sc"], {"show_config": True}),
    (["--show-config"], {"show_config": True}),
    (["-ap"], {"all_subprojects": True}),
    (["--all-subprojects"], {"all_subprojects": True}),
    (["-vb"], {"verbose": True}),
    (["--verbose"], {"verbose": True}),
    (["-rp"], {"pdf_repair": []}),
    (["-rp", "a.pdf", "b.pdf"], {"pdf_repair": ["a.pdf", "b.pdf"]}),
    (["--pdf-repair"], {"pdf_repair": []}),
    (["-f"], {"force_rebuild": True}),
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
        "-p", "-x", "-l", "-d", "-c", "-C", "-ca", "-Ca",
        "-nq", "-pa", "-sp", "-w", "-e", "-sc", "-ap",
        "-vb", "-rp", "-f", "-pv",
        "-s", "-ls", "-i", "-iu", "-r", "--report",
    ):
        assert flag in help_text, f"帮助页缺少 {flag}"


def test_report_and_pdflatex_do_not_collide_with_pdf_repair():
    """``-r -p``（报告 + PdfLaTeX）与 ``-rp``（PDF 修复）必须是两回事。"""
    separate = parse_args(["-r", "-p"])
    assert separate.report and separate.pdflatex
    assert separate.pdf_repair is None
    clustered_name = parse_args(["-rp"])
    assert clustered_name.pdf_repair == []
    assert not clustered_name.report
    assert not clustered_name.pdflatex


def test_long_options_are_not_abbreviated():
    """长名关闭缩写：``--draf`` 不能被当成 ``--draft``。"""
    with pytest.raises(SystemExit) as exc:
        parse_args(["--draf"])
    assert exc.value.code == 2


def test_unknown_flag_exits_with_usage_error():
    """未知开关必须是 argparse 的退出码 2，而不是被静默忽略。"""
    with pytest.raises(SystemExit) as exc:
        parse_args(["--no-such-flag"])
    assert exc.value.code == 2


@pytest.mark.parametrize(
    "removed",
    [
        ["--report=custom.json"],
        ["--readme"],
        ["-dr"],
        ["-dc"],
        ["-cr"],
        ["-dd"],
        ["-n"],
        ["-A"],
        ["-pr"],
        ["-fr"],
        ["--interaction", "batchmode"],
        ["--PdfLaTeX"],
        ["--LaTeXDiff", "old.tex", "new.tex"],
        ["--diff-style", "1"],
    ],
)
def test_removed_legacy_options_are_rejected(removed):
    """已删除/已更名的旧选项必须报参数错误，不能悄悄回退成新语义。"""
    with pytest.raises(SystemExit) as exc:
        parse_args(removed)
    assert exc.value.code == 2
