from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


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

    @property
    def secure_cookies(self) -> bool:
        return self.app_env == "production"


@lru_cache
def get_settings() -> Settings:
    return Settings()
