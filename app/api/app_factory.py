from __future__ import annotations

import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.staticfiles import StaticFiles

from app import db, models
from app.observability import RequestIdMiddleware, configure_logging
from app.settings import get_settings

from .routes.agent_anchoring import router as agent_anchoring_router
from .routes.agents import router as agents_router
from .routes.ai import router as ai_router
from .routes.ai_agents import router as ai_agents_router
from .routes.anchors import router as anchors_router
from .routes.api_keys import router as api_keys_router
from .routes.auth import router as auth_router
from .routes.config import router as config_router
from .routes.confirm_anchor import router as confirm_anchor_router
from .routes.debug import router as debug_router
from .routes.events import router as events_router
from .routes.fi_messages import router as fi_messages_router
from .routes.health import router as health_router
from .routes.iso_messages import router as iso_messages_router
from .routes.iso_write import router as iso_write_router
from .routes.projects import router as projects_router
from .routes.receipts import router as receipts_router
from .routes.refunds import router as refunds_router
from .routes.sdk import router as sdk_router
from .routes.ui import router as ui_router
from .routes.verify import router as verify_router
from .routes.x402 import router as x402_router
from .routes.x402_premium import router as x402_premium_router


def create_app() -> FastAPI:
    configure_logging()
    settings = get_settings()

    app = FastAPI(title="ISO 20022 Payments Middleware", version="0.1.0")

    # Request correlation
    app.add_middleware(RequestIdMiddleware)

    # DB init
    # Prefer Alembic migrations (production). For local/dev we can auto-create tables.
    if settings.auto_create_db:
        models.Base.metadata.create_all(bind=db.engine)

    # CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.allow_origins_list,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Static
    os.makedirs(settings.artifacts_dir, exist_ok=True)
    app.mount("/files", StaticFiles(directory=settings.artifacts_dir), name="files")
    app.mount("/ui", StaticFiles(directory="ui"), name="ui")
    app.mount("/embed", StaticFiles(directory="embed"), name="embed")

    # Routers
    app.include_router(health_router)
    app.include_router(receipts_router)
    app.include_router(verify_router)
    app.include_router(iso_messages_router)
    app.include_router(fi_messages_router)
    app.include_router(refunds_router)
    app.include_router(sdk_router)
    app.include_router(ai_router)
    app.include_router(config_router)
    app.include_router(auth_router)
    app.include_router(projects_router)
    app.include_router(iso_write_router)
    app.include_router(anchors_router)
    app.include_router(ui_router)
    app.include_router(events_router)
    app.include_router(debug_router)
    app.include_router(api_keys_router)
    app.include_router(confirm_anchor_router)
    app.include_router(x402_router)
    app.include_router(x402_premium_router)
    app.include_router(agents_router)
    app.include_router(ai_agents_router)
    app.include_router(agent_anchoring_router)

    return app
