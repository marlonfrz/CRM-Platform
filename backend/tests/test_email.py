from email.message import EmailMessage

import pytest

from app.config import Settings
from app.services import email as email_service


@pytest.mark.asyncio
async def test_smtp_invitation_contains_local_acceptance_link(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    sent_messages: list[EmailMessage] = []

    class FakeSMTP:
        def __init__(self, *, host: str, port: int, timeout: float) -> None:
            assert host == "mailpit"
            assert port == 1025
            assert timeout == 10

        def __enter__(self) -> "FakeSMTP":
            return self

        def __exit__(self, *args: object) -> None:
            return None

        def starttls(self) -> None:
            raise AssertionError("Mailpit must not use STARTTLS in local development")

        def login(self, username: str, password: str) -> None:
            raise AssertionError("Mailpit must not receive credentials in local development")

        def send_message(self, message: EmailMessage) -> None:
            sent_messages.append(message)

    monkeypatch.setattr(email_service, "SMTP", FakeSMTP)
    settings = Settings(
        app_env="development",
        email_backend="smtp",
        smtp_host="mailpit",
        smtp_port=1025,
        email_from_address="development@crm.local",
        email_from_name="CRM Platform",
    )

    await email_service.send_user_invitation(
        settings=settings,
        recipient="invited@example.com",
        recipient_name="Invited User",
        token="one-time-token",
    )

    assert len(sent_messages) == 1
    message = sent_messages[0]
    assert message["From"] == "CRM Platform <development@crm.local>"
    assert message["To"] == "Invited User <invited@example.com>"
    plain_body = message.get_body(preferencelist=("plain",))
    assert plain_body is not None
    assert "http://localhost:3000/invite?token=one-time-token" in plain_body.get_content()


@pytest.mark.asyncio
async def test_production_smtp_delivery_uses_tls_and_credentials(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    events: list[object] = []

    class FakeSMTP:
        def __init__(self, *, host: str, port: int, timeout: float) -> None:
            events.append((host, port, timeout))

        def __enter__(self) -> "FakeSMTP":
            return self

        def __exit__(self, *args: object) -> None:
            return None

        def starttls(self) -> None:
            events.append("starttls")

        def login(self, username: str, password: str) -> None:
            events.append((username, password))

        def send_message(self, message: EmailMessage) -> None:
            events.append(message)

    monkeypatch.setattr(email_service, "SMTP", FakeSMTP)
    await email_service.send_user_invitation(
        settings=Settings(
            app_env="production",
            frontend_public_url="https://crm.example.com",
            email_backend="smtp",
            email_from_address="crm@example.com",
            smtp_host="smtp.example.com",
            smtp_port=587,
            smtp_starttls=True,
            smtp_username="crm@example.com",
            smtp_password="smtp-secret",
            ai_credentials_encryption_key="test-production-ai-encryption-key",
        ),
        recipient="invited@example.com",
        recipient_name="Invited User",
        token="one-time-token",
    )

    assert events[:3] == [
        ("smtp.example.com", 587, 10),
        "starttls",
        ("crm@example.com", "smtp-secret"),
    ]
    message = events[3]
    assert isinstance(message, EmailMessage)
    assert "https://crm.example.com/invite?token=one-time-token" in message.get_body(
        preferencelist=("plain",)
    ).get_content()


def test_production_settings_reject_insecure_public_url_and_console_email() -> None:
    with pytest.raises(ValueError, match="FRONTEND_PUBLIC_URL must use HTTPS"):
        Settings(
            app_env="production",
            email_backend="disabled",
            ai_credentials_encryption_key="test-production-ai-encryption-key",
        )

    with pytest.raises(ValueError, match="EMAIL_BACKEND=console"):
        Settings(
            app_env="production",
            frontend_public_url="https://crm.example.com",
            email_backend="console",
            ai_credentials_encryption_key="test-production-ai-encryption-key",
        )
