"""Add client assignments.

Revision ID: 20260907_0005
Revises: 20260903_0004
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260907_0005"
down_revision: str | None = "20260903_0004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "client_assignments",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("client_id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("assigned_by_user_id", sa.Uuid(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_client_assignments")),
        sa.ForeignKeyConstraint(
            ["organization_id", "client_id"],
            ["clients.organization_id", "clients.id"],
            name="fk_client_assignments_client",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["organization_id", "user_id"],
            ["users.organization_id", "users.id"],
            name="fk_client_assignments_user",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["organization_id", "assigned_by_user_id"],
            ["users.organization_id", "users.id"],
            name="fk_client_assignments_actor",
        ),
        sa.UniqueConstraint("client_id", "user_id", name="uq_client_assignments_client_user"),
    )
    op.create_index(
        "ix_client_assignments_organization_user",
        "client_assignments",
        ["organization_id", "user_id"],
    )


def downgrade() -> None:
    op.drop_table("client_assignments")
