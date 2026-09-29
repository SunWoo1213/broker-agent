"""통합 테스트 공용 픽스처. 단위 테스트는 이 파일의 DB 픽스처에 의존하지 않는다.

세션 픽스처는 **autouse가 아니다** — 자동 실행되면 단위 테스트만 고른 실행(명령 A)에서도
DB 초기화가 걸려, 마이그레이션이 깨진 변이(r 등)가 단위 테스트까지 무너뜨린다.
"""

from __future__ import annotations

import asyncio

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import async_sessionmaker

from control.db import eventloop
from control.db.seed import seed_all
from control.db.session import create_engine as create_db_engine

from tests import dbsupport


@pytest.fixture(scope="session")
def event_loop_policy():
    """D20: 윈도우에서만 Selector 정책. 맥 · 리눅스는 현재 기본 정책 그대로."""
    return eventloop.event_loop_policy()


def _prepare_and_seed(db_name: str) -> str:
    """스키마를 초기화하고 head까지 마이그레이션한 뒤 시드한다. 동기 함수."""
    url = dbsupport.test_database_url(db_name)
    dbsupport.ensure_database(db_name)
    dbsupport.reset_schema(url)
    dbsupport.upgrade_head(url)

    async def _seed() -> None:
        engine = create_db_engine(url)
        try:
            session_factory = async_sessionmaker(engine, expire_on_commit=False)
            async with session_factory() as session:
                await seed_all(session)
                await session.commit()
        finally:
            await engine.dispose()

    # D20: 이 함수는 pytest-asyncio가 세션 이벤트 루프 정책을 바꿔 두기 전에(즉 동기
    # 픽스처 맥락에서) 호출될 수 있다. 전역 정책에 기대는 대신 `loop_factory`로 직접
    # Selector 루프를 지정해, 실행 순서와 무관하게 윈도우에서 psycopg 비동기가 항상
    # 동작하게 한다(④ 권고 5). 맥 · 리눅스는 `needs_selector_policy()`가 False라
    # `loop_factory=None`(기본 동작) 그대로다.
    loop_factory = asyncio.SelectorEventLoop if eventloop.needs_selector_policy() else None
    asyncio.run(_seed(), loop_factory=loop_factory)
    return url


@pytest.fixture(scope="session")
def integration_db_url() -> str:
    """`broker_test`를 세션에 한 번만 초기화 · 마이그레이션 · 시드한다."""
    return _prepare_and_seed("broker_test")


@pytest_asyncio.fixture
async def db_session(integration_db_url):
    """함수 픽스처: 바깥 트랜잭션을 열고 테스트가 끝나면 롤백한다."""
    engine = create_db_engine(integration_db_url)
    try:
        async with engine.connect() as conn:
            trans = await conn.begin()
            session_factory = async_sessionmaker(
                bind=conn, expire_on_commit=False, join_transaction_mode="create_savepoint"
            )
            async with session_factory() as session:
                yield session
            await trans.rollback()
    finally:
        await engine.dispose()


@pytest.fixture
def migration_db_url() -> str:
    """I16 전용: `broker_test_mig`를 매 테스트마다 초기화 · 마이그레이션한다(시드 없음)."""
    db_name = "broker_test_mig"
    url = dbsupport.test_database_url(db_name)
    dbsupport.ensure_database(db_name)
    dbsupport.reset_schema(url)
    dbsupport.upgrade_head(url)
    return url
