from __future__ import annotations

from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

from .settings import get_settings

settings = get_settings()

DATABASE_URL = settings.effective_database_url

# Use a wide type to allow SQLAlchemy engine kwargs mutations (e.g. connect_args for sqlite)
engine_kwargs: dict[str, object] = {"echo": settings.sql_echo, "future": True}

if DATABASE_URL.startswith("sqlite"):
    # Needed for SQLite in multithreaded FastAPI dev
    engine_kwargs["connect_args"] = {"check_same_thread": False}

engine = create_engine(DATABASE_URL, **engine_kwargs)

SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)

Base = declarative_base()
