import asyncio
from datetime import UTC, date, datetime
from uuid import UUID, uuid4

import pytest
from httpx import AsyncClient
from sqlalchemy import delete, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from test_activities import assign
from test_assignments import PASSWORD, Team, login
from test_assignments import team as team

from app.models import (
    Activity,
    AuditLog,
    Client,
    ClientAssignment,
    Department,
    DepartmentMember,
    Organization,
    OrganizationMode,
    User,
    UserRole,
    UserStatus,
)
from app.models.activity_type import activity_type_identifier
from app.services import activities
from app.services.bootstrap import bootstrap_organization


def path(value: Team) -> str:
    return f"/api/v1/clients/{value.client.id}/tasks"


def body(**kwargs: object) -> dict[str, object]:
    return {"title": "Call the client", "description": "Discuss the open issue", **kwargs}


def task_record(**values: object) -> Activity:
    organization_id = values["organization_id"]
    assert isinstance(organization_id, UUID)
    values.setdefault("activity_type_id", activity_type_identifier(organization_id, "otro"))
    creator = values.pop("created_by_user_id")
    values.setdefault("user_id", creator)
    values.setdefault("status", "PENDING")
    values.setdefault("description", values["title"])
    values.setdefault("occurred_at", values.get("completed_at"))
    due_at = values.pop("due_at", None)
    values.setdefault(
        "scheduled_for",
        due_at.date() if isinstance(due_at, datetime) else date.today(),
    )
    return Activity(**values)


