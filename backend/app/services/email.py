import asyncio
import logging
from email.message import EmailMessage
from email.utils import formataddr
from html import escape
from smtplib import SMTP

from app.config import Settings

logger = logging.getLogger(__name__)


async def send_user_invitation(
    *, settings: Settings, recipient: str, recipient_name: str, token: str
) -> None:
    invitation_url = f"{settings.frontend_public_url}/invite?token={token}"
    if settings.email_backend == "disabled":
        raise RuntimeError("Email delivery is disabled")
    if settings.email_backend == "console":
        logger.warning(
            "Development-only invitation for %s <%s>: %s",
            recipient_name,
            recipient,
            invitation_url,
        )
        return

    message = _build_invitation_message(
        settings=settings,
        recipient=recipient,
        recipient_name=recipient_name,
        invitation_url=invitation_url,
    )
    await asyncio.to_thread(_send_smtp_message, settings, message)


def _build_invitation_message(
    *, settings: Settings, recipient: str, recipient_name: str, invitation_url: str
) -> EmailMessage:
    safe_name = escape(recipient_name)
    safe_url = escape(invitation_url, quote=True)
    message = EmailMessage()
    message["Subject"] = "Completa tu acceso a CRM Platform"
    message["From"] = formataddr((settings.email_from_name, settings.email_from_address))
    message["To"] = formataddr((recipient_name, recipient))
    message.set_content(
        f"Hola {recipient_name},\n\n"
        "Te han invitado a CRM Platform. Completa tu acceso desde este enlace:\n\n"
        f"{invitation_url}\n\n"
        "Si no esperabas esta invitación, puedes ignorar este mensaje."
    )
    message.add_alternative(
        f"""\
<!doctype html>
<html lang="es">
  <body>
    <p>Hola {safe_name},</p>
    <p>Te han invitado a CRM Platform.</p>
    <p><a href="{safe_url}">Completar mi acceso</a></p>
    <p>Si no esperabas esta invitación, puedes ignorar este mensaje.</p>
  </body>
</html>
""",
        subtype="html",
    )
    return message


def _send_smtp_message(settings: Settings, message: EmailMessage) -> None:
    with SMTP(
        host=settings.smtp_host,
        port=settings.smtp_port,
        timeout=settings.smtp_timeout_seconds,
    ) as smtp:
        if settings.smtp_starttls:
            smtp.starttls()
        if settings.smtp_username and settings.smtp_password:
            smtp.login(settings.smtp_username, settings.smtp_password.get_secret_value())
        smtp.send_message(message)
