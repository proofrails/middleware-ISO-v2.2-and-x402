"""Agent anchoring integration - connect agents with on-chain anchoring."""
from uuid import uuid4
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session

from app import models, anchor
from app.api.deps import get_session
from app.auth.principal import Principal
from app.auth.api_key_auth import resolve_principal

router = APIRouter(tags=["agent-anchoring"])


@router.post("/v1/agents/{agent_id}/anchor")
async def trigger_agent_anchor(
    agent_id: str,
    payload: dict,
    background_tasks: BackgroundTasks,
    session: Session = Depends(get_session),
    principal: Principal = Depends(resolve_principal),
):
    """Manually trigger anchoring for an agent.
    
    Allows agents to manually anchor bundle hashes on-chain.
    Uses agent's anchor wallet if configured, otherwise system wallet.
    """
    if principal.is_public:
        raise HTTPException(401, "auth_required")
    
    agent = session.get(models.AgentConfig, agent_id)
    if not agent:
        raise HTTPException(404, "agent_not_found")
    
    if not principal.is_admin and agent.project_id != principal.project_id:
        raise HTTPException(403, "access_denied")
    
    bundle_hash = payload.get("bundle_hash")
    receipt_id = payload.get("receipt_id")
    
    if not bundle_hash:
        raise HTTPException(400, "bundle_hash_required")
    
    # Create anchor record
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
    
    # Queue background anchoring job
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
        "message": "Anchoring initiated"
    }


@router.get("/v1/agents/{agent_id}/anchors")
def list_agent_anchors(
    agent_id: str,
    days: int = 7,
    status: str = None,
    session: Session = Depends(get_session),
    principal: Principal = Depends(resolve_principal),
):
    """List all anchors created by this agent."""
    if principal.is_public:
        raise HTTPException(401, "auth_required")
    
    agent = session.get(models.AgentConfig, agent_id)
    if not agent:
        raise HTTPException(404, "agent_not_found")
    
    if not principal.is_admin and agent.project_id != principal.project_id:
        raise HTTPException(403, "access_denied")
    
    # Build query
    query = session.query(models.AgentAnchor).filter_by(agent_id=agent_id)
    
    # Filter by date range
    since = datetime.utcnow() - timedelta(days=days)
    query = query.filter(models.AgentAnchor.created_at >= since)
    
    # Filter by status if provided
    if status:
        query = query.filter_by(status=status)
    
    anchors = query.order_by(models.AgentAnchor.created_at.desc()).all()
    
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


@router.put("/v1/agents/{agent_id}/anchoring-config")
def update_anchoring_config(
    agent_id: str,
    payload: dict,
    session: Session = Depends(get_session),
    principal: Principal = Depends(resolve_principal),
):
    """Update agent's anchoring configuration."""
    if principal.is_public:
        raise HTTPException(401, "auth_required")
    
    agent = session.get(models.AgentConfig, agent_id)
    if not agent:
        raise HTTPException(404, "agent_not_found")
    
    if not principal.is_admin and agent.project_id != principal.project_id:
        raise HTTPException(403, "access_denied")
    
    # Update anchoring config
    if "auto_anchor_enabled" in payload:
        agent.auto_anchor_enabled = str(payload["auto_anchor_enabled"]).lower()
    
    if "anchor_on_payment" in payload:
        agent.anchor_on_payment = str(payload["anchor_on_payment"]).lower()
    
    if "anchor_wallet_address" in payload:
        agent.anchor_wallet_address = payload["anchor_wallet_address"]
    
    if "anchor_private_key" in payload and payload["anchor_private_key"]:
        # Encrypt the private key (simple base64 for now)
        import base64
        encrypted = base64.b64encode(payload["anchor_private_key"].encode()).decode()
        agent.anchor_private_key_encrypted = encrypted
    
    agent.updated_at = datetime.utcnow()
    
    session.commit()
    session.refresh(agent)
    
    return {
        "id": str(agent.id),
        "auto_anchor_enabled": agent.auto_anchor_enabled == "true",
        "anchor_on_payment": agent.anchor_on_payment == "true",
        "anchor_wallet": agent.anchor_wallet_address,
    }


@router.get("/v1/agents/{agent_id}/activity-unified")
def get_unified_activity(
    agent_id: str,
    days: int = 7,
    session: Session = Depends(get_session),
    principal: Principal = Depends(resolve_principal),
):
    """Get unified activity feed (payments + anchors + messages)."""
    if principal.is_public:
        raise HTTPException(401, "auth_required")
    
    agent = session.get(models.AgentConfig, agent_id)
    if not agent:
        raise HTTPException(404, "agent_not_found")
    
    if not principal.is_admin and agent.project_id != principal.project_id:
        raise HTTPException(403, "access_denied")
    
    since = datetime.utcnow() - timedelta(days=days)
    
    # Get payments
    payments = (
        session.query(models.X402Payment)
        .filter_by(agent_id=agent_id)
        .filter(models.X402Payment.verified_at >= since)
        .all()
    )
    
    # Get anchors
    anchors = (
        session.query(models.AgentAnchor)
        .filter_by(agent_id=agent_id)
        .filter(models.AgentAnchor.created_at >= since)
        .all()
    )
    
    # Combine into unified feed
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
            }
        })
    
    for a in anchors:
        activities.append({
            "type": "anchor",
            "id": str(a.id),
            "content": f"Anchored bundle {a.bundle_hash[:10]}... on {a.chain}",
            "timestamp": a.created_at.isoformat(),
            "details": {
                "bundle_hash": a.bundle_hash,
                "anchor_txid": a.anchor_txid,
                "chain": a.chain,
                "status": a.status,
            }
        })
    
    # Sort by timestamp
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
        }
    }


# Background task to perform anchoring
async def _perform_anchor(
    anchor_id: str,
    bundle_hash: str,
    agent_wallet: str = None,
    agent_key: str = None,
):
    """Background task to anchor bundle on-chain."""
    from app.api.deps import get_session
    from app import anchor as anchor_module
    
    session = next(get_session())
    
    try:
        agent_anchor = session.get(models.AgentAnchor, anchor_id)
        if not agent_anchor:
            return
        
        # Decrypt agent key if provided
        private_key = None
        if agent_key:
            import base64
            private_key = base64.b64decode(agent_key).decode()
        
        # Anchor on-chain
        txid, block_number = anchor_module.anchor_bundle(
            bundle_hash,
            private_key=private_key,
        )
        
        # Update anchor record
        agent_anchor.anchor_txid = txid
        agent_anchor.status = "confirmed"
        agent_anchor.anchored_at = datetime.utcnow()
        
        # If this anchor is linked to a payment, update it too
        if agent_anchor.receipt_id:
            payment = session.query(models.X402Payment).filter_by(
                receipt_id=agent_anchor.receipt_id
            ).first()
            if payment:
                payment.anchor_txid = txid
                payment.anchor_status = "anchored"
        
        session.commit()
        
    except Exception as e:
        # Mark as failed
        if agent_anchor:
            agent_anchor.status = "failed"
            session.commit()
        print(f"Anchoring failed for {anchor_id}: {e}")