async def test_admin_assigns_employee_edits_completes_and_audit_is_idempotent(
    team: Team,
    api_client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    await assign(db_session, team)
    headers = await login(api_client, team.users["admin"])
    response = await api_client.post(
        path(team), headers=headers, json=body(assigned_to_user_id=str(team.users["employee"].id))
    )
    assert response.status_code == 201
    identifier = response.json()["id"]
    assert (await api_client.get("/api/v1/tasks/mine")).json()["items"] == []
    headers = await login(api_client, team.users["employee"])
    item = (await api_client.get("/api/v1/tasks/mine")).json()["items"][0]
    assert item["due_at"] == date.today().isoformat() and item["status"] == "PENDING"
    assert item["department_id"] == str(team.department.id)
    assert item["created_by_user_id"] == str(team.users["admin"].id)
    assert (
        await api_client.patch(
            f"{path(team)}/{identifier}",
            headers=headers,
            json=body(title="Updated", due_at="2026-10-01T10:00:00Z"),
        )
    ).status_code == 204
    responses = await asyncio.gather(
        *[api_client.post(f"{path(team)}/{identifier}/complete", headers=headers) for _ in range(2)]
    )
    assert [r.status_code for r in responses] == [204, 204]
    item = (await api_client.get("/api/v1/tasks/mine?status=COMPLETED")).json()["items"][0]
    assert item["completed_at"] is not None and item["title"] == "Updated"
    assert (
        await api_client.patch(f"{path(team)}/{identifier}", headers=headers, json=body())
    ).status_code == 409
    assert (
        await api_client.delete(f"{path(team)}/{identifier}", headers=headers)
    ).status_code == 405
    events = list(
        await db_session.scalars(select(AuditLog).where(AuditLog.entity_type == "ACTIVITY"))
    )
    assert [e.action for e in events].count("COMPLETED_ACTIVITY") == 1
    assert {e.action for e in events} == {
        "CREATED_ACTIVITY",
        "UPDATED_ACTIVITY",
        "COMPLETED_ACTIVITY",
    }
    assert all("Discuss the open issue" not in str(e.event_data) for e in events)


async def test_owner_reassignment_changes_my_tasks_and_is_audited(
    team: Team,
    api_client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    await assign(db_session, team)
    headers = await login(api_client, team.users["owner"])
    response = await api_client.post(
        path(team), headers=headers, json=body(department_id=str(team.department.id))
    )
    identifier = response.json()["id"]
    assert len((await api_client.get("/api/v1/tasks/mine")).json()["items"]) == 1
    assert (
        await api_client.patch(
            f"{path(team)}/{identifier}",
            headers=headers,
            json=body(assigned_to_user_id=str(team.users["employee"].id)),
        )
    ).status_code == 204
    assert (await api_client.get("/api/v1/tasks/mine")).json()["items"] == []
    await login(api_client, team.users["employee"])
    assert len((await api_client.get("/api/v1/tasks/mine")).json()["items"]) == 1
    event = await db_session.scalar(select(AuditLog).where(AuditLog.action == "UPDATED_ACTIVITY"))
    assert event and "assigned_to_user_id" in event.event_data["changed_fields"]


async def test_employee_can_create_only_own_tasks_on_assigned_clients(
    team: Team,
    api_client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    headers = await login(api_client, team.users["employee"])
    assert (await api_client.post(path(team), headers=headers, json=body())).status_code == 403
    await assign(db_session, team)
    assert (await api_client.post(path(team), headers=headers, json=body())).status_code == 409
    payload = body(department_id=str(team.department.id))
    response = await api_client.post(path(team), headers=headers, json=payload)
    assert response.status_code == 201
    identifier = response.json()["id"]
    payload["assigned_to_user_id"] = str(team.users["admin"].id)
    assert (await api_client.post(path(team), headers=headers, json=payload)).status_code == 403
    assert (
        await api_client.patch(
            f"{path(team)}/{identifier}",
            headers=headers,
            json=body(assigned_to_user_id=str(team.users["admin"].id)),
        )
    ).status_code == 403
    options = (await api_client.get(path(team))).json()["options"]
    assert [u["id"] for u in options["candidates"]] == [str(team.users["employee"].id)]


@pytest.mark.parametrize(
    "target", ["employee", "pending", "disabled", "hidden", "no_department", "owner"]
)
async def test_admin_cannot_assign_ineligible_or_out_of_scope_users(
    team: Team,
    api_client: AsyncClient,
    target: str,
) -> None:
    headers = await login(api_client, team.users["admin"])
    assert (
        await api_client.post(
            path(team), headers=headers, json=body(assigned_to_user_id=str(team.users[target].id))
        )
    ).status_code == 403


async def test_department_and_user_scope_apply_to_list_and_mutations(
    team: Team,
    api_client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    await assign(db_session, team, "hidden")
    other = await db_session.scalar(select(Department).where(Department.id != team.department.id))
    assert other is not None
    headers = await login(api_client, team.users["owner"])
    hidden = (
        await api_client.post(
            path(team),
            headers=headers,
            json=body(
                department_id=str(other.id), assigned_to_user_id=str(team.users["hidden"].id)
            ),
        )
    ).json()["id"]
    owner_task = (
        await api_client.post(
            path(team), headers=headers, json=body(department_id=str(team.department.id))
        )
    ).json()["id"]
    headers = await login(api_client, team.users["admin"])
    assert (await api_client.get(path(team))).json()["items"] == []
    for identifier in [hidden, owner_task]:
        assert (
            await api_client.post(f"{path(team)}/{identifier}/complete", headers=headers)
        ).status_code == 404
        assert (
            await api_client.patch(f"{path(team)}/{identifier}", headers=headers, json=body())
        ).status_code == 404
    assert (
        await api_client.post(path(team), headers=headers, json=body(department_id=str(other.id)))
    ).status_code == 403


async def test_revocation_and_membership_change_do_not_destroy_tasks(
    team: Team,
    api_client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    await assign(db_session, team)
    headers = await login(api_client, team.users["admin"])
    identifier = (
        await api_client.post(
            path(team),
            headers=headers,
            json=body(assigned_to_user_id=str(team.users["employee"].id)),
        )
    ).json()["id"]
    await db_session.execute(
        delete(DepartmentMember).where(
            DepartmentMember.user_id == team.users["employee"].id,
            DepartmentMember.department_id == team.department.id,
        )
    )
    await db_session.commit()
    headers = await login(api_client, team.users["employee"])
    assert (await api_client.get("/api/v1/tasks/mine")).json()["items"] == []
    assert (
        await api_client.post(f"{path(team)}/{identifier}/complete", headers=headers)
    ).status_code == 404
    await db_session.execute(delete(ClientAssignment))
    await db_session.commit()
    assert (await api_client.get(path(team))).status_code == 403
    assert (
        await api_client.post(f"{path(team)}/{identifier}/complete", headers=headers)
    ).status_code == 403
    headers = await login(api_client, team.users["admin"])
    assert len((await api_client.get(path(team))).json()["items"]) == 1
    assert (
        await api_client.patch(
            f"{path(team)}/{identifier}",
            headers=headers,
            json=body(assigned_to_user_id=str(team.users["admin"].id)),
        )
    ).status_code == 204
    saved = await db_session.get(Activity, identifier)
    assert saved and saved.department_id == team.department.id


async def test_individual_owner_uses_no_department_and_no_assignee_selection(
    api_client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    organization, owner = await bootstrap_organization(
        db_session,
        mode=OrganizationMode.INDIVIDUAL,
        organization_name="Personal",
        owner_name="Owner",
        owner_email="owner@example.com",
        owner_password=PASSWORD,
    )
    client = Client(organization_id=organization.id, name="Personal")
    db_session.add(client)
    await db_session.commit()
    headers = await login(api_client, owner)
    endpoint = f"/api/v1/clients/{client.id}/tasks"
    result = await api_client.post(endpoint, headers=headers, json=body())
    assert result.status_code == 201
    page = (await api_client.get(endpoint)).json()
    assert page["options"]["individual"] and page["options"]["departments"] == []
    assert page["items"][0]["department_id"] is None
    assert page["items"][0]["assigned_to_user_id"] == str(owner.id)
    assert (
        await api_client.post(endpoint, headers=headers, json=body(department_id=str(uuid4())))
    ).status_code == 403
    assert (
        await api_client.post(f"{endpoint}/{result.json()['id']}/complete", headers=headers)
    ).status_code == 204


@pytest.mark.parametrize(
    "invalid",
    [
        {"title": " "},
        {"title": "x" * 201},
        {"description": "x" * 5001},
        {"due_at": "2026-10-01T10:00:00"},
        {"status": "COMPLETED"},
        {"created_by_user_id": str(uuid4())},
        {"organization_id": str(uuid4())},
    ],
)
async def test_invalid_fields_and_identity_injection(
    team: Team, api_client: AsyncClient, invalid: dict[str, object]
) -> None:
    headers = await login(api_client, team.users["admin"])
    assert (
        await api_client.post(path(team), headers=headers, json=body(**invalid))
    ).status_code == 422


async def test_auth_csrf_cross_org_unknown_ids_and_immutable_department(
    team: Team,
    api_client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    assert (await api_client.get(path(team))).status_code == 401
    assert (await api_client.get("/api/v1/tasks/mine")).status_code == 401
    headers = await login(api_client, team.users["admin"])
    assert (await api_client.post(path(team), json=body())).status_code == 403
    identifier = (await api_client.post(path(team), headers=headers, json=body())).json()["id"]
    assert (await api_client.patch(f"{path(team)}/{identifier}", json=body())).status_code == 403
    assert (await api_client.post(f"{path(team)}/{identifier}/complete")).status_code == 403
    assert (
        await api_client.patch(
            f"{path(team)}/{identifier}",
            headers=headers,
            json=body(department_id=str(team.department.id)),
        )
    ).status_code == 422
    org = Organization(name="Foreign", mode=OrganizationMode.BUSINESS)
    db_session.add(org)
    await db_session.flush()
    client = Client(organization_id=org.id, name="Foreign")
    db_session.add(client)
    await db_session.commit()
    for client_id in [client.id, uuid4()]:
        endpoint = f"/api/v1/clients/{client_id}/tasks"
        assert (await api_client.get(endpoint)).status_code == 404
        assert (await api_client.post(endpoint, headers=headers, json=body())).status_code == 404
        assert (
            await api_client.post(f"{endpoint}/{identifier}/complete", headers=headers)
        ).status_code == 404
    assert (
        await api_client.post(f"{path(team)}/{uuid4()}/complete", headers=headers)
    ).status_code == 404


@pytest.mark.parametrize(
    "field", ["client_id", "assigned_to_user_id", "created_by_user_id", "department_id"]
)
async def test_cross_organization_foreign_keys(
    team: Team, db_session: AsyncSession, field: str
) -> None:
    org = Organization(name="Foreign", mode=OrganizationMode.BUSINESS)
    db_session.add(org)
    await db_session.flush()
    user = User(
        organization_id=org.id,
        email="foreign@example.com",
        full_name="Foreign",
        role=UserRole.EMPLOYEE,
        status=UserStatus.PENDING,
    )
    department = Department(organization_id=org.id, name="Foreign", normalized_name="foreign")
    client = Client(organization_id=org.id, name="Foreign")
    db_session.add_all([user, department, client])
    await db_session.flush()
    values = dict(
        organization_id=team.client.organization_id,
        client_id=team.client.id,
        assigned_to_user_id=team.users["owner"].id,
        created_by_user_id=team.users["owner"].id,
        department_id=team.department.id,
        title="Test",
    )
    values[field] = {
        "client_id": client.id,
        "assigned_to_user_id": user.id,
        "created_by_user_id": user.id,
        "department_id": department.id,
    }[field]
    with pytest.raises(IntegrityError):
        async with db_session.begin_nested():
            db_session.add(task_record(**values))
            await db_session.flush()


@pytest.mark.parametrize("operation", ["create", "update", "reassign", "complete"])
async def test_audit_failure_rolls_back_mutation(
    team: Team,
    api_client: AsyncClient,
    db_session: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
    operation: str,
) -> None:
    await assign(db_session, team)
    headers = await login(api_client, team.users["admin"])
    identifier = None
    if operation != "create":
        identifier = (await api_client.post(path(team), headers=headers, json=body())).json()["id"]

    def fail(*args: object, **kwargs: object) -> None:
        raise RuntimeError("Audit unavailable")

    monkeypatch.setattr(activities, "add_audit_event", fail)
    with pytest.raises(RuntimeError, match="Audit unavailable"):
        if operation == "create":
            await api_client.post(path(team), headers=headers, json=body())
        elif operation == "complete":
            await api_client.post(f"{path(team)}/{identifier}/complete", headers=headers)
        else:
            await api_client.patch(
                f"{path(team)}/{identifier}",
                headers=headers,
                json=body(
                    title="Changed",
                    assigned_to_user_id=str(team.users["employee"].id)
                    if operation == "reassign"
                    else None,
                ),
            )
    assert await db_session.scalar(
        select(func.count()).select_from(Activity)
    ) == int(operation != "create")
    if identifier:
        saved = await db_session.get(Activity, identifier)
        assert saved and saved.title == "Call the client" and saved.status == "PENDING"
        assert saved.assigned_to_user_id == team.users["admin"].id


async def test_pagination_status_null_due_date_and_department_deletion(
    team: Team, api_client: AsyncClient
) -> None:
    headers = await login(api_client, team.users["admin"])
    for due in [None, "2026-10-01T10:00:00Z", "2026-09-01T10:00:00Z"]:
        assert (
            await api_client.post(path(team), headers=headers, json=body(due_at=due))
        ).status_code == 201
    first = (await api_client.get(f"{path(team)}?limit=2&status=PENDING")).json()
    second = (await api_client.get(f"{path(team)}?limit=2&offset=2")).json()
    assert first["has_more"] and not second["has_more"]
    assert first["items"][0]["due_at"].startswith("2026-09-01")
    assert second["items"][0]["due_at"].startswith("2026-10-01")
    for query in ["limit=101", "offset=-1", "status=OTHER"]:
        assert (await api_client.get(f"{path(team)}?{query}")).status_code == 422
    headers = await login(api_client, team.users["owner"])
    assert (
        await api_client.delete(f"/api/v1/admin/departments/{team.department.id}", headers=headers)
    ).status_code == 409


@pytest.mark.parametrize(
    "status,completed", [("OTHER", None), ("COMPLETED", None), ("PENDING", datetime.now(UTC))]
)
async def test_database_completion_invariant(
    team: Team, db_session: AsyncSession, status: str, completed: datetime | None
) -> None:
    with pytest.raises(IntegrityError):
        async with db_session.begin_nested():
            db_session.add(
                task_record(
                    organization_id=team.client.organization_id,
                    client_id=team.client.id,
                    assigned_to_user_id=team.users["owner"].id,
                    created_by_user_id=team.users["owner"].id,
                    department_id=team.department.id,
                    title="Test",
                    status=status,
                    completed_at=completed,
                )
            )
            await db_session.flush()
