from __future__ import annotations

"""HMAC-signed webhook dispatcher.

Fires HTTP POST callbacks to registered WebhookSubscription records when
payment lifecycle events occur. Designed to be called from RQ jobs so it
runs out-of-process and never blocks the API.

Delivery contract
-----------------
POST {url}  Content-Type: application/json
Headers:
  X-ISO-Event            – event topic, e.g. "receipt.anchored"
  X-ISO-Delivery         – UUID for this delivery attempt
  X-ISO-Timestamp        – Unix epoch of dispatch (string)
  X-ISO-Signature-256    – sha256=<hmac-sha256(secret, raw_body)>
  X-ISO-Retry-Attempt    – 1-based attempt number (absent on first delivery)

Verifying signatures (Python example)
--------------------------------------
    import hashlib, hmac
    expected = hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
    trusted = hmac.compare_digest(expected, received_sig.removeprefix("sha256="))

Retry policy
------------
Up to 3 delivery attempts per event with exponential back-off: 5 s, 30 s,
120 s. Retries are stored in a Redis sorted set (score = next_attempt_epoch).
Call `drain_webhook_retry_queue()` from a periodic task to process them.

Event topics
------------
  receipt.pending    – receipt created, processing started
  receipt.anchored   – evidence anchored on-chain (terminal success)
  receipt.failed     – processing or anchoring failed (terminal failure)
  agent.anchored     – agent-initiated anchor confirmed
"""

import hashlib
import hmac
import json
import logging
import time
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

logger = logging.getLogger("middleware.webhooks")

_RETRY_REDIS_KEY = "wh:retry"
_MAX_ATTEMPTS = 3
_RETRY_DELAYS_S = [5, 30, 120]  # seconds before each retry attempt


# ── Public helpers ────────────────────────────────────────────────────────────

def dispatch_event(
    project_id: Optional[str],
    event: str,
    payload: Dict[str, Any],
    session=None,
) -> None:
    """Dispatch an event to all matching webhook subscriptions.

    Safe to call from RQ workers — opens its own DB session when `session`
    is not provided. Never raises; errors are logged at WARNING level.
    """
    try:
        _dispatch(project_id=project_id, event=event, payload=payload, session=session)
    except Exception as exc:
        logger.warning("webhook_dispatch_error event=%s: %s", event, exc)


def dispatch_receipt_event(receipt, event: str, session=None) -> None:
    """Convenience wrapper for receipt lifecycle events.

    Builds the standard receipt event payload and calls `dispatch_event`.
    event: "receipt.pending" | "receipt.anchored" | "receipt.failed"
    """
    import os
    base_url = os.getenv("PUBLIC_BASE_URL", "")
    rid = str(receipt.id)
    payload: Dict[str, Any] = {
        "event": event,
        "receipt_id": rid,
        "status": receipt.status,
        "reference": receipt.reference,
        "bundle_hash": receipt.bundle_hash,
        "flare_txid": receipt.flare_txid,
        "xml_url": f"{base_url}/files/{rid}/pain001.xml",
        "bundle_url": f"{base_url}/files/{rid}/evidence.zip",
        "created_at": receipt.created_at.isoformat() if receipt.created_at else None,
        "anchored_at": receipt.anchored_at.isoformat() if receipt.anchored_at else None,
    }
    # Include agent-defined metadata if present (added in v2 agentic upgrade)
    if getattr(receipt, "metadata", None):
        payload["metadata"] = receipt.extra_metadata
    if getattr(receipt, "tags", None):
        payload["tags"] = receipt.tags

    dispatch_event(
        project_id=str(receipt.project_id) if receipt.project_id else None,
        event=event,
        payload=payload,
        session=session,
    )


def drain_webhook_retry_queue() -> int:
    """Process all due retry records from Redis.

    Returns the number of records processed. Call from a periodic task
    (e.g. a cron job or the monitor daemon).
    """
    try:
        from app.queue import get_redis
        r = get_redis()
    except Exception:
        return 0

    now = time.time()
    due_items: List[bytes] = r.zrangebyscore(_RETRY_REDIS_KEY, 0, now)
    if not due_items:
        return 0

    r.zremrangebyscore(_RETRY_REDIS_KEY, 0, now)
    processed = 0

    for item_bytes in due_items:
        try:
            record = json.loads(item_bytes.decode())
            _retry_delivery(record)
            processed += 1
        except Exception as exc:
            logger.debug("webhook_retry_process_error: %s", exc)

    return processed


# ── Internals ─────────────────────────────────────────────────────────────────

