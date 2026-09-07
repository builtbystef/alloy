"""ORM models.

Every model must be importable from this module: Alembic autogenerate reads
`Base.metadata`, and only models that have been imported are registered on it.
"""

from sqlalchemy import MetaData
from sqlalchemy.ext.asyncio import AsyncAttrs
from sqlalchemy.orm import DeclarativeBase

# Deterministic constraint and index names, so Alembic can drop and alter them
# by name in later migrations.
NAMING_CONVENTION = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


class Base(AsyncAttrs, DeclarativeBase):
    """Declarative base for all models.

    `AsyncAttrs` adds `awaitable_attrs`, for loading lazy relationships without
    implicit IO: `await user.awaitable_attrs.posts`.
    """

    metadata = MetaData(naming_convention=NAMING_CONVENTION)
