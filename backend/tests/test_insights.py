from datetime import UTC, date, datetime, timedelta

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from test_activities import assign
from test_assignments import PASSWORD, Team, login
from test_assignments import team as team

from app.models import Activity, Client, Department, OrganizationMode
from app.models.activity_type import activity_type_identifier
from app.services.bootstrap import bootstrap_organization


def activity_record(
    *,
    team: Team,
    author: str,
    department: Department,
    description: str,
    status: str,
    scheduled_for: date,
    completed_at: datetime | None = None,
) -> Activity:
    if status == "COMPLETED" and completed_at is None:
        completed_at = datetime.now(UTC).replace(microsecond=0)
    return Activity(
        organization_id=team.client.organization_id,
        client_id=team.client.id,
        user_id=team.users[author].id,
        assigned_to_user_id=team.users[author].id,
        department_id=department.id,
        activity_type_id=activity_type_identifier(team.client.organization_id, "nota"),
        description=description,
        scheduled_for=scheduled_for,
        status=status,
        occurred_at=completed_at,
        completed_at=completed_at,
    )


@pytest.fixture
async def populated(team: Team, db_session: AsyncSession) -> Team:
    await assign(db_session, team)
    await assign(db_session, team, "hidden")
    other = await db_session.scalar(select(Department).where(Department.id != team.department.id))
    assert other
    db_session.add_all(
        [
            activity_record(
                team=team,
                author="employee",
                department=team.department,
                description="Activity A",
                status="COMPLETED",
                scheduled_for=date(2026, 9, 7),
            ),
            activity_record(
                team=team,
                author="hidden",
                department=other,
                description="Activity B",
                status="COMPLETED",
                scheduled_for=date(2026, 9, 7),
                completed_at=datetime.now(UTC).replace(microsecond=0) - timedelta(days=1),
            ),
            activity_record(
                team=team,
                author="employee",
                department=team.department,
                description="Pending employee",
                status="PENDING",
                scheduled_for=date(2026, 9, 8),
            ),
            activity_record(
                team=team,
                author="hidden",
                department=other,
                description="Pending hidden",
                status="PENDING",
                scheduled_for=date(2026, 9, 9),
            ),
            activity_record(
                team=team,
                author="owner",
                department=team.department,
                description="Pending owner",
                status="PENDING",
                scheduled_for=date(2026, 9, 10),
            ),
        ]
    )
    await db_session.commit()
    return team


async def test_dashboard_counts_unified_activities(
    populated: Team, api_client: AsyncClient
) -> None:
    await login(api_client, populated.users["owner"])
    data = (await api_client.get("/api/v1/dashboard")).json()
    assert data["metrics"] == {
        "clients": 2,
        "activities": 5,
        "pending_tasks": 3,
        "completed_tasks": 1,
        "today_clients": 1,
        "today_activities": 1,
        "today_pending_tasks": 0,
        "active_users": 5,
        "departments": 2,
    }
    assert len(data["recent_activities"]) == 2
    assert len(data["pending_tasks"]) == 3
    assert [item["description"] for item in data["today_activities"]] == ["Activity A"]
    assert sum(department["activities"] for department in data["departments"]) == 1
    assert sum(department["pending_tasks"] for department in data["departments"]) == 0


async def test_department_scope_applies_to_history_and_dashboard(
    populated: Team, api_client: AsyncClient
) -> None:
    await login(api_client, populated.users["admin"])
    history = (
        await api_client.get(f"/api/v1/clients/{populated.client.id}/history")
    ).json()["items"]
    assert {item["description"] for item in history} == {
        "Activity A",
        "Pending employee",
        "Pending owner",
    }
    data = (await api_client.get("/api/v1/dashboard")).json()
    assert data["metrics"]["activities"] == 3
    assert data["metrics"]["pending_tasks"] == 2
    assert data["metrics"]["completed_tasks"] == 1
    assert data["metrics"]["today_activities"] == 1
    assert data["departments"][0]["activities"] == 1


async def test_history_filters_status_type_and_scheduled(
    populated: Team, api_client: AsyncClient
) -> None:
    await login(api_client, populated.users["owner"])
    endpoint = f"/api/v1/clients/{populated.client.id}/history"
    completed = (await api_client.get(f"{endpoint}?activity_status=COMPLETED")).json()["items"]
    assert len(completed) == 2 and {item["status"] for item in completed} == {"COMPLETED"}
    type_id = activity_type_identifier(populated.client.organization_id, "nota")
    typed = (await api_client.get(f"{endpoint}?activity_type_id={type_id}")).json()["items"]
    assert len(typed) == 5
    future = (await api_client.get(f"{endpoint}?scheduled=true")).json()["items"]
    assert future == []  # all fixture dates are historical relative to the test run


async def test_history_authentication_and_cross_organization_isolation(
    populated: Team, api_client: AsyncClient
) -> None:
    endpoint = f"/api/v1/clients/{populated.client.id}/history"
    assert (await api_client.get(endpoint)).status_code == 401
    await login(api_client, populated.users["no_department"])
    assert (await api_client.get(endpoint)).status_code == 403


async def test_individual_empty_dashboard(
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
    client = Client(organization_id=org.id, name="Personal client")
    db_session.add(client)
    await db_session.commit()
    await login(api_client, owner)
    data = (await api_client.get("/api/v1/dashboard")).json()
    assert data["metrics"]["clients"] == 1
    assert data["metrics"]["activities"] == 0
    assert data["metrics"]["today_activities"] == 0
    assert data["today_activities"] == []
    assert data["departments"] == []
