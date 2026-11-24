"""``.fls``（LaTeX ``-recorder``）INPUT 行的唯一解析入口。

``compile_engine``、``submission``、``pdf_tools`` 过去各自复制了一份
``startswith("INPUT ")`` + 切片 + ``splitlines`` 逻辑；三份的编码、反斜杠
规范化和异常处理并不完全一致。这里只负责“读出原始路径字符串”，
“是否属于项目根 / 是否保留某类后缀”由调用方决定。
"""

from collections.abc import Iterator
from pathlib import Path


def iter_fls_records(fls_path: str | Path) -> Iterator[tuple[str, str]]:
    """按顺序读取 recorder 的工作目录与输入输出记录。"""
    try:
        with Path(fls_path).open(encoding="utf-8", errors="surrogateescape") as stream:
            for line in stream:
                kind, _, path = line.partition(" ")
                if kind in {"PWD", "INPUT", "OUTPUT"} and path.strip():
                    yield kind, path.strip()
    except OSError:
        return


def iter_fls_inputs(fls_path: str | Path) -> Iterator[str]:
    """逐行产出 ``.fls`` 中 ``INPUT`` 后的原始路径字符串。

    文件不可读时返回空迭代器（与旧实现“没有依赖”语义一致）；不在这里
    ``resolve``、不按后缀过滤，避免把三种业务过滤重新混进解析层。
    """
    for kind, path in iter_fls_records(fls_path):
        if kind == "INPUT":
            yield path
