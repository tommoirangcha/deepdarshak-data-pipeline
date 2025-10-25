from functools import lru_cache
from contextlib import contextmanager
from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from ..core.config import get_settings


@lru_cache(maxsize=1)
def get_engine() -> Engine:
    """Create and cache a single database engine instance."""
    s = get_settings()
    url = f"postgresql+psycopg2://{s.db_user}:{s.db_pass}@{s.db_host}:{s.db_port}/{s.db_name}"
    return create_engine(url, pool_pre_ping=True)

@contextmanager
def db_conn():
    """Provide a database connection from the pool."""
    with get_engine().connect() as conn:
        yield conn