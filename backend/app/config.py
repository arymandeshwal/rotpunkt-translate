from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "Rotpunkt Translate"
    database_url: str = "postgresql+asyncpg://rotpunkt:rotpunkt@localhost:5433/rotpunkt"
    cors_origins: list[str] = ["http://localhost:5173"]
    upload_dir: str = "storage/uploads"

    # Translation Providers
    translation_provider: str = "mock"  # 'mock', 'deepl', or 'gemini'
    deepl_api_key: str | None = None
    gemini_api_key: str | None = None


@lru_cache
def get_settings() -> Settings:
    return Settings()
