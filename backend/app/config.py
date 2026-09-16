from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


BACKEND_DIR = Path(__file__).resolve().parents[1]
PROJECT_DIR = BACKEND_DIR.parent


class Settings(BaseSettings):
    app_name: str = "Pet Detective"
    environment: str = "development"
    database_url: str = "sqlite:///./pet_detective.db"
    openai_api_key: str | None = None
    openai_model: str = "gpt-5.6-luna"
    agent_reasoning_effort: str = "low"
    agent_max_steps: int = 4
    agent_max_output_tokens: int = 900
    rate_limit_per_minute: int = 10
    allowed_origins: str = "http://localhost:5173"

    model_config = SettingsConfigDict(
        env_file=(PROJECT_DIR / ".env", BACKEND_DIR / ".env"),
        extra="ignore",
    )

    @property
    def origins(self) -> list[str]:
        return [value.strip() for value in self.allowed_origins.split(",") if value.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
