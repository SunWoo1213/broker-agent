"""통합: 시드 내용 · D18 입력 계약 (I19-I24). `docker compose up -d postgres` 필요."""

from __future__ import annotations

import datetime as dt

import pytest
from sqlalchemy import func, select

from control.db.models import Agent, Delegation, Tool, ToolAction
from control.db.seed import AGENT
from control.db.seed import seed_all as _seed_all

pytestmark = pytest.mark.integration

MODELS = {"agents": Agent, "tools": Tool, "tool_actions": ToolAction, "delegations": Delegation}


async def _row_counts(session) -> dict[str, int]:
    counts = {}
    for name, model in MODELS.items():
        result = await session.execute(select(func.count()).select_from(model))
        counts[name] = result.scalar_one()
    return counts


@pytest.mark.asyncio
async def test_seed_is_idempotent(db_session):
    await _seed_all(db_session)
    first = await _row_counts(db_session)
    await _seed_all(db_session)
    second = await _row_counts(db_session)
    assert first == second


@pytest.mark.asyncio
async def test_seed_row_counts_are_exact(db_session):
    counts = await _row_counts(db_session)
    assert counts == {"agents": 1, "tools": 3, "tool_actions": 4, "delegations": 2}


@pytest.mark.asyncio
async def test_seed_rows_satisfy_d18_input_contract(db_session):
    delegations = (await db_session.execute(select(Delegation))).scalars().all()
    actions_by_name = {
        a.name: a for a in (await db_session.execute(select(ToolAction))).scalars().all()
    }

    # (위임 × 그 위임의 모든 scope)를 빠짐없이 만들고, 각 scope가 실제 작업 이름인지
    # 단언한다 — 작업 이름이 아닌 scope를 조용히 건너뛰지 않는다(④ 권고 7).
    combos = []
    for delegation in delegations:
        for scope in delegation.scopes:
            assert scope in actions_by_name, (
                f"delegation {delegation.id!r}의 scope {scope!r}가 어떤 작업 이름과도 "
                "일치하지 않는다"
            )
            combos.append((delegation, actions_by_name[scope]))

    assert combos  # 최소 한 조합은 있어야 한다. 정확한 개수는 I20이 행 수로 고정한다.

    now = dt.datetime.now(dt.timezone.utc)
    for delegation, action in combos:
        contract = {
            "agent": delegation.agent_id,
            "user": delegation.user_id,
            "action": {"name": action.name, "risk": action.risk},
            "delegation": {
                "scopes": delegation.scopes,
                "per_tx_limit": delegation.per_tx_limit,
                "expires_at": delegation.expires_at.isoformat(),
            },
            "args": {},
        }

        assert set(contract.keys()) == {"agent", "user", "action", "delegation", "args"}
        assert set(contract["action"].keys()) == {"name", "risk"}
        assert set(contract["delegation"].keys()) == {"scopes", "per_tx_limit", "expires_at"}

        assert isinstance(contract["agent"], str) and contract["agent"]
        assert isinstance(contract["user"], str) and contract["user"]
        assert isinstance(contract["action"]["name"], str) and contract["action"]["name"]

        assert contract["action"]["risk"] in {"low", "medium", "high"}

        scopes = contract["delegation"]["scopes"]
        assert isinstance(scopes, list)
        assert all(isinstance(s, str) and s for s in scopes)
        assert contract["action"]["name"] in scopes

        per_tx_limit = contract["delegation"]["per_tx_limit"]
        assert isinstance(per_tx_limit, int) and not isinstance(per_tx_limit, bool)
        assert per_tx_limit >= 0

        expires_at = contract["delegation"]["expires_at"]
        assert isinstance(expires_at, str)
        parsed = dt.datetime.fromisoformat(expires_at)
        assert parsed.tzinfo is not None
        assert parsed > now

        assert isinstance(contract["args"], dict)


@pytest.mark.asyncio
async def test_seed_expense_create_is_low_risk_in_db(db_session):
    action = (
        await db_session.execute(select(ToolAction).where(ToolAction.name == "expense.create"))
    ).scalar_one()
    assert action.risk == "low"


@pytest.mark.asyncio
async def test_alice_per_tx_limit_covers_demo_amount(db_session):
    delegation = (
        await db_session.execute(
            select(Delegation).where(Delegation.user_id == "alice@example.com")
        )
    ).scalar_one()
    assert delegation.per_tx_limit >= 180000


@pytest.mark.asyncio
async def test_seed_agent_status_is_suspended_in_db(db_session):
    agent = await db_session.get(Agent, AGENT["id"])
    assert agent.status == "suspended"
