from uuid import UUID

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models import ClientAssignment, OrganizationMode, User, UserRole, UserStatus
from app.policies.authorization import AuthorizationContext
from app.schemas.tasks import TaskCandidate, TaskDepartment, TaskOptions
from app.services.departments import list_departments


async def activity_options(
    session: AsyncSession,
    authorization: AuthorizationContext,
    client_id: UUID,
) -> TaskOptions:
    departments = await list_departments(session, authorization=authorization)
    allowed_ids = {department.id for department in departments}
    individual = authorization.organization_mode is OrganizationMode.INDIVIDUAL
    statement = (
        select(User)
        .options(selectinload(User.department_memberships))
        .where(
            User.organization_id == authorization.organization_id,
            User.status == UserStatus.ACTIVE,
            or_(
                User.role.in_([UserRole.OWNER, UserRole.ADMIN]),
                select(ClientAssignment.id)
                .where(
                    ClientAssignment.organization_id == authorization.organization_id,
                    ClientAssignment.client_id == client_id,
                    ClientAssignment.user_id == User.id,
                )
                .exists(),
            ),
        )
    )
    if individual or authorization.role is UserRole.EMPLOYEE:
        statement = statement.where(User.id == authorization.user_id)
    elif not authorization.is_owner:
        statement = statement.where(
            or_(User.id == authorization.user_id, User.role == UserRole.EMPLOYEE)
        )
    candidates = []
    for user in await session.scalars(statement.order_by(User.full_name, User.id)):
        ids = (
            allowed_ids
            if user.role is UserRole.OWNER
            else allowed_ids
            & {membership.department_id for membership in user.department_memberships}
        )
        if individual or ids:
            candidates.append(
                TaskCandidate(id=user.id, name=user.full_name, department_ids=sorted(ids))
            )
    return TaskOptions(
        departments=[TaskDepartment(id=item.id, name=item.name) for item in departments],
        candidates=candidates,
        individual=individual,
    )
