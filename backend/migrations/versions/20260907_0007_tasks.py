"""Add client tasks.

Revision ID: 20260907_0007
Revises: 20260907_0006
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260907_0007"
down_revision: str | None = "20260907_0006"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "tasks",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("client_id", sa.Uuid(), nullable=False),
        sa.Column("assigned_to_user_id", sa.Uuid(), nullable=False),
        sa.Column("created_by_user_id", sa.Uuid(), nullable=False),
        sa.Column("department_id", sa.Uuid(), nullable=True),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("description", sa.String(5000), nullable=True),
        sa.Column("due_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_tasks")),
        sa.ForeignKeyConstraint(
            ["organization_id", "client_id"],
            ["clients.organization_id", "clients.id"],
            name="fk_tasks_client",
        ),
        sa.ForeignKeyConstraint(
            ["organization_id", "assigned_to_user_id"],
            ["users.organization_id", "users.id"],
            name="fk_tasks_assignee",
        ),
        sa.ForeignKeyConstraint(
            ["organization_id", "created_by_user_id"],
            ["users.organization_id", "users.id"],
            name="fk_tasks_creator",
        ),
        sa.ForeignKeyConstraint(
            ["organization_id", "department_id"],
            ["departments.organization_id", "departments.id"],
            name="fk_tasks_department",
        ),
        sa.CheckConstraint("length(trim(title)) > 0", name=op.f("ck_tasks_task_title")),
        sa.CheckConstraint(
            "(status = 'PENDING' AND completed_at IS NULL) OR "
            "(status = 'COMPLETED' AND completed_at IS NOT NULL)",
            name=op.f("ck_tasks_task_completion"),
        ),
    )
    op.create_index(
        "ix_tasks_client", "tasks", ["organization_id", "client_id", "status", "due_at"]
    )
    op.create_index(
        "ix_tasks_assignee", "tasks", ["organization_id", "assigned_to_user_id", "status", "due_at"]
    )
    op.create_index("ix_tasks_department", "tasks", ["organization_id", "department_id"])


def downgrade() -> None:
    op.drop_table("tasks")
