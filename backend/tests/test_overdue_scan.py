"""逾期扫描 × 取件交叉路径测例。

本文件只编排场景：时钟走 clock_fixture（冻结/拨动 now），
布置与动作走 scenario_helpers，断言走 assertion_helpers。
逾期/取件业务语义以现网为准（due_at < now 才逾期，严格小于），
本文件不重新定义、也不试探修改该语义。
"""

from datetime import timedelta

from tests.assertion_helpers import (
    assert_hung_at,
    assert_no_placement,
    assert_order_status,
    assert_placement_active,
    assert_placement_snapshot,
    assert_scan_tickets,
    placement_snapshot,
)
from tests.scenario_helpers import (
    given_order,
    given_placement,
    given_store_with_rail,
    hang_via_api,
    pickup_via_api,
    scan_overdue_via_api,
)

ONE_MINUTE = timedelta(minutes=1)
ONE_SECOND = timedelta(seconds=1)


def test_hung_order_just_past_due_is_marked_overdue(client, db_session, frozen_clock):
    """刚好到期的 hung 工单：时钟刚拨过 due_at，扫描即标逾期，占位不动。"""
    _, rail = given_store_with_rail(db_session)
    order = given_order(
        db_session,
        store_id=rail.store_id,
        ticket_code="HR-T1",
        status="hung",
        due_at=frozen_clock.now,
    )
    given_placement(db_session, rail_id=rail.id, order_id=order.id)
    before = placement_snapshot(db_session)

    frozen_clock.advance(ONE_SECOND)  # 刚好越过到期时刻
    marked = scan_overdue_via_api(client)

    assert_scan_tickets(marked, ["HR-T1"])
    assert_order_status(db_session, "HR-T1", "overdue")
    assert_placement_snapshot(db_session, before)


def test_hung_order_one_minute_short_of_due_is_not_marked(client, db_session, frozen_clock):
    """差一分钟未到期的 hung 工单：扫描不得误标，状态与占位保持原样。"""
    _, rail = given_store_with_rail(db_session)
    order = given_order(
        db_session,
        store_id=rail.store_id,
        ticket_code="HR-T2",
        status="hung",
        due_at=frozen_clock.now + ONE_MINUTE,
    )
    given_placement(db_session, rail_id=rail.id, order_id=order.id)
    before = placement_snapshot(db_session)

    marked = scan_overdue_via_api(client)

    assert_scan_tickets(marked, [])
    assert_order_status(db_session, "HR-T2", "hung")
    assert_placement_snapshot(db_session, before)


def test_scan_after_pickup_has_no_side_effect_on_picked(client, db_session, frozen_clock):
    """取件释放后再扫描：已 picked 票不被标逾期、不改占位、不进扫描结果。"""
    _, rail = given_store_with_rail(db_session)
    picked = given_order(
        db_session,
        store_id=rail.store_id,
        ticket_code="HR-T3",
        status="ready",
        due_at=frozen_clock.now + ONE_MINUTE,
    )
    survivor = given_order(
        db_session,
        store_id=rail.store_id,
        ticket_code="HR-T3B",
        status="hung",
        due_at=frozen_clock.now + ONE_MINUTE,
    )
    given_placement(db_session, rail_id=rail.id, order_id=survivor.id, start_cm=40.0, end_cm=80.0)

    hang_via_api(client, picked.id)  # 上杆，hung_at 取自冻结时钟
    assert_order_status(db_session, "HR-T3", "hung")
    hung_at = frozen_clock.now
    pickup_via_api(client, "HR-T3")  # 取件，释放占位
    assert_order_status(db_session, "HR-T3", "picked")
    assert_placement_active(db_session, picked.id, 0)

    frozen_clock.advance(2 * ONE_MINUTE)  # 拨过两票的到期时刻
    before = placement_snapshot(db_session)
    marked = scan_overdue_via_api(client)

    # 扫描确实运行（仍在杆上的 HR-T3B 被标记），但对 picked 票零副作用
    assert_scan_tickets(marked, ["HR-T3B"])
    assert_order_status(db_session, "HR-T3", "picked")
    assert_hung_at(db_session, "HR-T3", hung_at)
    assert_placement_active(db_session, picked.id, 0)
    assert_placement_snapshot(db_session, before)


def test_ready_order_past_due_scan_only_changes_status(client, db_session, frozen_clock):
    """仅 ready 且到期的票：扫描只改状态，不产生也不触碰任何占位。"""
    _, rail = given_store_with_rail(db_session)
    ready_overdue = given_order(
        db_session,
        store_id=rail.store_id,
        ticket_code="HR-T4",
        status="ready",
        due_at=frozen_clock.now - ONE_MINUTE,
    )
    given_order(
        db_session,
        store_id=rail.store_id,
        ticket_code="HR-T4B",
        status="ready",
        due_at=frozen_clock.now + ONE_MINUTE,
    )
    bystander = given_order(
        db_session,
        store_id=rail.store_id,
        ticket_code="HR-T4C",
        status="hung",
        due_at=frozen_clock.now + ONE_MINUTE,
    )
    given_placement(db_session, rail_id=rail.id, order_id=bystander.id)
    before = placement_snapshot(db_session)

    marked = scan_overdue_via_api(client)

    assert_scan_tickets(marked, ["HR-T4"])
    assert_order_status(db_session, "HR-T4", "overdue")
    assert_order_status(db_session, "HR-T4B", "ready")
    assert_no_placement(db_session, ready_overdue.id)  # ready 票始终无占位
    assert_placement_snapshot(db_session, before)  # 旁观占位也不受影响


def test_hung_order_due_exactly_at_now_is_not_marked(client, db_session, frozen_clock):
    """边界锁定：due_at == now 不算逾期（现网为严格小于比较，方向冻结）。"""
    _, rail = given_store_with_rail(db_session)
    order = given_order(
        db_session,
        store_id=rail.store_id,
        ticket_code="HR-T5",
        status="hung",
        due_at=frozen_clock.now,
    )
    given_placement(db_session, rail_id=rail.id, order_id=order.id)

    marked = scan_overdue_via_api(client)

    assert_scan_tickets(marked, [])
    assert_order_status(db_session, "HR-T5", "hung")
