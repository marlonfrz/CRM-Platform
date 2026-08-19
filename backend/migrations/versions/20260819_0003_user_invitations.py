"""Add user invitations.

Revision ID: 20260819_0003
Revises: 20260819_0002
Create Date: 2026-08-19
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260819_0003"
down_revision: str | None = "20260819_0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "user_invitations",
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("token_hash", sa.String(length=64), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("accepted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("id", sa.Uuid(), nullable=False),
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
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["organization_id", "user_id"],
            ["users.organization_id", "users.id"],
            name="fk_user_invitations_user",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_user_invitations")),
        sa.UniqueConstraint("token_hash", name="uq_user_invitations_token_hash"),
    )


def downgrade() -> None:
    op.drop_table("user_invitations")
