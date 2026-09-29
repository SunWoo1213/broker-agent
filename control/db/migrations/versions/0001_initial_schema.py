"""1차 데이터 모델: agents · tools · tool_actions · delegations (D21)

Revision ID: 0001_initial_schema
Revises:
Create Date: 2026-09-29

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import ARRAY, JSONB

# revision identifiers, used by Alembic.
revision: str = "0001_initial_schema"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "agents",
        sa.Column("id", sa.Text(), primary_key=True),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("public_key", sa.Text(), nullable=False),
        sa.Column(
            "status", sa.Text(), nullable=False, server_default=sa.text("'suspended'")
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.CheckConstraint(
            "public_key ~ '^[0-9a-f]{64}$'", name="ck_agents_public_key_hex64"
        ),
        sa.CheckConstraint("status IN ('active','suspended')", name="ck_agents_status_enum"),
    )

    op.create_table(
        "tools",
        sa.Column("id", sa.Text(), primary_key=True),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("base_url", sa.Text(), nullable=False),
        sa.Column("owner_team", sa.Text(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )

    op.create_table(
        "tool_actions",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("tool_id", sa.Text(), sa.ForeignKey("tools.id"), nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("risk", sa.Text(), nullable=False),
        sa.Column("args_schema", JSONB(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.CheckConstraint(
            r"name ~ '^[a-z][a-z0-9_]*\.[a-z][a-z0-9_]*$'",
            name="ck_tool_actions_name_dotted",
        ),
        sa.CheckConstraint("risk IN ('low','medium','high')", name="ck_tool_actions_risk_enum"),
        sa.UniqueConstraint("name", name="uq_tool_actions_name"),
    )

    op.create_table(
        "delegations",
        sa.Column("id", sa.Text(), primary_key=True),
        sa.Column("user_id", sa.Text(), nullable=False),
        sa.Column("agent_id", sa.Text(), sa.ForeignKey("agents.id"), nullable=False),
        sa.Column(
            "scopes", ARRAY(sa.Text()), nullable=False, server_default=sa.text("'{}'")
        ),
        sa.Column(
            "per_tx_limit", sa.BigInteger(), nullable=False, server_default=sa.text("0")
        ),
        sa.Column(
            "daily_limit", sa.BigInteger(), nullable=False, server_default=sa.text("0")
        ),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("version", sa.Integer(), nullable=False, server_default=sa.text("1")),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.CheckConstraint("per_tx_limit >= 0", name="ck_delegations_per_tx_limit_nonneg"),
        sa.CheckConstraint("daily_limit >= 0", name="ck_delegations_daily_limit_nonneg"),
        sa.CheckConstraint(
            "array_position(scopes, NULL) IS NULL", name="ck_delegations_scopes_no_null"
        ),
        sa.CheckConstraint("NOT ('' = ANY(scopes))", name="ck_delegations_scopes_no_empty"),
        sa.CheckConstraint("version >= 1", name="ck_delegations_version_min"),
    )
    op.create_index(
        "ix_delegations_user_agent", "delegations", ["user_id", "agent_id"]
    )


def downgrade() -> None:
    op.drop_table("delegations")
    op.drop_table("tool_actions")
    op.drop_table("tools")
    op.drop_table("agents")
