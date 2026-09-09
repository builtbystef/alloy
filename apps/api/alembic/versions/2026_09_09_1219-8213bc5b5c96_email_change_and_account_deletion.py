"""email change and account deletion

Revision ID: 8213bc5b5c96
Revises: 61f8d12280ad
Create Date: 2026-09-09 12:19:48.953479
"""

from typing import TYPE_CHECKING

import sqlalchemy as sa
from alembic import op

if TYPE_CHECKING:
    from collections.abc import Sequence

revision: str = "8213bc5b5c96"
down_revision: str | Sequence[str] | None = "61f8d12280ad"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("users", sa.Column("pending_email", sa.String(length=320), nullable=True))
    op.add_column(
        "users", sa.Column("email_change_token_hash", sa.String(length=64), nullable=True)
    )
    op.add_column(
        "users", sa.Column("email_change_sent_at", sa.DateTime(timezone=True), nullable=True)
    )
    op.add_column("users", sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True))
    op.create_unique_constraint(
        op.f("uq_users_email_change_token_hash"), "users", ["email_change_token_hash"]
    )


def downgrade() -> None:
    op.drop_constraint(op.f("uq_users_email_change_token_hash"), "users", type_="unique")
    op.drop_column("users", "deleted_at")
    op.drop_column("users", "email_change_sent_at")
    op.drop_column("users", "email_change_token_hash")
    op.drop_column("users", "pending_email")
