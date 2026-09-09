from datetime import UTC, datetime, timedelta
from secrets import token_urlsafe
from uuid import UUID

from argon2 import PasswordHasher
from sqlalchemy import delete, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.config import Settings
from app.models import (
    Department,
    DepartmentMember,
    OrganizationMode,
    User,
    UserInvitation,
    UserRole,
    UserSession,
    UserStatus,
)
from app.policies.authorization import AuthorizationContext, can_manage_user
from app.services.audit import add_audit_event
from app.services.authentication import hash_token
from app.services.email import send_user_invitation
from app.services.exceptions import (
    AuthorizationDeniedError,
    IndividualModeViolationError,
    LastActiveOwnerError,
    ResourceConflictError,
    ResourceNotFoundError,
)
from app.services.normalization import normalize_email, normalize_name

password_hasher = PasswordHasher()


async def list_authorized_users(
    session: AsyncSession, *, authorization: AuthorizationContext
) -> list[User]:
    statement = (
        select(User)
        .options(selectinload(User.department_memberships))
        .where(User.organization_id == authorization.organization_id)
        .order_by(User.full_name)
    )
    if not authorization.is_owner:
        statement = (
            statement.join(DepartmentMember)
            .where(
                User.role == UserRole.EMPLOYEE,
                DepartmentMember.department_id.in_(authorization.department_ids),
            )
            .distinct()
        )
    return list(await session.scalars(statement))


async def create_user(
    session: AsyncSession,
    *,
    authorization: AuthorizationContext,
    settings: Settings,
    email: str,
    full_name: str,
    role: UserRole,
    department_ids: frozenset[UUID],
) -> User:
    if authorization.organization_mode is OrganizationMode.INDIVIDUAL:
        raise IndividualModeViolationError("Individual organizations cannot have users")
    if not can_manage_user(
        authorization,
        organization_id=authorization.organization_id,
        target_role=role,
        target_department_ids=department_ids,
    ):
        raise AuthorizationDeniedError("User creation is not allowed")
    normalized_email = normalize_email(email)
    if (
        await session.scalar(
            select(User.id).where(
                User.organization_id == authorization.organization_id,
                User.email == normalized_email,
            )
        )
        is not None
    ):
        raise ResourceConflictError("A user with this email already exists")
    await _validate_departments(
        session, authorization.organization_id, department_ids, required=role is not UserRole.OWNER
    )

    user = User(
        organization_id=authorization.organization_id,
        email=normalized_email,
        full_name=normalize_name(full_name),
        role=role,
        status=UserStatus.PENDING,
    )
    session.add(user)
    await session.flush()
    await _replace_memberships(session, user, department_ids)
    token = await _create_invitation(session, user, settings)
    add_audit_event(
        session,
        organization_id=user.organization_id,
        actor_user_id=authorization.user_id,
        action="CREATED_USER",
        entity_type="USER",
        entity_id=user.id,
        event_data={
            "role": user.role.value,
            "department_ids": sorted(str(item) for item in department_ids),
        },
    )
    await send_user_invitation(
        settings=settings, recipient=user.email, recipient_name=user.full_name, token=token
    )
    await session.refresh(user, attribute_names=["department_memberships"])
    return user


async def update_user(
    session: AsyncSession,
    *,
    authorization: AuthorizationContext,
    user_id: UUID,
    full_name: str,
    role: UserRole,
    department_ids: frozenset[UUID],
) -> User:
    user = await _get_user(session, authorization.organization_id, user_id, for_update=True)
    if not can_manage_user(
        authorization,
        organization_id=user.organization_id,
        target_role=role,
        target_department_ids=department_ids,
    ):
        raise AuthorizationDeniedError("User management is not allowed")
    await _protect_last_owner(session, user, new_role=role)
    await _validate_departments(
        session, authorization.organization_id, department_ids, required=role is not UserRole.OWNER
    )
    previous = {"full_name": user.full_name, "role": user.role.value}
    previous_department_ids = sorted(
        str(item.department_id) for item in user.department_memberships
    )
    user.full_name = normalize_name(full_name)
    user.role = role
    await _replace_memberships(session, user, department_ids)
    add_audit_event(
        session,
        organization_id=user.organization_id,
        actor_user_id=authorization.user_id,
        action="UPDATED_USER",
        entity_type="USER",
        entity_id=user.id,
        event_data={
            "previous": previous,
            "full_name": user.full_name,
            "role": role.value,
            "previous_department_ids": previous_department_ids,
            "department_ids": sorted(str(item) for item in department_ids),
        },
    )
    await session.refresh(user, attribute_names=["department_memberships"])
    return user


