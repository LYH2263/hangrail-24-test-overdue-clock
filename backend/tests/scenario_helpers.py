"""场景布置与动作辅助：建数据、调接口，供测例编排。"""

from __future__ import annotations

from datetime import datetime

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.models import HangRail, RailPlacement, Store, WorkOrder


def given_store_with_rail(session: Session, *, rail_length_cm: float = 200.0) -> tuple[Store, HangRail]:
    store = Store(name="测试门店")
    session.add(store)
    session.flush()
    rail = HangRail(store_id=store.id, label="T 杆", length_cm=rail_length_cm)
    session.add(rail)
    session.commit()
    return store, rail


def given_order(
    session: Session,
    *,
    store_id: int,
    ticket_code: str,
    status: str,
    due_at: datetime,
    length_cm: float = 40.0,
) -> WorkOrder:
    order = WorkOrder(
        store_id=store_id,
        ticket_code=ticket_code,
        garment_name="测试衣物",
        length_cm=length_cm,
        status=status,
        due_at=due_at,
    )
    session.add(order)
    session.commit()
    return order


def given_placement(
    session: Session,
    *,
    rail_id: int,
    order_id: int,
    start_cm: float = 0.0,
    end_cm: float = 40.0,
    active: int = 1,
) -> RailPlacement:
    placement = RailPlacement(
        rail_id=rail_id, order_id=order_id, start_cm=start_cm, end_cm=end_cm, active=active
    )
    session.add(placement)
    session.commit()
    return placement


def hang_via_api(client: TestClient, order_id: int) -> dict:
    resp = client.post("/api/hang", json={"order_id": order_id})
    assert resp.status_code == 200, resp.text
    return resp.json()


def pickup_via_api(client: TestClient, ticket_code: str) -> dict:
    resp = client.post("/api/pickup", json={"ticket_code": ticket_code})
    assert resp.status_code == 200, resp.text
    return resp.json()


def scan_overdue_via_api(client: TestClient) -> list[dict]:
    resp = client.post("/api/overdue/scan")
    assert resp.status_code == 200, resp.text
    return resp.json()
