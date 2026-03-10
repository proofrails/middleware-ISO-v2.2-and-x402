from __future__ import annotations

from app import db


def get_session():
    session = db.SessionLocal()
    try:
        yield session
    finally:
        session.close()
