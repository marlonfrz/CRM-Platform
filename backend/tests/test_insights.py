from datetime import UTC, datetime
from uuid import uuid4

import pytest
from httpx import AsyncClient
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession
from test_activities import assign
from test_assignments import PASSWORD, Team, login
from test_assignments import team as team

from app.models import (
    Activity,
    Client,
    ClientAssignment,
    Department,
    DepartmentMember,
    Organization,
    OrganizationMode,
    Task,
    User,
    UserRole,
    UserStatus,
)
from app.services.bootstrap import bootstrap_organization


@pytest.fixture
async def populated(team: Team, db_session: AsyncSession) -> Team:
    await assign(db_session, team)
    await assign(db_session, team, "hidden")
    other = await db_session.scalar(select(Department).where(Department.id != team.department.id))
    assert other
    timestamp = datetime(2026, 9, 7, 10, tzinfo=UTC)
    shared_id = uuid4()
    db_session.add_all(
        [
            Activity(
                id=shared_id,
                organization_id=team.client.organization_id,
                client_id=team.client.id,
                user_id=team.users["employee"].id,
                department_id=team.department.id,
                type="CALL",
                description="Activity A",
                occurred_at=timestamp,
            ),
            Activity(
                organization_id=team.client.organization_id,
                client_id=team.client.id,
                user_id=team.users["hidden"].id,
                department_id=other.id,
                type="NOTE",
                description="Activity B",
                occurred_at=timestamp,
            ),
            Activity(
                organization_id=team.client.organization_id,
                client_id=team.other_client.id,
                user_id=team.users["admin"].id,
                department_id=team.department.id,
                type="MEETING",
                description="Other client activity",
                occurred_at=timestamp,
            ),
        ]
    )
    for name, department, completed in [
        ("employee", team.department, False),
        ("hidden", other, False),
        ("owner", team.department, False),
        ("admin", team.department, True),
    ]:
        db_session.add(
            Task(
                id=shared_id if name == "employee" else uuid4(),
                organization_id=team.client.organization_id,
                client_id=team.client.id,
                assigned_to_user_id=team.users[name].id,
                created_by_user_id=team.users["owner"].id,
                department_id=department.id,
                title=f"Task {name}",
                status="COMPLETED" if completed else "PENDING",
                completed_at=timestamp if completed else None,
                created_at=timestamp,
                due_at=timestamp if name == "employee" else None,
            )
        )
    await db_session.commit()
    return team


@pytest.mark.parametrize(
    "role,clients,activities,pending,completed,users,deps",
    [
        ("owner", 2, 3, 3, 1, 5, 2),
        ("admin", 2, 2, 1, 1, 1, 1),
        ("employee", 1, 2, 1, 0, None, None),
        ("hidden", 1, 1, 1, 0, None, None),
    ],
)
async def test_dashboard_scope_and_counts(
    populated: Team,
    api_client: AsyncClient,
    role: str,
    clients: int,
    activities: int,
    pending: int,
    completed: int,
    users: int | None,
    deps: int | None,
) -> None:
    await login(api_client, populated.users[role])
    response = await api_client.get("/api/v1/dashboard")
    assert response.status_code == 200
    data = response.json()
    assert data["metrics"] == dict(
        clients=clients,
        activities=activities,
        pending_tasks=pending,
        completed_tasks=completed,
        active_users=users,
        departments=deps,
    )
    assert len(data["recent_activities"]) == activities
    assert len(data["pending_tasks"]) == pending
    assert len(data["departments"]) == (deps or 0)
    if role == "admin":
        assert data["departments"][0] == dict(
            id=str(populated.department.id),
            name="A",
            active_employees=1,
            activities=2,
            pending_tasks=1,
        )
        assert "Activity B" not in response.text and "Task owner" not in response.text
    if role in ["employee", "hidden"]:
        assert "Other client activity" not in response.text
        assert all(t["person_id"] == str(populated.users[role].id) for t in data["pending_tasks"])


