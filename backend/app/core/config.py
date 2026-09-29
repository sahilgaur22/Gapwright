from typing import Any

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=True,
    )

    ENV: str = "development"
    PROJECT_NAME: str = "Gapwright"
    VERSION: str = "0.1.0"
    API_V1_STR: str = "/api/v1"

    # Database
    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/gap"
    DATABASE_URL_MIGRATE: str | None = None

    # Security
    JWT_SECRET: str = "change-me-to-a-secure-secret-key-at-least-32-chars-long"
    JWT_EXPIRE_MINUTES: int = 60

    # LLM Settings
    LLM_PROVIDER: str = "gemini"
    GEMINI_API_KEY: str | None = None
    GROQ_API_KEY: str | None = None
    LLM_MODEL: str | None = None
    EMBED_MODEL: str | None = None
    EMBED_DIM: int = 768
    SKILL_MATCH_THRESHOLD: float = 0.85
    OBSOLETE_DEMAND_THRESHOLD: float = 0.01
    ANALYSIS_WINDOW_DAYS: int = 45

    # Job Sources
    ENABLED_SOURCES: str = "adzuna,jooble,remotive,remoteok,wwr_rss,fixture"
    ADZUNA_APP_ID: str | None = None
    ADZUNA_APP_KEY: str | None = None
    ADZUNA_COUNTRY: str = "in"
    ADZUNA_DAILY_BUDGET: int = 30
    JOOBLE_API_KEY: str | None = None
    JOOBLE_DAILY_BUDGET: int = 20
    CRAWL_PAIRS: str = "Data Scientist|Bangalore;Backend Developer|Delhi"
    CRAWL_TRIGGER_TOKEN: str | None = None
    CRAWL_USER_AGENT: str = "GapwrightBot/1.0 (+contact-url)"
    ENABLE_LOCAL_SCHEDULER: bool = False
    ENABLE_PLAYWRIGHT: bool = False

    # CORS
    CORS_ORIGINS: list[str] = ["http://localhost:3000"]
    CORS_ORIGIN_REGEX: str | None = None
    NEXT_PUBLIC_API_URL: str = "http://localhost:8000"

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def assemble_cors_origins(cls, v: Any) -> list[str]:
        if isinstance(v, str) and not v.startswith("["):
            return [i.strip() for i in v.split(",") if i.strip()]
        elif isinstance(v, list):
            return [str(i) for i in v]
        raise ValueError(f"Invalid CORS_ORIGINS format: {v}")


settings = Settings()
