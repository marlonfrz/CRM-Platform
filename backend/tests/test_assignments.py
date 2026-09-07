import asyncio
from dataclasses import dataclass
from uuid import uuid4

import pytest
from httpx import AsyncClient
from sqlalchemy import delete, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import (
    AuditLog,
    Client,
    ClientAssignment,
    ClientContact,
    Department,
    DepartmentMember,
    Organization,
    OrganizationMode,
    User,
    UserRole,
    UserStatus,
)
from app.services import assignments
from app.services.authentication import password_hasher
from app.services.bootstrap import bootstrap_organization
from app.services.departments import add_department_member, create_department

PASSWORD = "assignment-test-password"


@dataclass
class Team:
    client: Client
    other_client: Client
    department: Department
    users: dict[str, User]


@pytest.fixture
async def team(db_session: AsyncSession) -> Team:
    organization, owner = await bootstrap_organization(
        db_session,
        mode=OrganizationMode.BUSINESS,
        organization_name="Company",
        owner_name="Owner",
        owner_email="owner@example.com",
        owner_password=PASSWORD,
    )
    department = await create_department(db_session, organization_id=organization.id, name="A")
    other = await create_department(db_session, organization_id=organization.id, name="B")
    users = {"owner": owner}
    hashed = password_hasher.hash(PASSWORD)
    for name, role, status, departments in [
        ("admin", UserRole.ADMIN, UserStatus.ACTIVE, [department]),
        ("employee", UserRole.EMPLOYEE, UserStatus.ACTIVE, [department, other]),
        ("hidden", UserRole.EMPLOYEE, UserStatus.ACTIVE, [other]),
        ("disabled", UserRole.EMPLOYEE, UserStatus.DISABLED, [department]),
        ("pending", UserRole.EMPLOYEE, UserStatus.PENDING, [department]),
        ("no_department", UserRole.EMPLOYEE, UserStatus.ACTIVE, []),
    ]:
        user = User(
            organization_id=organization.id,
            email=f"{name}@example.com",
            full_name=name,
            role=role,
            status=status,
            password_hash=hashed,
        )
        db_session.add(user)
        await db_session.flush()
        users[name] = user
        for dep in departments:
            await add_department_member(
                db_session,
                organization_id=organization.id,
                department_id=dep.id,
                user_id=user.id,
            )
    client = Client(organization_id=organization.id, name="Global Hotel")
    other_client = Client(organization_id=organization.id, name="Other Hotel")
    db_session.add_all([client, other_client])
    await db_session.flush()
    db_session.add(
        ClientContact(
            organization_id=organization.id,
            client_id=client.id,
            full_name="Hotel Contact",
        )
    )
    await db_session.commit()
    return Team(client, other_client, department, users)


async def login(api: AsyncClient, user: User) -> dict[str, str]:
    response = await api.post(
        "/api/v1/auth/login", json={"email": user.email, "password": PASSWORD}
    )
    assert response.status_code == 200
    token = api.cookies.get("crm_csrf")
    assert token is not None
    return {"X-CSRF-Token": token}


def path(team: Team) -> str:
    return f"/api/v1/clients/{team.client.id}/assignments"


