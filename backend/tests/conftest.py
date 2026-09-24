"""测试基础设施：内存 SQLite + 依赖覆盖的 TestClient。

时钟夹具在 clock_fixture.py，这里仅引入注册。
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base, get_db
from app.main import app
from tests.clock_fixture import frozen_clock  # noqa: F401  # 注册为 pytest fixture


@pytest.fixture()
def db_engine():
    # StaticPool + 内存 SQLite：整个用例共享同一连接，建表后数据可见；
    # 每个用例独立引擎，互不污染，也不依赖外部 Postgres。
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    yield engine
    engine.dispose()


@pytest.fixture()
def db_session(db_engine):
    session = sessionmaker(bind=db_engine, autoflush=False, expire_on_commit=True)()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture()
def client(db_session):
    # 与用例共用同一条会话：避免内存库单连接上的事务互踩；
    # 接口内的 commit 对用例立即可见。
    def _override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = _override_get_db
    try:
        # 不进入 lifespan：避免触碰真实数据库与种子数据。
        yield TestClient(app)
    finally:
        app.dependency_overrides.clear()
