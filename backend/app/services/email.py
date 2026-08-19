import logging

from app.config import Settings

logger = logging.getLogger(__name__)


async def send_user_invitation(
    *, settings: Settings, recipient: str, recipient_name: str, token: str
) -> None:
    if settings.app_env == "production":
        raise RuntimeError("Production email delivery is not configured")
    invitation_url = f"{settings.frontend_public_url}/invite?token={token}"
    logger.warning(
        "Development-only invitation for %s <%s>: %s",
        recipient_name,
        recipient,
        invitation_url,
    )
