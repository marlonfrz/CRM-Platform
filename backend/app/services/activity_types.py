from uuid import UUID

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import ActivityType, UserRole
from app.policies.authorization import AuthorizationContext
from app.schemas.activities import ActivityTypeOption
from app.services.exceptions import (
    AuthorizationDeniedError,
    ResourceConflictError,
    ResourceNotFoundError,
)
from app.services.normalization import normalize_name


async def list_activity_types(
    session: AsyncSession,
    authorization: AuthorizationContext,
) -> list[ActivityType]:
    statement = select(ActivityType).where(
        ActivityType.organization_id == authorization.organization_id,
        ActivityType.is_active.is_(True),
    )
    if not authorization.is_owner:
        statement = statement.where(
            or_(
                ActivityType.department_id.is_(None),
                ActivityType.department_id.in_(authorization.department_ids),
            )
        )
    return list(
        await session.scalars(
            statement.order_by(
                ActivityType.department_id.asc().nulls_first(), ActivityType.name, ActivityType.id
            )
        )
    )


async def require_activity_type(
    session: AsyncSession,
    authorization: AuthorizationContext,
    activity_type_id: UUID,
    department_id: UUID | None,
) -> ActivityType:
    activity_type = await session.scalar(
        select(ActivityType).where(
            ActivityType.id == activity_type_id,
            ActivityType.organization_id == authorization.organization_id,
            ActivityType.is_active.is_(True),
        )
    )
    if activity_type is None:
        raise ResourceNotFoundError("Activity type not found")
    if activity_type.department_id is not None and activity_type.department_id != department_id:
        raise AuthorizationDeniedError("Activity type is outside the selected department")
    return activity_type


async def create_activity_type(
    session: AsyncSession,
    *,
    authorization: AuthorizationContext,
    name: str,
    department_id: UUID | None,
) -> ActivityTypeOption:
    if authorization.role is UserRole.EMPLOYEE:
        raise AuthorizationDeniedError("Activity type management is not allowed")
    if authorization.role is UserRole.ADMIN and (
        department_id is None or department_id not in authorization.department_ids
    ):
        raise AuthorizationDeniedError("Administrators can manage their department types")
    normalized = normalize_name(name)
    existing = await session.scalar(
        select(ActivityType.id).where(
            ActivityType.organization_id == authorization.organization_id,
            ActivityType.department_id == department_id,
            ActivityType.normalized_name == normalized.casefold(),
        )
    )
    if existing is not None:
        raise ResourceConflictError("An activity type with this name already exists")
    activity_type = ActivityType(
        organization_id=authorization.organization_id,
        department_id=department_id,
        name=normalized,
        normalized_name=normalized.casefold(),
        is_active=True,
    )
    session.add(activity_type)
    await session.flush()
    return ActivityTypeOption(
        id=activity_type.id,
        name=activity_type.name,
        department_id=activity_type.department_id,
    )
