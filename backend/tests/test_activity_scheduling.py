from datetime import date, timedelta

from httpx import AsyncClient
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from test_activities import assign
from test_assignments import Team, login
from test_assignments import team as team

from app.models import Activity, ActivitySchedule, ActivityType
from app.services.recurrence import materialize_schedules


async def default_type(db_session: AsyncSession, team: Team) -> ActivityType:
    activity_type = await db_session.scalar(
        select(ActivityType).where(
            ActivityType.organization_id == team.client.organization_id,
            ActivityType.normalized_name == "llamada",
        )
    )
    assert activity_type
    return activity_type


def endpoint(team: Team) -> str:
    return f"/api/v1/clients/{team.client.id}/activities"


async def test_recurrence_materializes_current_and_one_future_occurrence(
    team: Team, api_client: AsyncClient, db_session: AsyncSession
) -> None:
    activity_type = await default_type(db_session, team)
    headers = await login(api_client, team.users["admin"])
    today = date.today()
    response = await api_client.post(
        endpoint(team),
        headers=headers,
        json={
            "activity_type_id": str(activity_type.id),
            "title": "Daily follow-up",
            "description": "Contact the client",
            "status": "PENDING",
            "scheduled_for": today.isoformat(),
            "assigned_to_user_id": str(team.users["admin"].id),
            "recurrence": {"repeat_unit": "DAY", "repeat_interval": 1},
        },
    )
    assert response.status_code == 201
    assert len(response.json()["ids"]) == 2
    schedule = await db_session.scalar(select(ActivitySchedule))
    assert schedule and schedule.last_materialized_on == today + timedelta(days=1)
    dates = list(
        await db_session.scalars(
            select(Activity.scheduled_for).order_by(Activity.scheduled_for)
        )
    )
    assert dates == [today, today + timedelta(days=1)]

    await materialize_schedules(
        db_session,
        organization_id=team.client.organization_id,
        client_id=team.client.id,
        today=today + timedelta(days=1),
    )
    await materialize_schedules(
        db_session,
        organization_id=team.client.organization_id,
        client_id=team.client.id,
        today=today + timedelta(days=1),
    )
    await db_session.commit()
    dates = list(
        await db_session.scalars(
            select(Activity.scheduled_for).order_by(Activity.scheduled_for)
        )
    )
    assert dates == [today, today + timedelta(days=1), today + timedelta(days=2)]


async def test_delete_permissions_and_cancel_following_occurrences(
    team: Team, api_client: AsyncClient, db_session: AsyncSession
) -> None:
    await assign(db_session, team)
    activity_type = await default_type(db_session, team)
    headers = await login(api_client, team.users["admin"])
    response = await api_client.post(
        endpoint(team),
        headers=headers,
        json={
            "activity_type_id": str(activity_type.id),
            "title": "Weekly review",
            "description": "Review progress",
            "status": "PENDING",
            "scheduled_for": date.today().isoformat(),
            "assigned_to_user_id": str(team.users["employee"].id),
            "recurrence": {
                "repeat_unit": "WEEK",
                "repeat_interval": 1,
                "weekdays": [date.today().weekday()],
            },
        },
    )
    identifiers = response.json()["ids"]
    headers = await login(api_client, team.users["employee"])
    result = await api_client.delete(
        f"{endpoint(team)}/{identifiers[0]}?scope=THIS_AND_FOLLOWING",
        headers=headers,
    )
    assert result.status_code == 204
    assert await db_session.scalar(select(func.count()).select_from(Activity)) == 0
    schedule = await db_session.scalar(select(ActivitySchedule))
    assert schedule and not schedule.active


async def test_activity_types_are_normalized_and_department_scoped(
    team: Team, api_client: AsyncClient
) -> None:
    headers = await login(api_client, team.users["admin"])
    response = await api_client.post(
        "/api/v1/activity-types",
        headers=headers,
        json={"name": "  Revisión creativa  ", "department_id": str(team.department.id)},
    )
    assert response.status_code == 201
    assert response.json()["name"] == "Revisión creativa"
    duplicate = await api_client.post(
        "/api/v1/activity-types",
        headers=headers,
        json={"name": "revisión creativa", "department_id": str(team.department.id)},
    )
    assert duplicate.status_code == 409
    headers = await login(api_client, team.users["employee"])
    assert (
        await api_client.post(
            "/api/v1/activity-types",
            headers=headers,
            json={"name": "Private", "department_id": str(team.department.id)},
        )
    ).status_code == 403


async def test_activity_periods_separate_today_scheduled_and_history(
    team: Team, api_client: AsyncClient, db_session: AsyncSession
) -> None:
    activity_type = await default_type(db_session, team)
    headers = await login(api_client, team.users["admin"])
    today = date.today()
    cases = [
        (today - timedelta(days=1), "COMPLETED", "HISTORY"),
        (today, "PENDING", "TODAY"),
        (today + timedelta(days=1), "PENDING", "SCHEDULED"),
    ]
    for scheduled_for, status, _ in cases:
        response = await api_client.post(
            endpoint(team),
            headers=headers,
            json={
                "activity_type_id": str(activity_type.id),
                "description": f"Activity for {scheduled_for.isoformat()}",
                "status": status,
                "scheduled_for": scheduled_for.isoformat(),
                "assigned_to_user_id": str(team.users["admin"].id),
            },
        )
        assert response.status_code == 201

    for expected_date, _, period in cases:
        response = await api_client.get(
            f"{endpoint(team)}?period={period}&limit=20", headers=headers
        )
        assert response.status_code == 200
        assert [item["scheduled_for"] for item in response.json()["items"]] == [
            expected_date.isoformat()
        ]
