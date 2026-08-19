from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession


async def test_setup_is_available_once(db_session: AsyncSession, api_client: AsyncClient) -> None:
    initial_status = await api_client.get("/api/v1/setup/status")

    assert initial_status.status_code == 200
    assert initial_status.json() == {"initialized": False}

    payload = {
        "mode": "BUSINESS",
        "organization_name": "First Company",
        "owner_name": "First Owner",
        "owner_email": "owner@example.com",
        "owner_password": "a-secure-first-password",
        "owner_password_confirmation": "a-secure-first-password",
    }
    setup_response = await api_client.post("/api/v1/setup", json=payload)

    assert setup_response.status_code == 201
    assert setup_response.json()["organization_name"] == "First Company"
    assert setup_response.json()["owner"]["email"] == "owner@example.com"

    initialized_status = await api_client.get("/api/v1/setup/status")
    repeated_setup = await api_client.post("/api/v1/setup", json=payload)

    assert initialized_status.json() == {"initialized": True}
    assert repeated_setup.status_code == 409


async def test_setup_rejects_password_confirmation_mismatch(
    db_session: AsyncSession, api_client: AsyncClient
) -> None:
    response = await api_client.post(
        "/api/v1/setup",
        json={
            "mode": "INDIVIDUAL",
            "organization_name": "Personal Workspace",
            "owner_name": "Owner",
            "owner_email": "owner@example.com",
            "owner_password": "a-secure-first-password",
            "owner_password_confirmation": "a-different-secure-password",
        },
    )

    assert response.status_code == 422
