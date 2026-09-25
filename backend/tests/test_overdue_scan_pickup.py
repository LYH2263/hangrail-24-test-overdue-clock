"""逾期扫描 × 取件交叉路径的时钟可控测例。

本文件只编排场景：时钟夹具见 clock_fixture.py，断言辅助见
assertion_helpers.py，装配见 conftest.py。所有时刻均由 FakeClock
冻结或拨动，不依赖机器真实墙钟；现网到期比较（严格小于）语义冻结。
"""

from datetime import timedelta

from tests.assertion_helpers import (
    assert_marked_tickets,
    assert_no_placement,
    assert_pickup_response,
    assert_placement,
    assert_status,
)
from tests.clock_fixture import BASE_NOW


def test_hung_order_just_past_due_is_marked_overdue(client, clock, db_session, make_order):
    """刚好越过到期时刻的 hung 工单：扫描后标记为逾期。"""
    clock.freeze(BASE_NOW)
    order = make_order(ticket_code="HR-9001", status="hung", due_at=BASE_NOW, on_rail=True)
    clock.advance(minutes=1)  # 刚好越过到期时刻

    resp = client.post("/api/overdue/scan")

    assert_marked_tickets(resp, {"HR-9001"})
    assert_status(db_session, order.id, "overdue")
    assert_placement(db_session, order.id, active=1)  # 扫描只改状态，不释放占位


def test_hung_order_one_minute_before_due_is_not_marked(client, clock, db_session, make_order):
    """差一分钟未到期的 hung 工单：扫描不得误标。"""
    clock.freeze(BASE_NOW)
    order = make_order(
        ticket_code="HR-9002",
        status="hung",
        due_at=BASE_NOW + timedelta(minutes=1),
        on_rail=True,
    )

    resp = client.post("/api/overdue/scan")

    assert_marked_tickets(resp, set())
    assert_status(db_session, order.id, "hung")
    assert_placement(db_session, order.id, active=1)


def test_scan_after_pickup_has_no_side_effect_on_picked_order(client, clock, db_session, make_order):
    """取件释放占位后，再扫描不得对已 picked 票产生任何副作用。"""
    clock.freeze(BASE_NOW)
    order = make_order(
        ticket_code="HR-9003",
        status="hung",
        due_at=BASE_NOW + timedelta(minutes=30),
        on_rail=True,
    )

    pickup_resp = client.post("/api/pickup", json={"ticket_code": "HR-9003"})
    assert_pickup_response(pickup_resp, ticket_code="HR-9003", status="picked")
    assert_placement(db_session, order.id, active=0)  # 取件释放占位

    clock.advance(hours=2)  # 拨过到期时刻后再扫描
    resp = client.post("/api/overdue/scan")

    assert_marked_tickets(resp, set())
    assert_status(db_session, order.id, "picked")  # 已取件票据不受扫描影响
    assert_placement(db_session, order.id, active=0)


def test_ready_order_past_due_only_changes_status_without_touching_placement(
    client, clock, db_session, make_order
):
    """仅 ready 且到期的票：扫描只改状态，不涉及任何占位。"""
    clock.freeze(BASE_NOW)
    ready = make_order(ticket_code="HR-9004", status="ready", due_at=BASE_NOW - timedelta(minutes=1))
    bystander = make_order(
        ticket_code="HR-9005",
        status="hung",
        due_at=BASE_NOW + timedelta(days=1),
        on_rail=True,
    )

    resp = client.post("/api/overdue/scan")

    assert_marked_tickets(resp, {"HR-9004"})
    assert_status(db_session, ready.id, "overdue")
    assert_no_placement(db_session, ready.id)  # ready 票不产生占位
    assert_status(db_session, bystander.id, "hung")
    assert_placement(db_session, bystander.id, active=1)  # 旁证：既有占位不受影响


def test_hung_order_due_exactly_at_now_is_not_marked(client, clock, db_session, make_order):
    """边界锁定：due_at == now 时不标逾期（现网为严格小于比较，方向冻结）。"""
    clock.freeze(BASE_NOW)
    order = make_order(ticket_code="HR-9006", status="hung", due_at=BASE_NOW, on_rail=True)

    resp = client.post("/api/overdue/scan")

    assert_marked_tickets(resp, set())
    assert_status(db_session, order.id, "hung")
