"""打包环境（PyInstaller onedir）下的子进程运行期净化。

问题背景
--------
PyInstaller 的 bootloader 会把 ``sys._MEIPASS``（onedir 下即 ``_internal``）前插到
``LD_LIBRARY_PATH`` / ``DYLD_LIBRARY_PATH`` / ``LIBPATH``，Windows 上还会
``SetDllDirectoryW`` 到同一目录。这些设置会被**子进程继承**：PyTeXMK 调起的
lualatex / xelatex / biber / dvipdfmx 等外部程序，于是优先加载了打包目录里的同名库
（如 ``libssl.so.3`` / ``libcrypto.so.3`` / ``libcurl.so.4``），与系统库版本不匹配时
直接报 ``version `OPENSSL_3.2.0' not found`` 之类的错误。

官方给出的修法（PyInstaller 文档「Launching External Programs」）：运行期在启动外部
程序前还原环境——环境里若有 ``*_ORIG`` 变量则用它还原，否则把这些变量里的打包目录
条目摘掉；Windows 额外用 ``SetDllDirectoryW(None)`` 临时清空 DLL 搜索目录。

本模块只做这三件事，不改变 PyTeXMK 自身进程的分库搜索行为。
"""

import contextlib
import ctypes
import os
import sys
from collections.abc import Iterator

_ORIG_SUFFIX = "_ORIG"
_LIB_PATH_VARS = ("LD_LIBRARY_PATH", "DYLD_LIBRARY_PATH", "LIBPATH")


def bundle_dir() -> str | None:
    """返回打包目录的真实路径；源码运行时返回 ``None``。"""
    if not getattr(sys, "frozen", False):
        return None
    meipass = getattr(sys, "_MEIPASS", None)
    if not meipass:
        return None
    return os.path.realpath(meipass)


def child_env(base_env: dict[str, str] | None = None) -> dict[str, str]:
    """返回适合外部程序的环境变量副本（复制后修改，不改动当前进程）。"""
    env = dict(os.environ if base_env is None else base_env)
    bundle = bundle_dir()

    for var in _LIB_PATH_VARS:
        orig_key = f"{var}{_ORIG_SUFFIX}"
        # 1) 存在 *_ORIG：以它为准（空值表示原本没有这个变量，直接删除）
        if orig_key in env:
            original = env.pop(orig_key)
            if original:
                env[var] = original
            else:
                env.pop(var, None)
            continue

        # 2) 没有 *_ORIG：手工摘掉打包目录条目
        if bundle is None or var not in env:
            continue
        kept = [entry for entry in env[var].split(os.pathsep) if entry and os.path.realpath(entry) != bundle]
        if kept:
            env[var] = os.pathsep.join(kept)
        else:
            env.pop(var, None)

    return env


@contextlib.contextmanager
def external_process_scope() -> Iterator[None]:
    """Windows：在启动外部程序的瞬间清空 DLL 搜索目录，退出后恢复。

    非 Windows 或非打包运行时为空操作（POSIX 下靠 ``child_env`` 已足够）。
    """
    bundle = bundle_dir()
    if sys.platform != "win32" or bundle is None:
        yield
        return

    kernel32 = ctypes.windll.kernel32
    kernel32.SetDllDirectoryW.argtypes = [ctypes.c_wchar_p]
    kernel32.SetDllDirectoryW.restype = ctypes.c_int
    kernel32.SetDllDirectoryW(None)
    try:
        yield
    finally:
        kernel32.SetDllDirectoryW(bundle)
