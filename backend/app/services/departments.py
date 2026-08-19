from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Department, DepartmentMember, Organization, OrganizationMode, User
from app.services.exceptions import IndividualModeViolationError, ResourceNotFoundError
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
