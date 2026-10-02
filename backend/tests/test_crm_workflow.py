from httpx import AsyncClient
from test_assignments import Team, login
from test_assignments import team as team


async def test_owner_creates_client_with_multiple_contacts(
    team: Team, api_client: AsyncClient
) -> None:
    headers = await login(api_client, team.users["owner"])
    created = await api_client.post(
        "/api/v1/clients",
        headers=headers,
        json={"name": "New Hotel", "address": "Tenerife", "notes": "New account"},
    )
    assert created.status_code == 201
    client_id = created.json()["id"]

    for name in ["Elena Diaz", "Pablo Reyes"]:
        contact = await api_client.post(
            f"/api/v1/clients/{client_id}/contacts",
            headers=headers,
            json={"full_name": name, "position": "Reservations"},
        )
        assert contact.status_code == 201

    detail = await api_client.get(f"/api/v1/clients/{client_id}")
    search = await api_client.get("/api/v1/clients", params={"search": "New Hotel"})
    assert detail.status_code == 200
    assert [contact["full_name"] for contact in detail.json()["contacts"]] == [
        "Elena Diaz",
        "Pablo Reyes",
    ]
    assert [client["id"] for client in search.json()] == [client_id]


async def test_employee_completes_assigned_client_task(
    team: Team, api_client: AsyncClient
) -> None:
    headers = await login(api_client, team.users["owner"])
    client_id = str(team.client.id)
    employee_id = str(team.users["employee"].id)
    assignment = await api_client.post(
        f"/api/v1/clients/{client_id}/assignments",
        headers=headers,
        json={"user_id": employee_id},
    )
    assert assignment.status_code == 201

    created = await api_client.post(
        f"/api/v1/clients/{client_id}/tasks",
        headers=headers,
        json={
            "title": "Call the hotel",
            "description": "Confirm the booking",
            "department_id": str(team.department.id),
            "assigned_to_user_id": employee_id,
        },
    )
    assert created.status_code == 201
    task_id = created.json()["id"]

    employee_headers = await login(api_client, team.users["employee"])
    pending = await api_client.get("/api/v1/tasks/mine", params={"status": "PENDING"})
    assert [task["id"] for task in pending.json()["items"]] == [task_id]

    completed = await api_client.post(
        f"/api/v1/clients/{client_id}/tasks/{task_id}/complete",
        headers=employee_headers,
    )
    assert completed.status_code == 204
    finished = await api_client.get("/api/v1/tasks/mine", params={"status": "COMPLETED"})
    assert [task["id"] for task in finished.json()["items"]] == [task_id]
