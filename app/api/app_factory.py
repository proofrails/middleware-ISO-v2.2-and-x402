from __future__ import annotations

import os

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.staticfiles import StaticFiles

from app import db, models
from app.errors import APIError, api_error_handler
from app.middleware import IdempotencyMiddleware, RateLimitMiddleware
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
from .routes.flare_ai import router as flare_ai_router
from .routes.health import router as health_router
from .routes.iso_messages import router as iso_messages_router
from .routes.iso_write import router as iso_write_router
from .routes.monitor import router as monitor_router
from .routes.operations import router as operations_router
from .routes.projects import router as projects_router
from .routes.receipts import router as receipts_router
from .routes.refunds import router as refunds_router
from .routes.sdk import router as sdk_router
from .routes.ui import router as ui_router
from .routes.verify import router as verify_router
from .routes.webhooks import router as webhooks_router
from .routes.x402 import router as x402_router
from .routes.x402_premium import router as x402_premium_router


def create_app() -> FastAPI:
    configure_logging()
    settings = get_settings()

    app = FastAPI(
        title="ISO 20022 Payments Middleware",
        version="2.2.0",
        description=(
            "ISO 20022 payment processing with on-chain anchoring on Flare. "
            "Supports autonomous agent integrations via webhooks, idempotency keys, "
            "cursor pagination, structured errors, and Flare AI Skills (FTSO/FDC)."
        ),
    )

    # ── Exception handlers ────────────────────────────────────────────────────
    app.add_exception_handler(APIError, api_error_handler)

    # ── Middleware stack (innermost first — outermost wraps the request) ──────
    # Order matters: RequestId → RateLimit → Idempotency → CORS → routes
    app.add_middleware(RequestIdMiddleware)
    if settings.rate_limit_enabled:
        app.add_middleware(RateLimitMiddleware)
    if settings.idempotency_enabled:
        app.add_middleware(IdempotencyMiddleware)

    # DB init
    # Prefer Alembic migrations (production). For local/dev we can auto-create tables.
    if settings.auto_create_db:
        models.Base.metadata.create_all(bind=db.engine)

    # Demo mode: seed sample data
    if settings.demo_mode:
        try:
            from app.demo_seed import seed_demo_data
            _s = db.SessionLocal()
            try:
                seed_demo_data(_s)
            finally:
                _s.close()
        except Exception as _e:
            import logging
            logging.getLogger(__name__).warning("demo_seed failed: %s", _e)

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
    # Agentic integration routers
    app.include_router(webhooks_router)
    app.include_router(operations_router)
    app.include_router(flare_ai_router)
    if settings.monitor_enabled:
        app.include_router(monitor_router)

    # Start proactive monitoring loop (daemon thread) only when explicitly enabled.
    if settings.monitor_enabled:
        try:
            from app.monitor import get_monitor
            get_monitor().start()
        except Exception as _exc:
            import logging as _log
            _log.getLogger(__name__).warning("monitor_start_failed: %s", _exc)

    # Demo mode: register demo landing page and start auto-producer
    if settings.demo_mode:
        from .routes.demo import router as demo_router
        app.include_router(demo_router)

        if settings.demo_auto_produce:
            _start_demo_auto_producer()

    return app


def _start_demo_auto_producer() -> None:
    """Start a background thread that creates a new receipt every 30-90 seconds."""
    import logging
    import random
    import threading
    import time
    from datetime import datetime
    from decimal import Decimal
    from uuid import uuid4

    _log = logging.getLogger("demo.auto_producer")

    def _produce_loop():
        # Wait for the app to be fully ready
        time.sleep(5)
        _log.info("demo_auto_producer started")

        chains = ["flare", "ethereum", "base"]
        ccy_map = {"flare": "FLR", "ethereum": "ETH", "base": "USDC"}

        while True:
            interval = random.uniform(30, 90)
            time.sleep(interval)
            try:
                from app import db as _db, models as _models
                from app.queue import enqueue_receipt_processing

                chain = random.choice(chains)
                rid = uuid4()
                now = datetime.utcnow()
                hex8 = lambda: format(random.getrandbits(32), '08x')
                tx_hash = "0x" + hex8() + hex8() + hex8() + hex8() + hex8() + hex8() + hex8() + hex8()
                ref = f"auto:{now.strftime('%H%M%S')}:{hex8()}"
                amt = Decimal(str(round(random.uniform(10, 3000), 2)))
                sender = "0x" + hex8() + hex8() + hex8() + hex8() + hex8()
                receiver = "0x" + hex8() + hex8() + hex8() + hex8() + hex8()

                # Find demo project
                s = _db.SessionLocal()
                try:
                    proj = s.query(_models.Project).filter(_models.Project.name == "Demo Project").first()
                    project_id = proj.id if proj else None

                    receipt = _models.Receipt(
                        id=rid,
                        project_id=project_id,
                        reference=ref,
                        tip_tx_hash=tx_hash,
                        chain=chain,
                        amount=amt,
                        currency=ccy_map[chain],
                        sender_wallet=sender,
                        receiver_wallet=receiver,
                        status="pending",
                        created_at=now,
                    )
                    s.add(receipt)
                    s.commit()

                    enqueue_receipt_processing(receipt_id=str(rid))
                    _log.info("demo_auto_produced rid=%s ref=%s", str(rid), ref)
                finally:
                    s.close()
            except Exception as e:
                _log.debug("demo_auto_produce error: %s", e)

    t = threading.Thread(target=_produce_loop, daemon=True, name="demo-auto-producer")
    t.start()
