from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
from contextlib import contextmanager
from ..core.config import get_settings


def make_engine() -> Engine:
    s = get_settings()
    url = f"postgresql+psycopg2://{s.db_user}:{s.db_pass}@{s.db_host}:{s.db_port}/{s.db_name}"
    engine = create_engine(url, pool_pre_ping=True, pool_size=5, max_overflow=5)
    return engine


_engine = None


def get_engine() -> Engine:
    global _engine
    if _engine is None:
        _engine = make_engine()
    return _engine


@contextmanager
def db_conn():
    eng = get_engine()
    with eng.connect() as conn:
        yield conn