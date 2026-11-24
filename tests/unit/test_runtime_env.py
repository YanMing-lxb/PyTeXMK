"""用例：打包环境下的子进程环境净化（pytexmk.runtime_env）。

背景：PyInstaller 会把 ``sys._MEIPASS`` 前插到 ``LD_LIBRARY_PATH`` 等变量，子进程继承后
优先加载打包目录里的同名库，导致 lualatex 报 ``version 'OPENSSL_3.2.0' not found``。
这里覆盖两条修法的边界：
  1) ``*_ORIG`` 优先（空值 = 原本没有该变量，必须删除而不是留下空串）
  2) 没有 ``*_ORIG`` 时按真实路径摘掉打包目录条目，其它条目顺序不变
"""

import os
import sys

import pytest

import pytexmk.runtime_env as runtime_env
from pytexmk.runtime_env import (
    bundle_dir,
    child_env,
    ensure_writable_temp,
    external_process_scope,
)


def _join(*parts):
    """按当前平台的路径分隔符拼接（Windows 是 ';'，POSIX 是 ':'）。"""
    return os.pathsep.join(str(part) for part in parts)


@pytest.fixture
def frozen(monkeypatch, tmp_path):
    """把当前进程伪装成 PyInstaller onedir 运行，返回打包目录。"""
    bundle = tmp_path / "_internal"
    bundle.mkdir()
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.setattr(sys, "_MEIPASS", str(bundle), raising=False)
    return bundle


@pytest.fixture
def unpinned(monkeypatch):
    """清掉环境里的库路径变量与 *_ORIG，避免宿主环境影响断言。"""
    for var in ("LD_LIBRARY_PATH", "LD_LIBRARY_PATH_ORIG", "DYLD_LIBRARY_PATH", "LIBPATH"):
        monkeypatch.delenv(var, raising=False)


def test_bundle_dir_is_none_when_running_from_source(monkeypatch):
    """源码运行（无 sys.frozen）时不存在打包目录。"""
    monkeypatch.setattr(sys, "frozen", False, raising=False)
    monkeypatch.setattr(sys, "_MEIPASS", "/somewhere", raising=False)
    assert bundle_dir() is None


def test_bundle_dir_uses_realpath(frozen, tmp_path):
    """打包目录返回真实路径（软链要解开）。"""
    link = tmp_path / "link_to_bundle"
    try:
        link.symlink_to(frozen)
    except OSError as exc:
        # Windows 默认需要开发者模式/符号链接权限；这是环境限制，不是代码缺陷。
        pytest.skip(f"平台不允许创建符号链接: {exc}")
    assert bundle_dir() == os.path.realpath(frozen)


def test_source_run_keeps_library_path_untouched(unpinned, monkeypatch):
    """源码运行时 child_env 不改动 LD_LIBRARY_PATH。"""
    monkeypatch.setenv("LD_LIBRARY_PATH", _join("/usr/lib", "/opt/lib"))
    assert child_env()["LD_LIBRARY_PATH"] == _join("/usr/lib", "/opt/lib")


def test_bundle_entries_are_removed(frozen, unpinned, monkeypatch):
    """打包目录条目被摘掉，其它条目与顺序保持不变。"""
    monkeypatch.setenv("LD_LIBRARY_PATH", _join("/usr/lib", frozen, "/opt/lib"))
    env = child_env()
    assert env["LD_LIBRARY_PATH"] == _join("/usr/lib", "/opt/lib")


def test_variable_is_dropped_when_only_bundle_remains(frozen, unpinned, monkeypatch):
    """只剩打包目录时整条变量删除，而不是留空串。"""
    monkeypatch.setenv("LD_LIBRARY_PATH", str(frozen))
    assert "LD_LIBRARY_PATH" not in child_env()


def test_orig_variable_wins(frozen, unpinned, monkeypatch):
    """存在 *_ORIG 时以它为准，并清掉 *_ORIG 自身（不泄漏给子进程）。"""
    monkeypatch.setenv("LD_LIBRARY_PATH", _join(frozen, "/usr/lib"))
    monkeypatch.setenv("LD_LIBRARY_PATH_ORIG", "/usr/lib")
    env = child_env()
    assert env["LD_LIBRARY_PATH"] == "/usr/lib"
    assert "LD_LIBRARY_PATH_ORIG" not in env


