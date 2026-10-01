from functools import lru_cache
from typing import Literal

from pydantic import Field, SecretStr, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

DEVELOPMENT_AI_CREDENTIALS_KEY = "development-only-ai-key-change-before-production"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_env: str = "development"
    database_url: str = (
        "postgresql+asyncpg://crm_platform:development-only@localhost:5432/crm_platform"
    )
    session_cookie_name: str = "crm_session"
    csrf_cookie_name: str = "crm_csrf"
    session_idle_seconds: int = 8 * 60 * 60
    invitation_lifetime_seconds: int = 72 * 60 * 60
    frontend_public_url: str = "http://localhost:3000"
    email_backend: Literal["console", "smtp", "disabled"] = "console"
    email_from_address: str = "development@crm.local"
    email_from_name: str = "CRM Platform"
    smtp_host: str = "localhost"
    smtp_port: int = 1025
    smtp_starttls: bool = False
    smtp_username: str | None = None
    smtp_password: SecretStr | None = None
    smtp_timeout_seconds: float = 10
    ai_provider: Literal["disabled", "ollama", "openai", "anthropic", "gemini"] = "disabled"
    ai_model: str = Field(default="", max_length=100, pattern=r"^[a-zA-Z0-9._:/-]*$")
    ai_ollama_url: str = "http://ollama:11434"
    ai_ollama_local_confirmed: bool = False
    ai_openai_api_key: SecretStr | None = None
    ai_anthropic_api_key: SecretStr | None = None
    ai_gemini_api_key: SecretStr | None = None
    ai_credentials_encryption_key: SecretStr = SecretStr(DEVELOPMENT_AI_CREDENTIALS_KEY)
    ai_timeout_seconds: float = Field(default=45, ge=1, le=300)
    ai_cooldown_seconds: int = Field(default=30, ge=1, le=3600)
    ai_cache_ttl_seconds: int = Field(default=900, ge=0, le=86400)

    @property
    def secure_cookies(self) -> bool:
        return self.app_env == "production"

    @model_validator(mode="after")
    def require_production_configuration(self) -> "Settings":
        if self.app_env != "production":
            return self
        encryption_key = self.ai_credentials_encryption_key.get_secret_value()
        if encryption_key == DEVELOPMENT_AI_CREDENTIALS_KEY or len(encryption_key) < 32:
            raise ValueError(
                "AI_CREDENTIALS_ENCRYPTION_KEY must contain at least 32 characters in production"
            )
        if not self.frontend_public_url.startswith("https://"):
            raise ValueError("FRONTEND_PUBLIC_URL must use HTTPS in production")
        if self.email_backend == "console":
            raise ValueError("EMAIL_BACKEND=console is not allowed in production")
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()
