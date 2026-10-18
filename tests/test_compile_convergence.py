"""用例：编译收敛调度（compile_engine）与辅助文件自愈（aux_repair）。

覆盖两个真实故障：
  1. `pytexmk -l` 在文献/索引维度长期非零时一路跑到安全上限（历史上 11 次编译）。
  2. 被 Ctrl+C 中断的编译留下截断的 .aux，导致之后每次编译都报
     `File ended while scanning use of \\@writefile`。
"""

import pytest

from pytexmk.aux_repair import find_truncated_aux_files, repair_auxiliary_files
from pytexmk.compile_engine import (
    ACTIONABLE_DIMS,
    MAX_EXTRA_COMPILATIONS,
    _convergence_stop_reason,
    _has_actionable_work,
    _ordinal,
)


# ---------------------------------------------------------------- 序数词
@pytest.mark.parametrize(
    ("n", "expected"),
    [
        (1, "1st"),
        (2, "2nd"),
        (3, "3rd"),
        (4, "4th"),
        (10, "10th"),
        (11, "11th"),
        (12, "12th"),
        (13, "13th"),
        (21, "21st"),
        (22, "22nd"),
        (23, "23rd"),
        (101, "101st"),
        (111, "111th"),
        (112, "112th"),
    ],
)
def test_ordinal(n, expected):
    assert _ordinal(n) == expected


def test_ordinal_never_index_errors():
    """历史实现用固定 13 元组，第 14 次编译会抛 IndexError。"""
    assert _ordinal(14) == "14th"
    assert _ordinal(100) == "100th"


# ------------------------------------------------------- 收敛判定
def test_has_actionable_work_ignores_log_dimension():
    """log 维度是警告信号，本身无法靠继续编译消除，不参与推进判断。"""
    assert _has_actionable_work({"bib": 0, "idx": 0, "toc": -1, "aux": 0, "out": 0, "log": 1}) is False
    assert _has_actionable_work({"bib": 2, "idx": 0, "toc": -1, "aux": 0, "out": 0, "log": 1}) is True


def test_actionable_dims_excludes_log():
    assert "log" not in ACTIONABLE_DIMS
    assert set(ACTIONABLE_DIMS) == {"bib", "idx", "toc", "aux", "out"}


def test_stop_reason_fixed_point():
    """本轮指纹等于上一轮 → 不动点，立刻停。"""
    dims = {"bib": 0, "idx": 0, "toc": -1, "aux": 0, "out": 0, "log": 1}
    assert _convergence_stop_reason(dims, ["aaa"], "aaa") == "fixed_point"


def test_stop_reason_cycle():
    """本轮指纹等于更早的轮次 → 两态震荡，停。"""
    dims = {"bib": 0, "idx": 0, "toc": -1, "aux": 0, "out": 0, "log": 1}
    assert _convergence_stop_reason(dims, ["aaa", "bbb"], "aaa") == "cycle"


def test_stop_reason_stable_when_artifacts_all_zero():
    """变更类维度全部归零 → stable（日志是否还有残留警告无关紧要）。"""
    dims = {"bib": 0, "idx": 0, "toc": -1, "aux": 0, "out": 0, "log": 1}
    assert _convergence_stop_reason(dims, ["aaa"], "bbb") == "stable"


def test_stop_reason_log_stalled_when_only_permanent_signals():
    """还有维度非零，但日志只剩永久信号 → 不必再编一轮去确认。

    这是省掉"确认轮"的核心用例：辅助文件仍在动（aux=1），可是日志明确说
    剩下的只有未定义引用/重复标签，再编一轮只会得到同一份警告。
    """
    dims = {"bib": 0, "idx": 0, "toc": 1, "aux": 1, "out": 0, "log": 1}
    signals = {"permanent": ["pat0", "undef:sec:x"], "transient": []}
    assert _convergence_stop_reason(dims, ["aaa"], "bbb", signals) == "log_stalled"


def test_stop_reason_continue_when_transient_signals_remain():
    """日志里还有 transient 信号 → 必须再编一轮，让 LaTeX 自己确认收敛。

    `Label(s) may have changed` 是内核给出的权威判断：交叉引用可能还没到位，
    此时把维度非零当成"伪需求"提前收工，会产出带 ?? 的 PDF。
    """
    dims = {"bib": 0, "idx": 0, "toc": 1, "aux": 1, "out": 0, "log": 1}
    signals = {"permanent": ["undef:sec:x"], "transient": ["pat1"]}
    assert _convergence_stop_reason(dims, ["aaa"], "bbb", signals) == ""


