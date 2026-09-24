"""断言辅助：工单状态、占位与扫描结果的核验。"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.models import RailPlacement, WorkOrder


def get_order(session: Session, ticket_code: str) -> WorkOrder:
    session.expire_all()  # 绕过会话缓存，读库内最新提交
    order = session.scalar(select(WorkOrder).where(WorkOrder.ticket_code == ticket_code))
    assert order is not None, f"工单不存在: {ticket_code}"
    return order


def assert_order_status(session: Session, ticket_code: str, expected_status: str) -> None:
    order = get_order(session, ticket_code)
    assert order.status == expected_status, (
        f"{ticket_code} 状态应为 {expected_status}，实际 {order.status}"
    )


def assert_hung_at(session: Session, ticket_code: str, expected: datetime | None) -> None:
    order = get_order(session, ticket_code)
    assert order.hung_at == expected, (
        f"{ticket_code} hung_at 应为 {expected}，实际 {order.hung_at}"
    )


def assert_placement_active(session: Session, order_id: int, expected_active: int) -> None:
    session.expire_all()
    rows = session.scalars(
        select(RailPlacement).where(RailPlacement.order_id == order_id)
    ).all()
    assert rows, f"工单 {order_id} 无占位记录"
    assert all(p.active == expected_active for p in rows), (
        f"工单 {order_id} 占位 active 应全为 {expected_active}，"
        f"实际 {[p.active for p in rows]}"
    )


def assert_no_placement(session: Session, order_id: int) -> None:
    session.expire_all()
    rows = session.scalars(
        select(RailPlacement).where(RailPlacement.order_id == order_id)
    ).all()
    assert rows == [], f"工单 {order_id} 不应有占位记录，实际 {len(rows)} 条"


def placement_snapshot(session: Session) -> dict[int, tuple[int, float, float]]:
    """占位表快照 {order_id: (active, start_cm, end_cm)}，用于副作用对比。"""
    session.expire_all()
    rows = session.scalars(select(RailPlacement)).all()
    return {row.order_id: (row.active, row.start_cm, row.end_cm) for row in rows}


def assert_placement_snapshot(session: Session, expected: dict[int, tuple[int, float, float]]) -> None:
    actual = placement_snapshot(session)
    assert actual == expected, f"占位表发生变化：\n之前 {expected}\n之后 {actual}"


def assert_scan_tickets(marked: list[dict], expected_ticket_codes: list[str]) -> None:
    actual = sorted(o["ticket_code"] for o in marked)
    assert actual == sorted(expected_ticket_codes), (
        f"扫描标记集合应为 {sorted(expected_ticket_codes)}，实际 {actual}"
    )
