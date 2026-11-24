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
import functools
import os
import sys
import time
from collections.abc import Iterator
from pathlib import Path

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


_TEMP_VARS = ("TEMP", "TMP", "TMPDIR")


def is_dir_writable(path: Path | str) -> bool:
    """真正建一个探针文件来判断目录可写（Windows ACL 下 os.access 会误判）。

    结果按绝对路径缓存：一次构建会调起 2–9 个外部命令，逐次写+删探针文件纯属
    重复 I/O。同一进程内目录权限不会中途改变（没有运行时改 ACL 的入口），
    缓存与"每次实测"等价；跨进程（--watch 的每轮）仍是新进程，自然重新探测。
    """
    return _is_dir_writable_cached(str(Path(path).absolute()))


@functools.cache
def _is_dir_writable_cached(path: str) -> bool:
    try:
        probe = Path(path) / f".pytexmk_tmp_probe_{os.getpid()}_{time.time_ns()}"
        probe.write_text("", encoding="utf-8")
        probe.unlink()
    except OSError:
        return False
    return True


def ensure_writable_temp(
    env: dict[str, str], fallback: Path | str
) -> tuple[dict[str, str], str | None]:
    """保证子进程拿到的 ``TEMP/TMP/TMPDIR`` 可写，不可写时改用项目内目录。

    背景：部分 Windows 环境（受限令牌、安全软件拦截）里，Python 进程和它
    启动的 TeX 工具都写不了 ``%TEMP%``，xelatex 会在 shipout 阶段直接死掉，
    只留下截断的 ``main.log`` 与 ``main.synctex(busy)``；xindy 也会因为临时
    文件建不出来报 ``Win32 error 267``。这里先探测当前值，不可写就把三个变量
    统一指向调用方给的兜底目录，子进程不再依赖系统临时目录。

    返回 ``(env, 兜底目录或 None)``；未改写时第二项为 ``None``，便于调用方
    只在真正改写时提示一次。
    """
    current = env.get("TEMP") or env.get("TMP")
    if current and is_dir_writable(current):
        return env, None

    target = Path(fallback)
    try:
        target.mkdir(parents=True, exist_ok=True)
    except OSError:
        return env, None
    if not is_dir_writable(target):
        return env, None

    for var in _TEMP_VARS:
        env[var] = str(target)
    return env, str(target)


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
