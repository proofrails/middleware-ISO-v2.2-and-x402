"""x402 payment protocol endpoints for configuration and analytics."""
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app import models, schemas
from app.api.deps import get_session
from app.auth.principal import Principal
from app.auth.api_key_auth import resolve_principal
from app.x402 import X402PaymentVerifier, generate_payment_payload

router = APIRouter(tags=["x402"])


@router.get("/v1/x402/pricing")
def get_pricing(session: Session = Depends(get_session)):
    """Get all protected endpoint pricing."""
    endpoints = session.query(models.ProtectedEndpoint).filter_by(enabled="true").all()
    return [
        {
            "path": e.path,
            "price": str(e.price),
            "currency": e.currency,
            "recipient": e.recipient,
        }
        for e in endpoints
    ]


@router.post("/v1/x402/pricing")
def update_pricing(
    pricing: List[dict],
    session: Session = Depends(get_session),
    principal: Principal = Depends(resolve_principal),
):
    """Update protected endpoint pricing (admin only)."""
    if not principal.is_admin:
        raise HTTPException(403, "admin_required")
    
    for item in pricing:
        path = item.get("path")
        if not path:
            continue
        
        endpoint = session.query(models.ProtectedEndpoint).filter_by(path=path).first()
        if endpoint:
            endpoint.price = item.get("price", endpoint.price)
            endpoint.recipient = item.get("recipient", endpoint.recipient)
            endpoint.enabled = item.get("enabled", endpoint.enabled)
        else:
            endpoint = models.ProtectedEndpoint(
                path=path,
                price=item["price"],
                currency=item.get("currency", "USDC"),
                recipient=item["recipient"],
                enabled=item.get("enabled", "true"),
            )
            session.add(endpoint)
    
    session.commit()
    return {"status": "updated"}


@router.get("/v1/x402/payments")
def list_payments(
    limit: int = 50,
    offset: int = 0,
    currency: Optional[str] = None,
    chain: Optional[str] = None,
    status: Optional[str] = None,
    payment_type: Optional[str] = None,
    session: Session = Depends(get_session),
    principal: Principal = Depends(resolve_principal),
):
    """List recent x402 payments with optional filters."""
    if principal.is_public:
        raise HTTPException(401, "auth_required")

    q = session.query(models.X402Payment)
    if currency:
        q = q.filter(models.X402Payment.currency == currency)
    if chain:
        q = q.filter(models.X402Payment.chain == chain)
    if status:
        q = q.filter(models.X402Payment.status == status)
    if payment_type:
        q = q.filter(models.X402Payment.payment_type == payment_type)

    total = q.count()
    payments = q.order_by(models.X402Payment.verified_at.desc()).offset(offset).limit(limit).all()

    return {
        "total": total,
        "limit": limit,
        "offset": offset,
        "items": [
            {
                "id": str(p.id),
                "payment_type": p.payment_type,
                "tx_hash": p.tx_hash,
                "amount": str(p.amount),
                "currency": p.currency,
                "chain": p.chain,
                "chain_id": p.chain_id,
                "token_address": p.token_address,
                "facilitator_address": p.facilitator_address,
                "payer_address": p.payer_address,
                "recipient": p.recipient,
                "eip3009_nonce": p.eip3009_nonce,
                "authorization_type": p.authorization_type,
                "facilitator_payment_id": p.facilitator_payment_id,
                "endpoint": p.endpoint,
                "status": p.status,
                "verified_at": p.verified_at.isoformat() if p.verified_at else None,
            }
            for p in payments
        ],
    }


