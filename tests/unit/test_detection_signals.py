"""用例：日志信号分类（permanent / transient）。

这是省掉"确认轮"的判定依据：
  - permanent（未定义引用、重复标签）→ 改源码才能消除，不能用来要求再编一轮
  - transient（Label(s) may have changed、Rerun to get cross-references right）
    → 会随轮次消失，必须继续编

分类错了的后果是不对称的：
  把 transient 误判成 permanent → 少编一轮，产出带 ?? 的 PDF（严重）
  把 permanent 误判成 transient → 多编一轮，只是浪费时间（轻微）
因此测试要重点覆盖"不能漏掉 transient"这一侧。
"""

import pytest

from pytexmk.detection import (
    _PERMANENT_PATTERN_TOKENS,
    RERUN_LOG_PATTERNS,
    CompilationDetector,
)


def _detector(tmp_path) -> CompilationDetector:
    """构造一个绑定到 tmp_path 的检测器。"""
    return CompilationDetector(
        project_name="main",
        compiled_program="LuaLaTeX",
        out_files=[".pdf"],
        aux_files=[".aux"],
        outdir=str(tmp_path),
        auxdir=str(tmp_path),
        non_quiet=False,
        MRO=None,
    )


def _write_log(tmp_path, body: str):
    """写 main.log 并返回路径。"""
    log = tmp_path / "main.log"
    log.write_text(body, encoding="utf-8")
    return log


# ------------------------------------------------------------ token 推导


def test_permanent_tokens_derive_from_pattern_order():
    """永久信号集合必须由正则文本推导，不能手写下标。"""
    assert _PERMANENT_PATTERN_TOKENS, "至少要有 3 类永久信号"
    for token in _PERMANENT_PATTERN_TOKENS:
        assert token.startswith("pat")
    # undefined references / Citation undefined / multiply-defined labels
    assert len(_PERMANENT_PATTERN_TOKENS) == 3


def test_label_may_have_changed_is_not_permanent():
    """核心回归：`Label(s) may have changed` 绝不能归为永久信号。

    它是 LaTeX 内核比对读入/写出 .aux 后给出的权威结论，说明交叉引用可能
    还没到位。把它当永久信号会直接导致少编一轮、产出带 ?? 的 PDF。
    """
    idx = next(
        i
        for i, (_pkg, pattern) in enumerate(RERUN_LOG_PATTERNS)
        if "Label(s) may have changed" in pattern.pattern or "Label\\(s\\) may have changed" in pattern.pattern
    )
    assert f"pat{idx}" not in _PERMANENT_PATTERN_TOKENS


# ------------------------------------------------------------ 分类行为


def test_undefined_refs_are_permanent(tmp_path):
    _write_log(
        tmp_path,
        "LaTeX Warning: Reference `sec:x' on page 1 undefined on input line 5.\n"
        "LaTeX Warning: There were undefined references.\n",
    )
    signals = _detector(tmp_path).classify_signals()

    assert signals["transient"] == []
    assert "undef:sec:x" in signals["permanent"]
    assert any(tok.startswith("pat") for tok in signals["permanent"])


def test_label_changed_is_transient(tmp_path):
    _write_log(
        tmp_path,
        "LaTeX Warning: Label(s) may have changed. Rerun to get cross-references right.\n",
    )
    signals = _detector(tmp_path).classify_signals()

    assert signals["permanent"] == []
    assert len(signals["transient"]) == 1


def test_mixed_signals_split_correctly(tmp_path):
    _write_log(
        tmp_path,
        "LaTeX Warning: Label(s) may have changed. Rerun to get cross-references right.\n"
        "LaTeX Warning: There were undefined references.\n"
        "LaTeX Warning: Reference `sec:a' on page 1 undefined on input line 9.\n",
    )
    signals = _detector(tmp_path).classify_signals()

    assert "undef:sec:a" in signals["permanent"]
    assert len(signals["transient"]) == 1


def test_clean_log_yields_empty_classification(tmp_path):
    _write_log(tmp_path, "This is LuaHBTeX, Version 1.25.7\nOutput written on main.pdf.\n")
    signals = _detector(tmp_path).classify_signals()

    assert signals == {"permanent": [], "transient": []}


def test_missing_log_yields_empty_classification(tmp_path):
    assert _detector(tmp_path).classify_signals() == {"permanent": [], "transient": []}


def test_citation_undefined_is_permanent(tmp_path):
    _write_log(tmp_path, "LaTeX Warning: Citation `nokey' on page 2 undefined on input line 40.\n")
    signals = _detector(tmp_path).classify_signals()

    assert "undef:nokey" in signals["permanent"]


def test_multiply_defined_labels_are_permanent(tmp_path):
    _write_log(tmp_path, "LaTeX Warning: There were multiply-defined labels.\n")
    signals = _detector(tmp_path).classify_signals()

    assert signals["transient"] == []
    assert signals["permanent"]


@pytest.mark.parametrize(
    "warning",
    [
        "Package lastpage Warning: Rerun to get the references right on input line 3.\n",
        "Package rerunfilecheck Warning: File `main.out' has changed. Rerun to get outlines right.\n",
    ],
)
def test_rerun_style_warnings_are_transient(tmp_path, warning):
    """这两类警告说明某一轮写入尚未被读回，再编一轮就能消除。"""
    _write_log(tmp_path, warning)
    signals = _detector(tmp_path).classify_signals()

    assert signals["transient"], f"{warning!r} 应归为 transient"
    assert signals["permanent"] == []


def test_signature_and_classification_stay_consistent(tmp_path):
    """签名里的每个 token 都必须出现在分类结果里，不能丢。"""
    _write_log(
        tmp_path,
        "LaTeX Warning: Label(s) may have changed. Rerun to get cross-references right.\n"
        "LaTeX Warning: There were undefined references.\n",
    )
    detector = _detector(tmp_path)
    signature = set(detector.log_rerun_signature())
    signals = detector.classify_signals()

    assert signature == set(signals["permanent"]) | set(signals["transient"])
