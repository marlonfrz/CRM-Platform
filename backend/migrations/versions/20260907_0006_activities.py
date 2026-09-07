"""Add client activities.

Revision ID: 20260907_0006
Revises: 20260907_0005
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260907_0006"
down_revision: str | None = "20260907_0005"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "activities",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("client_id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("department_id", sa.Uuid(), nullable=True),
        sa.Column("type", sa.String(20), nullable=False),
        sa.Column("description", sa.String(5000), nullable=False),
        sa.Column("next_action", sa.String(2000), nullable=True),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
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
        sa.PrimaryKeyConstraint("id", name=op.f("pk_activities")),
        sa.ForeignKeyConstraint(
            ["organization_id", "client_id"],
            ["clients.organization_id", "clients.id"],
            name="fk_activities_client",
        ),
        sa.ForeignKeyConstraint(
            ["organization_id", "user_id"],
            ["users.organization_id", "users.id"],
            name="fk_activities_user",
        ),
        sa.ForeignKeyConstraint(
            ["organization_id", "department_id"],
            ["departments.organization_id", "departments.id"],
            name="fk_activities_department",
        ),
        sa.CheckConstraint(
            "type IN ('CALL', 'EMAIL', 'MEETING', 'NOTE', 'INCIDENT', 'OTHER')",
            name=op.f("ck_activities_activity_type"),
        ),
        sa.CheckConstraint(
            "length(trim(description)) > 0", name=op.f("ck_activities_activity_description")
        ),
    )
    op.create_index(
        "ix_activities_client_date",
        "activities",
        ["organization_id", "client_id", "occurred_at", "id"],
    )
    op.create_index("ix_activities_department", "activities", ["organization_id", "department_id"])


def downgrade() -> None:
    op.drop_table("activities")
