"""CLI 轻量启动器：`--version` 在导入 rich/argparse 之前直接返回。

安装后的 `pytexmk` 入口与 `python -m pytexmk` 都走这里。除了版本号快速路径，
其余参数一律延迟到 `pytexmk.cli.__main__`，避免影响正常解析与 `-h` 行为。
"""

import sys

from .version import __version__, script_name

_VERSION_FLAGS = frozenset({"-v", "--version"})


def main() -> None:
    if len(sys.argv) == 2 and sys.argv[1] in _VERSION_FLAGS:
        print(f"{script_name} {__version__}")
        return

    # Python 3.15：版本快速路径之后再开启惰性导入，避免为 `-h`/普通命令
    # 一次性加载 rich、argparse 与全部 CLI 依赖；`--version` 已在上面返回，
    # 不会受该进程级开关影响。`hasattr` 保留 3.14 及更早解释器的兼容性。
    if hasattr(sys, "set_lazy_imports"):
        sys.set_lazy_imports("all")

    from .cli.__main__ import main as cli_main

    cli_main()
