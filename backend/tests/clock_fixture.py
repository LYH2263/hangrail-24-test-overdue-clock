"""独立时钟夹具：测例专用，可冻结或拨动“现在”。

生产代码经 ``app.services.clock.get_clock`` 读取当前时刻；
本夹具通过 FastAPI 依赖覆盖替换该时间源（见 conftest.py），
因此测例完全不依赖机器真实墙钟。
"""

from __future__ import annotations

from datetime import datetime, timedelta

from app.services.clock import Clock

# 夹具默认冻结的基准时刻（naive UTC，与生产存储语义一致）。
BASE_NOW = datetime(2026, 9, 25, 9, 0, 0)


class FakeClock(Clock):
    """测试时钟：now 固定在被冻结的时刻，仅在被显式拨动时前进。"""

    def __init__(self, initial: datetime = BASE_NOW) -> None:
        self._now = initial

    def now(self) -> datetime:
        return self._now

    def freeze(self, moment: datetime) -> None:
        """把“现在”冻结到指定时刻。"""
        self._now = moment

    def advance(self, **kwargs) -> None:
        """把“现在”向前拨动给定步长（参数同 timedelta）。"""
        self._now += timedelta(**kwargs)
