"""The `alloy_evals` database: pointing settings at it, creating it, and
migrating it."""

import os
from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Connection, make_url
from sqlalchemy.ext.asyncio import AsyncEngine
from sqlalchemy.pool import NullPool

from alloy_api.config import Settings, get_settings

API_ROOT = Path(__file__).resolve().parents[1]
EVAL_DATABASE = "alloy_evals"


def use_eval_database() -> Settings:
    """Point `Settings` at `alloy_evals` on the configured server, creating the
    database if it is not there yet. Mirrors what the tests do with `alloy_test`,
    kept separate so a test run cannot interfere with an eval run."""
    configured = make_url(str(get_settings().database_url))
    os.environ["ALLOY_DATABASE_URL"] = configured.set(database=EVAL_DATABASE).render_as_string(
        hide_password=False
    )
    get_settings.cache_clear()
    # CREATE DATABASE cannot run inside a transaction, hence autocommit.
    engine = create_engine(configured, isolation_level="AUTOCOMMIT", poolclass=NullPool)
    try:
        with engine.connect() as connection:
            exists = connection.execute(
                text("SELECT 1 FROM pg_database WHERE datname = :name"), {"name": EVAL_DATABASE}
            ).scalar()
            if not exists:
                connection.execute(text(f'CREATE DATABASE "{EVAL_DATABASE}"'))
    finally:
        engine.dispose()
    return get_settings()


def _upgrade(connection: Connection) -> None:
    config = Config(file_=API_ROOT / "alembic.ini", toml_file=API_ROOT / "pyproject.toml")
    # env.py migrates on this connection instead of opening its own.
    config.attributes["connection"] = connection
    command.upgrade(config, "head")


async def migrate(engine: AsyncEngine) -> None:
    """Bring the eval database up to the current schema."""
    async with engine.begin() as connection:
        await connection.run_sync(_upgrade)
