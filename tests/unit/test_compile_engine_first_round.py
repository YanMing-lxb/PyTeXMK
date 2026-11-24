"""首轮收敛判定：有未消费的外部工具产物时不能停。

首轮后维度归零常被误判为"到不动点"，但 biber/makeindex 刚写出的
``.bbl/.ind`` 还没被 TeX 读进去，此时停下会让 PDF 里缺参考文献/索引。
"""
import pytest

from pytexmk.compile_engine import _first_round_stop_reason


@pytest.mark.parametrize(
    ("dims", "tools_pending", "expected"),
    [
        # 全部归零且无待消费产物：可以停在首轮
        ({"bib": 0, "idx": 0, "toc": 0, "aux": 0, "out": 0}, False, "stable"),
        # 任一维度仍有变化：继续编
        ({"bib": 1, "idx": 0, "toc": 0, "aux": 0, "out": 0}, False, ""),
        ({"bib": 0, "idx": 0, "toc": 0, "aux": 1, "out": 0}, False, ""),
        ({"bib": 0, "idx": 0, "toc": 0, "aux": 0, "out": 1}, False, ""),
        # 维度归零但外部工具刚写出 .bbl/.ind：必须再编一轮
        ({"bib": 0, "idx": 0, "toc": 0, "aux": 0, "out": 0}, True, ""),
        # 维度归零 + 有待消费产物：同样不能停
        ({"bib": 1, "idx": 0, "toc": 0, "aux": 0, "out": 0}, True, ""),
        # 非 ACTIONABLE 维度（如日志变化）不影响首轮判定
        ({"bib": 0, "idx": 0, "toc": 0, "aux": 0, "out": 0, "log": 9}, False, "stable"),
    ],
)
def test_first_round_stop_reason(dims, tools_pending, expected):
    assert _first_round_stop_reason(dims, tools_pending) == expected
