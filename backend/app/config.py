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

    @property
    def secure_cookies(self) -> bool:
        return self.app_env == "production"


@lru_cache
def get_settings() -> Settings:
    return Settings()
