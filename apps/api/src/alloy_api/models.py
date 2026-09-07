import uuid
from datetime import UTC, datetime

from sqlalchemy import DateTime, MetaData
from sqlalchemy.ext.asyncio import AsyncAttrs
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

# Named constraints, so later migrations can alter and drop them.
NAMING_CONVENTION = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


class Base(AsyncAttrs, DeclarativeBase):
    """`AsyncAttrs` adds `awaitable_attrs` for loading lazy relationships in async code."""

    metadata = MetaData(naming_convention=NAMING_CONVENTION)


def utcnow() -> datetime:
    return datetime.now(UTC)


class UUIDPrimaryKey:
    """Time-ordered UUIDv7 ids, generated client-side, so they never enumerate."""

    # sort_order: mixin columns would otherwise come after the class's own.
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid7, sort_order=-100)


class Timestamps:
    """Python-side defaults: set on flush, so the values are on the object after commit."""

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, sort_order=100
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow, sort_order=100
    )


# Autogenerate only sees models on `Base.metadata`, so every feature's models are
# imported here. They import `Base` from this module, which is defined above.
from alloy_api.auth import models as _auth_models  # noqa: E402, F401
from alloy_api.crm import models as _crm_models  # noqa: E402, F401
