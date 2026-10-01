"""Unify activities and tasks.

Revision ID: 20260914_0009
Revises: 20260909_0008
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260914_0009"
down_revision: str | None = "20260909_0008"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("activities", sa.Column("category", sa.String(20), nullable=True))
    op.add_column("activities", sa.Column("title", sa.String(200), nullable=True))
    op.add_column("activities", sa.Column("assigned_to_user_id", sa.Uuid(), nullable=True))
    op.add_column("activities", sa.Column("due_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("activities", sa.Column("status", sa.String(20), nullable=True))
    op.add_column(
        "activities", sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True)
    )
    op.alter_column(
        "activities",
        "occurred_at",
        existing_type=sa.DateTime(timezone=True),
        nullable=True,
    )
    op.execute(
        "UPDATE activities SET category = 'ACTIVITY', assigned_to_user_id = user_id, "
        "status = 'COMPLETED', completed_at = created_at"
    )
    op.execute(
        "CREATE TEMPORARY TABLE task_activity_ids ON COMMIT DROP AS "
        "SELECT tasks.id AS old_id, "
        "CASE WHEN activities.id IS NULL THEN tasks.id ELSE gen_random_uuid() END AS new_id "
        "FROM tasks LEFT JOIN activities ON activities.id = tasks.id"
    )
    op.execute(
        "INSERT INTO activities "
        "(id, organization_id, client_id, user_id, assigned_to_user_id, department_id, "
        "category, type, title, description, next_action, occurred_at, due_at, status, "
        "completed_at, created_at, updated_at) "
        "SELECT ids.new_id, tasks.organization_id, tasks.client_id, tasks.created_by_user_id, "
        "tasks.assigned_to_user_id, tasks.department_id, 'TASK', 'OTHER', tasks.title, "
        "COALESCE(tasks.description, tasks.title), NULL, tasks.completed_at, tasks.due_at, "
        "tasks.status, tasks.completed_at, tasks.created_at, tasks.updated_at "
        "FROM tasks JOIN task_activity_ids AS ids ON ids.old_id = tasks.id"
    )
    op.execute(
        "UPDATE audit_logs SET entity_id = ids.new_id FROM task_activity_ids AS ids "
        "WHERE audit_logs.entity_type = 'TASK' AND audit_logs.entity_id = ids.old_id"
    )
    op.alter_column("activities", "category", existing_type=sa.String(20), nullable=False)
    op.alter_column("activities", "assigned_to_user_id", existing_type=sa.Uuid(), nullable=False)
    op.alter_column("activities", "status", existing_type=sa.String(20), nullable=False)
    op.create_foreign_key(
        "fk_activities_assignee",
        "activities",
        "users",
        ["organization_id", "assigned_to_user_id"],
        ["organization_id", "id"],
    )
    op.create_check_constraint(
        op.f("ck_activities_activity_category"),
        "activities",
        "category IN ('ACTIVITY', 'TASK')",
    )
    op.create_check_constraint(
        op.f("ck_activities_activity_status"),
        "activities",
        "status IN ('PENDING', 'COMPLETED')",
    )
    op.create_check_constraint(
        op.f("ck_activities_activity_completion"),
        "activities",
        "(status = 'PENDING' AND occurred_at IS NULL AND completed_at IS NULL) OR "
        "(status = 'COMPLETED' AND occurred_at IS NOT NULL AND completed_at IS NOT NULL)",
    )
    op.create_index(
        "ix_activities_client_status",
        "activities",
        ["organization_id", "client_id", "status", "due_at"],
    )
    op.create_index(
        "ix_activities_assignee",
        "activities",
        ["organization_id", "assigned_to_user_id", "status", "due_at"],
    )
    op.drop_table("tasks")


def downgrade() -> None:
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
    op.execute(
        "INSERT INTO tasks "
        "(id, organization_id, client_id, assigned_to_user_id, created_by_user_id, "
        "department_id, title, description, due_at, status, completed_at, created_at, updated_at) "
        "SELECT id, organization_id, client_id, assigned_to_user_id, user_id, department_id, "
        "COALESCE(title, description, type), description, due_at, status, completed_at, "
        "created_at, updated_at FROM activities WHERE category = 'TASK'"
    )
    op.create_index(
        "ix_tasks_client",
        "tasks",
        ["organization_id", "client_id", "status", "due_at"],
    )
    op.create_index(
        "ix_tasks_assignee",
        "tasks",
        ["organization_id", "assigned_to_user_id", "status", "due_at"],
    )
    op.create_index("ix_tasks_department", "tasks", ["organization_id", "department_id"])
    op.execute("DELETE FROM activities WHERE category = 'TASK'")
    op.execute(
        "UPDATE activities SET occurred_at = COALESCE(occurred_at, completed_at, created_at)"
    )
    op.drop_index("ix_activities_assignee", table_name="activities")
    op.drop_index("ix_activities_client_status", table_name="activities")
    op.drop_constraint(op.f("ck_activities_activity_completion"), "activities", type_="check")
    op.drop_constraint(op.f("ck_activities_activity_status"), "activities", type_="check")
    op.drop_constraint(op.f("ck_activities_activity_category"), "activities", type_="check")
    op.drop_constraint("fk_activities_assignee", "activities", type_="foreignkey")
    op.alter_column(
        "activities",
        "occurred_at",
        existing_type=sa.DateTime(timezone=True),
        nullable=False,
    )
    op.drop_column("activities", "completed_at")
    op.drop_column("activities", "status")
    op.drop_column("activities", "due_at")
    op.drop_column("activities", "assigned_to_user_id")
    op.drop_column("activities", "title")
    op.drop_column("activities", "category")
