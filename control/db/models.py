"""1차 데이터 모델 (D21). 테이블 4개: agents · tools · tool_actions · delegations.

게이트웨이는 이 모델을 읽기 전용으로 import한다. 여기서 스키마를 바꾸면
`control/db/migrations/versions/0001_initial_schema.py`도 같이 바꿔야
`alembic check`(I17)가 차이를 보고하지 않는다.
"""

from __future__ import annotations

import datetime as dt

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import ARRAY, JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class Agent(Base):
    __tablename__ = "agents"

    id: Mapped[str] = mapped_column(Text, primary_key=True)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    public_key: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(Text, nullable=False, server_default=text("'suspended'"))
    created_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )

    __table_args__ = (
        CheckConstraint("public_key ~ '^[0-9a-f]{64}$'", name="ck_agents_public_key_hex64"),
        CheckConstraint("status IN ('active','suspended')", name="ck_agents_status_enum"),
    )


class Tool(Base):
    __tablename__ = "tools"

    id: Mapped[str] = mapped_column(Text, primary_key=True)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    base_url: Mapped[str] = mapped_column(Text, nullable=False)
    owner_team: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )


class ToolAction(Base):
    __tablename__ = "tool_actions"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    tool_id: Mapped[str] = mapped_column(Text, ForeignKey("tools.id"), nullable=False)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    risk: Mapped[str] = mapped_column(Text, nullable=False)
    args_schema: Mapped[dict] = mapped_column(JSONB, nullable=False)
    created_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )

    __table_args__ = (
        CheckConstraint(
            r"name ~ '^[a-z][a-z0-9_]*\.[a-z][a-z0-9_]*$'", name="ck_tool_actions_name_dotted"
        ),
        CheckConstraint("risk IN ('low','medium','high')", name="ck_tool_actions_risk_enum"),
        UniqueConstraint("name", name="uq_tool_actions_name"),
    )


class Delegation(Base):
    __tablename__ = "delegations"

    id: Mapped[str] = mapped_column(Text, primary_key=True)
    user_id: Mapped[str] = mapped_column(Text, nullable=False)
    agent_id: Mapped[str] = mapped_column(Text, ForeignKey("agents.id"), nullable=False)
    scopes: Mapped[list[str]] = mapped_column(
        ARRAY(Text), nullable=False, server_default=text("'{}'")
    )
    per_tx_limit: Mapped[int] = mapped_column(
        BigInteger, nullable=False, server_default=text("0")
    )
    daily_limit: Mapped[int] = mapped_column(
        BigInteger, nullable=False, server_default=text("0")
    )
    expires_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    revoked_at: Mapped[dt.datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    version: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("1"))
    created_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )

    __table_args__ = (
        CheckConstraint("per_tx_limit >= 0", name="ck_delegations_per_tx_limit_nonneg"),
        CheckConstraint("daily_limit >= 0", name="ck_delegations_daily_limit_nonneg"),
        CheckConstraint(
            "array_position(scopes, NULL) IS NULL", name="ck_delegations_scopes_no_null"
        ),
        CheckConstraint("NOT ('' = ANY(scopes))", name="ck_delegations_scopes_no_empty"),
        CheckConstraint("version >= 1", name="ck_delegations_version_min"),
        Index("ix_delegations_user_agent", "user_id", "agent_id"),
    )
