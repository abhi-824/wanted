from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    # Database
    db_path: str = "./netacheck.db"

    # CORS — comma-separated origins in .env, parsed into a list here
    allowed_origins: str = "http://localhost:5500"

    # Rate limiting
    rate_limit_enabled: bool = True

    # Environment: "development" | "production"
    env: str = "development"

    @property
    def origins_list(self) -> list[str]:
        return [o.strip() for o in self.allowed_origins.split(",")]

    @property
    def is_production(self) -> bool:
        return self.env == "production"


@lru_cache
def get_settings() -> Settings:
    """
    Cached singleton — same Settings object returned on every call.
    lru_cache means .env is read exactly once at startup.
    """
    return Settings()