async def disable_authorized_user(
    session: AsyncSession, *, authorization: AuthorizationContext, user_id: UUID
) -> User:
    user = await _get_user(session, authorization.organization_id, user_id, for_update=True)
    department_ids = frozenset(item.department_id for item in user.department_memberships)
    if not can_manage_user(
        authorization,
        organization_id=user.organization_id,
        target_role=user.role,
        target_department_ids=department_ids,
    ):
        raise AuthorizationDeniedError("User management is not allowed")
    user = await disable_user(session, user_id=user.id)
    add_audit_event(
        session,
        organization_id=user.organization_id,
        actor_user_id=authorization.user_id,
        action="DISABLED_USER",
        entity_type="USER",
        entity_id=user.id,
    )
    return user


async def activate_user(
    session: AsyncSession, *, authorization: AuthorizationContext, user_id: UUID
) -> User:
    user = await _get_user(session, authorization.organization_id, user_id, for_update=True)
    department_ids = frozenset(item.department_id for item in user.department_memberships)
    if not can_manage_user(
        authorization,
        organization_id=user.organization_id,
        target_role=user.role,
        target_department_ids=department_ids,
    ):
        raise AuthorizationDeniedError("User management is not allowed")
    if user.password_hash is None:
        raise ResourceConflictError("Pending users must accept their invitation")
    user.status = UserStatus.ACTIVE
    add_audit_event(
        session,
        organization_id=user.organization_id,
        actor_user_id=authorization.user_id,
        action="ACTIVATED_USER",
        entity_type="USER",
        entity_id=user.id,
    )
    await session.flush()
    return user


async def resend_invitation(
    session: AsyncSession,
    *,
    authorization: AuthorizationContext,
    settings: Settings,
    user_id: UUID,
) -> User:
    user = await _get_user(session, authorization.organization_id, user_id, for_update=True)
    department_ids = frozenset(item.department_id for item in user.department_memberships)
    if user.status is not UserStatus.PENDING or not can_manage_user(
        authorization,
        organization_id=user.organization_id,
        target_role=user.role,
        target_department_ids=department_ids,
    ):
        raise AuthorizationDeniedError("Invitation resend is not allowed")
    token = await _create_invitation(session, user, settings)
    await send_user_invitation(
        settings=settings, recipient=user.email, recipient_name=user.full_name, token=token
    )
    add_audit_event(
        session,
        organization_id=user.organization_id,
        actor_user_id=authorization.user_id,
        action="RESENT_INVITATION",
        entity_type="USER",
        entity_id=user.id,
    )
    return user


async def accept_invitation(session: AsyncSession, *, token: str, password: str) -> User:
    now = datetime.now(UTC)
    invitation = await session.scalar(
        select(UserInvitation)
        .options(selectinload(UserInvitation.user))
        .where(UserInvitation.token_hash == hash_token(token))
        .with_for_update()
    )
    if (
        invitation is None
        or invitation.accepted_at is not None
        or invitation.revoked_at is not None
        or invitation.expires_at <= now
        or invitation.user.status is not UserStatus.PENDING
    ):
        raise ResourceNotFoundError("Invitation not found")
    invitation.accepted_at = now
    invitation.user.password_hash = password_hasher.hash(password)
    invitation.user.status = UserStatus.ACTIVE
    await session.execute(
        update(UserInvitation)
        .where(
            UserInvitation.user_id == invitation.user_id,
            UserInvitation.id != invitation.id,
            UserInvitation.revoked_at.is_(None),
        )
        .values(revoked_at=now)
    )
    add_audit_event(
        session,
        organization_id=invitation.organization_id,
        actor_user_id=invitation.user_id,
        action="ACCEPTED_INVITATION",
        entity_type="USER",
        entity_id=invitation.user_id,
    )
    await session.flush()
    return invitation.user


