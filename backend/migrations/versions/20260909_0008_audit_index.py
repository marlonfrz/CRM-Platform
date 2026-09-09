"""Index authorized audit pagination."""

from alembic import op

revision = "20260909_0008"
down_revision = "20260907_0007"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_index(
        "ix_audit_logs_organization_created_id",
        "audit_logs",
        ["organization_id", "created_at", "id"],
    )


def downgrade() -> None:
    op.drop_index("ix_audit_logs_organization_created_id", table_name="audit_logs")