@router.get("/v1/x402/revenue")
def get_revenue(
    days: int = 7,
    session: Session = Depends(get_session),
    principal: Principal = Depends(resolve_principal),
):
    """Get revenue analytics."""
    if not principal.is_admin:
        raise HTTPException(403, "admin_required")
    
    # Simple aggregation
    from sqlalchemy import func as sql_func
    from datetime import datetime, timedelta
    
    since = datetime.utcnow() - timedelta(days=days)
    
    total = (
        session.query(sql_func.sum(models.X402Payment.amount))
        .filter(models.X402Payment.verified_at >= since)
        .scalar()
        or 0
    )
    
    count = (
        session.query(sql_func.count(models.X402Payment.id))
        .filter(models.X402Payment.verified_at >= since)
        .scalar()
        or 0
    )
    
    # By endpoint
    by_endpoint = (
        session.query(
            models.X402Payment.endpoint,
            sql_func.count(models.X402Payment.id).label("count"),
            sql_func.sum(models.X402Payment.amount).label("total"),
        )
        .filter(models.X402Payment.verified_at >= since)
        .group_by(models.X402Payment.endpoint)
        .all()
    )
    
    # By currency
    by_currency = (
        session.query(
            models.X402Payment.currency,
            models.X402Payment.chain,
            sql_func.count(models.X402Payment.id).label("count"),
            sql_func.sum(models.X402Payment.amount).label("total"),
        )
        .filter(models.X402Payment.verified_at >= since)
        .group_by(models.X402Payment.currency, models.X402Payment.chain)
        .all()
    )

    # By payment_type
    by_type = (
        session.query(
            models.X402Payment.payment_type,
            sql_func.count(models.X402Payment.id).label("count"),
            sql_func.sum(models.X402Payment.amount).label("total"),
        )
        .filter(models.X402Payment.verified_at >= since)
        .group_by(models.X402Payment.payment_type)
        .all()
    )

    return {
        "total_revenue_usd_equivalent": str(total),
        "payment_count": count,
        "days": days,
        "by_endpoint": [
            {"endpoint": row[0], "count": row[1], "revenue": str(row[2])}
            for row in by_endpoint
        ],
        "by_currency": [
            {"currency": row[0], "chain": row[1], "count": row[2], "revenue": str(row[3])}
            for row in by_currency
        ],
        "by_payment_type": [
            {"payment_type": row[0], "count": row[1], "revenue": str(row[2])}
            for row in by_type
        ],
    }


@router.get("/v1/x402/facilitator-config")
def get_facilitator_config(
    principal: Principal = Depends(resolve_principal),
):
    """Return current x402 facilitator configuration (read from env/settings)."""
    if not principal.is_admin:
        raise HTTPException(403, "admin_required")

    from app.settings import get_settings
    s = get_settings()

    return {
        "settlement_mode": s.x402_settlement_mode,
        "usdc": {
            "enabled": s.x402_enable_base_usdc,
            "amount": s.x402_usdc_amount,
            "recipient": s.x402_effective_usdc_recipient,
            "token_address": s.x402_usdc_address,
            "network": "base",
            "chain_id": 8453,
        },
        "usdt0": {
            "enabled": s.x402_enable_flare_usdt0,
            "amount": s.x402_usdt0_amount,
            "recipient": s.x402_effective_usdt0_recipient,
            "token_address": s.x402_usdt0_flare_address,
            "facilitator_address": s.x402_flare_facilitator_address,
            "network": "flare",
            "chain_id": s.x402_flare_chain_id,
            "decimals": s.x402_usdt0_decimals,
        },
        "flr": {
            "enabled": s.x402_enable_flare_native_flr,
            "amount": s.x402_flr_amount,
            "recipient": s.x402_effective_flr_recipient,
            "network": "flare",
            "chain_id": s.x402_flare_chain_id,
        },
    }


@router.post("/v1/x402/verify-payment")
async def verify_payment_manual(payload: dict, session: Session = Depends(get_session)):
    """Manually verify a payment (for testing/debugging)."""
    tx_hash = payload.get("tx_hash")
    amount = payload.get("amount")
    recipient = payload.get("recipient")
    
    if not all([tx_hash, amount, recipient]):
        raise HTTPException(400, "missing_required_fields")
    
    verifier = X402PaymentVerifier()
    
    # Create proof
    from app.x402 import PaymentProof
    proof = PaymentProof(
        tx_hash=tx_hash,
        amount=amount,
        recipient=recipient,
        currency=payload.get("currency", "USDC"),
        chain=payload.get("chain", "base"),
    )
    
    # Verify
    is_valid = await verifier.verify_payment(proof, amount, recipient)
    
    if is_valid:
        # Record payment
        payment = await verifier.record_payment(session, proof, "manual_verification")
        return {
            "verified": True,
            "payment_id": str(payment.id),
            "tx_hash": tx_hash,
        }
    else:
        return {"verified": False, "error": "payment_not_found_or_invalid"}