async def test_assignment_grants_and_removal_revokes_read_access(
    team: Team,
    api_client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    headers = await login(api_client, team.users["owner"])
    response = await api_client.post(
        path(team), headers=headers, json={"user_id": str(team.users["employee"].id)}
    )
    assert response.status_code == 201
    assignment = await db_session.scalar(select(ClientAssignment))
    assert assignment is not None
    assert assignment.assigned_by_user_id == team.users["owner"].id
    await login(api_client, team.users["employee"])
    for query in ["", "?search=hotel", "?search=Global"]:
        result = await api_client.get(f"/api/v1/clients{query}")
        assert [c["id"] for c in result.json()] == [str(team.client.id)]
    assert (await api_client.get("/api/v1/clients?search=Other")).json() == []
    detail = await api_client.get(f"/api/v1/clients/{team.client.id}")
    assert detail.status_code == 200
    assert detail.json()["contacts"][0]["full_name"] == "Hotel Contact"
    assert (await api_client.get(f"/api/v1/clients/{team.other_client.id}")).status_code == 403
    headers = await login(api_client, team.users["owner"])
    assert (
        await api_client.delete(
            f"{path(team)}/{team.users['employee'].id}",
            headers=headers,
        )
    ).status_code == 204
    await login(api_client, team.users["employee"])
    assert (await api_client.get("/api/v1/clients")).json() == []
    assert (await api_client.get(f"/api/v1/clients/{team.client.id}")).status_code == 403
    assert await db_session.scalar(select(func.count()).select_from(Client)) == 2
    assert await db_session.scalar(select(func.count()).select_from(ClientContact)) == 1
    events = list(
        await db_session.scalars(
            select(AuditLog).where(AuditLog.entity_type == "CLIENT_ASSIGNMENT")
        )
    )
    assert {event.action for event in events} == {"ASSIGNED_CLIENT", "UNASSIGNED_CLIENT"}
    assert all(event.event_data["user_id"] == str(team.users["employee"].id) for event in events)


async def test_admin_sees_and_manages_only_shared_department_employees(
    team: Team,
    api_client: AsyncClient,
) -> None:
    headers = await login(api_client, team.users["owner"])
    await api_client.post(
        path(team), headers=headers, json={"user_id": str(team.users["hidden"].id)}
    )
    headers = await login(api_client, team.users["admin"])
    result = (await api_client.get(path(team))).json()
    assert result["assigned"] == []
    assert [u["user_id"] for u in result["available"]] == [str(team.users["employee"].id)]
    assert (
        await api_client.post(
            path(team), headers=headers, json={"user_id": str(team.users["employee"].id)}
        )
    ).status_code == 201
    assert (
        await api_client.post(
            path(team), headers=headers, json={"user_id": str(team.users["hidden"].id)}
        )
    ).status_code == 403
    assert (
        await api_client.delete(f"{path(team)}/{team.users['hidden'].id}", headers=headers)
    ).status_code == 403
    assert (
        await api_client.delete(f"{path(team)}/{team.users['employee'].id}", headers=headers)
    ).status_code == 204


@pytest.mark.parametrize("name", ["owner", "admin", "pending", "disabled", "no_department"])
async def test_owner_cannot_assign_ineligible_target(
    team: Team,
    api_client: AsyncClient,
    name: str,
) -> None:
    headers = await login(api_client, team.users["owner"])
    assert (
        await api_client.post(
            path(team), headers=headers, json={"user_id": str(team.users[name].id)}
        )
    ).status_code == 409


async def test_authentication_csrf_and_employee_write_denials(
    team: Team,
    api_client: AsyncClient,
) -> None:
    body = {"user_id": str(team.users["employee"].id)}
    assert (await api_client.get(path(team))).status_code == 401
    assert (await api_client.post(path(team), json=body)).status_code == 401
    headers = await login(api_client, team.users["owner"])
    assert (await api_client.post(path(team), json=body)).status_code == 403
    assert (await api_client.post(path(team), json=body, headers=headers)).status_code == 201
    assert (await api_client.delete(f"{path(team)}/{team.users['employee'].id}")).status_code == 403
    headers = await login(api_client, team.users["employee"])
    assert (await api_client.get(path(team))).status_code == 403
    assert (await api_client.post(path(team), json=body, headers=headers)).status_code == 403
    assert (
        await api_client.delete(f"{path(team)}/{team.users['employee'].id}", headers=headers)
    ).status_code == 403
    assert (
        await api_client.patch(
            f"/api/v1/clients/{team.client.id}", json={"name": "Not allowed"}, headers=headers
        )
    ).status_code == 403
    assert (
        await api_client.post(
            f"/api/v1/clients/{team.client.id}/contacts",
            json={"full_name": "Not allowed"},
            headers=headers,
        )
    ).status_code == 403


async def test_duplicate_requests_produce_one_assignment_and_audit(
    team: Team,
    api_client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    headers = await login(api_client, team.users["owner"])
    responses = await asyncio.gather(
        *[
            api_client.post(
                path(team), headers=headers, json={"user_id": str(team.users["employee"].id)}
            )
            for _ in range(2)
        ]
    )
    assert sorted(r.status_code for r in responses) == [201, 409]
    assert await db_session.scalar(select(func.count()).select_from(ClientAssignment)) == 1
    assert (
        await db_session.scalar(
            select(func.count()).select_from(AuditLog).where(AuditLog.action == "ASSIGNED_CLIENT")
        )
        == 1
    )


async def test_individual_owner_needs_no_assignment(
    db_session: AsyncSession,
    api_client: AsyncClient,
) -> None:
    org, owner = await bootstrap_organization(
        db_session,
        mode=OrganizationMode.INDIVIDUAL,
        organization_name="Personal",
        owner_name="Owner",
        owner_email="owner@example.com",
        owner_password=PASSWORD,
    )
    client = Client(organization_id=org.id, name="Personal Client")
    db_session.add(client)
    await db_session.commit()
    headers = await login(api_client, owner)
    endpoint = f"/api/v1/clients/{client.id}/assignments"
    assert (await api_client.get(endpoint)).status_code == 409
    assert (
        await api_client.post(endpoint, headers=headers, json={"user_id": str(owner.id)})
    ).status_code == 409
    assert (await api_client.delete(f"{endpoint}/{owner.id}", headers=headers)).status_code == 409
    assert (await api_client.get(f"/api/v1/clients/{client.id}")).status_code == 200
    assert len((await api_client.get("/api/v1/clients")).json()) == 1
    assert await db_session.scalar(select(func.count()).select_from(ClientAssignment)) == 0


async def test_cross_organization_and_unknown_ids_are_rejected(
    team: Team,
    db_session: AsyncSession,
    api_client: AsyncClient,
) -> None:
    org = Organization(name="Foreign", mode=OrganizationMode.BUSINESS)
    db_session.add(org)
    await db_session.flush()
    foreign = User(
        organization_id=org.id,
        full_name="Foreign",
        email="foreign@example.com",
        role=UserRole.EMPLOYEE,
        status=UserStatus.PENDING,
    )
    client = Client(organization_id=org.id, name="Foreign Client")
    db_session.add_all([foreign, client])
    await db_session.commit()
    headers = await login(api_client, team.users["owner"])
    for client_id in [client.id, uuid4()]:
        endpoint = f"/api/v1/clients/{client_id}/assignments"
        assert (await api_client.get(endpoint)).status_code == 404
        assert (
            await api_client.post(
                endpoint, headers=headers, json={"user_id": str(team.users["employee"].id)}
            )
        ).status_code == 404
        assert (
            await api_client.delete(f"{endpoint}/{team.users['employee'].id}", headers=headers)
        ).status_code == 404
    for user_id in [foreign.id, uuid4()]:
        assert (
            await api_client.post(path(team), headers=headers, json={"user_id": str(user_id)})
        ).status_code == 404
        assert (
            await api_client.delete(f"{path(team)}/{user_id}", headers=headers)
        ).status_code == 404


@pytest.mark.parametrize("field", ["client_id", "user_id", "assigned_by_user_id"])
async def test_database_rejects_cross_organization_links(
    team: Team,
    db_session: AsyncSession,
    field: str,
) -> None:
    org = Organization(name="Foreign", mode=OrganizationMode.BUSINESS)
    db_session.add(org)
    await db_session.flush()
    foreign_user = User(
        organization_id=org.id,
        full_name="Foreign",
        email="foreign@example.com",
        role=UserRole.EMPLOYEE,
        status=UserStatus.PENDING,
    )
    foreign_client = Client(organization_id=org.id, name="Foreign Client")
    db_session.add_all([foreign_user, foreign_client])
    await db_session.flush()
    values = {
        "organization_id": team.client.organization_id,
        "client_id": team.client.id,
        "user_id": team.users["employee"].id,
        "assigned_by_user_id": team.users["owner"].id,
    }
    values[field] = foreign_client.id if field == "client_id" else foreign_user.id
    with pytest.raises(IntegrityError):
        async with db_session.begin_nested():
            db_session.add(ClientAssignment(**values))
            await db_session.flush()


@pytest.mark.parametrize("remove", [False, True])
async def test_audit_failure_rolls_back_assignment_mutation(
    team: Team,
    db_session: AsyncSession,
    api_client: AsyncClient,
    monkeypatch: pytest.MonkeyPatch,
    remove: bool,
) -> None:
    headers = await login(api_client, team.users["owner"])
    body = {"user_id": str(team.users["employee"].id)}
    if remove:
        assert (await api_client.post(path(team), headers=headers, json=body)).status_code == 201

    def fail_audit(*args: object, **kwargs: object) -> None:
        raise RuntimeError("Audit unavailable")

    monkeypatch.setattr(assignments, "add_audit_event", fail_audit)
    with pytest.raises(RuntimeError, match="Audit unavailable"):
        if remove:
            await api_client.delete(f"{path(team)}/{team.users['employee'].id}", headers=headers)
        else:
            await api_client.post(path(team), headers=headers, json=body)
    assert await db_session.scalar(select(func.count()).select_from(ClientAssignment)) == int(
        remove
    )


async def test_membership_changes_update_admin_scope_and_disabled_assignments_can_be_removed(
    team: Team,
    db_session: AsyncSession,
    api_client: AsyncClient,
) -> None:
    headers = await login(api_client, team.users["admin"])
    assert (
        await api_client.post(
            path(team), headers=headers, json={"user_id": str(team.users["employee"].id)}
        )
    ).status_code == 201
    await db_session.execute(
        delete(DepartmentMember).where(
            DepartmentMember.user_id == team.users["employee"].id,
            DepartmentMember.department_id == team.department.id,
        )
    )
    team.users["employee"].status = UserStatus.DISABLED
    await db_session.commit()
    assert (await api_client.get(path(team))).json()["assigned"] == []
    assert (
        await api_client.delete(f"{path(team)}/{team.users['employee'].id}", headers=headers)
    ).status_code == 403
    headers = await login(api_client, team.users["owner"])
    result = (await api_client.get(path(team))).json()
    assert result["assigned"][0]["status"] == "DISABLED"
    assert (
        await api_client.delete(f"{path(team)}/{team.users['employee'].id}", headers=headers)
    ).status_code == 204
