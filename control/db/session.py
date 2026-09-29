"""DB 접속 설정 (원칙 1 fail-closed · 원칙 2 자격 증명 비노출).

`DATABASE_URL` 환경 변수에서만 접속 정보를 읽는다. 기본 URL로 되돌아가지 않는다.
드라이버는 `postgresql+psycopg://`만 허용한다(D20). 모든 연결에 `connect_timeout`을
걸고, 오류 메시지에는 `redact_url()`을 거친 문자열만 남긴다.
"""

from __future__ import annotations

import os
import re

from sqlalchemy import text
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine

REQUIRED_DRIVER_PREFIX = "postgresql+psycopg://"

_PASSWORD_IN_URL = re.compile(r"://([^:@/]+):([^@/]+)@")


def redact_url(url: str) -> str:
    """URL에서 비밀번호를 가리되 호스트 · DB 이름은 남긴다 (순수 함수, 원칙 2)."""
    try:
        parsed = make_url(url)
    except Exception:
        return _PASSWORD_IN_URL.sub(r"://\1:***@", url)
    return str(parsed)  # SQLAlchemy URL.__str__은 기본적으로 비밀번호를 "***"로 가린다


def get_database_url() -> str:
    """`DATABASE_URL`이 없거나 공백이면 예외를 낸다. 기본값으로 되돌아가지 않는다 (원칙 1)."""
    url = os.environ.get("DATABASE_URL")
    if url is None or not url.strip():
        raise RuntimeError("DATABASE_URL is not set")
    return url


def _validate_driver(url: str) -> None:
    if not url.startswith(REQUIRED_DRIVER_PREFIX):
        raise RuntimeError(
            f"DATABASE_URL must use the {REQUIRED_DRIVER_PREFIX} driver ({redact_url(url)})"
        )


def _connect_args(connect_timeout: int = 2) -> dict:
    """모든 DB 연결에 타임아웃을 건다 (원칙 1). 1~5초 범위."""
    return {"connect_timeout": connect_timeout}


def create_engine(url: str, connect_timeout: int = 2) -> AsyncEngine:
    """URL을 직접 받아 async 엔진을 만든다. 드라이버가 다르면 예외."""
    _validate_driver(url)
    try:
        return create_async_engine(url, connect_args=_connect_args(connect_timeout))
    except Exception as exc:
        raise RuntimeError(
            f"failed to create database engine ({redact_url(url)})"
        ) from exc


def create_engine_from_env() -> AsyncEngine:
    """`DATABASE_URL` 환경 변수로 async 엔진을 만든다."""
    return create_engine(get_database_url())


async def db_ping(url: str, connect_timeout: int = 2) -> bool:
    """연결 · 질의에 실패하면 예외를 삼키고 False를 돌려준다. 성공을 꾸며내지 않는다 (원칙 1)."""
    try:
        engine = create_engine(url, connect_timeout=connect_timeout)
    except Exception:
        return False
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        return True
    except Exception:
        return False
    finally:
        await engine.dispose()
