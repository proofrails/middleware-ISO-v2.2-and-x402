from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter
from starlette.responses import PlainTextResponse

from app.queue import get_redis
from app.settings import get_settings

router = APIRouter(tags=["health"])


@router.get("/v1/health")
def health() -> dict:
    settings = get_settings()

    # Best-effort dependency checks
    db_ok = True
    db_detail = "ok"
    try:
        # Lazy import to avoid circular imports
        from sqlalchemy import text

        from app.db import engine

        with engine.connect() as c:
            c.execute(text("select 1"))
    except Exception as e:  # pragma: no cover
        db_ok = False
        db_detail = str(e)

    redis_ok = True
    redis_detail = "ok"
    try:
        get_redis().ping()
    except Exception as e:  # pragma: no cover
        redis_ok = False
        redis_detail = str(e)

    return {
        "status": "ok" if (db_ok and redis_ok) else "degraded",
        "ts": datetime.utcnow().isoformat(),
        "env": settings.app_env,
        "deps": {
            "db": {"ok": db_ok, "detail": db_detail},
            "redis": {"ok": redis_ok, "detail": redis_detail},
        },
    }


@router.get("/v1/ping", response_class=PlainTextResponse)
def ping() -> str:
    return "pong"
