from __future__ import annotations

"""Webhook subscription management.

Agents and integrations register webhook URLs here to receive push
notifications for receipt lifecycle events instead of polling.

Event topics
------------
  receipt.pending   – receipt accepted and queued for processing
  receipt.anchored  – evidence anchored on-chain (terminal success)
  receipt.failed    – processing or anchoring failed (terminal failure)
  *                 – wildcard: receive all events

Payload shape (all events)
--------------------------
    {
      "event": "receipt.anchored",
      "receipt_id": "...",
      "status": "anchored",
      "reference": "...",
      "bundle_hash": "0x...",
      "flare_txid": "0x...",
      "xml_url": "https://api/files/.../pain001.xml",
      "bundle_url": "https://api/files/.../evidence.zip",
      "created_at": "2024-01-01T00:00:00Z",
      "anchored_at": "2024-01-01T00:01:00Z",
      "metadata": {...},
      "tags": [...]
    }

Signature verification
----------------------
    import hashlib, hmac
    body = request.body()          # raw bytes
    sig = request.headers["X-ISO-Signature-256"].removeprefix("sha256=")
    expected = hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
    assert hmac.compare_digest(expected, sig)
"""

import secrets
import uuid
from datetime import datetime, timezone
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from app import models
from app.api.deps import get_session
from app.auth import Principal, resolve_principal
from app.errors import APIError, ErrorCode

router = APIRouter(prefix="/v1/webhooks", tags=["webhooks"])

_MAX_PER_PROJECT = 10  # configurable via settings if needed

VALID_EVENTS = frozenset({
    "receipt.pending",
    "receipt.anchored",
    "receipt.failed",
    "agent.anchored",
    "*",
})


# ── Schemas ───────────────────────────────────────────────────────────────────

class WebhookCreate(BaseModel):
    url: str = Field(..., description="HTTPS URL to receive webhook POST requests")
    events: List[str] = Field(
        default=["receipt.anchored", "receipt.failed"],
        description="Event topics to subscribe to. Use '*' for all events.",
    )
    description: Optional[str] = Field(None, description="Human-readable label")


class WebhookUpdate(BaseModel):
    url: Optional[str] = None
    events: Optional[List[str]] = None
    description: Optional[str] = None
    enabled: Optional[bool] = None


class WebhookInfo(BaseModel):
    id: str
    url: str
    events: List[str]
    description: Optional[str]
    enabled: bool
    created_at: datetime
    last_fired_at: Optional[datetime]
    last_status_code: Optional[str]


class WebhookTestResponse(BaseModel):
    delivered: bool
    status_code: Optional[int]
    error: Optional[str]


# ── Routes ────────────────────────────────────────────────────────────────────

@router.post("", response_model=WebhookInfo, status_code=201)
def create_webhook(
    body: WebhookCreate,
    session=Depends(get_session),
    principal: Principal = Depends(resolve_principal),
):
    """Register a new webhook subscription.

    Returns the subscription including the `secret` field which is only
    surfaced at creation time — store it securely for signature verification.
    """
    if principal.is_public:
        raise HTTPException(status_code=401, detail="Unauthorized")

    # Validate event topics
    invalid = [e for e in body.events if e not in VALID_EVENTS]
    if invalid:
        raise APIError(
            ErrorCode.VALIDATION_ERROR,
            f"Unknown event topics: {invalid}. Valid: {sorted(VALID_EVENTS)}",
            400,
        )

    # Enforce per-project cap
    if principal.project_id:
        count = (
            session.query(models.WebhookSubscription)
            .filter(models.WebhookSubscription.project_id == principal.project_id)
            .count()
        )
        if count >= _MAX_PER_PROJECT:
            raise APIError(
                ErrorCode.WEBHOOK_LIMIT_REACHED,
                f"Maximum {_MAX_PER_PROJECT} webhooks per project",
                409,
            )

    sub = models.WebhookSubscription(
        id=uuid.uuid4(),
        project_id=principal.project_id,
        url=body.url,
        events=body.events,
        description=body.description,
        secret=secrets.token_hex(32),
        enabled="true",
        created_at=datetime.now(timezone.utc),
    )
    session.add(sub)
    session.commit()

    return _to_info(sub)


