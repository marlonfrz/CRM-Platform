from datetime import UTC, datetime
from uuid import uuid4

import pytest
from httpx import AsyncClient
from sqlalchemy import event, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from test_assignments import PASSWORD, Team, login
from test_assignments import team as team

from app.models import AuditLog, Client, Department, Organization, OrganizationMode, User
from app.schemas.audit import EVENT_FIELDS, readable_metadata, validate_metadata
from app.services.bootstrap import bootstrap_organization


@pytest.mark.parametrize("role", ["admin", "employee"])
async def test_audit_owner_only(team: Team, api_client: AsyncClient, role: str) -> None:
    assert (await api_client.get("/api/v1/audit")).status_code == 401
    await login(api_client, team.users[role])
    assert (await api_client.get("/api/v1/audit")).status_code == 403


async def test_audit_scope_filters_pagination_and_legacy_privacy(
    team: Team, api_client: AsyncClient, db_session: AsyncSession
) -> None:
    other = Organization(name="Other", mode=OrganizationMode.BUSINESS)
    db_session.add(other)
    await db_session.flush()
    timestamp = datetime(2026, 1, 1, tzinfo=UTC)
    foreign_entity_id = uuid4()
    ids = [uuid4() for _ in range(3)]
    for identifier in ids:
        db_session.add(
            AuditLog(
                id=identifier,
                organization_id=team.client.organization_id,
                actor_user_id=team.users["owner"].id,
                action="CREATED_USER",
                entity_type="USER",
                entity_id=team.users["employee"].id,
                created_at=timestamp,
                event_data={"role": "EMPLOYEE", "email": "private@example.com", "token": "secret"},
            )
        )
    db_session.add(
        AuditLog(
            organization_id=other.id,
            actor_user_id=None,
            action="CREATED_USER",
            entity_type="USER",
            entity_id=foreign_entity_id,
            event_data={"name": "hidden"},
            created_at=timestamp,
        )
    )
    await db_session.commit()
    await login(api_client, team.users["owner"])
    params = {
        "action": "CREATED_USER",
        "actor_user_id": str(team.users["owner"].id),
        "entity_id": str(team.users["employee"].id),
        "since": timestamp.isoformat(),
        "until": timestamp.isoformat(),
        "limit": 2,
    }
    first = await api_client.get("/api/v1/audit", params=params)
    second = await api_client.get("/api/v1/audit", params={**params, "offset": 2})
    assert first.status_code == second.status_code == 200
    assert first.json()["has_more"] and not second.json()["has_more"]
    rows = first.json()["items"] + second.json()["items"]
    assert [row["id"] for row in rows] == sorted(map(str, ids), reverse=True)
    assert all(row["metadata"] == {"role": "EMPLOYEE"} for row in rows)
    assert all(row["actor_name"] == "Owner" for row in rows)
    assert "private@example.com" not in first.text and "secret" not in first.text
    assert (
        await api_client.get("/api/v1/audit", params={"entity_id": str(foreign_entity_id)})
    ).json()["items"] == []
    unscoped = await api_client.get("/api/v1/audit?action=CREATED_USER")
    assert len(unscoped.json()["items"]) == 3
    assert all(
        row["actor_user_id"] == str(team.users["owner"].id) for row in unscoped.json()["items"]
    )
    raw = await db_session.scalar(select(AuditLog).where(AuditLog.id == ids[0]))
    assert raw and raw.event_data["token"] == "secret"


@pytest.mark.parametrize(
    "query",
    [
        "offset=-1",
        "limit=101",
        "actor_user_id=invalid",
        "action=bad",
        "since=2026-01-01T00:00:00",
        "since=2026-02-01T00:00:00Z&until=2026-01-01T00:00:00Z",
    ],
)
async def test_invalid_audit_filters(team: Team, api_client: AsyncClient, query: str) -> None:
    await login(api_client, team.users["owner"])
    assert (await api_client.get(f"/api/v1/audit?{query}")).status_code == 422


async def test_individual_bootstrap_and_read_only_api(
    db_session: AsyncSession, api_client: AsyncClient
) -> None:
    _, owner = await bootstrap_organization(
        db_session,
        mode=OrganizationMode.INDIVIDUAL,
        organization_name="Personal",
        owner_name="Owner",
        owner_email="owner@example.com",
        owner_password=PASSWORD,
    )
    await db_session.commit()
    headers = await login(api_client, owner)
    response = await api_client.get("/api/v1/audit?action=INITIALIZED_ORGANIZATION")
    assert response.status_code == 200
    record = response.json()["items"][0]
    assert record["actor_user_id"] == str(owner.id) and record["metadata"] == {}
    for method in ["POST", "PATCH", "PUT", "DELETE"]:
        for path in ["/api/v1/audit", f"/api/v1/audit/{record['id']}"]:
            denied = await api_client.request(
                method, path, headers=headers, json={"action": "ALTERED"}
            )
            assert denied.status_code in {404, 405}
    assert (
        await api_client.get("/api/v1/audit?action=INITIALIZED_ORGANIZATION")
    ).json() == response.json()


