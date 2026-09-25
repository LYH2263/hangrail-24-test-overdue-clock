"""可替换时间源：业务代码读取当前时刻的唯一入口。

生产环境使用系统时钟（naive UTC，与既有存储语义一致）；
测例通过 FastAPI 依赖覆盖注入假时钟，从而冻结或拨动“现在”，
无需触碰机器真实墙钟。
"""

from __future__ import annotations

from datetime import datetime


class Clock:
    """默认系统时钟。"""

    def now(self) -> datetime:
        return datetime.utcnow()


def get_clock() -> Clock:
    """FastAPI 依赖：提供时间源。测例可覆盖此依赖注入假时钟。"""
    return Clock()
