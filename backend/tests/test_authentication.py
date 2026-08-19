from datetime import UTC, datetime, timedelta

from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import AuditLog, OrganizationMode, User, UserRole, UserSession, UserStatus
from app.services.bootstrap import bootstrap_organization
from app.services.users import disable_user

CURRENT_PASSWORD = "current-secure-password"
NEW_PASSWORD = "new-secure-password-value"


async def create_owner(db_session: AsyncSession) -> User:
    _, owner = await bootstrap_organization(
        db_session,
        mode=OrganizationMode.BUSINESS,
        organization_name="Authentication Test",
        owner_name="Test Owner",
        owner_email="owner@example.com",
        owner_password=CURRENT_PASSWORD,
    )
    await db_session.commit()
    return owner


async def login(api_client: AsyncClient, password: str = CURRENT_PASSWORD) -> None:
    response = await api_client.post(
        "/api/v1/auth/login",
        json={"email": "owner@example.com", "password": password},
    )
    assert response.status_code == 200


def csrf_headers(api_client: AsyncClient) -> dict[str, str]:
    csrf_token = api_client.cookies.get("crm_csrf")
    assert csrf_token is not None
    return {"X-CSRF-Token": csrf_token}


async def test_login_stores_only_token_hash_and_audits_event(
    db_session: AsyncSession, api_client: AsyncClient
) -> None:
    owner = await create_owner(db_session)

    response = await api_client.post(
        "/api/v1/auth/login",
        json={"email": " OWNER@example.com ", "password": CURRENT_PASSWORD},
    )

    assert response.status_code == 200
    assert response.json()["id"] == str(owner.id)
    session_token = api_client.cookies.get("crm_session")
    csrf_token = api_client.cookies.get("crm_csrf")
    assert session_token is not None
    assert csrf_token is not None

    user_session = await db_session.scalar(select(UserSession))
    audit_event = await db_session.scalar(select(AuditLog).where(AuditLog.action == "AUTH_LOGIN"))
    assert user_session is not None
    assert user_session.token_hash != session_token
    assert user_session.csrf_token_hash != csrf_token
    assert audit_event is not None
    assert audit_event.actor_user_id == owner.id


async def test_invalid_credentials_do_not_create_session(
    db_session: AsyncSession, api_client: AsyncClient
) -> None:
    await create_owner(db_session)

    response = await api_client.post(
        "/api/v1/auth/login",
        json={"email": "owner@example.com", "password": "wrong-password"},
    )

    assert response.status_code == 401
    assert await db_session.scalar(select(UserSession)) is None


async def test_workspace_is_derived_from_authenticated_user(
    db_session: AsyncSession, api_client: AsyncClient
) -> None:
    owner = await create_owner(db_session)
    await login(api_client)

    response = await api_client.get("/api/v1/workspace")

    assert response.status_code == 200
    assert response.json() == {
        "organization_id": str(owner.organization_id),
        "organization_name": "Authentication Test",
        "organization_mode": "BUSINESS",
        "user_id": str(owner.id),
        "user_name": "Test Owner",
        "user_email": "owner@example.com",
        "user_role": "OWNER",
        "departments": [],
    }


async def test_pending_user_cannot_login(db_session: AsyncSession, api_client: AsyncClient) -> None:
    owner = await create_owner(db_session)
    pending = User(
        organization_id=owner.organization_id,
        email="pending@example.com",
        full_name="Pending User",
        role=UserRole.EMPLOYEE,
        status=UserStatus.PENDING,
    )
    db_session.add(pending)
    await db_session.commit()

    response = await api_client.post(
        "/api/v1/auth/login",
        json={"email": "pending@example.com", "password": CURRENT_PASSWORD},
    )

    assert response.status_code == 401


async def test_authenticated_request_renews_sliding_expiration(
    db_session: AsyncSession, api_client: AsyncClient
) -> None:
    await create_owner(db_session)
    await login(api_client)
    user_session = await db_session.scalar(select(UserSession))
    assert user_session is not None
    previous_expiration = datetime.now(UTC) + timedelta(minutes=5)
    user_session.expires_at = previous_expiration
    user_session.last_used_at = datetime.now(UTC) - timedelta(hours=1)
    await db_session.commit()

    response = await api_client.get("/api/v1/auth/me")

    assert response.status_code == 200
    await db_session.refresh(user_session)
    assert user_session.expires_at > previous_expiration
    assert user_session.last_used_at > datetime.now(UTC) - timedelta(minutes=1)


async def test_expired_session_is_rejected(
    db_session: AsyncSession, api_client: AsyncClient
) -> None:
    await create_owner(db_session)
    await login(api_client)
    user_session = await db_session.scalar(select(UserSession))
    assert user_session is not None
    user_session.expires_at = datetime.now(UTC) - timedelta(seconds=1)
    await db_session.commit()

    response = await api_client.get("/api/v1/auth/me")

    assert response.status_code == 401


async def test_logout_requires_csrf_and_revokes_session(
    db_session: AsyncSession, api_client: AsyncClient
) -> None:
    await create_owner(db_session)
    await login(api_client)

    rejected = await api_client.post("/api/v1/auth/logout")
    assert rejected.status_code == 403

    response = await api_client.post("/api/v1/auth/logout", headers=csrf_headers(api_client))

    assert response.status_code == 204
    user_session = await db_session.scalar(select(UserSession))
    assert user_session is not None
    assert user_session.revoked_at is not None
    assert api_client.cookies.get("crm_session") is None
    audit_event = await db_session.scalar(select(AuditLog).where(AuditLog.action == "AUTH_LOGOUT"))
    assert audit_event is not None


async def test_change_password_revokes_sessions_and_replaces_password(
    db_session: AsyncSession, api_client: AsyncClient
) -> None:
    await create_owner(db_session)
    await login(api_client)

    response = await api_client.put(
        "/api/v1/auth/password",
        headers=csrf_headers(api_client),
        json={"current_password": CURRENT_PASSWORD, "new_password": NEW_PASSWORD},
    )

    assert response.status_code == 204
    user_session = await db_session.scalar(select(UserSession))
    assert user_session is not None
    assert user_session.revoked_at is not None

    old_login = await api_client.post(
        "/api/v1/auth/login",
        json={"email": "owner@example.com", "password": CURRENT_PASSWORD},
    )
    assert old_login.status_code == 401
    await login(api_client, NEW_PASSWORD)


async def test_disabling_user_revokes_existing_sessions(
    db_session: AsyncSession, api_client: AsyncClient
) -> None:
    owner = await create_owner(db_session)
    second_owner = User(
        organization_id=owner.organization_id,
        email="second-owner@example.com",
        full_name="Second Owner",
        password_hash=owner.password_hash,
        role=UserRole.OWNER,
        status=UserStatus.ACTIVE,
    )
    db_session.add(second_owner)
    await db_session.commit()
    await login(api_client)

    await disable_user(db_session, user_id=owner.id)
    await db_session.commit()

    response = await api_client.get("/api/v1/auth/me")
    assert response.status_code == 401
    user_session = await db_session.scalar(
        select(UserSession).where(UserSession.user_id == owner.id)
    )
    assert user_session is not None
    assert user_session.revoked_at is not None
