from base64 import urlsafe_b64decode, urlsafe_b64encode
from hashlib import sha256
from secrets import token_bytes

from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings
from app.models import AIConfiguration
from app.policies.authorization import AuthorizationContext
from app.schemas.summaries import AIConfigurationResponse, UpdateAIConfigurationRequest
from app.services.audit import add_audit_event
from app.services.exceptions import AuthorizationDeniedError, InvalidAIConfigurationError
from app.services.summary_provider import (
    EXTERNAL_PROVIDERS,
    RuntimeAIConfiguration,
    configuration_from_settings,
)

ASSOCIATED_DATA_PREFIX = b"crm-platform-ai-configuration-v1:"


def require_ai_configuration_access(authorization: AuthorizationContext) -> None:
    if not authorization.is_owner:
        raise AuthorizationDeniedError("AI configuration requires owner access")


def _cipher(settings: Settings) -> AESGCM:
    secret = settings.ai_credentials_encryption_key.get_secret_value().encode()
    return AESGCM(sha256(secret).digest())


def encrypt_api_key(settings: Settings, organization_id: object, api_key: str) -> str:
    nonce = token_bytes(12)
    associated_data = ASSOCIATED_DATA_PREFIX + str(organization_id).encode()
    encrypted = _cipher(settings).encrypt(nonce, api_key.encode(), associated_data)
    return urlsafe_b64encode(b"\x01" + nonce + encrypted).decode()


def decrypt_api_key(
    settings: Settings, organization_id: object, encrypted_api_key: str
) -> str | None:
    try:
        raw = urlsafe_b64decode(encrypted_api_key.encode())
        if len(raw) < 30 or raw[0] != 1:
            return None
        associated_data = ASSOCIATED_DATA_PREFIX + str(organization_id).encode()
        return _cipher(settings).decrypt(raw[1:13], raw[13:], associated_data).decode()
    except (ValueError, InvalidTag, UnicodeDecodeError):
        return None


async def load_ai_configuration(
    session: AsyncSession,
    *,
    authorization: AuthorizationContext,
    settings: Settings,
) -> RuntimeAIConfiguration:
    stored = await session.get(AIConfiguration, authorization.organization_id)
    if stored is None:
        return configuration_from_settings(settings)
    api_key = (
        decrypt_api_key(settings, stored.organization_id, stored.encrypted_api_key)
        if stored.encrypted_api_key
        else None
    )
    return RuntimeAIConfiguration(
        provider=stored.provider,  # type: ignore[arg-type]
        model=stored.model,
        api_key=api_key,
        source="organization",
    )


def configuration_response(configuration: RuntimeAIConfiguration) -> AIConfigurationResponse:
    return AIConfigurationResponse(
        provider=configuration.provider,
        model=configuration.model,
        has_api_key=bool(configuration.api_key),
        source=configuration.source,
    )


async def update_ai_configuration(
    session: AsyncSession,
    *,
    authorization: AuthorizationContext,
    settings: Settings,
    payload: UpdateAIConfigurationRequest,
) -> RuntimeAIConfiguration:
    require_ai_configuration_access(authorization)
    current = await load_ai_configuration(
        session, authorization=authorization, settings=settings
    )
    supplied_key = payload.api_key.get_secret_value() if payload.api_key else None
    api_key = supplied_key or (
        current.api_key if current.provider == payload.provider else None
    )
    if payload.provider in EXTERNAL_PROVIDERS and not api_key:
        raise InvalidAIConfigurationError("The selected provider requires an API key")
    if payload.provider not in EXTERNAL_PROVIDERS:
        api_key = None

    stored = await session.get(AIConfiguration, authorization.organization_id)
    if stored is None:
        stored = AIConfiguration(organization_id=authorization.organization_id)
        session.add(stored)
    stored.provider = payload.provider
    stored.model = payload.model
    stored.encrypted_api_key = (
        encrypt_api_key(settings, authorization.organization_id, api_key) if api_key else None
    )
    add_audit_event(
        session,
        organization_id=authorization.organization_id,
        actor_user_id=authorization.user_id,
        action="UPDATED_AI_CONFIGURATION",
        entity_type="AI_CONFIGURATION",
        entity_id=authorization.organization_id,
        event_data={"provider": payload.provider, "model": payload.model or None},
    )
    await session.flush()
    return RuntimeAIConfiguration(
        provider=payload.provider,
        model=payload.model,
        api_key=api_key,
        source="organization",
    )
