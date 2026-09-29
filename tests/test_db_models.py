"""단위: 모델 메타데이터 (U13-U15). 서비스 불필요."""

from __future__ import annotations

from sqlalchemy import DateTime

from control.db.models import Base


def _all_columns():
    for table in Base.metadata.tables.values():
        for column in table.columns:
            yield table.name, column


def test_all_datetime_columns_are_timezone_aware():
    offenders = [
        f"{table}.{col.name}"
        for table, col in _all_columns()
        if isinstance(col.type, DateTime) and col.type.timezone is not True
    ]
    assert offenders == []


def test_fail_closed_column_defaults():
    agents = Base.metadata.tables["agents"]
    delegations = Base.metadata.tables["delegations"]

    status = agents.c.status
    assert status.server_default is not None
    assert status.server_default.arg.text == "'suspended'"

    per_tx_limit = delegations.c.per_tx_limit
    assert per_tx_limit.nullable is False
    assert per_tx_limit.server_default is not None
    assert per_tx_limit.server_default.arg.text == "0"

    daily_limit = delegations.c.daily_limit
    assert daily_limit.nullable is False
    assert daily_limit.server_default is not None
    assert daily_limit.server_default.arg.text == "0"

    scopes = delegations.c.scopes
    assert scopes.nullable is False
    assert scopes.server_default is not None
    assert scopes.server_default.arg.text == "'{}'"

    version = delegations.c.version
    assert version.server_default is not None
    assert version.server_default.arg.text == "1"


def test_model_tables_are_exactly_the_four():
    assert set(Base.metadata.tables.keys()) == {"agents", "tools", "tool_actions", "delegations"}
