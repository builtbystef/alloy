from pathlib import Path

from alembic import command
from alembic.config import Config
from pydantic import PostgresDsn
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Connection, make_url
from sqlalchemy.ext.asyncio import AsyncEngine
from sqlalchemy.pool import NullPool

from alloy_server.config import Settings

API_ROOT = Path(__file__).resolve().parents[1]
EVAL_DATABASE = "alloy_evals"


def use_eval_database() -> Settings:
    """The configured settings (environment or `.env`), pointed at `alloy_evals`
    on the same server, which is created if it is not there yet. Mirrors what the
    tests do with `alloy_test`, kept separate so a test run cannot interfere with
    an eval run."""
    configured = Settings()
    url = make_url(str(configured.database_url))
    # CREATE DATABASE cannot run inside a transaction, hence autocommit.
    engine = create_engine(url, isolation_level="AUTOCOMMIT", poolclass=NullPool)
    try:
        with engine.connect() as connection:
            exists = connection.execute(
                text("SELECT 1 FROM pg_database WHERE datname = :name"), {"name": EVAL_DATABASE}
            ).scalar()
            if not exists:
                connection.execute(text(f'CREATE DATABASE "{EVAL_DATABASE}"'))
    finally:
        engine.dispose()
    eval_url = url.set(database=EVAL_DATABASE).render_as_string(hide_password=False)
    return configured.model_copy(update={"database_url": PostgresDsn(eval_url)})


def _upgrade(connection: Connection) -> None:
    config = Config(file_=API_ROOT / "alembic.ini", toml_file=API_ROOT / "pyproject.toml")
    # env.py migrates on this connection instead of opening its own.
    config.attributes["connection"] = connection
    command.upgrade(config, "head")


async def migrate(engine: AsyncEngine) -> None:
    async with engine.begin() as connection:
        await connection.run_sync(_upgrade)
