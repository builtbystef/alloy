"""tasks link to a contact or a company

A contact task's company is the contact's, so the row no longer stores both.

Revision ID: 6b57756e0c34
Revises: 22643acfb969
Create Date: 2026-09-13 16:45:49.223670
"""

from typing import TYPE_CHECKING

from alembic import op

if TYPE_CHECKING:
    from collections.abc import Sequence

revision: str = "6b57756e0c34"
down_revision: str | Sequence[str] | None = "22643acfb969"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("UPDATE tasks SET company_id = NULL WHERE contact_id IS NOT NULL")
    op.create_check_constraint("one_link", "tasks", "contact_id IS NULL OR company_id IS NULL")


def downgrade() -> None:
    op.drop_constraint(op.f("ck_tasks_one_link"), "tasks", type_="check")
