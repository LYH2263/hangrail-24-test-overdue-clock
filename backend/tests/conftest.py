"""pytest 装配：内存数据库、假时钟与 HTTP 客户端的依赖覆盖接线。

- 每个测例使用独立的 SQLite 内存库，不触碰真实数据库；
- 时钟经 ``get_clock`` 依赖覆盖替换为 FakeClock，测例不读机器墙钟；
- TestClient 不进入上下文管理器，避免触发 lifespan（其会连接真实库并种子化）。
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base, get_db
from app.main import app
from app.models.models import HangRail, RailPlacement, Store, WorkOrder
from app.services.clock import get_clock
from tests.clock_fixture import BASE_NOW, FakeClock


@pytest.fixture()
def db_session():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    session_factory = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = session_factory()
    try:
        yield session
    finally:
        session.close()
        engine.dispose()


@pytest.fixture()
def clock() -> FakeClock:
    """假时钟：默认冻结在 BASE_NOW，测例内可再冻结或拨动。"""
    return FakeClock(BASE_NOW)


@pytest.fixture()
def client(db_session, clock):
    def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_clock] = lambda: clock
    try:
        yield TestClient(app)
    finally:
        app.dependency_overrides.clear()


@pytest.fixture()
def make_order(db_session):
    """场景数据工厂：创建工单，可选同时在挂杆上放置占位。"""

    def _make(*, ticket_code: str, status: str, due_at, on_rail: bool = False) -> WorkOrder:
        store = db_session.scalar(select(Store).limit(1))
        if store is None:
            store = Store(name="测试门店")
            db_session.add(store)
            db_session.flush()
        order = WorkOrder(
            store_id=store.id,
            ticket_code=ticket_code,
            garment_name="测试衣物",
            length_cm=40,
            status=status,
            due_at=due_at,
            hung_at=due_at if status == "hung" else None,
        )
        db_session.add(order)
        db_session.flush()
        if on_rail:
            rail = db_session.scalar(select(HangRail).limit(1))
            if rail is None:
                rail = HangRail(store_id=store.id, label="测试杆", length_cm=200)
                db_session.add(rail)
                db_session.flush()
            db_session.add(
                RailPlacement(rail_id=rail.id, order_id=order.id, start_cm=0, end_cm=order.length_cm)
            )
        db_session.commit()
        return order

    return _make