def _dispatch(
    project_id: Optional[str],
    event: str,
    payload: Dict[str, Any],
    session=None,
) -> None:
    own_session = session is None
    if own_session:
        from app import db
        session = db.SessionLocal()

    try:
        from app.models import WebhookSubscription
        q = session.query(WebhookSubscription).filter(
            WebhookSubscription.enabled == "true",
        )
        if project_id:
            q = q.filter(WebhookSubscription.project_id == project_id)
        else:
            q = q.filter(WebhookSubscription.project_id.is_(None))

        subs = q.all()
        for sub in subs:
            events: List[str] = sub.events or []
            if "*" not in events and event not in events:
                continue
            _fire(sub, event, payload, session)
    finally:
        if own_session:
            session.close()


def _fire(sub, event: str, payload: Dict[str, Any], session) -> None:
    delivery_id = str(uuid.uuid4())
    body_str = json.dumps(payload, default=str)
    sig = _sign(sub.secret, body_str)
    ts = str(int(time.time()))

    headers = {
        "Content-Type": "application/json",
        "X-ISO-Event": event,
        "X-ISO-Delivery": delivery_id,
        "X-ISO-Timestamp": ts,
        "X-ISO-Signature-256": f"sha256={sig}",
    }

    succeeded = False
    try:
        import requests as req
        resp = req.post(sub.url, data=body_str.encode(), headers=headers, timeout=10)
        status = resp.status_code

        sub.last_fired_at = datetime.now(timezone.utc)
        sub.last_status_code = str(status)
        session.commit()

        if 200 <= status < 300:
            logger.info(
                "webhook_delivered sub=%s event=%s status=%s delivery=%s",
                str(sub.id), event, status, delivery_id,
            )
            succeeded = True
        else:
            logger.warning(
                "webhook_non2xx sub=%s event=%s status=%s",
                str(sub.id), event, status,
            )
    except Exception as exc:
        logger.warning("webhook_delivery_error sub=%s event=%s: %s", str(sub.id), event, exc)

    if not succeeded:
        _schedule_retry(
            sub_id=str(sub.id),
            event=event,
            payload=payload,
            attempt=1,
            delivery_id=delivery_id,
        )


def _retry_delivery(record: Dict[str, Any]) -> None:
    sub_id = record["sub_id"]
    event = record["event"]
    payload = record["payload"]
    attempt = record["attempt"]
    delivery_id = record["delivery_id"]

    from app import db
    from app.models import WebhookSubscription
    session = db.SessionLocal()
    try:
        sub = session.get(WebhookSubscription, sub_id)
        if not sub or sub.enabled != "true":
            return

        body_str = json.dumps(payload, default=str)
        sig = _sign(sub.secret, body_str)
        ts = str(int(time.time()))
        headers = {
            "Content-Type": "application/json",
            "X-ISO-Event": event,
            "X-ISO-Delivery": delivery_id,
            "X-ISO-Timestamp": ts,
            "X-ISO-Signature-256": f"sha256={sig}",
            "X-ISO-Retry-Attempt": str(attempt),
        }

        import requests as req
        succeeded = False
        try:
            resp = req.post(sub.url, data=body_str.encode(), headers=headers, timeout=10)
            status = resp.status_code
            sub.last_fired_at = datetime.now(timezone.utc)
            sub.last_status_code = str(status)
            session.commit()
            if 200 <= status < 300:
                logger.info(
                    "webhook_retry_delivered sub=%s attempt=%s delivery=%s",
                    sub_id, attempt, delivery_id,
                )
                succeeded = True
        except Exception as exc:
            logger.debug("webhook_retry_error sub=%s attempt=%s: %s", sub_id, attempt, exc)

        if not succeeded:
            _schedule_retry(sub_id, event, payload, attempt + 1, delivery_id)
    finally:
        session.close()


def _schedule_retry(
    sub_id: str,
    event: str,
    payload: Dict[str, Any],
    attempt: int,
    delivery_id: str,
) -> None:
    if attempt > _MAX_ATTEMPTS:
        logger.warning(
            "webhook_max_attempts_reached sub=%s event=%s delivery=%s",
            sub_id, event, delivery_id,
        )
        return

    delay = _RETRY_DELAYS_S[attempt - 1]
    next_at = time.time() + delay
    record = json.dumps({
        "sub_id": sub_id,
        "event": event,
        "payload": payload,
        "attempt": attempt,
        "delivery_id": delivery_id,
    }, default=str)
    try:
        from app.queue import get_redis
        r = get_redis()
        r.zadd(_RETRY_REDIS_KEY, {record: next_at})
        logger.debug(
            "webhook_retry_scheduled sub=%s attempt=%s in=%ss",
            sub_id, attempt, delay,
        )
    except Exception as exc:
        logger.debug("webhook_retry_schedule_error: %s", exc)


def _sign(secret: str, body: str) -> str:
    return hmac.new(secret.encode(), body.encode(), hashlib.sha256).hexdigest()
