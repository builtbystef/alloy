from typing import TYPE_CHECKING

from procrastinate import App, PsycopgConnector
from sqlalchemy.engine import make_url

if TYPE_CHECKING:
    from alloy_server.config import Settings

# Imported by the worker before it starts, so every task is registered. The API
# imports the ones it queues.
TASK_MODULES = [
    "alloy_server.jobs.emails",
    "alloy_server.jobs.imports",
    "alloy_server.jobs.purge",
    "alloy_server.jobs.stalled",
]


def conninfo(settings: Settings) -> str:
    """The database URL for psycopg itself: no SQLAlchemy driver in the scheme."""
    url = make_url(str(settings.database_url)).set(drivername="postgresql")
    return url.render_as_string(hide_password=False)


def create_app(settings: Settings) -> App:
    return App(
        connector=PsycopgConnector(
            conninfo=conninfo(settings), min_size=1, max_size=settings.database_pool_size
        ),
        import_paths=TASK_MODULES,
        # A job that succeeded is dropped from the table; one that failed stays
        # to be looked at (`procrastinate shell`) until the purge job removes it.
        worker_defaults={"delete_jobs": "successful"},
    )


__all__ = ["TASK_MODULES", "conninfo", "create_app"]
