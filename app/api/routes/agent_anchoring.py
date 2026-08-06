"""Agent anchoring — connect agents with on-chain evidence anchoring."""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timedelta
from uuid import uuid4

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from sqlalchemy.orm import Session

from app import models, schemas
from app.api.deps import get_session
from app.auth.api_key_auth import resolve_principal
from app.auth.principal import Principal

router = APIRouter(tags=["agent-anchoring"])


# ── Helpers ───────────────────────────────────────────────────────────────────

def _require_agent(
    agent_id: str,
    session: Session,
    principal: Principal,
) -> models.AgentConfig:
    """Load agent and verify ownership. Raises 404 or 403."""
    import uuid as _uuid
    try:
        _uuid.UUID(agent_id)
    except (ValueError, AttributeError):
        raise HTTPException(404, "agent_not_found")
    agent = session.get(models.AgentConfig, agent_id)
    if not agent:
        raise HTTPException(404, "agent_not_found")
    if not principal.is_admin and agent.project_id != principal.project_id:
        raise HTTPException(403, "access_denied")
    return agent


def _canonical_hash(data: dict) -> str:
    """SHA-256 of canonical JSON (sorted keys, compact). Returns 0x-prefixed hex."""
    canonical = json.dumps(data, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    digest = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
    return f"0x{digest}"


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.get("/v1/agents/{agent_id}/anchoring-config")
def get_anchoring_config(
    agent_id: str,
    session: Session = Depends(get_session),
    principal: Principal = Depends(resolve_principal),
):
    """Return the current anchoring configuration for an agent.

    Fields:
    - ``auto_anchor_enabled``: whether receipts are automatically anchored
    - ``anchor_on_payment``: whether x402 payments trigger auto-anchoring
    - ``anchor_wallet``: EVM wallet used for on-chain transactions (address only)
    """
    if principal.is_public:
        raise HTTPException(401, "auth_required")
    agent = _require_agent(agent_id, session, principal)

    return {
        "id": str(agent.id),
        "auto_anchor_enabled": bool(agent.auto_anchor_enabled),
        "anchor_on_payment": bool(agent.anchor_on_payment),
        "anchor_wallet": agent.anchor_wallet_address,
    }


@router.put("/v1/agents/{agent_id}/anchoring-config")
def update_anchoring_config(
    agent_id: str,
    payload: schemas.AgentAnchoringConfig,
    session: Session = Depends(get_session),
    principal: Principal = Depends(resolve_principal),
):
    """Update anchoring configuration for an agent.

    Pass only the fields you want to change. Private key is write-only:
    it is stored encrypted and never returned.
    """
    if principal.is_public:
        raise HTTPException(401, "auth_required")
    agent = _require_agent(agent_id, session, principal)

    if payload.auto_anchor_enabled is not None:
        agent.auto_anchor_enabled = payload.auto_anchor_enabled

    if payload.anchor_on_payment is not None:
        agent.anchor_on_payment = payload.anchor_on_payment

    if payload.anchor_wallet_address is not None:
        agent.anchor_wallet_address = payload.anchor_wallet_address

    if payload.anchor_private_key is not None and payload.anchor_private_key:
        import base64
        agent.anchor_private_key_encrypted = base64.b64encode(
            payload.anchor_private_key.encode()
        ).decode()

    agent.updated_at = datetime.utcnow()
    session.commit()
    session.refresh(agent)

    return {
        "id": str(agent.id),
        "auto_anchor_enabled": bool(agent.auto_anchor_enabled),
        "anchor_on_payment": bool(agent.anchor_on_payment),
        "anchor_wallet": agent.anchor_wallet_address,
    }


@router.post("/v1/agents/{agent_id}/anchor-data")
def anchor_data(
    agent_id: str,
    payload: schemas.AgentAnchorDataRequest,
    background_tasks: BackgroundTasks,
    session: Session = Depends(get_session),
    principal: Principal = Depends(resolve_principal),
):
    """Hash arbitrary JSON data and optionally anchor the hash on-chain.

    The ``data`` dict is serialised to canonical JSON (sorted keys, compact),
    then SHA-256 hashed. Only the hash is stored — raw data is never persisted.

    Set ``submit_onchain=true`` to immediately queue an on-chain anchor
    transaction. Requires either the agent's ``anchor_wallet_address`` or the
    system ``ANCHOR_PRIVATE_KEY`` env var to be configured.
    """
    if principal.is_public:
        raise HTTPException(401, "auth_required")
    agent = _require_agent(agent_id, session, principal)

    anchor_hash = _canonical_hash(payload.data)

    chain = payload.chain or "flare"

    agent_anchor = models.AgentAnchor(
        id=uuid4(),
        agent_id=agent.id,
        receipt_id=None,
        bundle_hash=anchor_hash,
        chain=chain,
        status="pending",
    )
    session.add(agent_anchor)
    session.commit()
    session.refresh(agent_anchor)

    if payload.submit_onchain:
        background_tasks.add_task(
            _perform_anchor,
            anchor_id=str(agent_anchor.id),
            bundle_hash=anchor_hash,
            agent_wallet=agent.anchor_wallet_address,
            agent_key=agent.anchor_private_key_encrypted,
        )

    return schemas.AgentAnchorDataResponse(
        id=str(agent_anchor.id),
        agent_id=str(agent.id),
        anchor_hash=anchor_hash,
        chain=chain,
        status=agent_anchor.status,
        submit_onchain=payload.submit_onchain,
        description=payload.description,
        created_at=agent_anchor.created_at,
    )


@router.post("/v1/agents/{agent_id}/anchor")
async def trigger_agent_anchor(
    agent_id: str,
    payload: schemas.AgentAnchorRequest,
    background_tasks: BackgroundTasks,
    session: Session = Depends(get_session),
    principal: Principal = Depends(resolve_principal),
):
    """Anchor an existing bundle hash on-chain.

    Use this when you already have a ``bundle_hash`` (e.g. from a receipt).
    To hash and anchor arbitrary data in one step use POST anchor-data instead.
    """
    if principal.is_public:
        raise HTTPException(401, "auth_required")
    agent = _require_agent(agent_id, session, principal)

    bundle_hash = payload.bundle_hash
    receipt_id = payload.receipt_id

    agent_anchor = models.AgentAnchor(
        id=uuid4(),
        agent_id=agent.id,
        receipt_id=receipt_id,
        bundle_hash=bundle_hash,
        status="pending",
    )
    session.add(agent_anchor)
    session.commit()
    session.refresh(agent_anchor)

    background_tasks.add_task(
        _perform_anchor,
        anchor_id=str(agent_anchor.id),
        bundle_hash=bundle_hash,
        agent_wallet=agent.anchor_wallet_address,
        agent_key=agent.anchor_private_key_encrypted,
    )

    return {
        "anchor_id": str(agent_anchor.id),
        "bundle_hash": bundle_hash,
        "status": "pending",
        "message": "Anchoring queued",
    }


@router.get("/v1/agents/{agent_id}/anchors")
def list_agent_anchors(
    agent_id: str,
    days: int = 7,
    status: str = None,
    session: Session = Depends(get_session),
    principal: Principal = Depends(resolve_principal),
):
    """List anchors created by this agent, newest first."""
    if principal.is_public:
        raise HTTPException(401, "auth_required")
    _require_agent(agent_id, session, principal)

    q = session.query(models.AgentAnchor).filter_by(agent_id=agent_id)
    since = datetime.utcnow() - timedelta(days=days)
    q = q.filter(models.AgentAnchor.created_at >= since)
    if status:
        q = q.filter(models.AgentAnchor.status == status)

    anchors = q.order_by(models.AgentAnchor.created_at.desc()).all()

    return [
        {
            "id": str(a.id),
            "bundle_hash": a.bundle_hash,
            "anchor_txid": a.anchor_txid,
            "chain": a.chain,
            "status": a.status,
            "anchored_at": a.anchored_at.isoformat() if a.anchored_at else None,
            "created_at": a.created_at.isoformat() if a.created_at else None,
        }
        for a in anchors
    ]


@router.get("/v1/agents/{agent_id}/activity-unified")
def get_unified_activity(
    agent_id: str,
    days: int = 7,
    session: Session = Depends(get_session),
    principal: Principal = Depends(resolve_principal),
):
    """Unified activity feed combining x402 payments and anchor events."""
    if principal.is_public:
        raise HTTPException(401, "auth_required")
    agent = _require_agent(agent_id, session, principal)

    since = datetime.utcnow() - timedelta(days=days)

    payments = (
        session.query(models.X402Payment)
        .filter(models.X402Payment.agent_id == agent_id)
        .filter(models.X402Payment.verified_at >= since)
        .all()
    )

    anchors = (
        session.query(models.AgentAnchor)
        .filter(models.AgentAnchor.agent_id == agent_id)
        .filter(models.AgentAnchor.created_at >= since)
        .all()
    )

    activities = []

    for p in payments:
        activities.append({
            "type": "payment",
            "id": str(p.id),
            "content": f"x402 payment: {p.amount} {p.currency} to {p.endpoint}",
            "timestamp": p.verified_at.isoformat(),
            "details": {
                "tx_hash": p.tx_hash,
                "amount": str(p.amount),
                "endpoint": p.endpoint,
                "anchor_txid": p.anchor_txid,
                "anchor_status": p.anchor_status,
            },
        })

    for a in anchors:
        activities.append({
            "type": "anchor",
            "id": str(a.id),
            "content": f"Anchored {a.bundle_hash[:10]}... on {a.chain}",
            "timestamp": a.created_at.isoformat(),
            "details": {
                "bundle_hash": a.bundle_hash,
                "anchor_txid": a.anchor_txid,
                "chain": a.chain,
                "status": a.status,
            },
        })

    activities.sort(key=lambda x: x["timestamp"], reverse=True)

    return {
        "agent_id": agent_id,
        "agent_name": agent.name,
        "days": days,
        "activities": activities,
        "summary": {
            "total_payments": len(payments),
            "total_anchors": len(anchors),
            "anchored_payments": sum(1 for p in payments if p.anchor_txid),
        },
    }


# ── Background task ───────────────────────────────────────────────────────────

async def _perform_anchor(
    anchor_id: str,
    bundle_hash: str,
    agent_wallet: str = None,
    agent_key: str = None,
):
    """Background task: submit bundle hash to the configured anchor contract."""
    from app.api.deps import get_session as _get_session
    from app import anchor as anchor_module

    session = next(_get_session())
    agent_anchor = None

    try:
        agent_anchor = session.get(models.AgentAnchor, anchor_id)
        if not agent_anchor:
            return

        private_key = None
        if agent_key:
            import base64
            private_key = base64.b64decode(agent_key).decode()

        txid, _block = anchor_module.anchor_bundle(bundle_hash, private_key=private_key)

        agent_anchor.anchor_txid = txid
        agent_anchor.status = "confirmed"
        agent_anchor.anchored_at = datetime.utcnow()
        session.commit()

    except Exception as exc:
        if agent_anchor:
            agent_anchor.status = "failed"
            try:
                session.commit()
            except Exception:
                pass
        import logging
        logging.getLogger("middleware.anchor").warning(
            "agent_anchor_failed anchor_id=%s: %s", anchor_id, exc
        )
    finally:
        session.close()
