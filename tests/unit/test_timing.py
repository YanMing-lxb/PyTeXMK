"""运行时长统计口径：重复工具累加、明细键与调用次数。"""

from pytexmk import timing
from pytexmk.compile_engine import _accumulate_tool_time  # noqa: PLC2701


def test_repeated_tool_time_is_accumulated_not_overwritten():
    runtime: dict[str, float] = {}
    _accumulate_tool_time(runtime, "bib", "bibtex", 0.3076, 1)
    _accumulate_tool_time(runtime, "bib", "bibtex", 0.3078, 2)

    assert runtime["bib_bibtex"] == 0.6154
    assert runtime["bib_bibtex_1"] == 0.3076
    assert runtime["bib_bibtex_2"] == 0.3078


def test_detail_keys_do_not_double_count_latex_seconds():
    assert timing._is_latex_slug("bib_bibtex") is True  # noqa: SLF001
    assert timing._is_latex_slug("bib_bibtex_1") is False  # noqa: SLF001
    assert timing._is_latex_slug("index_makeindex_2") is False  # noqa: SLF001


def test_tool_call_counts_use_detail_keys():
    runtime = {
        "latex_1": 1.0,
        "latex_2": 1.0,
        "latex_3": 1.0,
        "bib_bibtex": 0.6,
        "bib_bibtex_1": 0.3,
        "bib_bibtex_2": 0.3,
        "index_makeindex": 0.2,
        "index_makeindex_1": 0.2,
    }
    assert timing._tool_call_counts(runtime, "pdflatex") == {  # noqa: SLF001
        "pdflatex": 3,
        "bibtex": 2,
        "makeindex": 1,
    }
