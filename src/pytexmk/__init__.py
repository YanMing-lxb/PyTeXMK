"""PyTeXMK 入口模块：版本号与惰性公共 API。

`import pytexmk` 不应拉起 rich / argparse / pypdf 等重依赖，因此包级只做惰性转发
（见 ``__getattr__``），真正的 CLI 在 ``pytexmk.cli`` 下。
"""


def main() -> None:
    """CLI 入口（`pytexmk:main`）：版本快速路径 + 延迟加载 cli 子包。"""
    from ._launcher import main as _main

    _main()


def __getattr__(name: str):
    """包级惰性导出：`pytexmk.cli_args` 在首次访问时才真正 import。

    子模块本身就是惰性的（`from .cli import ...` 才会加载），因此这里只做一层转发；
    好处是 `import pytexmk` 不会拉起 rich / pypdf / argparse 等重依赖。
    """
    if name in {"cli_args", "cli_workflow", "__main__"}:
        import importlib

        return importlib.import_module(f".cli.{name}", __name__)
    raise AttributeError(f"{__name__!r}.{name!r}")
