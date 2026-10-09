from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "Rotpunkt Translate"
    database_url: str = "postgresql+asyncpg://rotpunkt:rotpunkt@localhost:5433/rotpunkt"
    cors_origins: list[str] = ["http://localhost:5173", "http://localhost:5174", "http://localhost:5555"]
    upload_dir: str = "storage/uploads"

    # Authentication
    secret_key: str = "change_me_in_production_extremely_long_and_secure_random_string"
    access_token_expire_minutes: int = 60 * 24 * 7  # 1 week for MVP convenience

    # Translation Providers
    translation_provider: str = "mock"  # 'mock', 'deepl', or 'gemini'
    deepl_api_key: str | None = None
    gemini_api_key: str | None = None
    openrouter_api_key: str | None = None


@lru_cache
def get_settings() -> Settings:
    return Settings()
