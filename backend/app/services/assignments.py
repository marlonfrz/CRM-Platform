from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import (
    Client,
    ClientAssignment,
    DepartmentMember,
    OrganizationMode,
    User,
    UserRole,
    UserStatus,
)
from app.policies.authorization import AuthorizationContext, can_assign_client, can_manage_client
from app.services.audit import add_audit_event
from app.services.exceptions import (
    AuthorizationDeniedError,
    IndividualModeViolationError,
    ResourceConflictError,
    ResourceNotFoundError,
)


def _require_team_access(authorization: AuthorizationContext) -> None:
    if authorization.organization_mode is OrganizationMode.INDIVIDUAL:
        raise IndividualModeViolationError("Individual organizations do not use assignments")
    if not can_manage_client(authorization, organization_id=authorization.organization_id):
        raise AuthorizationDeniedError("Assignment management is not allowed")


async def _client(
    session: AsyncSession,
    authorization: AuthorizationContext,
    client_id: UUID,
    *,
    lock: bool = False,
) -> Client:
    _require_team_access(authorization)
    statement = select(Client).where(
        Client.id == client_id, Client.organization_id == authorization.organization_id
    )
    if lock:
        statement = statement.with_for_update()
    client = await session.scalar(statement)
    if client is None:
        raise ResourceNotFoundError("Client not found")
    return client


async def list_team(
    session: AsyncSession,
    *,
    authorization: AuthorizationContext,
    client_id: UUID,
) -> tuple[list[User], list[User]]:
    await _client(session, authorization, client_id)
    membership = select(DepartmentMember.id).where(
        DepartmentMember.organization_id == authorization.organization_id,
        DepartmentMember.user_id == User.id,
    )
    users = select(User).where(User.organization_id == authorization.organization_id)
    if not authorization.is_owner:
        membership = membership.where(
            DepartmentMember.department_id.in_(authorization.department_ids)
        )
        users = users.where(User.role == UserRole.EMPLOYEE, membership.exists())
    assigned = (
        select(ClientAssignment.id)
        .where(
            ClientAssignment.organization_id == authorization.organization_id,
            ClientAssignment.client_id == client_id,
            ClientAssignment.user_id == User.id,
        )
        .exists()
    )
    assigned_users = list(
        await session.scalars(users.where(assigned).order_by(User.full_name, User.id))
    )
    available_users = list(
        await session.scalars(
            users.where(
                ~assigned,
                User.role == UserRole.EMPLOYEE,
                User.status == UserStatus.ACTIVE,
                membership.exists(),
            ).order_by(User.full_name, User.id)
        )
    )
    return assigned_users, available_users


async def _target(
    session: AsyncSession,
    authorization: AuthorizationContext,
    user_id: UUID,
    *,
    removing: bool,
) -> User:
    user = await session.scalar(
        select(User)
        .where(User.id == user_id, User.organization_id == authorization.organization_id)
        .with_for_update()
    )
    if user is None:
        raise ResourceNotFoundError("User not found")
    departments = frozenset(
        await session.scalars(
            select(DepartmentMember.department_id).where(
                DepartmentMember.organization_id == authorization.organization_id,
                DepartmentMember.user_id == user_id,
            )
        )
    )
    if not can_assign_client(
        authorization,
        organization_id=user.organization_id,
        target_role=user.role,
        target_department_ids=departments,
    ):
        raise AuthorizationDeniedError("Assignment is outside your scope")
    if not removing and (
        user.role is not UserRole.EMPLOYEE
        or user.status is not UserStatus.ACTIVE
        or not departments
    ):
        raise ResourceConflictError("An active employee with a department is required")
    return user


async def assign_client(
    session: AsyncSession,
    *,
    authorization: AuthorizationContext,
    client_id: UUID,
    user_id: UUID,
) -> None:
    await _client(session, authorization, client_id, lock=True)
    await _target(session, authorization, user_id, removing=False)
    existing = await session.scalar(
        select(ClientAssignment.id).where(
            ClientAssignment.organization_id == authorization.organization_id,
            ClientAssignment.client_id == client_id,
            ClientAssignment.user_id == user_id,
        )
    )
    if existing is not None:
        raise ResourceConflictError("User is already assigned")
    assignment = ClientAssignment(
        organization_id=authorization.organization_id,
        client_id=client_id,
        user_id=user_id,
        assigned_by_user_id=authorization.user_id,
    )
    session.add(assignment)
    await session.flush()
    _audit(session, authorization, client_id, user_id, "ASSIGNED_CLIENT", assignment.id)


async def unassign_client(
    session: AsyncSession,
    *,
    authorization: AuthorizationContext,
    client_id: UUID,
    user_id: UUID,
) -> None:
    await _client(session, authorization, client_id, lock=True)
    await _target(session, authorization, user_id, removing=True)
    assignment = await session.scalar(
        select(ClientAssignment).where(
            ClientAssignment.organization_id == authorization.organization_id,
            ClientAssignment.client_id == client_id,
            ClientAssignment.user_id == user_id,
        )
    )
    if assignment is None:
        raise ResourceNotFoundError("Assignment not found")
    await session.delete(assignment)
    await session.flush()
    _audit(session, authorization, client_id, user_id, "UNASSIGNED_CLIENT", assignment.id)


def _audit(
    session: AsyncSession,
    authorization: AuthorizationContext,
    client_id: UUID,
    user_id: UUID,
    action: str,
    assignment_id: UUID,
) -> None:
    add_audit_event(
        session,
        organization_id=authorization.organization_id,
        actor_user_id=authorization.user_id,
        action=action,
        entity_type="CLIENT_ASSIGNMENT",
        entity_id=assignment_id,
        event_data={"client_id": str(client_id), "user_id": str(user_id)},
    )
