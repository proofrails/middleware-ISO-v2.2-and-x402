from __future__ import annotations

"""ASGI entrypoint.

Keep this file intentionally small.
All routing is defined under `app/api/routes/*` and registered in `create_app()`.
"""

# Expose Prometheus metrics at /metrics (best-effort)
try:
    from prometheus_fastapi_instrumentator import Instrumentator  # type: ignore
except Exception:  # pragma: no cover
    Instrumentator = None  # type: ignore

from app.api.app_factory import create_app

app = create_app()

try:
    if Instrumentator:
        Instrumentator().instrument(app).expose(app)  # type: ignore
except Exception:
    pass
