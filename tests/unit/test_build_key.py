"""构建指纹（``_build_key``）的维度契约。

缓存跳过编译时，只要指纹漏掉任何一个构建参数，改了那个参数也会被当成
"源未变"直接复用旧 PDF。这里逐个维度验证：改一项，指纹必须变。
"""
from types import SimpleNamespace

import pytest

from pytexmk.compile_engine import _build_key, _build_options
from pytexmk.version import __version__

BASE = {
    "engine": "XeLaTeX",
    "interaction": "nonstopmode",
    "shell_escape": False,
    "synctex": True,
    "draft": False,
    "native": True,
    "outdir": "Build",
    "auxdir": "Auxiliary",
    "jobname": "",
    "extra_args": [],
    "max_extra": 8,
    "version": __version__,
}


def test_same_options_produce_same_key():
    assert _build_key(dict(BASE)) == _build_key(dict(BASE))


@pytest.mark.parametrize(
    ("field", "changed"),
    [
        ("engine", "LuaLaTeX"),
        ("interaction", "batchmode"),
        ("shell_escape", True),
        ("synctex", False),
        ("draft", True),
        ("native", False),
        ("outdir", "OtherBuild"),
        ("auxdir", "OtherAux"),
        ("jobname", "main"),
        ("extra_args", ["-8bit"]),
        ("max_extra", 0),
        ("version", "0"),
    ],
)
def test_each_build_knob_changes_key(field, changed):
    assert _build_key({**BASE, field: changed}) != _build_key(dict(BASE))


def test_key_format_is_sha256_prefixed():
    key = _build_key(dict(BASE))
    assert key.startswith("sha256:")
    assert len(key) == len("sha256:") + 64
    int(key.removeprefix("sha256:"), 16)  # 必须是合法十六进制


def test_build_options_carry_version_and_all_knobs():
    """调用点必须真的把 version 等参数交给指纹，而不只是 _build_key 会算。"""
    model = SimpleNamespace(synctex=True, jobname="", extra_args=[])
    options = _build_options(
        "XeLaTeX", model, "Build", "Auxiliary", False, False, True, None, 8
    )
    assert options == BASE
    assert options["version"] == __version__
    assert _build_key(options) == _build_key(dict(BASE))
