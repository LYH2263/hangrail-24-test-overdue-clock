"""断言辅助：逾期扫描 / 取件交叉场景的共用断言。

测例文件只编排场景；所有重复的状态与占位断言集中在本文件。
"""

from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.models import RailPlacement, WorkOrder


def assert_status(db: Session, order_id: int, expected: str) -> None:
    """断言工单当前状态。"""
    order = db.get(WorkOrder, order_id)
    assert order is not None, f"工单 {order_id} 不存在"
    assert order.status == expected, f"工单 {order_id} 状态应为 {expected!r}，实际 {order.status!r}"


def assert_marked_tickets(scan_response, expected: set[str]) -> None:
    """断言逾期扫描响应成功，且被标逾期的取件码集合与预期一致。"""
    assert scan_response.status_code == 200, f"扫描应成功，实际 {scan_response.status_code}: {scan_response.text}"
    got = {item["ticket_code"] for item in scan_response.json()}
    assert got == expected, f"扫描标记集合应为 {expected}，实际 {got}"


def assert_pickup_response(pickup_response, *, ticket_code: str, status: str) -> None:
    """断言取件响应成功，且返回的票据与状态符合预期。"""
    assert pickup_response.status_code == 200, f"取件应成功，实际 {pickup_response.status_code}: {pickup_response.text}"
    body = pickup_response.json()
    assert body["ticket_code"] == ticket_code, f"取件票据应为 {ticket_code}，实际 {body['ticket_code']}"
    assert body["status"] == status, f"取件后状态应为 {status!r}，实际 {body['status']!r}"


def assert_placement(db: Session, order_id: int, *, active: int) -> None:
    """断言工单存在占位记录，且 active 标志全部符合预期。"""
    rows = db.scalars(select(RailPlacement).where(RailPlacement.order_id == order_id)).all()
    assert rows, f"工单 {order_id} 应存在占位记录"
    states = [p.active for p in rows]
    assert all(a == active for a in states), f"工单 {order_id} 占位 active 应全为 {active}，实际 {states}"


def assert_no_placement(db: Session, order_id: int) -> None:
    """断言工单不存在任何占位记录。"""
    total = db.scalar(select(func.count()).select_from(RailPlacement).where(RailPlacement.order_id == order_id))
    assert total == 0, f"工单 {order_id} 不应存在占位记录，实际 {total} 条"
