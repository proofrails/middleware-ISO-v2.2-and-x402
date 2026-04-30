"""Shared pytest fixtures for in-process TestClient tests.

Sets up a SQLite database and disables Redis-backed middleware so tests run
without any external services.
"""
from __future__ import annotations

import os
import pytest

# Disable Redis-backed middleware before any app imports
os.environ.setdefault("RATE_LIMIT_ENABLED", "false")
os.environ.setdefault("IDEMPOTENCY_ENABLED", "false")
os.environ.setdefault("AUTO_CREATE_DB", "true")
os.environ.setdefault("DATABASE_URL", "sqlite:///./test_agentic.db")
os.environ.setdefault("DEMO_MODE", "false")
os.environ.setdefault("MONITOR_ENABLED", "false")
os.environ.setdefault("FTSO_ENABLED", "false")   # no live RPC in tests


@pytest.fixture(scope="session")
def app():
    from app.api.app_factory import create_app
    return create_app()


@pytest.fixture(scope="session")
def client(app):
    from fastapi.testclient import TestClient
    with TestClient(app, raise_server_exceptions=True) as c:
        yield c


@pytest.fixture(scope="session")
def db_session():
    from app import db
    session = db.SessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture(scope="session")
def admin_headers():
    """Return headers for an admin principal (env-key based)."""
    os.environ["API_KEYS"] = "test-admin-key"
    return {"X-API-Key": "test-admin-key"}
