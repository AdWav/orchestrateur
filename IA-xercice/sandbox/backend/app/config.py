from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

SANDBOX_DIR = Path(__file__).resolve().parents[2]
ENV_PATH = SANDBOX_DIR / ".env"


class Settings(BaseSettings):
    app_name: str = "Livre d'or API"
    app_env: str = "development"
    database_url: str = "sqlite:///./guestbook.db"
    cors_origins: str = "http://localhost:5173"

    model_config = SettingsConfigDict(
        env_file=str(ENV_PATH),
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()