@router.get("", response_model=List[WebhookInfo])
def list_webhooks(
    session=Depends(get_session),
    principal: Principal = Depends(resolve_principal),
):
    """List all webhook subscriptions for the authenticated project."""
    if principal.is_public:
        raise HTTPException(status_code=401, detail="Unauthorized")

    q = session.query(models.WebhookSubscription)
    if not principal.is_admin:
        q = q.filter(models.WebhookSubscription.project_id == principal.project_id)

    return [_to_info(s) for s in q.order_by(models.WebhookSubscription.created_at.desc()).all()]


@router.get("/{webhook_id}", response_model=WebhookInfo)
def get_webhook(
    webhook_id: str,
    session=Depends(get_session),
    principal: Principal = Depends(resolve_principal),
):
    sub = _load_or_404(webhook_id, session, principal)
    return _to_info(sub)


@router.put("/{webhook_id}", response_model=WebhookInfo)
def update_webhook(
    webhook_id: str,
    body: WebhookUpdate,
    session=Depends(get_session),
    principal: Principal = Depends(resolve_principal),
):
    sub = _load_or_404(webhook_id, session, principal)

    if body.url is not None:
        sub.url = body.url
    if body.events is not None:
        invalid = [e for e in body.events if e not in VALID_EVENTS]
        if invalid:
            raise APIError(ErrorCode.VALIDATION_ERROR, f"Unknown event topics: {invalid}", 400)
        sub.events = body.events
    if body.description is not None:
        sub.description = body.description
    if body.enabled is not None:
        sub.enabled = "true" if body.enabled else "false"

    sub.updated_at = datetime.now(timezone.utc)
    session.commit()
    return _to_info(sub)


@router.delete("/{webhook_id}", status_code=204)
def delete_webhook(
    webhook_id: str,
    session=Depends(get_session),
    principal: Principal = Depends(resolve_principal),
):
    sub = _load_or_404(webhook_id, session, principal)
    session.delete(sub)
    session.commit()


@router.post("/{webhook_id}/test", response_model=WebhookTestResponse)
def test_webhook(
    webhook_id: str,
    session=Depends(get_session),
    principal: Principal = Depends(resolve_principal),
):
    """Fire a test event to the webhook URL.

    Sends a `webhook.test` event with a synthetic payload so you can verify
    your endpoint is reachable and your signature verification is correct.
    """
    sub = _load_or_404(webhook_id, session, principal)

    import hashlib
    import hmac
    import json
    import time

    import requests as req

    test_payload = {
        "event": "webhook.test",
        "webhook_id": str(sub.id),
        "message": "This is a test delivery from the ISO 20022 middleware.",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    body_str = json.dumps(test_payload)
    sig = hmac.new(sub.secret.encode(), body_str.encode(), hashlib.sha256).hexdigest()
    ts = str(int(time.time()))

    headers = {
        "Content-Type": "application/json",
        "X-ISO-Event": "webhook.test",
        "X-ISO-Delivery": str(uuid.uuid4()),
        "X-ISO-Timestamp": ts,
        "X-ISO-Signature-256": f"sha256={sig}",
    }

    try:
        resp = req.post(sub.url, data=body_str.encode(), headers=headers, timeout=10)
        return WebhookTestResponse(
            delivered=200 <= resp.status_code < 300,
            status_code=resp.status_code,
        )
    except Exception as exc:
        return WebhookTestResponse(delivered=False, error=str(exc))


# ── Helpers ───────────────────────────────────────────────────────────────────

def _load_or_404(webhook_id: str, session, principal: Principal) -> models.WebhookSubscription:
    sub = session.get(models.WebhookSubscription, webhook_id)
    if not sub:
        raise APIError(ErrorCode.WEBHOOK_NOT_FOUND, f"Webhook '{webhook_id}' not found", 404)
    if not principal.is_admin and str(sub.project_id) != principal.project_id:
        raise HTTPException(status_code=403, detail="Forbidden")
    return sub


def _to_info(sub: models.WebhookSubscription) -> WebhookInfo:
    return WebhookInfo(
        id=str(sub.id),
        url=sub.url,
        events=sub.events or [],
        description=sub.description,
        enabled=sub.enabled == "true",
        created_at=sub.created_at,
        last_fired_at=sub.last_fired_at,
        last_status_code=sub.last_status_code,
    )