async def disable_user(session: AsyncSession, *, user_id: UUID) -> User:
    user = await session.scalar(
        select(User)
        .options(selectinload(User.department_memberships))
        .where(User.id == user_id)
        .with_for_update()
    )
    if user is None:
        raise ResourceNotFoundError("User not found")
    await _protect_last_owner(session, user, disabling=True)
    user.status = UserStatus.DISABLED
    await session.execute(
        update(UserSession)
        .where(UserSession.user_id == user.id, UserSession.revoked_at.is_(None))
        .values(revoked_at=datetime.now(UTC))
    )
    await session.flush()
    return user


async def _get_user(
    session: AsyncSession, organization_id: UUID, user_id: UUID, *, for_update: bool
) -> User:
    statement = (
        select(User)
        .options(selectinload(User.department_memberships))
        .where(User.id == user_id, User.organization_id == organization_id)
    )
    if for_update:
        statement = statement.with_for_update()
    user = await session.scalar(statement)
    if user is None:
        raise ResourceNotFoundError("User not found")
    return user


async def _validate_departments(
    session: AsyncSession,
    organization_id: UUID,
    department_ids: frozenset[UUID],
    *,
    required: bool,
) -> None:
    if required and not department_ids:
        raise ResourceConflictError("At least one department is required")
    if not department_ids:
        return
    count = await session.scalar(
        select(func.count())
        .select_from(Department)
        .where(
            Department.organization_id == organization_id,
            Department.id.in_(department_ids),
        )
    )
    if count != len(department_ids):
        raise ResourceNotFoundError("Department not found")


async def _replace_memberships(
    session: AsyncSession, user: User, department_ids: frozenset[UUID]
) -> None:
    await session.execute(delete(DepartmentMember).where(DepartmentMember.user_id == user.id))
    session.add_all(
        DepartmentMember(
            organization_id=user.organization_id,
            department_id=department_id,
            user_id=user.id,
        )
        for department_id in department_ids
    )
    await session.flush()


async def _create_invitation(session: AsyncSession, user: User, settings: Settings) -> str:
    now = datetime.now(UTC)
    await session.execute(
        update(UserInvitation)
        .where(UserInvitation.user_id == user.id, UserInvitation.revoked_at.is_(None))
        .values(revoked_at=now)
    )
    token = token_urlsafe(48)
    session.add(
        UserInvitation(
            organization_id=user.organization_id,
            user_id=user.id,
            token_hash=hash_token(token),
            expires_at=now + timedelta(seconds=settings.invitation_lifetime_seconds),
        )
    )
    await session.flush()
    return token


async def _protect_last_owner(
    session: AsyncSession,
    user: User,
    *,
    new_role: UserRole | None = None,
    disabling: bool = False,
) -> None:
    removes_active_owner = (
        user.role is UserRole.OWNER
        and user.status is UserStatus.ACTIVE
        and (disabling or new_role is not UserRole.OWNER)
    )
    if not removes_active_owner:
        return
    active_owner_count = await session.scalar(
        select(func.count())
        .select_from(User)
        .where(
            User.organization_id == user.organization_id,
            User.role == UserRole.OWNER,
            User.status == UserStatus.ACTIVE,
        )
    )
    if active_owner_count is not None and active_owner_count <= 1:
        raise LastActiveOwnerError("The last active owner cannot be changed")
