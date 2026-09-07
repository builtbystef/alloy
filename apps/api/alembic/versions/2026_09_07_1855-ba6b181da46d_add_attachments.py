"""add attachments

Revision ID: ba6b181da46d
Revises: c7ce67509d36
Create Date: 2026-09-07 18:55:37.309738
"""

from typing import TYPE_CHECKING

import sqlalchemy as sa
from alembic import op

if TYPE_CHECKING:
    from collections.abc import Sequence

revision: str = "ba6b181da46d"
down_revision: str | Sequence[str] | None = "c7ce67509d36"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "attachments",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("workspace_id", sa.Uuid(), nullable=False),
        sa.Column("contact_id", sa.Uuid(), nullable=True),
        sa.Column("company_id", sa.Uuid(), nullable=True),
        sa.Column("uploaded_by_user_id", sa.Uuid(), nullable=True),
        sa.Column("filename", sa.String(length=255), nullable=False),
        sa.Column("content_type", sa.String(length=255), nullable=False),
        sa.Column("size", sa.BigInteger(), nullable=False),
        sa.Column("key", sa.String(length=512), nullable=False),
        sa.Column("uploaded_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "(contact_id IS NULL) <> (company_id IS NULL)", name=op.f("ck_attachments_one_parent")
        ),
        sa.ForeignKeyConstraint(
            ["company_id"],
            ["companies.id"],
            name=op.f("fk_attachments_company_id_companies"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["contact_id"],
            ["contacts.id"],
            name=op.f("fk_attachments_contact_id_contacts"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["uploaded_by_user_id"],
            ["users.id"],
            name=op.f("fk_attachments_uploaded_by_user_id_users"),
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["workspace_id"],
            ["workspaces.id"],
            name=op.f("fk_attachments_workspace_id_workspaces"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_attachments")),
        sa.UniqueConstraint("key", name=op.f("uq_attachments_key")),
    )
    op.create_index(op.f("ix_attachments_company_id"), "attachments", ["company_id"], unique=False)
    op.create_index(op.f("ix_attachments_contact_id"), "attachments", ["contact_id"], unique=False)
    op.create_index(
        op.f("ix_attachments_workspace_id"), "attachments", ["workspace_id"], unique=False
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_attachments_workspace_id"), table_name="attachments")
    op.drop_index(op.f("ix_attachments_contact_id"), table_name="attachments")
    op.drop_index(op.f("ix_attachments_company_id"), table_name="attachments")
    op.drop_table("attachments")
