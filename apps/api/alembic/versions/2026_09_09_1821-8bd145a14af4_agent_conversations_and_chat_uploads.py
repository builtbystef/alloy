"""agent conversations and chat uploads

Revision ID: 8bd145a14af4
Revises: ef7301f635b3
Create Date: 2026-09-09 18:21:05.147598
"""

from typing import TYPE_CHECKING

import sqlalchemy as sa
from alembic import op

if TYPE_CHECKING:
    from collections.abc import Sequence

revision: str = "8bd145a14af4"
down_revision: str | Sequence[str] | None = "ef7301f635b3"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "agent_conversations",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("workspace_id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("title", sa.String(length=120), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name=op.f("fk_agent_conversations_user_id_users"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["workspace_id"],
            ["workspaces.id"],
            name=op.f("fk_agent_conversations_workspace_id_workspaces"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_agent_conversations")),
    )
    op.create_index(
        op.f("ix_agent_conversations_user_id"), "agent_conversations", ["user_id"], unique=False
    )
    op.create_index(
        op.f("ix_agent_conversations_workspace_id"),
        "agent_conversations",
        ["workspace_id"],
        unique=False,
    )
    op.create_table(
        "agent_messages",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("conversation_id", sa.Uuid(), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("body", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["conversation_id"],
            ["agent_conversations.id"],
            name=op.f("fk_agent_messages_conversation_id_agent_conversations"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_agent_messages")),
        sa.UniqueConstraint(
            "conversation_id", "position", name=op.f("uq_agent_messages_conversation_id")
        ),
    )
    op.create_index(
        op.f("ix_agent_messages_conversation_id"),
        "agent_messages",
        ["conversation_id"],
        unique=False,
    )
    op.create_table(
        "chat_uploads",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("workspace_id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("conversation_id", sa.Uuid(), nullable=False),
        sa.Column("filename", sa.String(length=255), nullable=False),
        sa.Column("content_type", sa.String(length=255), nullable=False),
        sa.Column("size", sa.BigInteger(), nullable=False),
        sa.Column("key", sa.String(length=512), nullable=False),
        sa.Column("uploaded_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("attachment_id", sa.Uuid(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["attachment_id"],
            ["attachments.id"],
            name=op.f("fk_chat_uploads_attachment_id_attachments"),
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["conversation_id"],
            ["agent_conversations.id"],
            name=op.f("fk_chat_uploads_conversation_id_agent_conversations"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name=op.f("fk_chat_uploads_user_id_users"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["workspace_id"],
            ["workspaces.id"],
            name=op.f("fk_chat_uploads_workspace_id_workspaces"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_chat_uploads")),
        sa.UniqueConstraint("key", name=op.f("uq_chat_uploads_key")),
    )
    op.create_index(
        op.f("ix_chat_uploads_conversation_id"), "chat_uploads", ["conversation_id"], unique=False
    )
    op.create_index(
        op.f("ix_chat_uploads_workspace_id"), "chat_uploads", ["workspace_id"], unique=False
    )
    op.add_column(
        "activities",
        sa.Column(
            "source",
            sa.Enum("agent", "import", name="rowsource", native_enum=False, length=32),
            nullable=True,
        ),
    )
    op.add_column(
        "companies",
        sa.Column(
            "source",
            sa.Enum("agent", "import", name="rowsource", native_enum=False, length=32),
            nullable=True,
        ),
    )
    op.add_column(
        "contacts",
        sa.Column(
            "source",
            sa.Enum("agent", "import", name="rowsource", native_enum=False, length=32),
            nullable=True,
        ),
    )
    op.add_column(
        "tasks",
        sa.Column(
            "source",
            sa.Enum("agent", "import", name="rowsource", native_enum=False, length=32),
            nullable=True,
        ),
    )


def downgrade() -> None:
    op.drop_column("tasks", "source")
    op.drop_column("contacts", "source")
    op.drop_column("companies", "source")
    op.drop_column("activities", "source")
    op.drop_index(op.f("ix_chat_uploads_workspace_id"), table_name="chat_uploads")
    op.drop_index(op.f("ix_chat_uploads_conversation_id"), table_name="chat_uploads")
    op.drop_table("chat_uploads")
    op.drop_index(op.f("ix_agent_messages_conversation_id"), table_name="agent_messages")
    op.drop_table("agent_messages")
    op.drop_index(op.f("ix_agent_conversations_workspace_id"), table_name="agent_conversations")
    op.drop_index(op.f("ix_agent_conversations_user_id"), table_name="agent_conversations")
    op.drop_table("agent_conversations")
