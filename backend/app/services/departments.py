from uuid import UUID

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Department, DepartmentMember, Organization, OrganizationMode, User
from app.policies.authorization import (
    AuthorizationContext,
    can_manage_department,
    can_manage_organization,
)
from app.services.audit import add_audit_event
from app.services.exceptions import (
    AuthorizationDeniedError,
    IndividualModeViolationError,
    ResourceConflictError,
    ResourceNotFoundError,
)
from app.services.normalization import normalize_name


async def create_department(
    session: AsyncSession, *, organization_id: UUID, name: str
) -> Department:
    organization = await session.get(Organization, organization_id)
    if organization is None:
        raise ResourceNotFoundError("Organization not found")
    if organization.mode is OrganizationMode.INDIVIDUAL:
        raise IndividualModeViolationError("Individual organizations cannot have departments")

    display_name = normalize_name(name)
    department = Department(
        organization_id=organization_id,
        name=display_name,
        normalized_name=display_name.casefold(),
    )
    session.add(department)
    await session.flush()
    return department


async def add_department_member(
    session: AsyncSession,
    *,
    organization_id: UUID,
    department_id: UUID,
    user_id: UUID,
) -> DepartmentMember:
    organization = await session.get(Organization, organization_id)
    if organization is None:
        raise ResourceNotFoundError("Organization not found")
    if organization.mode is OrganizationMode.INDIVIDUAL:
        raise IndividualModeViolationError("Individual organizations cannot have memberships")

    department = await session.scalar(
        select(Department).where(
            Department.id == department_id,
            Department.organization_id == organization_id,
        )
    )
    user = await session.scalar(
        select(User).where(User.id == user_id, User.organization_id == organization_id)
    )
    if department is None or user is None:
        raise ResourceNotFoundError("Department or user not found in the organization")

    membership = DepartmentMember(
        organization_id=organization_id,
        department_id=department_id,
        user_id=user_id,
    )
    session.add(membership)
    await session.flush()
    return membership


async def list_departments(
    session: AsyncSession, *, authorization: AuthorizationContext
) -> list[Department]:
    statement = select(Department).where(
        Department.organization_id == authorization.organization_id
    )
    if not authorization.is_owner:
        statement = statement.where(Department.id.in_(authorization.department_ids))
    return list(await session.scalars(statement.order_by(Department.name)))


async def create_authorized_department(
    session: AsyncSession, *, authorization: AuthorizationContext, name: str
) -> Department:
    if not can_manage_organization(authorization, authorization.organization_id):
        raise AuthorizationDeniedError("Department creation is not allowed")
    await _ensure_department_name_available(
        session, authorization.organization_id, normalize_name(name).casefold()
    )
    department = await create_department(
        session, organization_id=authorization.organization_id, name=name
    )
    add_audit_event(
        session,
        organization_id=authorization.organization_id,
        actor_user_id=authorization.user_id,
        action="CREATED_DEPARTMENT",
        entity_type="DEPARTMENT",
        entity_id=department.id,
        event_data={"name": department.name},
    )
    return department


async def update_department(
    session: AsyncSession,
    *,
    authorization: AuthorizationContext,
    department_id: UUID,
    name: str,
) -> Department:
    department = await _authorized_department(session, authorization, department_id)
    normalized_name = normalize_name(name)
    await _ensure_department_name_available(
        session,
        authorization.organization_id,
        normalized_name.casefold(),
        excluding_department_id=department.id,
    )
    previous_name = department.name
    department.name = normalized_name
    department.normalized_name = department.name.casefold()
    add_audit_event(
        session,
        organization_id=authorization.organization_id,
        actor_user_id=authorization.user_id,
        action="UPDATED_DEPARTMENT",
        entity_type="DEPARTMENT",
        entity_id=department.id,
        event_data={"previous_name": previous_name, "name": department.name},
    )
    await session.flush()
    return department


async def delete_department(
    session: AsyncSession,
    *,
    authorization: AuthorizationContext,
    department_id: UUID,
) -> None:
    department = await _authorized_department(session, authorization, department_id)
    add_audit_event(
        session,
        organization_id=authorization.organization_id,
        actor_user_id=authorization.user_id,
        action="DELETED_DEPARTMENT",
        entity_type="DEPARTMENT",
        entity_id=department.id,
        event_data={"name": department.name},
    )
    await session.execute(delete(Department).where(Department.id == department.id))


async def _authorized_department(
    session: AsyncSession,
    authorization: AuthorizationContext,
    department_id: UUID,
) -> Department:
    department = await session.scalar(
        select(Department).where(
            Department.id == department_id,
            Department.organization_id == authorization.organization_id,
        )
    )
    if department is None:
        raise ResourceNotFoundError("Department not found")
    if not can_manage_department(
        authorization,
        organization_id=department.organization_id,
        department_id=department.id,
    ):
        raise AuthorizationDeniedError("Department management is not allowed")
    return department


async def _ensure_department_name_available(
    session: AsyncSession,
    organization_id: UUID,
    normalized_name: str,
    *,
    excluding_department_id: UUID | None = None,
) -> None:
    statement = select(Department.id).where(
        Department.organization_id == organization_id,
        Department.normalized_name == normalized_name,
    )
    if excluding_department_id is not None:
        statement = statement.where(Department.id != excluding_department_id)
    if await session.scalar(statement) is not None:
        raise ResourceConflictError("A department with this name already exists")
