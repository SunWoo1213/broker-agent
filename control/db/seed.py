"""1차 데이터 모델 시드 (D21, 원칙 7 — 고정값, 난수 · `now()` 기반 값 없음).

`seed_all(session)`은 **이 모듈 상수만** 읽어 행을 만들고 커밋하지 않는다
(커밋은 이 파일의 `main()`과 테스트 세션 픽스처가 한다). 멱등이다: 시드 에이전트가
이미 있으면 아무것도 하지 않는다.

만료 시각(`2027-12-31T23:59:59+09:00`)이 지나면 `test_seed_rows_satisfy_d18_input_contract`가
조용히 통과하지 않고 실패한다. 의도된 알람이다(원칙 7).
"""

from __future__ import annotations

import asyncio
import datetime as dt

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from control.db.models import Agent, Delegation, Tool, ToolAction

EXPIRES_AT = dt.datetime.fromisoformat("2027-12-31T23:59:59+09:00")

AGENT: dict = {
    "id": "agent-expense-01",
    "name": "경비 정산 데모 에이전트",
    "public_key": "d75a980182b10ab7d54bfed3c964073a0ee172f3daa62325af021a68f707511a",
    "status": "suspended",
}

TOOLS: list[dict] = [
    {"id": "expense", "name": "경비 처리 도구", "base_url": "http://localhost:9001", "owner_team": "finance"},
    {"id": "mail", "name": "메일 발송 도구", "base_url": "http://localhost:9002", "owner_team": "it"},
    {"id": "crm", "name": "고객 조회 도구", "base_url": "http://localhost:9003", "owner_team": "sales"},
]

TOOL_ACTIONS: list[dict] = [
    {
        "tool_id": "expense",
        "name": "expense.create",
        "risk": "low",
        "args_schema": {
            "type": "object",
            "properties": {
                "amount": {"type": "integer", "minimum": 1},
                "memo": {"type": "string"},
            },
            "required": ["amount"],
            "additionalProperties": False,
        },
    },
    {
        "tool_id": "expense",
        "name": "expense.list",
        "risk": "low",
        "args_schema": {
            "type": "object",
            "properties": {"month": {"type": "string"}},
            "required": [],
            "additionalProperties": False,
        },
    },
    {
        "tool_id": "mail",
        "name": "mail.send",
        "risk": "medium",
        "args_schema": {
            "type": "object",
            "properties": {
                "to": {"type": "array", "items": {"type": "string"}, "minItems": 1},
                "subject": {"type": "string"},
                "body": {"type": "string"},
            },
            "required": ["to", "subject", "body"],
            "additionalProperties": False,
        },
    },
    {
        "tool_id": "crm",
        "name": "customer.lookup",
        "risk": "high",
        "args_schema": {
            "type": "object",
            "properties": {"customer_id": {"type": "string"}},
            "required": ["customer_id"],
            "additionalProperties": False,
        },
    },
]

# 순서 고정: [0] alice, [1] bob (변이 j · m이 마지막 원소 bob만 바꾼다)
DELEGATIONS: list[dict] = [
    {
        "id": "delegation-alice-01",
        "user_id": "alice@example.com",
        "agent_id": "agent-expense-01",
        "scopes": ["expense.create", "expense.list"],
        "per_tx_limit": 200000,
        "daily_limit": 500000,
        "expires_at": EXPIRES_AT,
        "revoked_at": None,
        "version": 1,
    },
    {
        "id": "delegation-bob-01",
        "user_id": "bob@example.com",
        "agent_id": "agent-expense-01",
        "scopes": ["expense.list", "mail.send"],
        "per_tx_limit": 0,
        "daily_limit": 0,
        "expires_at": EXPIRES_AT,
        "revoked_at": None,
        "version": 1,
    },
]


async def seed_all(session: AsyncSession) -> None:
    """고정 시드 행을 만든다. 커밋하지 않는다. 이미 시드됐으면 아무 일도 하지 않는다(멱등)."""
    existing = await session.get(Agent, AGENT["id"])
    if existing is not None:
        return

    session.add(Agent(**AGENT))
    for tool in TOOLS:
        session.add(Tool(**tool))
    await session.flush()  # tool_actions.tool_id FK가 참조할 tools 행을 먼저 반영한다

    for action in TOOL_ACTIONS:
        session.add(ToolAction(**action))
    await session.flush()  # delegations.agent_id FK가 참조할 agents 행은 이미 반영됨

    for delegation in DELEGATIONS:
        session.add(Delegation(**delegation))
    await session.flush()


async def _main_async() -> None:
    from control.db.session import create_engine_from_env

    engine = create_engine_from_env()
    try:
        session_factory = async_sessionmaker(engine, expire_on_commit=False)
        async with session_factory() as session:
            await seed_all(session)
            await session.commit()
    finally:
        await engine.dispose()


def main() -> None:
    asyncio.run(_main_async())


if __name__ == "__main__":
    main()
