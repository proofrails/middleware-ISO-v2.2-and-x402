"""x402-protected premium endpoints.

All endpoints require a valid ``X-PAYMENT`` header (HTTP 402 is returned when absent).
Each endpoint accepts two payment currencies:

  1. USDC on Base  (default)
  2. FLR  on Flare (set currency="FLR", chain="flare" in the payment object)

X-PAYMENT header format::

    {
        "tx_hash":   "0x...",
        "amount":    "0.001",
        "recipient": "0x...",
        "currency":  "USDC",   # or "FLR"
        "chain":     "base"    # or "flare"
    }

Environment variables
---------------------
``X402_RECIPIENT_ADDRESS`` – USDC recipient on Base
``X402_FLR_RECIPIENT``     – FLR recipient on Flare (defaults to USDC recipient)
``X402_MOCK_PAYMENTS``     – set to "true" in dev/test to skip on-chain verification
``X402_FLR_VERIFY``        – FLR price for verify-bundle (default 0.05)
``X402_FLR_STATEMENT``     – FLR price for generate-statement (default 0.25)
``X402_FLR_ISO_MSG``       – FLR price for iso-message (default 0.10)
``X402_FLR_FX_LOOKUP``     – FLR price for fx-lookup (default 0.05)
``X402_FLR_BULK``          – FLR price for bulk-verify (default 0.50)
``X402_FLR_REFUND``        – FLR price for refund (default 0.15)
"""
from __future__ import annotations

import os
from datetime import datetime

from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app import schemas
from app.api.deps import get_session

router = APIRouter(tags=["x402-premium"])

X402_RECIPIENT = os.getenv("X402_RECIPIENT_ADDRESS", "0x0690d8cFb1897c12B2C0b34660edBDE4E20ff4d8")
X402_FLR_RECIPIENT = os.getenv("X402_FLR_RECIPIENT", X402_RECIPIENT)
_MOCK = os.getenv("X402_MOCK_PAYMENTS", "false").lower() == "true"

_FLR_VERIFY    = os.getenv("X402_FLR_VERIFY",    "0.05")
_FLR_STATEMENT = os.getenv("X402_FLR_STATEMENT", "0.25")
_FLR_ISO_MSG   = os.getenv("X402_FLR_ISO_MSG",   "0.10")
_FLR_FX_LOOKUP = os.getenv("X402_FLR_FX_LOOKUP", "0.05")
_FLR_BULK      = os.getenv("X402_FLR_BULK",       "0.50")
_FLR_REFUND    = os.getenv("X402_FLR_REFUND",     "0.15")


# ── Payment guard ─────────────────────────────────────────────────────────────

async def _verify_payment(
    request: Request,
    usdc_amount: str,
    usdc_recipient: str,
    flr_amount: str,
    flr_recipient: str,
    endpoint_label: str,
) -> JSONResponse | None:
    """Check X-PAYMENT header. Returns a JSONResponse on failure, None on success."""
    from app.x402 import X402PaymentVerifier, PaymentProof

    header = request.headers.get("X-PAYMENT") or request.headers.get("x-payment")

    if not header:
        ref = f"x402:{endpoint_label}:{datetime.utcnow().timestamp()}"
        return JSONResponse(
            status_code=402,
            content={
                "amount": usdc_amount,
                "recipient": usdc_recipient,
                "reference": ref,
                "currency": "USDC",
                "chain": "base",
                "accepted": [
                    {"amount": usdc_amount, "recipient": usdc_recipient,
                     "currency": "USDC", "chain": "base", "reference": ref},
                    {"amount": flr_amount, "recipient": flr_recipient,
                     "currency": "FLR", "chain": "flare", "reference": ref},
                ],
            },
            headers={
                "X-Payment-Required": "true",
                "X-Payment-Amount": usdc_amount,
                "X-Payment-Currency": "USDC",
            },
        )

    # Dev/test mock bypass — requires explicit opt-in via env var
    if _MOCK:
        return None

    verifier = X402PaymentVerifier()
    proof = verifier.parse_payment_header(header)

    if not proof:
        return JSONResponse(status_code=400, content={"detail": "invalid_payment_header"})

    if proof.currency.upper() == "FLR":
        ok = await verifier.verify_payment(proof, flr_amount, flr_recipient)
    else:
        ok = await verifier.verify_payment(proof, usdc_amount, usdc_recipient)

    if not ok:
        return JSONResponse(status_code=403, content={"detail": "payment_verification_failed"})

    # Record payment (best-effort — never block the endpoint)
    try:
        from app.db import SessionLocal
        _s = SessionLocal()
        await verifier.record_payment(_s, proof, endpoint_label)
        _s.close()
    except Exception:
        pass

    return None


# ── Premium endpoints ─────────────────────────────────────────────────────────

@router.post("/v1/x402/premium/verify-bundle")
async def premium_verify_bundle(
    request: Request,
    payload: schemas.VerifyRequest,
    session: Session = Depends(get_session),
):
    """Verify an evidence bundle. Price: 0.001 USDC or FLR equivalent."""
    err = await _verify_payment(
        request, "0.001", X402_RECIPIENT, _FLR_VERIFY, X402_FLR_RECIPIENT,
        "premium_verify_bundle",
    )
    if err:
        return err

    from app.api.routes.verify import verify as verify_impl
    return verify_impl(payload)


