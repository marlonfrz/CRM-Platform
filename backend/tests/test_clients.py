from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import (
    AuditLog,
    Client,
    ClientContact,
    Organization,
    OrganizationMode,
    User,
    UserRole,
    UserStatus,
)
from app.services.authentication import password_hasher
from app.services.bootstrap import bootstrap_organization
from app.services.departments import add_department_member, create_department

PASSWORD = "clients-secure-password"


async def login(api_client: AsyncClient, email: str) -> dict[str, str]:
    response = await api_client.post(
        "/api/v1/auth/login", json={"email": email, "password": PASSWORD}
    )
    assert response.status_code == 200
    csrf_token = api_client.cookies.get("crm_csrf")
    assert csrf_token is not None
    return {"X-CSRF-Token": csrf_token}


async def test_owner_manages_client_and_contact_lifecycle(
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

    created = await api_client.post(
        "/api/v1/clients",
        json={"name": "  Cliente Alfa  ", "address": "  Calle Ejemplo  ", "notes": "VIP"},
        headers=headers,
    )
    assert created.status_code == 201
    client_id = created.json()["id"]
    assert created.json()["name"] == "Cliente Alfa"
    assert created.json()["contacts"] == []

    contact = await api_client.post(
        f"/api/v1/clients/{client_id}/contacts",
        json={
            "full_name": "  Ana Pérez  ",
            "position": "Dirección",
            "email": "ANA@EXAMPLE.COM",
            "phone": "+34 600 000 000",
            "notes": "Contacto principal",
        },
        headers=headers,
    )
    assert contact.status_code == 201
    contact_id = contact.json()["id"]
    assert contact.json()["email"] == "ana@example.com"

    updated = await api_client.patch(
        f"/api/v1/clients/{client_id}",
        json={"name": "Cliente Alfa Actualizado", "address": "Ciudad Ejemplo", "notes": None},
        headers=headers,
    )
    updated_contact = await api_client.patch(
        f"/api/v1/clients/{client_id}/contacts/{contact_id}",
        json={
            "full_name": "Ana Pérez",
            "position": "Gerencia",
            "email": "ana@example.com",
            "phone": None,
            "notes": None,
        },
        headers=headers,
    )
    listed = await api_client.get("/api/v1/clients", params={"search": "actualizado"})
    detail = await api_client.get(f"/api/v1/clients/{client_id}")
    removed = await api_client.delete(
        f"/api/v1/clients/{client_id}/contacts/{contact_id}", headers=headers
    )

    assert updated.status_code == 200
    assert updated.json()["name"] == "Cliente Alfa Actualizado"
    assert updated_contact.json()["position"] == "Gerencia"
    assert [item["id"] for item in listed.json()] == [client_id]
    assert detail.json()["contacts"][0]["id"] == contact_id
    assert removed.status_code == 204
    assert (await api_client.get(f"/api/v1/clients/{client_id}")).json()["contacts"] == []
    actions = set(await db_session.scalars(select(AuditLog.action)))
    assert {
        "CREATED_CLIENT",
        "UPDATED_CLIENT",
        "CREATED_CLIENT_CONTACT",
        "UPDATED_CLIENT_CONTACT",
        "DELETED_CLIENT_CONTACT",
    } <= actions


async def test_admin_can_manage_global_clients(
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
    department = await create_department(
        db_session, organization_id=organization.id, name="Sales"
    )
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
        department_id=department.id,
        user_id=admin.id,
    )
    db_session.add(Client(organization_id=organization.id, name="Existing"))
    await db_session.commit()
    headers = await login(api_client, "admin@example.com")

    listed = await api_client.get("/api/v1/clients")
    created = await api_client.post(
        "/api/v1/clients",
        json={"name": "Admin Client", "address": None, "notes": None},
        headers=headers,
    )

    assert [item["name"] for item in listed.json()] == ["Existing"]
    assert created.status_code == 201


async def test_employee_has_no_client_access_before_assignments(
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
    department = await create_department(
        db_session, organization_id=organization.id, name="Support"
    )
    employee = User(
        organization_id=organization.id,
        email="employee@example.com",
        full_name="Employee",
        password_hash=password_hasher.hash(PASSWORD),
        role=UserRole.EMPLOYEE,
        status=UserStatus.ACTIVE,
    )
    client = Client(organization_id=organization.id, name="Hidden Client")
    db_session.add_all([employee, client])
    await db_session.flush()
    await add_department_member(
        db_session,
        organization_id=organization.id,
        department_id=department.id,
        user_id=employee.id,
    )
    await db_session.commit()
    headers = await login(api_client, "employee@example.com")

    listed = await api_client.get("/api/v1/clients")
    detail = await api_client.get(f"/api/v1/clients/{client.id}")
    created = await api_client.post(
        "/api/v1/clients",
        json={"name": "Forbidden", "address": None, "notes": None},
        headers=headers,
    )

    assert listed.json() == []
    assert detail.status_code == 403
    assert created.status_code == 403


async def test_individual_owner_manages_clients_without_departments(
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

    created = await api_client.post(
        "/api/v1/clients",
        json={"name": "Personal Client", "address": None, "notes": None},
        headers=headers,
    )

    assert created.status_code == 201
    assert (await api_client.get("/api/v1/clients")).json()[0]["name"] == "Personal Client"


async def test_client_detail_does_not_leak_between_organizations(
    db_session: AsyncSession, api_client: AsyncClient
) -> None:
    first, _ = await bootstrap_organization(
        db_session,
        mode=OrganizationMode.BUSINESS,
        organization_name="First",
        owner_name="First Owner",
        owner_email="first@example.com",
        owner_password=PASSWORD,
    )
    second = Organization(name="Second", mode=OrganizationMode.BUSINESS)
    db_session.add(second)
    await db_session.flush()
    hidden = Client(organization_id=second.id, name="Second Client")
    db_session.add(hidden)
    await db_session.commit()
    await login(api_client, "first@example.com")

    response = await api_client.get(f"/api/v1/clients/{hidden.id}")

    assert response.status_code == 404
    assert first.id != second.id


async def test_database_rejects_contact_from_another_organization(
    db_session: AsyncSession,
) -> None:
    first, _ = await bootstrap_organization(
        db_session,
        mode=OrganizationMode.BUSINESS,
        organization_name="First",
        owner_name="First Owner",
        owner_email="first@example.com",
        owner_password=PASSWORD,
    )
    second = Organization(name="Second", mode=OrganizationMode.BUSINESS)
    db_session.add(second)
    await db_session.flush()
    client = Client(organization_id=first.id, name="First Client")
    db_session.add(client)
    await db_session.flush()
    db_session.add(
        ClientContact(
            organization_id=second.id,
            client_id=client.id,
            full_name="Invalid Contact",
        )
    )

    try:
        await db_session.flush()
    except IntegrityError:
        await db_session.rollback()
    else:
        raise AssertionError("Cross-organization contacts must be rejected")
