"""
统一 Console 实例管理模块

提供全局唯一的 Rich Console 实例，避免各模块重复创建导致配置不一致。
同时提供 FallbackConsole 兼容无 Rich 环境。
"""


try:
    from rich.console import Console as RichConsole

    _HAS_RICH = True
except ImportError:
    _HAS_RICH = False


class FallbackConsole:
    """无 Rich 库时的回退控制台，提供兼容的 print 接口"""

    def print(self, *args, **kwargs):
        print(*args)

    def rule(self, *args, **kwargs):
        pass


_console_instance: RichConsole | None = None


def get_console(legacy_windows: bool = False) -> RichConsole:
    """
    获取全局唯一的 Console 实例

    参数:
        legacy_windows: 是否启用 Windows 旧版终端模式

    返回:
        RichConsole 或 FallbackConsole 实例
    """
    global _console_instance
    if _console_instance is None:
        if _HAS_RICH:
            _console_instance = RichConsole(legacy_windows=legacy_windows)
        else:
            _console_instance = FallbackConsole()
    return _console_instance