"""可替换时间源。

生产代码一律通过 ``clock.utcnow()`` 读取当前时刻，不直接调用
``datetime.utcnow()``。测试用 monkeypatch 替换本模块的 ``utcnow``
即可冻结或拨动时间，业务代码本身保持不变。
"""

from __future__ import annotations

from datetime import datetime


def utcnow() -> datetime:
    """当前 UTC 时刻（naive，与库内既有数据口径一致）。"""
    return datetime.utcnow()