@pytest.mark.parametrize("role", ["owner", "admin", "employee", "hidden"])
async def test_history_matches_existing_authorized_lists(
    populated: Team, api_client: AsyncClient, role: str
) -> None:
    await login(api_client, populated.users[role])
    path = f"/api/v1/clients/{populated.client.id}"
    history = (await api_client.get(f"{path}/history")).json()["items"]
    expected_activities = {
        a["id"] for a in (await api_client.get(f"{path}/activities")).json()["items"]
    }
    expected_tasks = {t["id"] for t in (await api_client.get(f"{path}/tasks")).json()["items"]}
    assert {h["id"] for h in history if h["kind"] == "ACTIVITY"} == expected_activities
    assert {h["id"] for h in history if h["kind"] == "TASK"} == expected_tasks
    for kind, expected in [("ACTIVITY", expected_activities), ("TASK", expected_tasks)]:
        result = (await api_client.get(f"{path}/history?kind={kind}")).json()["items"]
        assert {h["id"] for h in result} == expected
        assert all(h["kind"] == kind for h in result)


async def test_history_pagination_handles_timestamp_and_id_ties(
    populated: Team, api_client: AsyncClient
) -> None:
    await login(api_client, populated.users["owner"])
    endpoint = f"/api/v1/clients/{populated.client.id}/history"
    all_items = (await api_client.get(endpoint)).json()["items"]
    assert len(all_items) == 6
    pages = [
        (await api_client.get(f"{endpoint}?limit=2&offset={offset}")).json() for offset in [0, 2, 4]
    ]
    assert [p["has_more"] for p in pages] == [True, True, False]
    assert [item for page in pages for item in page["items"]] == all_items
    assert len({(item["kind"], item["id"]) for item in all_items}) == 6
    assert len({item["id"] for item in all_items}) == 5
    for query in ["kind=OTHER", "offset=-1", "limit=101", "limit=0"]:
        assert (await api_client.get(f"{endpoint}?{query}")).status_code == 422


async def test_revoked_assignment_and_changed_membership_update_aggregates(
    populated: Team, db_session: AsyncSession, api_client: AsyncClient
) -> None:
    await login(api_client, populated.users["employee"])
    await db_session.execute(
        delete(DepartmentMember).where(
            DepartmentMember.user_id == populated.users["employee"].id,
            DepartmentMember.department_id == populated.department.id,
        )
    )
    await db_session.commit()
    data = (await api_client.get("/api/v1/dashboard")).json()
    assert data["metrics"]["activities"] == 1 and data["metrics"]["pending_tasks"] == 0
    await db_session.execute(
        delete(ClientAssignment).where(ClientAssignment.user_id == populated.users["employee"].id)
    )
    await db_session.commit()
    data = (await api_client.get("/api/v1/dashboard")).json()
    assert (
        data["metrics"]["clients"]
        == data["metrics"]["activities"]
        == data["metrics"]["pending_tasks"]
        == 0
    )
    assert data["recent_activities"] == data["pending_tasks"] == []
    assert (
        await api_client.get(f"/api/v1/clients/{populated.client.id}/history")
    ).status_code == 403


