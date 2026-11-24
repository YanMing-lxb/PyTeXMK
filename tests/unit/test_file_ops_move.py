"""``FileMoveRemoveManager._replace`` 的失败回滚契约。

搬移 PDF 时若原子替换失败，必须回到"源文件还在原处、目标文件保持原样"，
否则一次磁盘错误就会把编译产物变成两边都没有。
"""
from pathlib import Path

from pytexmk.file_ops import FileMoveRemoveManager


def test_replace_failure_keeps_source_and_old_dest(tmp_path, monkeypatch):
    src = tmp_path / "new.pdf"
    src.write_bytes(b"fresh-pdf")
    dest = tmp_path / "dest" / "old.pdf"
    dest.parent.mkdir()
    dest.write_bytes(b"old-pdf")

    real_replace = Path.replace

    def boom(self, target):
        if Path(target) == dest:
            raise OSError("模拟原子替换失败")
        return real_replace(self, target)

    monkeypatch.setattr(Path, "replace", boom)

    manager = FileMoveRemoveManager()
    assert manager._replace(src, dest, "dest/old.pdf") is False

    # 源文件必须还在，内容未变；目标维持旧内容，没有被清空
    assert src.read_bytes() == b"fresh-pdf"
    assert dest.read_bytes() == b"old-pdf"
    # 临时文件不能留在目标目录
    assert list(dest.parent.glob("*.pytexmk-*.tmp")) == []


def test_replace_success_moves_and_overwrites(tmp_path):
    src = tmp_path / "src.pdf"
    src.write_bytes(b"v2")
    dest = tmp_path / "dest.pdf"
    dest.write_bytes(b"v1")

    manager = FileMoveRemoveManager()
    assert manager._replace(src, dest, "dest.pdf") is True

    assert not src.exists()
    assert dest.read_bytes() == b"v2"


def test_same_file_is_not_moved(tmp_path):
    """outdir 与 auxdir 相同时，源与目标是同一个文件，不能删了再搬。"""
    same = tmp_path / "main.pdf"
    same.write_bytes(b"pdf")

    manager = FileMoveRemoveManager()
    assert manager._replace(same, same, "main.pdf") is False
    assert same.read_bytes() == b"pdf"
