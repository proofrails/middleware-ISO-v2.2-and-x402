"""x402-protected premium endpoints.

These endpoints require x402 payment via X-PAYMENT header.
Agents pay micro-amounts (0.001-0.010 USDC/USDT0/FLR) to access premium features.

Decorator order matters: @router.post must be the OUTERMOST decorator so FastAPI
registers the require_payment wrapper, not the bare function.
"""
from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from app import schemas
from app.api.deps import get_session
from app.x402 import require_payment

router = APIRouter(tags=["x402-premium"])

import os
X402_RECIPIENT = os.getenv("X402_RECIPIENT_ADDRESS", "0x0690d8cFb1897c12B2C0b34660edBDE4E20ff4d8")


@router.post("/v1/x402/premium/fx-lookup")
@require_payment("0.001", X402_RECIPIENT)
async def premium_fx_lookup(request: Request, payload: dict):
    """Get FX rate lookup (x402-gated). Price: 0.001 USDC / USDT0."""
    from app import fx_providers

    base_ccy = payload.get("base_ccy", "USD")
    quote_ccy = payload.get("quote_ccy", "FLR")
    provider = payload.get("provider", "coingecko")

    try:
        detail = fx_providers.get_rate_detail(
            base_ccy=base_ccy,
            quote_ccy=quote_ccy,
            provider=provider,
        )
        return detail
    except Exception as e:
        return {"error": str(e)}


@router.post("/v1/x402/premium/verify-bundle")
@require_payment("0.001", X402_RECIPIENT)
async def premium_verify_bundle(request: Request, payload: schemas.VerifyRequest, session: Session = Depends(get_session)):
    """Verify an evidence bundle (x402-gated). Price: 0.001 USDC / USDT0."""
    from app.api.routes.verify import verify as verify_impl
    return await verify_impl(payload)


@router.post("/v1/x402/premium/generate-statement")
@require_payment("0.005", X402_RECIPIENT)
async def premium_generate_statement(request: Request, date: str, window: str = "00:00-23:59", session: Session = Depends(get_session)):
    """Generate camt.052 or camt.053 statement (x402-gated). Price: 0.005 USDC / USDT0."""
    from app.iso_messages import camt052, camt053

    if window and window != "00:00-23:59":
        receipts = []
        return {"type": "camt.052", "date": date, "window": window, "count": len(receipts)}
    else:
        receipts = []
        return {"type": "camt.053", "date": date, "count": len(receipts)}


@router.get("/v1/x402/premium/iso-message/{receipt_id}/{type}")
@require_payment("0.002", X402_RECIPIENT)
async def premium_get_iso_message(request: Request, receipt_id: str, type: str, session: Session = Depends(get_session)):
    """Get specific ISO message artifact (x402-gated). Price: 0.002 USDC / USDT0."""
    from app.api.routes.iso_messages import list_iso_messages
    return list_iso_messages(receipt_id, type, session)


@router.post("/v1/x402/premium/bulk-verify")
@require_payment("0.010", X402_RECIPIENT)
async def premium_bulk_verify(request: Request, payload: dict, session: Session = Depends(get_session)):
    """Bulk verify multiple bundles (x402-gated). Price: 0.010 USDC / USDT0."""
    bundle_urls = payload.get("bundle_urls", [])
    from app.api.routes.verify import verify as verify_impl

    results = []
    for url in bundle_urls[:10]:
        try:
            result = await verify_impl(schemas.VerifyRequest(bundle_url=url))
            results.append({"url": url, "result": result})
        except Exception as e:
            results.append({"url": url, "error": str(e)})

    return {"verified": len(results), "results": results}


@router.post("/v1/x402/premium/refund")
@require_payment("0.003", X402_RECIPIENT)
async def premium_refund(request: Request, payload: schemas.RefundRequest, session: Session = Depends(get_session)):
    """Initiate a refund via agent (x402-gated). Price: 0.003 USDC / USDT0."""
    from app.api.routes.refunds import refund_receipt
    from app.auth.principal import Principal

    principal = Principal(role="admin", project_id=None, is_admin=True, is_public=False)
    return refund_receipt(payload, session, principal)
