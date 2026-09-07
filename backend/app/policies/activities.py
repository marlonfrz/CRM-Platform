from datetime import datetime, timedelta
from uuid import UUID

from app.models import UserRole
from app.policies.authorization import AuthorizationContext, can_view_activity


def can_correct_activity(
    context: AuthorizationContext,
    *,
    organization_id: UUID,
    department_id: UUID | None,
    author_id: UUID,
    created_at: datetime,
    now: datetime,
    is_client_assigned: bool,
) -> bool:
    return (
        created_at <= now < created_at + timedelta(hours=24)
        and can_view_activity(
            context,
            organization_id=organization_id,
            department_id=department_id,
            is_client_assigned=is_client_assigned,
        )
        and (context.is_owner or context.role is UserRole.ADMIN or context.user_id == author_id)
    )
