from uuid import UUID

from sqlalchemy import CheckConstraint, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.mixins import TimestampMixin


class AIConfiguration(TimestampMixin, Base):
    __tablename__ = "ai_configurations"
    __table_args__ = (
        CheckConstraint(
            "provider IN ('disabled', 'ollama', 'openai', 'anthropic', 'gemini')",
            name="provider",
        ),
    )

    organization_id: Mapped[UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"), primary_key=True
    )
    provider: Mapped[str] = mapped_column(String(20), nullable=False)
    model: Mapped[str] = mapped_column(String(100), nullable=False)
    encrypted_api_key: Mapped[str | None] = mapped_column(Text, nullable=True)
