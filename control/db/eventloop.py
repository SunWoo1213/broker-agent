"""D20: DB 접근은 SQLAlchemy asyncio + psycopg 3. Windows 로컬 · pytest는 Selector
이벤트 루프를 쓰고, 맥 · 리눅스는 기본 정책 그대로 둔다(플랫폼 조건부).

psycopg 비동기는 Windows 기본 Proactor 루프에서 동작하지 않는다.
"""

from __future__ import annotations

import asyncio
import sys


def needs_selector_policy(platform: str = sys.platform) -> bool:
    """윈도우에서만 Selector 이벤트 루프 정책이 필요하다."""
    return platform == "win32"


def event_loop_policy_class(platform: str = sys.platform) -> type[asyncio.AbstractEventLoopPolicy]:
    """플랫폼에 맞는 이벤트 루프 정책 클래스.

    윈도우가 아니면 현재 실행 중인 기본 정책의 클래스를 그대로 돌려준다(바꾸지 않는다).
    """
    if needs_selector_policy(platform):
        cls = getattr(asyncio, "WindowsSelectorEventLoopPolicy", None)
        if cls is None:  # pragma: no cover - 윈도우가 아닌 환경에서는 도달하지 않는다
            raise RuntimeError("WindowsSelectorEventLoopPolicy is unavailable on this platform")
        return cls
    return type(asyncio.get_event_loop_policy())


def event_loop_policy(platform: str = sys.platform) -> asyncio.AbstractEventLoopPolicy:
    """conftest.py의 `event_loop_policy` 픽스처가 돌려줄 실제 정책 인스턴스."""
    if needs_selector_policy(platform):
        return event_loop_policy_class(platform)()
    return asyncio.get_event_loop_policy()
