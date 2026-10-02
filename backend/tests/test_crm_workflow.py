from datetime import date

from httpx import AsyncClient
from test_assignments import Team, login
from test_assignments import team as team


async def test_client_and_multiple_contacts_workflow(team: Team, api_client: AsyncClient) -> None:
    headers = await login(api_client, team.users["owner"])
    created = await api_client.post(
        "/api/v1/clients",
        headers=headers,
        json={"name": "Nuevo Hotel", "address": "Tenerife", "notes": "Cuenta de prueba"},
    )
    assert created.status_code == 201
    client_id = created.json()["id"]

    for name in ["Elena Díaz", "Pablo Reyes"]:
        response = await api_client.post(
            f"/api/v1/clients/{client_id}/contacts",
            headers=headers,
            json={"full_name": name, "position": "Reservas"},
        )
        assert response.status_code == 201

    detail = await api_client.get(f"/api/v1/clients/{client_id}")
    search = await api_client.get("/api/v1/clients", params={"search": "Nuevo Hotel"})
    assert detail.status_code == 200
    assert [contact["full_name"] for contact in detail.json()["contacts"]] == [
        "Elena Díaz",
        "Pablo Reyes",
    ]
    assert [client["id"] for client in search.json()] == [client_id]


async def test_assigned_employee_completes_client_activity(
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
        f"/api/v1/clients/{client_id}/activities",
        headers=headers,
        json={
            "type": "CALL",
            "title": "Llamar al hotel",
            "description": "Confirmar la reserva",
            "status": "PENDING",
            "scheduled_for": date.today().isoformat(),
            "department_id": str(team.department.id),
            "assigned_to_user_id": employee_id,
        },
    )
    assert created.status_code == 201
    activity_id = created.json()["id"]

    employee_headers = await login(api_client, team.users["employee"])
    pending = await api_client.get("/api/v1/tasks/mine", params={"status": "PENDING"})
    assert pending.status_code == 200
    assert [task["id"] for task in pending.json()["items"]] == [activity_id]

    completed = await api_client.post(
        f"/api/v1/clients/{client_id}/activities/{activity_id}/complete",
        headers=employee_headers,
    )
    assert completed.status_code == 204
    finished = await api_client.get("/api/v1/tasks/mine", params={"status": "COMPLETED"})
    dashboard = await api_client.get("/api/v1/dashboard")
    assert [task["id"] for task in finished.json()["items"]] == [activity_id]
    assert dashboard.status_code == 200
    assert dashboard.json()["metrics"]["completed_tasks"] >= 1