@pytest.mark.parametrize(
    "data",
    [
        {"token": "secret"},
        {"role": "OTHER"},
        {"department_ids": ["invalid"]},
        {"department_ids": [str(uuid4())] * 101},
        {"previous": {"full_name": "Owner", "role": "OWNER", "password": "secret"}},
    ],
)
def test_metadata_rejects_unknown_sensitive_and_invalid_fields(data: dict) -> None:
    with pytest.raises(ValueError):
        validate_metadata("UPDATED_USER", "USER", data)


def test_metadata_catalog_limits_and_legacy_fallback() -> None:
    for action, (entity, _) in EVENT_FIELDS.items():
        assert validate_metadata(action, entity, {}) == {}
    with pytest.raises(ValueError):
        validate_metadata("CREATED_CLIENT", "USER", {})
    with pytest.raises(ValueError):
        validate_metadata("CREATED_CLIENT", "CLIENT", {"name": "x" * 201})
    with pytest.raises(ValueError):
        validate_metadata("CREATED_ACTIVITY", "ACTIVITY", {"changed_fields": ["token"]})
    with pytest.raises(ValueError):
        validate_metadata(
            "UPDATED_USER",
            "USER",
            {
                "department_ids": [str(uuid4())] * 100,
                "previous_department_ids": [str(uuid4())] * 100,
                "full_name": "😀" * 200,
            },
        )
    assert readable_metadata("UNKNOWN", "USER", {"secret": "hidden"}) == {}


async def test_membership_changes_and_resend_are_audited(
    team: Team, api_client: AsyncClient, db_session: AsyncSession
) -> None:
    headers = await login(api_client, team.users["owner"])
    response = await api_client.patch(
        f"/api/v1/admin/users/{team.users['employee'].id}",
        headers=headers,
        json={
            "full_name": "Employee",
            "role": "EMPLOYEE",
            "department_ids": [str(team.department.id)],
        },
    )
    assert response.status_code == 200
    record = await db_session.scalar(select(AuditLog).where(AuditLog.action == "UPDATED_USER"))
    assert record and len(record.event_data["previous_department_ids"]) == 2
    assert record.event_data["department_ids"] == [str(team.department.id)]
    response = await api_client.post(
        f"/api/v1/admin/users/{team.users['pending'].id}/invitation", headers=headers
    )
    assert response.status_code == 200
    record = await db_session.scalar(select(AuditLog).where(AuditLog.action == "RESENT_INVITATION"))
    assert record and record.event_data == {} and record.actor_user_id == team.users["owner"].id


@pytest.mark.parametrize("operation", ["client", "department", "user"])
async def test_audit_insert_failure_rolls_back_business_write(
    team: Team, api_client: AsyncClient, db_session: AsyncSession, operation: str
) -> None:
    headers = await login(api_client, team.users["owner"])

    def fail(*args: object) -> None:
        raise RuntimeError("Audit storage failed")

    event.listen(AuditLog, "before_insert", fail)
    try:
        with pytest.raises(RuntimeError, match="Audit storage failed"):
            if operation == "client":
                await api_client.post(
                    "/api/v1/clients", headers=headers, json={"name": "Rolled back"}
                )
            elif operation == "department":
                await api_client.delete(
                    f"/api/v1/admin/departments/{team.department.id}", headers=headers
                )
            else:
                await api_client.patch(
                    f"/api/v1/admin/users/{team.users['employee'].id}",
                    headers=headers,
                    json={
                        "full_name": "Rolled back",
                        "role": "EMPLOYEE",
                        "department_ids": [str(team.department.id)],
                    },
                )
    finally:
        event.remove(AuditLog, "before_insert", fail)
    assert (
        await db_session.scalar(
            select(func.count()).select_from(Client).where(Client.name == "Rolled back")
        )
        == 0
    )
    assert await db_session.get(Department, team.department.id) is not None
    employee = await db_session.get(User, team.users["employee"].id, populate_existing=True)
    assert employee and employee.full_name == "employee"
