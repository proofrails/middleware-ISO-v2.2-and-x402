from __future__ import annotations

"""Sliding-window rate limiter backed by Redis.

Every response gets three standard headers:
  X-RateLimit-Limit      – request cap per window
  X-RateLimit-Remaining  – requests left in the current window
  X-RateLimit-Reset      – Unix timestamp when the window resets

Returns 429 with `Retry-After` when the cap is exceeded.

Tiers
-----
  public        30 req / 60 s   (no API key)
  project       200 req / 60 s  (project-scoped key)
  project_admin 200 req / 60 s
  admin         1000 req / 60 s

The middleware uses the API key hash to identify the caller cheaply without
hitting the database. Because we can't resolve the role in middleware without
a DB round-trip, unauthenticated callers get the `public` tier and any
bearer of an API key gets `project` — conservative but sufficient at the
middleware layer.
"""

import logging
import time

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

logger = logging.getLogger("middleware.rate_limit")

# (requests_per_window, window_seconds)
_TIERS = {
    "public":        (30,   60),
    "project":       (200,  60),
    "project_admin": (200,  60),
    "admin":         (1000, 60),
}

_SKIP = frozenset({
    "/v1/ping", "/v1/health", "/health", "/ping",
    "/docs", "/openapi.json", "/redoc",
})


class RateLimitMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        if request.url.path in _SKIP:
            return await call_next(request)

        try:
            from app.queue import get_redis
            redis = get_redis()
        except Exception:
            return await call_next(request)

        import hashlib
        raw_key = (
            request.headers.get("X-API-Key")
            or request.headers.get("x-api-key")
            or ""
        )
        if raw_key:
            client_id = "key:" + hashlib.sha256(raw_key.encode()).hexdigest()[:24]
            tier = "project"
        else:
            host = request.client.host if request.client else "0.0.0.0"
            client_id = f"ip:{host}"
            tier = "public"

        limit, window = _TIERS[tier]
        now = time.time()
        window_start = now - window
        redis_key = f"rl:{client_id}"

        try:
            pipe = redis.pipeline()
            pipe.zremrangebyscore(redis_key, 0, window_start)
            pipe.zadd(redis_key, {f"{now:.6f}": now})
            pipe.zcard(redis_key)
            pipe.expire(redis_key, window + 5)
            _, _, count, _ = pipe.execute()
        except Exception as exc:
            logger.debug("rate_limit_redis_error: %s", exc)
            return await call_next(request)

        remaining = max(0, limit - count)
        reset_ts = int(now + window)

        rl_headers = {
            "X-RateLimit-Limit": str(limit),
            "X-RateLimit-Remaining": str(remaining),
            "X-RateLimit-Reset": str(reset_ts),
        }

        if count > limit:
            body = {
                "error": {
                    "code": "RATE_LIMITED",
                    "message": "Rate limit exceeded",
                    "retryable": True,
                    "details": {"retry_after_seconds": window},
                }
            }
            return JSONResponse(
                status_code=429,
                content=body,
                headers={**rl_headers, "Retry-After": str(window)},
            )

        response = await call_next(request)
        for k, v in rl_headers.items():
            response.headers[k] = v
        return response
