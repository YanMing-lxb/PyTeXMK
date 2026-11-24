"""清理路径的同内容判定：保留 OSError 保守返回 False。"""

from pytexmk.cli.cli_compile import _same_bytes


def test_same_bytes_true_for_identical(tmp_path):
    left = tmp_path / "left.aux"
    right = tmp_path / "right.aux"
    left.write_bytes(b"same")
    right.write_bytes(b"same")
    assert _same_bytes(left, right) is True


def test_same_bytes_false_for_different(tmp_path):
    left = tmp_path / "left.aux"
    right = tmp_path / "right.aux"
    left.write_bytes(b"left")
    right.write_bytes(b"right")
    assert _same_bytes(left, right) is False


def test_same_bytes_false_when_missing(tmp_path):
    assert _same_bytes(tmp_path / "missing.aux", tmp_path / "other.aux") is False
