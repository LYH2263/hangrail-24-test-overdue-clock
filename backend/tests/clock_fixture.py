"""独立时钟夹具：测试内冻结或拨动 now，绝不读取机器真实墙钟。

用法::

    def test_xxx(frozen_clock):
        ...  # 此时生产代码读到的 now 为 DEFAULT_FROZEN_NOW
        frozen_clock.advance(timedelta(minutes=1))  # 拨动
        frozen_clock.freeze(datetime(2026, 1, 1))   # 或重新冻结
"""

from __future__ import annotations

from datetime import datetime, timedelta

import pytest

from app.services import clock

# 固定的冻结起点：任意选定的确定时刻，与运行测试的真实墙钟无关。
DEFAULT_FROZEN_NOW = datetime(2026, 9, 24, 10, 0, 0)


class FrozenClock:
    """可冻结、可拨动的测试时钟。"""

    def __init__(self, start: datetime) -> None:
        self._now = start

    @property
    def now(self) -> datetime:
        """当前冻结时刻（只读，拨动请用 freeze/advance）。"""
        return self._now

    def utcnow(self) -> datetime:
        """替换 ``app.services.clock.utcnow`` 的同名实现。"""
        return self._now

    def freeze(self, moment: datetime) -> None:
        """把 now 冻结到指定时刻。"""
        self._now = moment

    def advance(self, delta: timedelta) -> datetime:
        """把 now 向前拨 delta，返回拨动后的时刻。"""
        self._now += delta
        return self._now


@pytest.fixture()
def frozen_clock(monkeypatch: pytest.MonkeyPatch) -> FrozenClock:
    """把生产时间源替换为冻结在 DEFAULT_FROZEN_NOW 的时钟。"""
    frozen = FrozenClock(DEFAULT_FROZEN_NOW)
    monkeypatch.setattr(clock, "utcnow", frozen.utcnow)
    return frozen
