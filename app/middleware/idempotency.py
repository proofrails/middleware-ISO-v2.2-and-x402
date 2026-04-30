from __future__ import annotations

"""Idempotency-Key middleware for safe mutation retries.

Agentic clients frequently retry requests on transient failures. Without
idempotency protection, a network blip between the client receiving a 5xx
and the server having already committed the write produces duplicate receipts.

Usage
-----
Include `Idempotency-Key: <client-uuid>` on any POST/PUT/PATCH request.
The first execution is stored in Redis (TTL 24 h). Subsequent requests with
the same key receive the cached response with `Idempotency-Replayed: true`
instead of re-running the operation.

Scoping
-------
Keys are scoped to the caller (API-key hash or IP for anonymous clients) so
two different callers can use the same key value without collision.

Caching policy
--------------
Only 2xx responses are cached. 4xx/5xx are not stored so the client can
retry with a corrected request using the same key.
"""

import base64
import hashlib
import json
import logging
from typing import Optional

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

logger = logging.getLogger("middleware.idempotency")

_TTL_SECONDS = 86_400  # 24 hours
_METHODS = frozenset({"POST", "PUT", "PATCH"})


class IdempotencyMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        idem_key: Optional[str] = request.headers.get("Idempotency-Key")
        if not idem_key or request.method not in _METHODS:
            return await call_next(request)

        raw_api_key = (
            request.headers.get("X-API-Key")
            or request.headers.get("x-api-key")
            or ""
        )
        if raw_api_key:
            scope = hashlib.sha256(raw_api_key.encode()).hexdigest()[:16]
        else:
            scope = request.client.host if request.client else "anon"

        redis_key = f"idem:{scope}:{idem_key}"

        try:
            from app.queue import get_redis
            redis = get_redis()
        except Exception:
            return await call_next(request)

        # ── Cache hit ─────────────────────────────────────────────────────────
        try:
            cached_raw = redis.get(redis_key)
            if cached_raw:
                data = json.loads(cached_raw.decode())
                body = base64.b64decode(data["body"])
                headers = {
                    **data.get("headers", {}),
                    "Idempotency-Replayed": "true",
                }
                return Response(
                    content=body,
                    status_code=data["status_code"],
                    headers=headers,
                    media_type=data.get("media_type", "application/json"),
                )
        except Exception as exc:
            logger.debug("idempotency_cache_read_error: %s", exc)

        # ── Execute and cache on 2xx ───────────────────────────────────────────
        response = await call_next(request)

        if 200 <= response.status_code < 300:
            try:
                chunks = []
                async for chunk in response.body_iterator:
                    chunks.append(chunk)
                body = b"".join(chunks)

                safe_headers = {
                    k: v for k, v in response.headers.items()
                    if k.lower() in {"content-type", "x-request-id"}
                }
                payload = json.dumps({
                    "status_code": response.status_code,
                    "body": base64.b64encode(body).decode(),
                    "headers": safe_headers,
                    "media_type": response.media_type,
                })
                redis.setex(redis_key, _TTL_SECONDS, payload.encode())

                return Response(
                    content=body,
                    status_code=response.status_code,
                    headers=dict(response.headers),
                    media_type=response.media_type,
                )
            except Exception as exc:
                logger.debug("idempotency_cache_write_error: %s", exc)

        return response
