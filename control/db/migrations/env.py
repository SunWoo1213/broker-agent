"""Alembic 환경. URL은 config의 main option(alembic -x 또는 Config.set_main_option) →
없으면 `DATABASE_URL` 환경 변수 → 둘 다 없으면 예외(fail-closed). 비밀 · 주소를
`alembic.ini`에 하드코딩하지 않는다(원칙 2).
"""

from __future__ import annotations

import os
from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

from control.db.models import Base

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def _resolve_url() -> str:
    url = config.get_main_option("sqlalchemy.url")
    if url:
        return url
    url = os.environ.get("DATABASE_URL")
    if url:
        return url
    raise RuntimeError(
        "no database URL: set Config main option 'sqlalchemy.url' or DATABASE_URL env var"
    )


def run_migrations_offline() -> None:
    url = _resolve_url()
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    configuration = config.get_section(config.config_ini_section, {})
    configuration["sqlalchemy.url"] = _resolve_url()
    connectable = engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
