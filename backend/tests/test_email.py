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
async def test_production_email_delivery_remains_unconfigured() -> None:
    with pytest.raises(RuntimeError, match="Production email delivery is not configured"):
        await email_service.send_user_invitation(
            settings=Settings(app_env="production", email_backend="smtp"),
            recipient="invited@example.com",
            recipient_name="Invited User",
            token="one-time-token",
        )
