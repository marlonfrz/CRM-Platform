from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from httpx import AsyncClient
from sqlalchemy import delete, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
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
from app.policies.activities import can_correct_activity
from app.policies.authorization import AuthorizationContext
from app.services import activities
from app.services.bootstrap import bootstrap_organization


def path(value: Team) -> str:
    return f"/api/v1/clients/{value.client.id}/activities"


def body(**kwargs: object) -> dict[str, object]:
    return {
        "type": "CALL",
        "description": "Called the client",
        "next_action": "Follow up",
        "occurred_at": datetime.now(UTC).isoformat(),
        **kwargs,
    }


async def assign(db: AsyncSession, value: Team, name: str = "employee") -> None:
    db.add(
        ClientAssignment(
            organization_id=value.client.organization_id,
            client_id=value.client.id,
            user_id=value.users[name].id,
            assigned_by_user_id=value.users["owner"].id,
        )
    )
    await db.commit()


async def test_automatic_department_author_filters_and_correction(
    team: Team,
    api_client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    headers = await login(api_client, team.users["admin"])
    response = await api_client.post(path(team), headers=headers, json=body())
    assert response.status_code == 201
    identifier = response.json()["id"]
    page = (await api_client.get(path(team))).json()
    item = page["items"][0]
    assert item["department_id"] == str(team.department.id)
    assert item["user_id"] == str(team.users["admin"].id)
    assert item["can_edit"] and page["can_create"]
    assert len(page["departments"]) == 1
    assert (await api_client.get(f"{path(team)}?activity_type=NOTE")).json()["items"] == []
    assert (await api_client.get(f"{path(team)}?department_id={uuid4()}")).json()["items"] == []
    updated = await api_client.patch(
        f"{path(team)}/{identifier}", headers=headers, json=body(description="Corrected")
    )
    assert updated.status_code == 204
    item = (await api_client.get(path(team))).json()["items"][0]
    assert item["description"] == "Corrected"
    assert item["user_id"] == str(team.users["admin"].id)
    assert item["department_id"] == str(team.department.id)
    assert (
        await api_client.delete(f"{path(team)}/{identifier}", headers=headers)
    ).status_code == 405
    events = list(
        await db_session.scalars(select(AuditLog).where(AuditLog.entity_type == "ACTIVITY"))
    )
    assert {e.action for e in events} == {"CREATED_ACTIVITY", "UPDATED_ACTIVITY"}
    assert (
        "description"
        in next(e for e in events if e.action == "UPDATED_ACTIVITY").event_data["changed_fields"]
    )
    assert all(
        "Called the client" not in str(e.event_data) and "Corrected" not in str(e.event_data)
        for e in events
    )


async def test_multiple_departments_require_choice_and_scope_is_applied_in_sql(
    team: Team,
    api_client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    await assign(db_session, team)
    headers = await login(api_client, team.users["employee"])
    assert (await api_client.post(path(team), headers=headers, json=body())).status_code == 409
    department_ids = [d["id"] for d in (await api_client.get(path(team))).json()["departments"]]
    identifiers = []
    for dep in department_ids:
        result = await api_client.post(path(team), headers=headers, json=body(department_id=dep))
        assert result.status_code == 201
        identifiers.append(result.json()["id"])
    assert len((await api_client.get(path(team))).json()["items"]) == 2
    headers = await login(api_client, team.users["admin"])
    items = (await api_client.get(path(team))).json()["items"]
    assert len(items) == 1 and items[0]["department_id"] == str(team.department.id)
    hidden_id = next(identifier for identifier in identifiers if identifier != items[0]["id"])
    assert (
        await api_client.patch(f"{path(team)}/{hidden_id}", headers=headers, json=body())
    ).status_code == 404
    foreign_dep = next(dep for dep in department_ids if dep != str(team.department.id))
    assert (await api_client.get(f"{path(team)}?department_id={foreign_dep}")).json()["items"] == []
    assert (
        await api_client.post(path(team), headers=headers, json=body(department_id=foreign_dep))
    ).status_code == 403
    headers = await login(api_client, team.users["owner"])
    assert len((await api_client.get(path(team))).json()["items"]) == 2
    assert (
        await api_client.post(path(team), headers=headers, json=body(department_id=foreign_dep))
    ).status_code == 201


async def test_membership_changes_preserve_history_and_assignment_removal_revokes_access(
    team: Team,
    api_client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    await assign(db_session, team)
    headers = await login(api_client, team.users["employee"])
    created = await api_client.post(
        path(team), headers=headers, json=body(department_id=str(team.department.id))
    )
    identifier = created.json()["id"]
    await db_session.execute(
        delete(DepartmentMember).where(
            DepartmentMember.user_id == team.users["employee"].id,
            DepartmentMember.department_id == team.department.id,
        )
    )
    await db_session.commit()
    assert (await api_client.get(path(team))).json()["items"] == []
    assert (
        await api_client.patch(f"{path(team)}/{identifier}", headers=headers, json=body())
    ).status_code == 404
    activity = await db_session.get(Activity, identifier)
    assert activity and activity.department_id == team.department.id
    assert activity.user_id == team.users["employee"].id
    await db_session.execute(delete(ClientAssignment))
    await db_session.commit()
    assert (await api_client.get(path(team))).status_code == 403
    assert (await api_client.post(path(team), headers=headers, json=body())).status_code == 403
    await login(api_client, team.users["owner"])
    assert len((await api_client.get(path(team))).json()["items"]) == 1


async def test_employee_cannot_correct_another_author_and_owner_can(
    team: Team,
    api_client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    headers = await login(api_client, team.users["admin"])
    result = await api_client.post(path(team), headers=headers, json=body())
    identifier = result.json()["id"]
    await assign(db_session, team)
    headers = await login(api_client, team.users["employee"])
    assert not (await api_client.get(path(team))).json()["items"][0]["can_edit"]
    assert (
        await api_client.patch(f"{path(team)}/{identifier}", headers=headers, json=body())
    ).status_code == 403
    headers = await login(api_client, team.users["owner"])
    assert (
        await api_client.patch(
            f"{path(team)}/{identifier}", headers=headers, json=body(description="Owner correction")
        )
    ).status_code == 204


@pytest.mark.parametrize("role", ["OWNER", "ADMIN", "EMPLOYEE"])
def test_correction_window_is_strictly_less_than_24_hours(role: str) -> None:
    user_id, organization_id, department_id = uuid4(), uuid4(), uuid4()
    authorization = AuthorizationContext(
        user_id,
        organization_id,
        OrganizationMode.BUSINESS,
        UserRole(role),
        frozenset([department_id]),
    )
    created = datetime(2026, 9, 7, tzinfo=UTC)
    values = dict(
        organization_id=organization_id,
        department_id=department_id,
        author_id=user_id,
        created_at=created,
        is_client_assigned=True,
    )
    assert can_correct_activity(
        authorization, now=created + timedelta(hours=24, microseconds=-1), **values
    )
    assert not can_correct_activity(authorization, now=created + timedelta(hours=24), **values)


async def test_old_record_cannot_be_corrected_even_by_owner(
    team: Team,
    api_client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    activity = Activity(
        organization_id=team.client.organization_id,
        client_id=team.client.id,
        user_id=team.users["owner"].id,
        department_id=team.department.id,
        type="NOTE",
        description="Historical",
        occurred_at=datetime.now(UTC),
        created_at=datetime.now(UTC) - timedelta(days=2),
    )
    db_session.add(activity)
    await db_session.commit()
    headers = await login(api_client, team.users["owner"])
    assert not (await api_client.get(path(team))).json()["items"][0]["can_edit"]
    assert (
        await api_client.patch(f"{path(team)}/{activity.id}", headers=headers, json=body())
    ).status_code == 403


async def test_individual_mode_has_no_departments(
    api_client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    org, owner = await bootstrap_organization(
        db_session,
        mode=OrganizationMode.INDIVIDUAL,
        organization_name="Personal",
        owner_name="Owner",
        owner_email="owner@example.com",
        owner_password=PASSWORD,
    )
    client = Client(organization_id=org.id, name="Personal client")
    db_session.add(client)
    await db_session.commit()
    headers = await login(api_client, owner)
    endpoint = f"/api/v1/clients/{client.id}/activities"
    assert (await api_client.post(endpoint, headers=headers, json=body())).status_code == 201
    page = (await api_client.get(endpoint)).json()
    assert page["departments"] == [] and page["can_create"]
    assert page["items"][0]["department_id"] is None
    assert (
        await api_client.post(endpoint, headers=headers, json=body(department_id=str(uuid4())))
    ).status_code == 403


@pytest.mark.parametrize(
    "invalid",
    [
        {"user_id": str(uuid4())},
        {"organization_id": str(uuid4())},
        {"description": "   "},
        {"description": "x" * 5001},
        {"next_action": "x" * 2001},
        {"type": "CUSTOM"},
        {"occurred_at": "2026-09-07T12:00:00"},
    ],
)
async def test_invalid_payloads_and_spoofed_identity(
    team: Team,
    api_client: AsyncClient,
    invalid: dict[str, object],
) -> None:
    headers = await login(api_client, team.users["admin"])
    assert (
        await api_client.post(path(team), headers=headers, json=body(**invalid))
    ).status_code == 422


async def test_auth_csrf_immutable_department_unknown_and_cross_org_ids(
    team: Team,
    api_client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    assert (await api_client.get(path(team))).status_code == 401
    assert (await api_client.post(path(team), json=body())).status_code == 401
    headers = await login(api_client, team.users["admin"])
    assert (await api_client.post(path(team), json=body())).status_code == 403
    created = await api_client.post(path(team), headers=headers, json=body())
    identifier = created.json()["id"]
    assert (await api_client.patch(f"{path(team)}/{identifier}", json=body())).status_code == 403
    assert (
        await api_client.patch(
            f"{path(team)}/{identifier}",
            headers=headers,
            json=body(department_id=str(team.department.id)),
        )
    ).status_code == 422
    assert (
        await api_client.patch(f"{path(team)}/{uuid4()}", headers=headers, json=body())
    ).status_code == 404
    org = Organization(name="Foreign", mode=OrganizationMode.BUSINESS)
    db_session.add(org)
    await db_session.flush()
    client = Client(organization_id=org.id, name="Foreign Client")
    db_session.add(client)
    await db_session.commit()
    for client_id in [client.id, uuid4(), team.other_client.id]:
        endpoint = f"/api/v1/clients/{client_id}/activities"
        assert (
            await api_client.patch(f"{endpoint}/{identifier}", headers=headers, json=body())
        ).status_code == 404
        if client_id != team.other_client.id:
            assert (await api_client.get(endpoint)).status_code == 404
            assert (
                await api_client.post(endpoint, headers=headers, json=body())
            ).status_code == 404


@pytest.mark.parametrize("field", ["client_id", "user_id", "department_id"])
async def test_database_prevents_cross_organization_activity_links(
    team: Team,
    db_session: AsyncSession,
    field: str,
) -> None:
    org = Organization(name="Foreign", mode=OrganizationMode.BUSINESS)
    db_session.add(org)
    await db_session.flush()
    client = Client(organization_id=org.id, name="Foreign")
    user = User(
        organization_id=org.id,
        full_name="Foreign",
        email="foreign@example.com",
        role=UserRole.EMPLOYEE,
        status=UserStatus.PENDING,
    )
    dep = Department(organization_id=org.id, name="Foreign", normalized_name="foreign")
    db_session.add_all([client, user, dep])
    await db_session.flush()
    values = dict(
        organization_id=team.client.organization_id,
        client_id=team.client.id,
        user_id=team.users["owner"].id,
        department_id=team.department.id,
        type="NOTE",
        description="Test",
        occurred_at=datetime.now(UTC),
    )
    values[field] = {"client_id": client.id, "user_id": user.id, "department_id": dep.id}[field]
    with pytest.raises(IntegrityError):
        async with db_session.begin_nested():
            db_session.add(Activity(**values))
            await db_session.flush()


@pytest.mark.parametrize("correct", [False, True])
async def test_failed_audit_rolls_back_activity_write(
    team: Team,
    api_client: AsyncClient,
    db_session: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
    correct: bool,
) -> None:
    headers = await login(api_client, team.users["admin"])
    identifier = None
    if correct:
        identifier = (await api_client.post(path(team), headers=headers, json=body())).json()["id"]

    def fail(*args: object, **kwargs: object) -> None:
        raise RuntimeError("Audit unavailable")

    monkeypatch.setattr(activities, "add_audit_event", fail)
    with pytest.raises(RuntimeError, match="Audit unavailable"):
        if correct:
            await api_client.patch(
                f"{path(team)}/{identifier}",
                headers=headers,
                json=body(description="Should roll back"),
            )
        else:
            await api_client.post(path(team), headers=headers, json=body())
    assert await db_session.scalar(select(func.count()).select_from(Activity)) == int(correct)
    if correct:
        assert await db_session.scalar(select(Activity.description)) == "Called the client"


async def test_pagination_is_bounded_ordered_and_filters_do_not_leak(
    team: Team,
    api_client: AsyncClient,
) -> None:
    headers = await login(api_client, team.users["admin"])
    for day in range(1, 4):
        assert (
            await api_client.post(
                path(team), headers=headers, json=body(occurred_at=f"2026-09-0{day}T12:00:00Z")
            )
        ).status_code == 201
    first = (await api_client.get(f"{path(team)}?limit=2")).json()
    second = (await api_client.get(f"{path(team)}?limit=2&offset=2")).json()
    assert first["has_more"] and not second["has_more"]
    assert len(first["items"]) == 2 and len(second["items"]) == 1
    assert first["items"][0]["occurred_at"].startswith("2026-09-03")
    assert not {i["id"] for i in first["items"]} & {i["id"] for i in second["items"]}
    for query in ["limit=101", "offset=-1", "activity_type=HACK", "department_id=invalid"]:
        assert (await api_client.get(f"{path(team)}?{query}")).status_code == 422


async def test_department_with_history_cannot_be_deleted(
    team: Team,
    api_client: AsyncClient,
) -> None:
    headers = await login(api_client, team.users["admin"])
    assert (await api_client.post(path(team), headers=headers, json=body())).status_code == 201
    headers = await login(api_client, team.users["owner"])
    result = await api_client.delete(
        f"/api/v1/admin/departments/{team.department.id}", headers=headers
    )
    assert result.status_code == 409
    assert len((await api_client.get(path(team))).json()["items"]) == 1
