from functools import lru_cache
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    api_key: str | None = None

    db_host: str = "localhost"
    db_port: int = 5432
    db_user: str = "dev"
    db_pass: str = "dev"
    db_name: str = "deepdarshak_dev"

    class Config:
        env_prefix = ""  # read raw env names like DB_HOST, API_KEY
        case_sensitive = False


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()