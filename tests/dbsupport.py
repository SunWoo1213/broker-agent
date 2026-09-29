"""테스트 전용 DB 도우미. 전부 동기 함수다.

async 테스트 안에서 부르면 `asyncio.run()` 중첩 오류가 난다 — 반드시 동기 픽스처
(또는 `conftest.py`가 만드는 별도 이벤트 루프)에서만 부른다.

운영 코드(`control/db/session.py`)는 기본 접속 URL을 갖지 않는다(U1 · U2). 이 파일의
`DEFAULT_LOCAL_DATABASE_URL`은 테스트에서만 쓰는 개발용 기본값이고, `env.example`의
값과 같다(비밀이 아니다).
"""

from __future__ import annotations

import os
from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine as create_sync_engine
from sqlalchemy import text
from sqlalchemy.engine import make_url

ROOT = Path(__file__).resolve().parents[1]
ALEMBIC_INI = ROOT / "alembic.ini"

# = env.example의 개발용 값. 비밀 아님. 운영 코드에는 이 상수가 없다.
DEFAULT_LOCAL_DATABASE_URL = "postgresql+psycopg://broker:broker@localhost:5434/broker"

_TEST_DB_SUFFIXES = ("_test", "_test_mig")


def _base_url() -> str:
    return os.environ.get("DATABASE_URL") or DEFAULT_LOCAL_DATABASE_URL


def test_database_url(db_name: str = "broker_test") -> str:
    """`_base_url()`의 DB 이름만 `db_name`으로 바꾼 URL.

    `str(URL)`은 기본적으로 비밀번호를 "***"로 가리므로(SQLAlchemy 기본 동작) 여기서는
    `render_as_string(hide_password=False)`를 써서 실제 접속에 쓸 수 있는 URL을 돌려준다.
    """
    return make_url(_base_url()).set(database=db_name).render_as_string(hide_password=False)


def _require_test_db_name(db_name: str) -> None:
    if not db_name.endswith(_TEST_DB_SUFFIXES):
        raise ValueError(
            f"refusing to touch non-test database: {db_name!r} "
            f"(이름이 {_TEST_DB_SUFFIXES} 로 끝나야 한다)"
        )


def ensure_database(db_name: str) -> None:
    """`db_name` 데이터베이스가 없으면 만든다. 개발용 DB는 건드리지 않는다."""
    _require_test_db_name(db_name)
    admin_url = _base_url()
    engine = create_sync_engine(admin_url, isolation_level="AUTOCOMMIT")
    try:
        with engine.connect() as conn:
            exists = conn.execute(
                text("SELECT 1 FROM pg_database WHERE datname = :name"), {"name": db_name}
            ).scalar()
            if not exists:
                conn.execute(text(f'CREATE DATABASE "{db_name}"'))
    finally:
        engine.dispose()


def reset_schema(url: str) -> None:
    """`public` 스키마를 지우고 새로 만든다. DB 이름이 테스트용이 아니면 거부한다."""
    db_name = make_url(url).database or ""
    _require_test_db_name(db_name)
    engine = create_sync_engine(url)
    try:
        with engine.begin() as conn:
            conn.execute(text("DROP SCHEMA public CASCADE"))
            conn.execute(text("CREATE SCHEMA public"))
    finally:
        engine.dispose()


def _alembic_config(url: str) -> Config:
    cfg = Config(str(ALEMBIC_INI))
    cfg.set_main_option("sqlalchemy.url", url)
    return cfg


def upgrade_head(url: str) -> None:
    command.upgrade(_alembic_config(url), "head")


def downgrade_base(url: str) -> None:
    command.downgrade(_alembic_config(url), "base")


def alembic_check(url: str) -> None:
    """`alembic check`와 동등한 API 호출. 차이가 있으면 예외가 난다."""
    command.check(_alembic_config(url))


def public_table_names(url: str) -> set[str]:
    engine = create_sync_engine(url)
    try:
        with engine.connect() as conn:
            rows = conn.execute(
                text(
                    "SELECT tablename FROM pg_tables WHERE schemaname = 'public'"
                )
            )
            return {r[0] for r in rows}
    finally:
        engine.dispose()
