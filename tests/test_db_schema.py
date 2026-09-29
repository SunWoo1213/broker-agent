"""통합: 제약 · 마이그레이션 (I1-I18). `docker compose up -d postgres` 필요.

행 삽입 도우미는 NOT NULL 컬럼 값을 전부 명시한다. 기본값을 확인하는 I5 · I6만
일부러 생략한다. 제약 위반은 `pytest.raises(IntegrityError, match=...)`로 잡고
예외 메시지에서 제약 이름(또는 위반한 컬럼 이름)을 함께 확인한다.
"""

from __future__ import annotations

import datetime as dt

import pytest
from sqlalchemy.exc import IntegrityError

from control.db.models import Agent, Delegation, ToolAction
from tests import dbsupport

pytestmark = pytest.mark.integration

FUTURE = dt.datetime(2030, 1, 1, tzinfo=dt.timezone.utc)


def _tool_action(**overrides) -> ToolAction:
    kw = dict(tool_id="expense", name="test.action", risk="low", args_schema={})
    kw.update(overrides)
    return ToolAction(**kw)


def _delegation(**overrides) -> Delegation:
    kw = dict(
        id="test-delegation-default",
        user_id="tester@example.com",
        agent_id="agent-expense-01",
        scopes=["expense.list"],
        per_tx_limit=0,
        daily_limit=0,
        expires_at=FUTURE,
        revoked_at=None,
        version=1,
    )
    kw.update(overrides)
    return Delegation(**kw)


def _agent(**overrides) -> Agent:
    kw = dict(id="test-agent-default", name="Test Agent", public_key="a" * 64, status="active")
    kw.update(overrides)
    return Agent(**kw)


@pytest.mark.asyncio
async def test_risk_outside_enum_rejected(db_session):
    db_session.add(_tool_action(name="test.riskoutside", risk="critical"))
    with pytest.raises(IntegrityError, match="ck_tool_actions_risk_enum"):
        await db_session.flush()


@pytest.mark.asyncio
async def test_risk_null_rejected(db_session):
    db_session.add(ToolAction(tool_id="expense", name="test.risknull", args_schema={}))
    with pytest.raises(IntegrityError, match="risk"):
        await db_session.flush()


@pytest.mark.asyncio
async def test_per_tx_limit_negative_rejected(db_session):
    db_session.add(_delegation(id="test-per-tx-negative", per_tx_limit=-1))
    with pytest.raises(IntegrityError, match="ck_delegations_per_tx_limit_nonneg"):
        await db_session.flush()


@pytest.mark.asyncio
async def test_per_tx_limit_zero_allowed(db_session):
    db_session.add(_delegation(id="test-per-tx-zero", per_tx_limit=0))
    await db_session.flush()


@pytest.mark.asyncio
async def test_per_tx_limit_defaults_to_zero(db_session):
    d = Delegation(
        id="test-per-tx-default",
        user_id="tester2@example.com",
        agent_id="agent-expense-01",
        scopes=["expense.list"],
        expires_at=FUTURE,
    )
    db_session.add(d)
    await db_session.flush()
    assert d.per_tx_limit == 0


@pytest.mark.asyncio
async def test_agent_status_defaults_to_suspended(db_session):
    a = Agent(id="test-agent-status-default", name="Test", public_key="b" * 64)
    db_session.add(a)
    await db_session.flush()
    assert a.status == "suspended"


@pytest.mark.asyncio
async def test_agent_status_outside_enum_rejected(db_session):
    db_session.add(_agent(id="test-agent-status-bad", status="enabled"))
    with pytest.raises(IntegrityError, match="ck_agents_status_enum"):
        await db_session.flush()


@pytest.mark.asyncio
async def test_public_key_format_rejected(db_session):
    db_session.add(_agent(id="test-agent-bad-key", public_key="not-a-valid-hex-key"))
    with pytest.raises(IntegrityError, match="ck_agents_public_key_hex64"):
        await db_session.flush()


