from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import AuditLog, OrganizationMode, User, UserRole, UserStatus
from app.services.authentication import password_hasher
from app.services.bootstrap import bootstrap_organization
from app.services.departments import add_department_member, create_department

PASSWORD = "administration-password"


async def login(api_client: AsyncClient, email: str) -> dict[str, str]:
    response = await api_client.post(
        "/api/v1/auth/login", json={"email": email, "password": PASSWORD}
    )
    assert response.status_code == 200
    csrf_token = api_client.cookies.get("crm_csrf")
    assert csrf_token is not None
    return {"X-CSRF-Token": csrf_token}


async def test_owner_manages_organization_and_department_lifecycle(
    db_session: AsyncSession, api_client: AsyncClient
) -> None:
    organization, _ = await bootstrap_organization(
        db_session,
        mode=OrganizationMode.BUSINESS,
        organization_name="Original Name",
        owner_name="Owner",
        owner_email="owner@example.com",
        owner_password=PASSWORD,
    )
    await db_session.commit()
    headers = await login(api_client, "owner@example.com")

    organization_response = await api_client.patch(
        "/api/v1/admin/organization", json={"name": "Updated Company"}, headers=headers
    )
    created = await api_client.post(
        "/api/v1/admin/departments", json={"name": "Sales"}, headers=headers
    )
    department_id = created.json()["id"]
    updated = await api_client.patch(
        f"/api/v1/admin/departments/{department_id}",
        json={"name": "Commercial"},
        headers=headers,
    )
    listed = await api_client.get("/api/v1/admin/departments")
    removed = await api_client.delete(f"/api/v1/admin/departments/{department_id}", headers=headers)

    assert organization_response.status_code == 200
    assert organization_response.json()["name"] == "Updated Company"
    assert created.status_code == 201
    assert updated.json()["name"] == "Commercial"
    assert listed.json() == [{"id": department_id, "name": "Commercial"}]
    assert removed.status_code == 204
    assert (await api_client.get("/api/v1/admin/departments")).json() == []
    actions = set(await db_session.scalars(select(AuditLog.action)))
    assert {
        "UPDATED_ORGANIZATION",
        "CREATED_DEPARTMENT",
        "UPDATED_DEPARTMENT",
        "DELETED_DEPARTMENT",
    } <= actions
    assert organization.id is not None


async def test_owner_cannot_create_duplicate_department_name(
    db_session: AsyncSession, api_client: AsyncClient
) -> None:
    await bootstrap_organization(
        db_session,
        mode=OrganizationMode.BUSINESS,
        organization_name="Company",
        owner_name="Owner",
        owner_email="owner@example.com",
        owner_password=PASSWORD,
    )
    await db_session.commit()
    headers = await login(api_client, "owner@example.com")
    await api_client.post("/api/v1/admin/departments", json={"name": "Sales"}, headers=headers)

    duplicate = await api_client.post(
        "/api/v1/admin/departments", json={"name": " sales "}, headers=headers
    )

    assert duplicate.status_code == 409


async def test_individual_owner_cannot_create_departments(
    db_session: AsyncSession, api_client: AsyncClient
) -> None:
    await bootstrap_organization(
        db_session,
        mode=OrganizationMode.INDIVIDUAL,
        organization_name="Personal",
        owner_name="Owner",
        owner_email="owner@example.com",
        owner_password=PASSWORD,
    )
    await db_session.commit()
    headers = await login(api_client, "owner@example.com")

    response = await api_client.post(
        "/api/v1/admin/departments", json={"name": "Fake"}, headers=headers
    )

    assert response.status_code == 409


async def test_admin_only_accesses_managed_departments(
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
    db_session.add(admin)
    await db_session.flush()
    await add_department_member(
        db_session,
        organization_id=organization.id,
        department_id=managed.id,
        user_id=admin.id,
    )
    await db_session.commit()
    headers = await login(api_client, "admin@example.com")

    listed = await api_client.get("/api/v1/admin/departments")
    create_response = await api_client.post(
        "/api/v1/admin/departments", json={"name": "Forbidden"}, headers=headers
    )
    hidden_update = await api_client.patch(
        f"/api/v1/admin/departments/{hidden.id}",
        json={"name": "Leaked"},
        headers=headers,
    )
    managed_update = await api_client.patch(
        f"/api/v1/admin/departments/{managed.id}",
        json={"name": "Allowed"},
        headers=headers,
    )

    assert listed.json() == [{"id": str(managed.id), "name": "Managed"}]
    assert create_response.status_code == 403
    assert hidden_update.status_code == 403
    assert managed_update.status_code == 200
