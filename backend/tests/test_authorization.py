from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import Principal, get_authorization_context
from app.models import Organization, OrganizationMode, User, UserRole, UserSession, UserStatus
from app.policies.authorization import (
    AuthorizationContext,
    can_assign_client,
    can_create_activity,
    can_manage_client,
    can_manage_department,
    can_manage_task,
    can_manage_user,
    can_view_activity,
    can_view_client,
    can_view_department_report,
    can_view_global_report,
)
from app.services.departments import add_department_member, create_department


def context(
    role: UserRole,
    organization_id: UUID,
    *department_ids: UUID,
    mode: OrganizationMode = OrganizationMode.BUSINESS,
) -> AuthorizationContext:
    return AuthorizationContext(
        user_id=uuid4(),
        organization_id=organization_id,
        organization_mode=mode,
        role=role,
        department_ids=frozenset(department_ids),
    )


@pytest.mark.parametrize("role", [UserRole.OWNER, UserRole.ADMIN, UserRole.EMPLOYEE])
def test_cross_organization_access_is_always_denied(role: UserRole) -> None:
    own_organization_id = uuid4()
    other_organization_id = uuid4()
    department_id = uuid4()
    actor = context(role, own_organization_id, department_id)

    assert not can_manage_client(actor, organization_id=other_organization_id)
    assert not can_view_client(actor, organization_id=other_organization_id, is_assigned=True)
    assert not can_create_activity(
        actor,
        organization_id=other_organization_id,
        department_id=department_id,
        is_client_assigned=True,
    )


def test_owner_has_organization_wide_business_scope() -> None:
    organization_id = uuid4()
    department_id = uuid4()
    actor = context(UserRole.OWNER, organization_id)

    assert can_manage_department(
        actor, organization_id=organization_id, department_id=department_id
    )
    assert can_manage_user(
        actor,
        organization_id=organization_id,
        target_role=UserRole.ADMIN,
        target_department_ids=frozenset({department_id}),
    )
    assert can_view_global_report(actor, organization_id)
    assert can_view_department_report(
        actor, organization_id=organization_id, department_id=department_id
    )


def test_admin_is_limited_to_managed_departments() -> None:
    organization_id = uuid4()
    managed_department_id = uuid4()
    other_department_id = uuid4()
    actor = context(UserRole.ADMIN, organization_id, managed_department_id)

    assert can_manage_department(
        actor, organization_id=organization_id, department_id=managed_department_id
    )
    assert not can_manage_department(
        actor, organization_id=organization_id, department_id=other_department_id
    )
    assert can_manage_user(
        actor,
        organization_id=organization_id,
        target_role=UserRole.EMPLOYEE,
        target_department_ids=frozenset({managed_department_id}),
    )
    assert not can_manage_user(
        actor,
        organization_id=organization_id,
        target_role=UserRole.EMPLOYEE,
        target_department_ids=frozenset({managed_department_id, other_department_id}),
    )
    assert not can_manage_user(
        actor,
        organization_id=organization_id,
        target_role=UserRole.ADMIN,
        target_department_ids=frozenset({managed_department_id}),
    )


def test_admin_can_use_global_client_catalog_without_seeing_other_activity() -> None:
    organization_id = uuid4()
    managed_department_id = uuid4()
    other_department_id = uuid4()
    actor = context(UserRole.ADMIN, organization_id, managed_department_id)

    assert can_view_client(actor, organization_id=organization_id, is_assigned=False)
    assert can_manage_client(actor, organization_id=organization_id)
    assert can_view_activity(
        actor,
        organization_id=organization_id,
        department_id=managed_department_id,
        is_client_assigned=False,
    )
    assert not can_view_activity(
        actor,
        organization_id=organization_id,
        department_id=other_department_id,
        is_client_assigned=False,
    )


def test_admin_assigns_only_employees_with_shared_department() -> None:
    organization_id = uuid4()
    managed_department_id = uuid4()
    actor = context(UserRole.ADMIN, organization_id, managed_department_id)

    assert can_assign_client(
        actor,
        organization_id=organization_id,
        target_role=UserRole.EMPLOYEE,
        target_department_ids=frozenset({managed_department_id}),
    )
    assert not can_assign_client(
        actor,
        organization_id=organization_id,
        target_role=UserRole.EMPLOYEE,
        target_department_ids=frozenset({uuid4()}),
    )


def test_employee_needs_assignment_and_department_scope() -> None:
    organization_id = uuid4()
    department_id = uuid4()
    actor = context(UserRole.EMPLOYEE, organization_id, department_id)

    assert not can_view_client(actor, organization_id=organization_id, is_assigned=False)
    assert can_view_client(actor, organization_id=organization_id, is_assigned=True)
    assert can_create_activity(
        actor,
        organization_id=organization_id,
        department_id=department_id,
        is_client_assigned=True,
    )
    assert not can_create_activity(
        actor,
        organization_id=organization_id,
        department_id=department_id,
        is_client_assigned=False,
    )
    assert can_manage_task(
        actor,
        organization_id=organization_id,
        department_id=department_id,
        is_assigned_to_actor=True,
        is_client_assigned=True,
    )
    assert not can_manage_task(
        actor,
        organization_id=organization_id,
        department_id=department_id,
        is_assigned_to_actor=False,
        is_client_assigned=True,
    )


def test_individual_owner_bypasses_departments_without_fake_membership() -> None:
    organization_id = uuid4()
    actor = context(UserRole.OWNER, organization_id, mode=OrganizationMode.INDIVIDUAL)

    assert actor.department_ids == frozenset()
    assert can_create_activity(
        actor,
        organization_id=organization_id,
        department_id=None,
        is_client_assigned=False,
    )
    assert can_view_activity(
        actor,
        organization_id=organization_id,
        department_id=None,
        is_client_assigned=False,
    )
    assert not can_create_activity(
        actor,
        organization_id=organization_id,
        department_id=uuid4(),
        is_client_assigned=False,
    )
    assert not can_view_activity(
        actor,
        organization_id=organization_id,
        department_id=uuid4(),
        is_client_assigned=False,
    )


async def test_authorization_context_is_loaded_from_persisted_memberships(
    db_session: AsyncSession,
) -> None:
    organization = Organization(name="Example", mode=OrganizationMode.BUSINESS)
    admin = User(
        organization=organization,
        email="admin@example.com",
        full_name="Admin",
        role=UserRole.ADMIN,
        status=UserStatus.ACTIVE,
        password_hash="already-hashed",
    )
    db_session.add_all([organization, admin])
    await db_session.flush()
    sales = await create_department(db_session, organization_id=organization.id, name="Sales")
    support = await create_department(db_session, organization_id=organization.id, name="Support")
    for department in (sales, support):
        await add_department_member(
            db_session,
            organization_id=organization.id,
            department_id=department.id,
            user_id=admin.id,
        )

    now = datetime.now(UTC)
    user_session = UserSession(
        organization_id=organization.id,
        user_id=admin.id,
        token_hash="token-hash",
        csrf_token_hash="csrf-hash",
        expires_at=now + timedelta(hours=8),
        last_used_at=now,
    )
    authorization = await get_authorization_context(
        Principal(
            user=admin,
            session=user_session,
            session_token="token",
            csrf_token="csrf",
        ),
        db_session,
    )

    assert authorization.organization_id == organization.id
    assert authorization.role is UserRole.ADMIN
    assert authorization.department_ids == frozenset({sales.id, support.id})