def test_empty_orig_variable_deletes_it(frozen, unpinned, monkeypatch):
    """*_ORIG 为空表示原本没有该变量，必须删除。"""
    monkeypatch.setenv("LD_LIBRARY_PATH", str(frozen))
    monkeypatch.setenv("LD_LIBRARY_PATH_ORIG", "")
    env = child_env()
    assert "LD_LIBRARY_PATH" not in env
    assert "LD_LIBRARY_PATH_ORIG" not in env


def test_dyld_library_path_is_handled(frozen, unpinned, monkeypatch):
    """macOS 的 DYLD_LIBRARY_PATH 走同一套逻辑。"""
    monkeypatch.setenv("DYLD_LIBRARY_PATH", _join(frozen, "/usr/local/lib"))
    assert child_env()["DYLD_LIBRARY_PATH"] == "/usr/local/lib"


def test_child_env_does_not_mutate_current_process(frozen, unpinned, monkeypatch):
    """净化只作用于副本，不能改动当前进程的环境。"""
    value = _join(frozen, "/usr/lib")
    monkeypatch.setenv("LD_LIBRARY_PATH", value)
    child_env()
    assert os.environ["LD_LIBRARY_PATH"] == value


@pytest.mark.skipif(sys.platform != "win32", reason="SetDllDirectoryW 只在 Windows 上存在")
def test_external_process_scope_clears_and_restores_dll_directory(frozen, monkeypatch):
    """Windows：作用域内 DLL 搜索目录为 None，退出后恢复成打包目录。"""
    import ctypes

    calls: list = []

    class FakeKernel32:
        @staticmethod
        def SetDllDirectoryW(path):
            calls.append(path)
            return 1

    monkeypatch.setattr(ctypes, "windll", type("W", (), {"kernel32": FakeKernel32}), raising=False)

    with external_process_scope():
        pass

    # 进入时清空、退出时恢复
    assert calls[0] is None
    assert calls[1] == os.path.realpath(frozen)


def test_external_process_scope_is_noop_outside_frozen(monkeypatch):
    """非打包运行时作用域是空操作，不触碰任何库搜索设置。"""

    monkeypatch.setattr(sys, "frozen", False, raising=False)

    class BoomKernel32:
        @staticmethod
        def SetDllDirectoryW(path):
            raise AssertionError("非打包运行不应调用 SetDllDirectoryW")

    class FakeCtypes:
        windll = type("W", (), {"kernel32": BoomKernel32})

    monkeypatch.setattr(runtime_env, "ctypes", FakeCtypes)
    with external_process_scope():
        pass


def test_ensure_writable_temp_keeps_env_when_temp_writable(tmp_path):
    """系统临时目录可写时原样返回，不改写任何变量。"""
    env = {"TEMP": str(tmp_path), "TMP": str(tmp_path), "TMPDIR": str(tmp_path)}
    new_env, override = ensure_writable_temp(env, tmp_path / "fallback")
    assert override is None
    assert new_env["TEMP"] == str(tmp_path)
    assert not (tmp_path / "fallback").exists()


def test_ensure_writable_temp_switches_to_fallback_when_unwritable(tmp_path):
    """临时目录不可写（不存在或受限）时，三个变量一起指向兜底目录。"""
    env = {"TEMP": str(tmp_path / "missing"), "TMP": str(tmp_path / "missing")}
    fallback = tmp_path / "proj" / ".pytexmk-tmp"
    new_env, override = ensure_writable_temp(env, fallback)
    assert override == str(fallback)
    assert new_env["TEMP"] == str(fallback)
    assert new_env["TMP"] == str(fallback)
    assert new_env["TMPDIR"] == str(fallback)
    assert fallback.is_dir()


def test_ensure_writable_temp_gives_up_when_fallback_unusable(tmp_path):
    """兜底目录也建不出来时保持原环境，不让编译因为探测而中断。"""
    env = {"TEMP": str(tmp_path / "missing")}
    blocker = tmp_path / "blocked"
    blocker.write_text("x", encoding="utf-8")  # 同名文件占位，mkdir 必失败
    new_env, override = ensure_writable_temp(env, blocker / "sub")
    assert override is None
    assert new_env["TEMP"] == str(tmp_path / "missing")
