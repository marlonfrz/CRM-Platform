from datetime import UTC, datetime, timedelta
from hashlib import sha256
from secrets import token_urlsafe

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerifyMismatchError
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.config import get_settings
from app.models import User, UserSession, UserStatus
from app.services.audit import add_audit_event
from app.services.exceptions import InvalidCredentialsError, InvalidSessionError
from app.services.normalization import normalize_email

password_hasher = PasswordHasher()
dummy_password_hash = password_hasher.hash("authentication-timing-placeholder")


def hash_token(token: str) -> str:
    return sha256(token.encode()).hexdigest()


def verify_password(password_hash: str, password: str) -> bool:
    try:
        return password_hasher.verify(password_hash, password)
    except (InvalidHashError, VerifyMismatchError):
        return False


async def login(
    session: AsyncSession, *, email: str, password: str
) -> tuple[UserSession, User, str, str]:
    user = await session.scalar(select(User).where(User.email == normalize_email(email)))
    password_hash = (
        user.password_hash if user is not None and user.password_hash else dummy_password_hash
    )
    password_is_valid = verify_password(password_hash, password)
    if user is None or user.status is not UserStatus.ACTIVE or not password_is_valid:
        raise InvalidCredentialsError("Invalid credentials")

    current_password_hash = user.password_hash
    if current_password_hash is None:
        raise InvalidCredentialsError("Invalid credentials")
    if password_hasher.check_needs_rehash(current_password_hash):
        user.password_hash = password_hasher.hash(password)

    now = datetime.now(UTC)
    settings = get_settings()
    session_token = token_urlsafe(48)
    csrf_token = token_urlsafe(32)
    user_session = UserSession(
        organization_id=user.organization_id,
        user_id=user.id,
        token_hash=hash_token(session_token),
        csrf_token_hash=hash_token(csrf_token),
        expires_at=now + timedelta(seconds=settings.session_idle_seconds),
        last_used_at=now,
    )
    session.add(user_session)
    await session.flush()
    add_audit_event(
        session,
        organization_id=user.organization_id,
        actor_user_id=user.id,
        action="AUTH_LOGIN",
        entity_type="USER_SESSION",
        entity_id=user_session.id,
    )
    return user_session, user, session_token, csrf_token


async def authenticate_session(
    session: AsyncSession, *, session_token: str
) -> tuple[UserSession, User]:
    now = datetime.now(UTC)
    user_session = await session.scalar(
        select(UserSession)
        .options(joinedload(UserSession.user, innerjoin=True))
        .where(UserSession.token_hash == hash_token(session_token))
        .with_for_update()
    )
    if (
        user_session is None
        or user_session.revoked_at is not None
        or user_session.expires_at <= now
        or user_session.user.status is not UserStatus.ACTIVE
    ):
        raise InvalidSessionError("Invalid or expired session")

    user_session.last_used_at = now
    user_session.expires_at = now + timedelta(seconds=get_settings().session_idle_seconds)
    return user_session, user_session.user


async def logout(session: AsyncSession, *, user_session: UserSession, user: User) -> None:
    user_session.revoked_at = datetime.now(UTC)
    add_audit_event(
        session,
        organization_id=user.organization_id,
        actor_user_id=user.id,
        action="AUTH_LOGOUT",
        entity_type="USER_SESSION",
        entity_id=user_session.id,
    )
    await session.flush()


async def change_password(
    session: AsyncSession,
    *,
    user: User,
    current_password: str,
    new_password: str,
) -> None:
    if user.password_hash is None or not verify_password(user.password_hash, current_password):
        raise InvalidCredentialsError("Current password is invalid")
    if len(new_password) < 12:
        raise ValueError("The new password must contain at least 12 characters")

    user.password_hash = password_hasher.hash(new_password)
    now = datetime.now(UTC)
    await session.execute(
        update(UserSession)
        .where(UserSession.user_id == user.id, UserSession.revoked_at.is_(None))
        .values(revoked_at=now)
    )
    add_audit_event(
        session,
        organization_id=user.organization_id,
        actor_user_id=user.id,
        action="PASSWORD_CHANGED",
        entity_type="USER",
        entity_id=user.id,
    )
    await session.flush()
