"""단위: DB 설정 · fail-closed (U1-U12). 서비스 불필요, 마커 없음."""

from __future__ import annotations

import asyncio
import socket
import sys
from pathlib import Path

import pytest
from alembic.config import Config
from alembic.script import ScriptDirectory

from control.db import eventloop
from control.db.session import (
    _connect_args,
    _validate_driver,
    create_engine,
    db_ping,
    get_database_url,
    redact_url,
)
from tests import dbsupport

ROOT = Path(__file__).resolve().parents[1]


def test_database_url_missing_raises(monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    with pytest.raises(RuntimeError):
        get_database_url()


def test_database_url_blank_raises(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "   ")
    with pytest.raises(RuntimeError):
        get_database_url()


def test_database_url_must_use_psycopg_driver():
    # _validate_driver()를 직접 호출해, SQLAlchemy 자체의 부수적인 오류(비동기 드라이버
    # 요구 · asyncpg 미설치)와 섞이지 않고 이 프로젝트의 드라이버 검사만 시험한다.
    # RuntimeError로 좁혀서 무관한 오류(NameError 등)로도 통과하지 않게 한다(④ 권고 6).
    with pytest.raises(RuntimeError):
        _validate_driver("postgresql://broker:broker@localhost:5434/broker")
    with pytest.raises(RuntimeError):
        _validate_driver("postgresql+asyncpg://broker:broker@localhost:5434/broker")
    _validate_driver("postgresql+psycopg://broker:broker@localhost:5434/broker")  # 통과, 예외 없음

    engine = create_engine("postgresql+psycopg://broker:broker@localhost:5434/broker")
    assert engine is not None


def test_engine_error_message_hides_password():
    redacted = redact_url("postgresql+psycopg://broker:s3cr3t@localhost:5434/broker")
    assert "s3cr3t" not in redacted
    assert "***" in redacted
    assert "localhost" in redacted
    assert "broker" in redacted

    with pytest.raises(RuntimeError) as excinfo:
        create_engine("postgresql+psycopg://broker:s3cr3t@localhost:notaport/broker")
    assert "s3cr3t" not in str(excinfo.value)


def test_connect_timeout_is_configured():
    args = _connect_args()
    assert "connect_timeout" in args
    assert 1 <= args["connect_timeout"] <= 5


@pytest.mark.asyncio
async def test_db_ping_returns_false_on_closed_port():
    result = await db_ping("postgresql+psycopg://broker:broker@127.0.0.1:1/broker")
    assert result is False


@pytest.mark.asyncio
async def test_db_ping_times_out_on_silent_server():
    srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    srv.bind(("127.0.0.1", 0))
    srv.listen(1)
    host, port = srv.getsockname()
    url = f"postgresql+psycopg://broker:broker@{host}:{port}/broker"
    try:
        result = await asyncio.wait_for(db_ping(url, connect_timeout=1), timeout=3)
    finally:
        srv.close()
    assert result is False


def test_needs_selector_policy_by_platform():
    assert eventloop.needs_selector_policy("win32") is True
    assert eventloop.needs_selector_policy("darwin") is False
    assert eventloop.needs_selector_policy("linux") is False


def test_event_loop_policy_on_current_platform():
    cls = eventloop.event_loop_policy_class()
    if sys.platform == "win32":
        assert cls.__name__ == "WindowsSelectorEventLoopPolicy"
    else:
        assert cls is type(asyncio.get_event_loop_policy())


def test_alembic_ini_has_script_location_and_no_url():
    import re

    text = (ROOT / "alembic.ini").read_text(encoding="utf-8")
    assert re.search(r"(?m)^script_location[ \t]*=[ \t]*control/db/migrations[ \t]*$", text)
    m = re.search(r"(?m)^sqlalchemy\.url[ \t]*=[ \t]*(.*?)[ \t]*$", text)
    assert m is not None
    assert m.group(1) == ""


def test_migrations_have_exactly_one_head():
    cfg = Config(str(ROOT / "alembic.ini"))
    script = ScriptDirectory.from_config(cfg)
    heads = script.get_heads()
    assert len(heads) == 1


def test_reset_refuses_non_test_database():
    # 가드가 없으면 실제로 연결을 시도하게 되므로, 보호 대상(개발용 broker)의 실제 주소를
    # 쓰지 않는다. 닫힌 포트(127.0.0.1:1) + 테스트용이 아닌 DB 이름을 함께 써서, 가드가
    # 있으면 연결 전에 ValueError로 거부되고(정상), 가드가 없으면 연결 자체가 거부돼
    # OperationalError가 나 여전히 이 단언은 실패한다(red) — 어느 쪽이든 실제 DB에 닿지
    # 않는다(④ 지적 1).
    with pytest.raises(ValueError):
        dbsupport.reset_schema(
            "postgresql+psycopg://broker:broker@127.0.0.1:1/broker_do_not_touch"
        )