@pytest.mark.asyncio
async def test_action_name_without_dot_rejected(db_session):
    db_session.add(_tool_action(name="expensecreate"))
    with pytest.raises(IntegrityError, match="ck_tool_actions_name_dotted"):
        await db_session.flush()


@pytest.mark.asyncio
async def test_duplicate_action_name_rejected(db_session):
    db_session.add(_tool_action(name="test.duplicate"))
    await db_session.flush()
    db_session.add(_tool_action(name="test.duplicate"))
    with pytest.raises(IntegrityError, match="uq_tool_actions_name"):
        await db_session.flush()


@pytest.mark.asyncio
async def test_scopes_reject_empty_element(db_session):
    db_session.add(_delegation(id="test-scope-empty", scopes=[""]))
    with pytest.raises(IntegrityError, match="ck_delegations_scopes_no_empty"):
        await db_session.flush()


@pytest.mark.asyncio
async def test_scopes_reject_null_element(db_session):
    db_session.add(_delegation(id="test-scope-null", scopes=["expense.list", None]))
    with pytest.raises(IntegrityError, match="ck_delegations_scopes_no_null"):
        await db_session.flush()


@pytest.mark.asyncio
async def test_delegation_requires_existing_agent(db_session):
    db_session.add(_delegation(id="test-no-agent", agent_id="does-not-exist"))
    with pytest.raises(IntegrityError, match="delegations_agent_id_fkey"):
        await db_session.flush()


@pytest.mark.asyncio
async def test_expires_at_null_rejected(db_session):
    d = Delegation(
        id="test-no-expiry",
        user_id="tester3@example.com",
        agent_id="agent-expense-01",
        scopes=["expense.list"],
    )
    db_session.add(d)
    with pytest.raises(IntegrityError, match="expires_at"):
        await db_session.flush()


@pytest.mark.asyncio
async def test_timestamptz_keeps_offset(db_session):
    tz = dt.timezone(dt.timedelta(hours=9))
    expires = dt.datetime(2027, 12, 31, 23, 59, 59, tzinfo=tz)
    d = _delegation(id="test-tz-offset", expires_at=expires)
    db_session.add(d)
    await db_session.flush()
    await db_session.refresh(d)
    assert d.expires_at.tzinfo is not None
    assert d.expires_at.astimezone(dt.timezone.utc) == expires.astimezone(dt.timezone.utc)


def test_downgrade_then_upgrade_restores_tables(migration_db_url):
    expected = {"agents", "tools", "tool_actions", "delegations"}
    dbsupport.downgrade_base(migration_db_url)
    after_down = dbsupport.public_table_names(migration_db_url)
    assert not (expected & after_down)
    dbsupport.upgrade_head(migration_db_url)
    after_up = dbsupport.public_table_names(migration_db_url)
    assert expected <= after_up


def test_alembic_check_reports_no_diff(integration_db_url):
    dbsupport.alembic_check(integration_db_url)


def test_public_tables_are_exactly_expected(integration_db_url):
    tables = dbsupport.public_table_names(integration_db_url)
    assert tables == {"agents", "tools", "tool_actions", "delegations", "alembic_version"}


# I25-I27: ④ 구현 검증 지적 2 — A4에서 거부 테스트가 없던 제약 3개를 채운다.
# (daily_limit >= 0, version >= 1, tool_actions.tool_id -> tools.id FK)


@pytest.mark.asyncio
async def test_daily_limit_negative_rejected(db_session):
    db_session.add(_delegation(id="test-daily-limit-negative", daily_limit=-1))
    with pytest.raises(IntegrityError, match="ck_delegations_daily_limit_nonneg"):
        await db_session.flush()


@pytest.mark.asyncio
async def test_version_below_one_rejected(db_session):
    db_session.add(_delegation(id="test-version-below-one", version=0))
    with pytest.raises(IntegrityError, match="ck_delegations_version_min"):
        await db_session.flush()


@pytest.mark.asyncio
async def test_tool_action_requires_existing_tool(db_session):
    db_session.add(_tool_action(name="test.notool", tool_id="does-not-exist"))
    with pytest.raises(IntegrityError, match="tool_actions_tool_id_fkey"):
        await db_session.flush()