async def test_authentication_and_cross_organization_isolation(
    populated: Team, db_session: AsyncSession, api_client: AsyncClient
) -> None:
    assert (await api_client.get("/api/v1/dashboard")).status_code == 401
    assert (
        await api_client.get(f"/api/v1/clients/{populated.client.id}/history")
    ).status_code == 401
    foreign = Organization(name="Foreign secret", mode=OrganizationMode.INDIVIDUAL)
    db_session.add(foreign)
    await db_session.flush()
    user = User(
        organization_id=foreign.id,
        email="foreign@example.com",
        full_name="Foreign secret",
        role=UserRole.OWNER,
        status=UserStatus.PENDING,
    )
    client = Client(organization_id=foreign.id, name="Foreign secret")
    db_session.add_all([user, client])
    await db_session.flush()
    db_session.add_all(
        [
            Activity(
                organization_id=foreign.id,
                client_id=client.id,
                user_id=user.id,
                type="NOTE",
                description="Foreign secret",
                occurred_at=datetime.now(UTC),
            ),
            Task(
                organization_id=foreign.id,
                client_id=client.id,
                assigned_to_user_id=user.id,
                created_by_user_id=user.id,
                title="Foreign secret",
            ),
        ]
    )
    await db_session.commit()
    await login(api_client, populated.users["owner"])
    response = await api_client.get("/api/v1/dashboard")
    assert response.json()["metrics"]["clients"] == 2
    assert "Foreign secret" not in response.text
    for identifier in [client.id, uuid4()]:
        assert (await api_client.get(f"/api/v1/clients/{identifier}/history")).status_code == 404


async def test_individual_and_empty_dashboard(
    db_session: AsyncSession, api_client: AsyncClient
) -> None:
    org, owner = await bootstrap_organization(
        db_session,
        mode=OrganizationMode.INDIVIDUAL,
        organization_name="Personal",
        owner_name="Owner",
        owner_email="owner@example.com",
        owner_password=PASSWORD,
    )
    await db_session.commit()
    await login(api_client, owner)
    data = (await api_client.get("/api/v1/dashboard")).json()
    assert data["metrics"] == dict(
        clients=0,
        activities=0,
        pending_tasks=0,
        completed_tasks=0,
        active_users=None,
        departments=None,
    )
    assert data["departments"] == data["recent_activities"] == data["pending_tasks"] == []
    client = Client(organization_id=org.id, name="Personal client")
    db_session.add(client)
    await db_session.flush()
    db_session.add_all(
        [
            Activity(
                organization_id=org.id,
                client_id=client.id,
                user_id=owner.id,
                type="NOTE",
                description="Personal note",
                occurred_at=datetime.now(UTC),
            ),
            Task(
                organization_id=org.id,
                client_id=client.id,
                assigned_to_user_id=owner.id,
                created_by_user_id=owner.id,
                title="Personal task",
            ),
        ]
    )
    await db_session.commit()
    data = (await api_client.get("/api/v1/dashboard")).json()
    assert data["metrics"]["activities"] == data["metrics"]["pending_tasks"] == 1
    history = (await api_client.get(f"/api/v1/clients/{client.id}/history")).json()
    assert len(history["items"]) == 2 and all(i["department_id"] is None for i in history["items"])


async def test_recent_and_pending_lists_are_bounded_and_use_correct_order(
    populated: Team, db_session: AsyncSession, api_client: AsyncClient
) -> None:
    for day in range(1, 8):
        db_session.add_all(
            [
                Activity(
                    organization_id=populated.client.organization_id,
                    client_id=populated.client.id,
                    user_id=populated.users["admin"].id,
                    department_id=populated.department.id,
                    type="NOTE",
                    description=f"New {day}",
                    occurred_at=datetime(2026, 10, day, tzinfo=UTC),
                ),
                Task(
                    organization_id=populated.client.organization_id,
                    client_id=populated.client.id,
                    assigned_to_user_id=populated.users["admin"].id,
                    created_by_user_id=populated.users["admin"].id,
                    department_id=populated.department.id,
                    title=f"Due {day}",
                    due_at=datetime(2026, 1, day, tzinfo=UTC),
                ),
            ]
        )
    await db_session.commit()
    await login(api_client, populated.users["admin"])
    data = (await api_client.get("/api/v1/dashboard")).json()
    assert len(data["recent_activities"]) == len(data["pending_tasks"]) == 5
    assert data["metrics"]["activities"] == 9 and data["metrics"]["pending_tasks"] == 8
    assert [a["description"] for a in data["recent_activities"]] == [
        f"New {day}" for day in range(7, 2, -1)
    ]
    assert [t["title"] for t in data["pending_tasks"]] == [f"Due {day}" for day in range(1, 6)]
