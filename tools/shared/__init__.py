"""tools 内部共享模块：路径/版本常量与跨脚本复用的辅助函数。

本包不提供 CLI 入口；各分类子目录下的脚本通过 tools 根路径引导后
``from shared.config import ...`` / ``from shared.utils import ...`` 引用。
"""