def test_stop_reason_continue_when_only_permanent_but_no_log_dim():
    """permanent 信号不依赖 log 维度是否启用；log 未启用时按普通非零维度继续。"""
    dims = {"bib": 0, "idx": 0, "toc": 1, "aux": 1, "out": 0, "log": -1}
    signals = {"permanent": ["pat0"], "transient": []}
    assert _convergence_stop_reason(dims, ["aaa"], "bbb", signals) == ""


def test_stop_reason_continue_without_signal_info():
    """没有信号分类信息时退化为保守策略：维度非零就继续编。"""
    dims = {"bib": 0, "idx": 0, "toc": 1, "aux": 1, "out": 0, "log": 1}
    assert _convergence_stop_reason(dims, ["aaa"], "bbb") == ""


def test_stop_reason_stable_when_everything_clean():
    dims = {"bib": 0, "idx": 0, "toc": -1, "aux": 0, "out": 0, "log": 0}
    assert _convergence_stop_reason(dims, ["aaa"], "bbb") == "stable"


def test_stop_reason_continue_while_actionable():
    """还有变更类维度非零且指纹是新的 → 空串表示继续编译。"""
    dims = {"bib": 2, "idx": 0, "toc": -1, "aux": 1, "out": 0, "log": 1}
    assert _convergence_stop_reason(dims, ["aaa"], "bbb") == ""


def test_stop_reason_fingerprint_beats_stuck_dimension():
    """关键回归：某个维度因宏包 churn 长期非零，但产物指纹不再变化时必须停。

    这正是历史上 11 次编译的成因 —— 旧实现要求 bib/idx/aux/out 全部归零
    才肯判定停滞，只要有一个维度非零就一路跑到上限。
    """
    dims = {"bib": 2, "idx": 0, "toc": -1, "aux": 1, "out": 0, "log": 1}
    assert _convergence_stop_reason(dims, ["same"], "same") == "fixed_point"


def test_stop_reason_first_round_never_stops_early():
    """首轮没有历史指纹时，不能因为指纹"已在列表里"就提前退出。"""
    dims = {"bib": 2, "idx": 0, "toc": -1, "aux": 1, "out": 0, "log": 1}
    assert _convergence_stop_reason(dims, [], "first") == ""


def test_max_extra_compilations_is_bounded():
    """上限必须存在且不至于把最坏情况拖到 11 次以上。"""
    assert 1 <= MAX_EXTRA_COMPILATIONS <= 8


# ------------------------------------------------- 截断辅助文件自愈
def _write_truncated(path, size=16384):
    """写一个"括号不配平"的截断文件，模拟 Ctrl+C 打断的写入。"""
    body = "\\relax\n" * (size // 8)
    body += "\\@writefile{toc}{\\contentsline {section}{未闭合"
    path.write_text(body, encoding="utf-8")


def test_find_truncated_aux_detects_unbalanced_braces(tmp_path):
    _write_truncated(tmp_path / "main.aux")
    found = find_truncated_aux_files([tmp_path], project_name="main")
    assert [p.name for p in found] == ["main.aux"]


def test_find_truncated_aux_ignores_healthy_file(tmp_path):
    healthy = tmp_path / "main.aux"
    healthy.write_text("\\relax\n\\bibcite{key}{{1}{}{{}}{{}}}\n\\gdef \\@abspage@last{3}\n", encoding="utf-8")
    assert find_truncated_aux_files([tmp_path], project_name="main") == []


def test_find_truncated_aux_ignores_empty_file(tmp_path):
    """空文件是合法的（.spl 等本来就允许为空），不能误删。"""
    (tmp_path / "main.spl").write_text("", encoding="utf-8")
    assert find_truncated_aux_files([tmp_path], project_name="main") == []


def test_find_truncated_aux_skips_non_checked_suffix(tmp_path):
    """只检查行式写入、括号必须配平的辅助文件，不碰 .log 等。"""
    (tmp_path / "main.log").write_text("{\\unbalanced", encoding="utf-8")
    assert find_truncated_aux_files([tmp_path], project_name="main") == []


def test_repair_auxiliary_files_deletes_only_broken(tmp_path):
    _write_truncated(tmp_path / "main.aux")
    good = tmp_path / "main.out"
    good.write_text("\\BOOKMARK [1][-]{x}{Title}{}\n", encoding="utf-8")

    repaired = repair_auxiliary_files([tmp_path], project_name="main")
    assert [p.name for p in repaired] == ["main.aux"]
    assert not (tmp_path / "main.aux").exists()
    assert good.exists()


def test_repair_auxiliary_files_noop_when_clean(tmp_path):
    (tmp_path / "main.aux").write_text("\\relax\n", encoding="utf-8")
    assert repair_auxiliary_files([tmp_path], project_name="main") == []
