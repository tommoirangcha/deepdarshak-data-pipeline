from functools import lru_cache
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # API key (optional) - should be provided via env var in production
    api_key: str | None = None

    # Database connection settings. Avoid storing real passwords in code;
    # these should be provided via environment variables or a local .env file.
    db_host: str = "localhost"
    db_port: int = 5432
    db_user: str = "dev"
    db_pass: str | None = None
    db_name: str = "deepdarshak_dev"

    class Config:
        env_prefix = ""  # read raw env names like DB_HOST, API_KEY
        case_sensitive = False
        # Allow loading from a local .env file
        env_file = ".env"
        env_file_encoding = "utf-8"


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    # Returns a cached Settings instance. Values are loaded from environment
    # variables (or `.env` when present). db_pass will be None unless set.
    return Settings()