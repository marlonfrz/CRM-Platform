from datetime import UTC, datetime, timedelta

from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import (
    OrganizationMode,
    User,
    UserInvitation,
    UserRole,
    UserStatus,
)
from app.services.authentication import hash_token, password_hasher
from app.services.bootstrap import bootstrap_organization
from app.services.departments import add_department_member, create_department

PASSWORD = "user-administration-password"


async def login(api_client: AsyncClient, email: str, password: str = PASSWORD) -> dict[str, str]:
    response = await api_client.post(
        "/api/v1/auth/login", json={"email": email, "password": password}
    )
    assert response.status_code == 200
    csrf_token = api_client.cookies.get("crm_csrf")
    assert csrf_token is not None
    return {"X-CSRF-Token": csrf_token}


async def test_owner_creates_pending_user_with_hashed_invitation(
    db_session: AsyncSession, api_client: AsyncClient
) -> None:
    organization, _ = await bootstrap_organization(
        db_session,
        mode=OrganizationMode.BUSINESS,
        organization_name="Company",
        owner_name="Owner",
        owner_email="owner@example.com",
        owner_password=PASSWORD,
    )
    department = await create_department(db_session, organization_id=organization.id, name="Sales")
    await db_session.commit()
    headers = await login(api_client, "owner@example.com")

    response = await api_client.post(
        "/api/v1/admin/users",
        json={
            "email": "employee@example.com",
            "full_name": "Employee",
            "role": "EMPLOYEE",
            "department_ids": [str(department.id)],
        },
        headers=headers,
    )

    assert response.status_code == 201
    assert response.json()["status"] == "PENDING"
    assert response.json()["department_ids"] == [str(department.id)]
    invitation = await db_session.scalar(select(UserInvitation))
    assert invitation is not None
    assert len(invitation.token_hash) == 64


async def test_invitation_acceptance_activates_user(
    db_session: AsyncSession, api_client: AsyncClient
) -> None:
    organization, _ = await bootstrap_organization(
        db_session,
        mode=OrganizationMode.BUSINESS,
        organization_name="Company",
        owner_name="Owner",
        owner_email="owner@example.com",
        owner_password=PASSWORD,
    )
    user = User(
        organization_id=organization.id,
        email="invited@example.com",
        full_name="Invited User",
        role=UserRole.EMPLOYEE,
        status=UserStatus.PENDING,
    )
    db_session.add(user)
    await db_session.flush()
    token = "known-invitation-token-with-enough-entropy"
    db_session.add(
        UserInvitation(
            organization_id=organization.id,
            user_id=user.id,
            token_hash=hash_token(token),
            expires_at=datetime.now(UTC) + timedelta(hours=1),
        )
    )
    await db_session.commit()

    response = await api_client.post(
        "/api/v1/auth/invitations/accept",
        json={
            "token": token,
            "password": "accepted-secure-password",
            "password_confirmation": "accepted-secure-password",
        },
    )
    login_response = await api_client.post(
        "/api/v1/auth/login",
        json={"email": "invited@example.com", "password": "accepted-secure-password"},
    )

    assert response.status_code == 204
    assert login_response.status_code == 200
    await db_session.refresh(user)
    assert user.status is UserStatus.ACTIVE
    assert user.password_hash is not None
    assert password_hasher.verify(user.password_hash, "accepted-secure-password")


async def test_admin_lists_and_updates_only_scoped_employees(
    db_session: AsyncSession, api_client: AsyncClient
) -> None:
    organization, _ = await bootstrap_organization(
        db_session,
        mode=OrganizationMode.BUSINESS,
        organization_name="Company",
        owner_name="Owner",
        owner_email="owner@example.com",
        owner_password=PASSWORD,
    )
    managed = await create_department(db_session, organization_id=organization.id, name="Managed")
    hidden = await create_department(db_session, organization_id=organization.id, name="Hidden")
    admin = User(
        organization_id=organization.id,
        email="admin@example.com",
        full_name="Admin",
        password_hash=password_hasher.hash(PASSWORD),
        role=UserRole.ADMIN,
        status=UserStatus.ACTIVE,
    )
    managed_employee = User(
        organization_id=organization.id,
        email="managed@example.com",
        full_name="Managed Employee",
        role=UserRole.EMPLOYEE,
        status=UserStatus.PENDING,
    )
    hidden_employee = User(
        organization_id=organization.id,
        email="hidden@example.com",
        full_name="Hidden Employee",
        role=UserRole.EMPLOYEE,
        status=UserStatus.PENDING,
    )
    db_session.add_all([admin, managed_employee, hidden_employee])
    await db_session.flush()
    for member, department in (
        (admin, managed),
        (managed_employee, managed),
        (hidden_employee, hidden),
    ):
        await add_department_member(
            db_session,
            organization_id=organization.id,
            department_id=department.id,
            user_id=member.id,
        )
    await db_session.commit()
    headers = await login(api_client, "admin@example.com")

    listed = await api_client.get("/api/v1/admin/users")
    updated = await api_client.patch(
        f"/api/v1/admin/users/{managed_employee.id}",
        json={
            "full_name": "Updated Employee",
            "role": "EMPLOYEE",
            "department_ids": [str(managed.id)],
        },
        headers=headers,
    )
    forbidden = await api_client.patch(
        f"/api/v1/admin/users/{hidden_employee.id}",
        json={
            "full_name": "Leaked",
            "role": "EMPLOYEE",
            "department_ids": [str(hidden.id)],
        },
        headers=headers,
    )

    assert [item["email"] for item in listed.json()] == ["managed@example.com"]
    assert updated.status_code == 200
    assert forbidden.status_code == 403