@router.post("/v1/x402/premium/generate-statement")
async def premium_generate_statement(
    request: Request,
    payload: schemas.StatementRequest,
    session: Session = Depends(get_session),
):
    """Generate a camt.052 (intraday) or camt.053 (end-of-day) statement.

    Price: 0.005 USDC or FLR equivalent.

    Request body::

        {"date": "2026-01-15", "window": "00:00-23:59"}

    Omit ``window`` or use ``"00:00-23:59"`` for a full-day camt.053.
    Supply a narrower window (e.g. ``"09:00-17:00"``) for camt.052.
    """
    err = await _verify_payment(
        request, "0.005", X402_RECIPIENT, _FLR_STATEMENT, X402_FLR_RECIPIENT,
        "premium_generate_statement",
    )
    if err:
        return err

    from app.iso_messages import camt052, camt053

    date = payload.date
    window = payload.window or "00:00-23:59"

    # Query receipts for the requested date
    from datetime import datetime as dt
    try:
        day_start = dt.strptime(date, "%Y-%m-%d")
    except ValueError:
        return JSONResponse(status_code=400, content={"detail": "invalid_date_format"})

    receipts_q = (
        session.query(
            __import__("app.models", fromlist=["Receipt"]).Receipt
        )
        .filter(
            __import__("app.models", fromlist=["Receipt"]).Receipt.created_at >= day_start,
            __import__("app.models", fromlist=["Receipt"]).Receipt.created_at < day_start.replace(
                hour=23, minute=59, second=59
            ),
        )
        .all()
    )

    if window and window != "00:00-23:59":
        xml = camt052.generate_camt052(date, window, receipts_q)
        return {
            "type": "camt.052",
            "date": date,
            "window": window,
            "count": len(receipts_q),
            "xml": xml if isinstance(xml, str) else None,
        }
    else:
        xml = camt053.generate_camt053(date, receipts_q)
        return {
            "type": "camt.053",
            "date": date,
            "count": len(receipts_q),
            "xml": xml if isinstance(xml, str) else None,
        }


@router.get("/v1/x402/premium/iso-message/{receipt_id}/{msg_type}")
async def premium_get_iso_message(
    request: Request,
    receipt_id: str,
    msg_type: str,
    session: Session = Depends(get_session),
):
    """Retrieve a specific ISO message artifact. Price: 0.002 USDC or FLR equivalent."""
    err = await _verify_payment(
        request, "0.002", X402_RECIPIENT, _FLR_ISO_MSG, X402_FLR_RECIPIENT,
        "premium_get_iso_message",
    )
    if err:
        return err

    from app.api.routes.iso_messages import list_iso_messages
    return list_iso_messages(receipt_id, msg_type, session)


@router.post("/v1/x402/premium/fx-lookup")
async def premium_fx_lookup(
    request: Request,
    payload: schemas.FXLookupRequest,
):
    """FX rate lookup with optional FTSO oracle source. Price: 0.001 USDC or FLR equivalent."""
    err = await _verify_payment(
        request, "0.001", X402_RECIPIENT, _FLR_FX_LOOKUP, X402_FLR_RECIPIENT,
        "premium_fx_lookup",
    )
    if err:
        return err

    from app import fx_providers

    try:
        detail = fx_providers.get_rate_detail(
            base_ccy=payload.base_ccy,
            quote_ccy=payload.quote_ccy,
            provider=payload.provider,
        )
        return detail
    except Exception as exc:
        return JSONResponse(status_code=503, content={"error": str(exc)})


@router.post("/v1/x402/premium/bulk-verify")
async def premium_bulk_verify(
    request: Request,
    payload: schemas.BulkVerifyRequest,
    session: Session = Depends(get_session),
):
    """Verify up to 10 evidence bundles in one call. Price: 0.010 USDC or FLR equivalent."""
    err = await _verify_payment(
        request, "0.010", X402_RECIPIENT, _FLR_BULK, X402_FLR_RECIPIENT,
        "premium_bulk_verify",
    )
    if err:
        return err

    from app.api.routes.verify import verify as verify_impl

    results = []
    for url in payload.bundle_urls[:10]:
        try:
            result = verify_impl(schemas.VerifyRequest(bundle_url=url))
            results.append({"url": url, "result": result})
        except Exception as exc:
            results.append({"url": url, "error": str(exc)})

    return {"verified": len(results), "results": results}


@router.post("/v1/x402/premium/refund")
async def premium_refund(
    request: Request,
    payload: schemas.RefundRequest,
    session: Session = Depends(get_session),
):
    """Initiate a payment refund. Price: 0.003 USDC or FLR equivalent."""
    err = await _verify_payment(
        request, "0.003", X402_RECIPIENT, _FLR_REFUND, X402_FLR_RECIPIENT,
        "premium_refund",
    )
    if err:
        return err

    from app.api.routes.refunds import refund_receipt
    from app.auth.principal import Principal

    principal = Principal(role="admin", project_id=None, is_admin=True, is_public=False)
    return refund_receipt(payload, session, principal)
