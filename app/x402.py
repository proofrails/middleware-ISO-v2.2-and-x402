"""x402 Payment Protocol — multi-chain implementation.

Supports three payment paths:
  1. USDC on Base (erc20_transfer)
  2. USDT0 on Flare via EIP-3009 facilitator (eip3009_facilitator)
  3. Native FLR on Flare (native_transfer)

The 402 response includes all enabled payment options so clients/agents can
choose. Each path has its own verification flow.
"""
from __future__ import annotations

import functools
import inspect
import json
import os
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Any, Callable, Dict, Optional

from fastapi import HTTPException, Request
from fastapi.responses import JSONResponse
from web3 import Web3

from . import models


# ── Legacy PaymentProof (Base USDC) ──────────────────────────────────────────

@dataclass
class PaymentProof:
    """Parsed payment proof from X-PAYMENT header (Base USDC path)."""
    tx_hash: str
    amount: str
    recipient: str
    currency: str
    chain: str
    timestamp: Optional[str] = None


# ── Base USDC verifier (unchanged) ───────────────────────────────────────────

class X402PaymentVerifier:
    """Verifies USDC x402 payments on Base."""

    def __init__(self, rpc_url: Optional[str] = None):
        self.rpc_url = rpc_url or os.getenv("X402_BASE_RPC_URL", "https://mainnet.base.org")
        self.w3 = Web3(Web3.HTTPProvider(self.rpc_url))
        self.usdc_address = os.getenv("X402_USDC_ADDRESS", "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913")
        self.transfer_topic = "0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef"

    def parse_payment_header(self, payment_header: str) -> Optional[PaymentProof]:
        try:
            data = json.loads(payment_header)
            return PaymentProof(
                tx_hash=data["tx_hash"],
                amount=str(data["amount"]),
                recipient=str(data["recipient"]),
                currency=data.get("currency", "USDC"),
                chain=data.get("chain", "base"),
                timestamp=data.get("timestamp"),
            )
        except Exception:
            return None

    async def verify_payment(
        self,
        proof: PaymentProof,
        expected_amount: str,
        expected_recipient: str,
    ) -> bool:
        try:
            tx_receipt = self.w3.eth.get_transaction_receipt(proof.tx_hash)
            if not tx_receipt or tx_receipt.get("status") != 1:
                return False

            for log in tx_receipt.get("logs", []):
                if (
                    log.get("address", "").lower() == self.usdc_address.lower()
                    and len(log.get("topics", [])) >= 3
                    and log["topics"][0].hex() == self.transfer_topic
                ):
                    to_address = "0x" + log["topics"][2].hex()[-40:]
                    if to_address.lower() != expected_recipient.lower():
                        continue
                    amount_wei = int(log.get("data", "0x"), 16)
                    amount_usdc = Decimal(amount_wei) / Decimal(10 ** 6)
                    if abs(amount_usdc - Decimal(expected_amount)) < Decimal("0.0001"):
                        return True
            return False
        except Exception:
            return False

    async def record_payment(self, session, proof: PaymentProof, endpoint: str) -> models.X402Payment:
        payment = models.X402Payment(
            payment_type="erc20_transfer",
            tx_hash=proof.tx_hash,
            amount=Decimal(proof.amount),
            currency=proof.currency,
            chain=proof.chain,
            chain_id="8453",
            token_address=os.getenv("X402_USDC_ADDRESS", "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913"),
            recipient=proof.recipient,
            endpoint=endpoint,
            status="verified",
            verified_at=datetime.utcnow(),
        )
        session.add(payment)
        session.commit()
        session.refresh(payment)
        return payment


# ── Multi-payment 402 response builder ───────────────────────────────────────

def _build_402_response(endpoint_name: str, accepts: list[dict]) -> JSONResponse:
    """Return a properly-structured 402 Payment Required response."""
    return JSONResponse(
        status_code=402,
        content={
            "version": "1.0",
            "error": "payment_required",
            "endpoint": endpoint_name,
            "accepts": accepts,
        },
        headers={"X-Payment-Required": "true"},
    )


# ── require_payment decorator ─────────────────────────────────────────────────

def require_payment(amount: str, recipient: str, currency: str = "USDC", chain: str = "base"):
    """Gate an endpoint behind x402 payment.

    When called without X-PAYMENT, returns 402 with all enabled payment options.
    When called with X-PAYMENT, routes to the correct verification path.

    The decorator inspects the payment_type in the X-PAYMENT header to decide
    which verifier to use. Unknown payment types return 400.
    """
    def decorator(func: Callable):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            # FastAPI injects named parameters; request is always present by name or position
            request: Request = kwargs.get("request") or next(
                (a for a in args if isinstance(a, Request)), None
            )
            from .settings import get_settings
            settings = get_settings()

            payment_header = request.headers.get("X-PAYMENT") or request.headers.get("x-payment")

            if not payment_header:
                # Build 402 with all enabled payment options
                from .x402_flare import build_402_payment_options
                accepts = build_402_payment_options(
                    usdc_enabled=settings.x402_enable_base_usdc,
                    usdt0_enabled=settings.x402_enable_flare_usdt0,
                    flr_enabled=settings.x402_enable_flare_native_flr,
                    usdc_recipient=settings.x402_effective_usdc_recipient or recipient,
                    usdt0_recipient=settings.x402_effective_usdt0_recipient,
                    flr_recipient=settings.x402_effective_flr_recipient,
                    usdc_amount=settings.x402_usdc_amount,
                    usdt0_amount=settings.x402_usdt0_amount,
                    flr_amount=settings.x402_flr_amount,
                    usdc_token=settings.x402_usdc_address,
                    usdt0_token=settings.x402_usdt0_flare_address,
                    facilitator=settings.x402_flare_facilitator_address,
                )
                return _build_402_response(func.__name__, accepts)

            # Detect payment type from header
            try:
                header_data = json.loads(payment_header)
            except Exception:
                raise HTTPException(status_code=400, detail="invalid_payment_header")

            payment_type = header_data.get("payment_type", "erc20_transfer")
            pmt_chain = header_data.get("chain", "base")

            # ── Route to correct verifier ─────────────────────────────────

            if payment_type == "eip3009_facilitator" or (
                pmt_chain == "flare" and header_data.get("currency") == "USDT0"
            ):
                if not settings.x402_enable_flare_usdt0:
                    raise HTTPException(status_code=400, detail="usdt0_payment_not_enabled")
                return await _handle_usdt0_payment(
                    request, payment_header, settings, amount, recipient, func, args, kwargs
                )

            elif payment_type == "native_transfer" or (
                pmt_chain == "flare" and header_data.get("currency") == "FLR"
            ):
                if not settings.x402_enable_flare_native_flr:
                    raise HTTPException(status_code=400, detail="flr_payment_not_enabled")
                return await _handle_flr_payment(
                    request, payment_header, settings, amount, recipient, func, args, kwargs
                )

            elif payment_type in ("erc20_transfer", "") or pmt_chain == "base":
                if not settings.x402_enable_base_usdc:
                    raise HTTPException(status_code=400, detail="usdc_payment_not_enabled")
                return await _handle_usdc_payment(
                    request, payment_header, settings, amount, recipient, func, args, kwargs
                )

            else:
                raise HTTPException(status_code=400, detail=f"unsupported_payment_type:{payment_type}")

        # Preserve the original function's signature so FastAPI injects parameters correctly
        wrapper.__signature__ = inspect.signature(func)
        return wrapper
    return decorator


# ── Path handlers ─────────────────────────────────────────────────────────────

async def _handle_usdc_payment(
    request: Request,
    payment_header: str,
    settings,
    amount: str,
    recipient: str,
    func: Callable,
    args, kwargs,
) -> Any:
    verifier = X402PaymentVerifier(rpc_url=settings.x402_base_rpc_url)
    proof = verifier.parse_payment_header(payment_header)
    if not proof:
        raise HTTPException(status_code=400, detail="invalid_payment_header")

    effective_recipient = settings.x402_effective_usdc_recipient or recipient
    is_valid = await verifier.verify_payment(proof, settings.x402_usdc_amount, effective_recipient)
    if not is_valid:
        raise HTTPException(status_code=403, detail="payment_verification_failed")

    await _record_payment_best_effort(
        session_factory=_get_session_factory(),
        record_fn=lambda s: verifier.record_payment(s, proof, func.__name__),
    )

    result = await func(*args, **kwargs)
    _add_payment_header(result, {"verified": True, "tx_hash": proof.tx_hash, "currency": "USDC"})
    return result


async def _handle_usdt0_payment(
    request: Request,
    payment_header: str,
    settings,
    amount: str,
    recipient: str,
    func: Callable,
    args, kwargs,
) -> Any:
    from .x402_flare import (
        FlarePaymentVerifier, parse_flare_payment, FlareUSDT0Payment,
        usdt0_to_raw,
    )

    payment = parse_flare_payment(payment_header)
    if not isinstance(payment, FlareUSDT0Payment):
        raise HTTPException(status_code=400, detail="invalid_usdt0_payment_header")

    effective_token = settings.x402_usdt0_flare_address
    effective_recipient = settings.x402_effective_usdt0_recipient
    effective_facilitator = settings.x402_flare_facilitator_address

    if not effective_recipient:
        raise HTTPException(status_code=503, detail="usdt0_recipient_not_configured")
    if not effective_facilitator:
        raise HTTPException(status_code=503, detail="facilitator_not_configured")

    # Validate token + facilitator from header match server config
    if payment.token.lower() != effective_token.lower():
        raise HTTPException(status_code=400, detail="wrong_token_address")
    if payment.facilitator.lower() != effective_facilitator.lower():
        raise HTTPException(status_code=400, detail="wrong_facilitator_address")

    expected_raw = usdt0_to_raw(settings.x402_usdt0_amount, settings.x402_usdt0_decimals)

    verifier = FlarePaymentVerifier(
        rpc_url=settings.x402_flare_rpc_url,
        chain_id=settings.x402_flare_chain_id,
    )

    settlement_mode = settings.x402_settlement_mode

    if payment.settlement_tx_hash:
        # Client-submitted settlement mode
        ok, facilitator_payment_id, err = await verifier.verify_usdt0_settlement_tx(
            payment=payment,
            expected_token=effective_token,
            expected_recipient=effective_recipient,
            expected_raw_amount=expected_raw,
            facilitator_address=effective_facilitator,
            confirmations=settings.x402_flare_confirmations,
        )
        if not ok:
            raise HTTPException(status_code=403, detail=f"payment_verification_failed:{err}")

        # Replay protection: check settlement_tx_hash not already recorded
        await _check_tx_not_replayed(payment.settlement_tx_hash)

        await _record_usdt0_payment(
            payment=payment,
            settlement_tx_hash=payment.settlement_tx_hash,
            facilitator_payment_id=facilitator_payment_id,
            effective_recipient=effective_recipient,
            effective_token=effective_token,
            effective_facilitator=effective_facilitator,
            expected_raw=expected_raw,
            endpoint=func.__name__,
            settings=settings,
        )

        result = await func(*args, **kwargs)
        _add_payment_header(result, {
            "verified": True,
            "currency": "USDT0",
            "settlement_tx_hash": payment.settlement_tx_hash,
        })
        return result

    elif settlement_mode == "server" and settings.x402_settler_private_key:
        # Server-submitted settlement mode
        if not payment.nonce:
            raise HTTPException(status_code=400, detail="missing_eip3009_authorization")

        # Replay protection: check nonce not already used
        await _check_nonce_not_replayed(payment.nonce, effective_token, str(settings.x402_flare_chain_id))

        ok, settlement_tx, facilitator_payment_id, err = await verifier.submit_and_verify_usdt0(
            payment=payment,
            expected_token=effective_token,
            expected_recipient=effective_recipient,
            expected_raw_amount=expected_raw,
            facilitator_address=effective_facilitator,
            settler_private_key=settings.x402_settler_private_key,
            authorization_type=payment.authorization_type,
        )
        if not ok:
            raise HTTPException(status_code=403, detail=f"settlement_failed:{err}")

        await _record_usdt0_payment(
            payment=payment,
            settlement_tx_hash=settlement_tx,
            facilitator_payment_id=facilitator_payment_id,
            effective_recipient=effective_recipient,
            effective_token=effective_token,
            effective_facilitator=effective_facilitator,
            expected_raw=expected_raw,
            endpoint=func.__name__,
            settings=settings,
        )

        result = await func(*args, **kwargs)
        _add_payment_header(result, {
            "verified": True,
            "currency": "USDT0",
            "settlement_tx_hash": settlement_tx,
        })
        return result

    else:
        raise HTTPException(
            status_code=400,
            detail="provide_settlement_tx_hash_or_configure_server_mode",
        )


async def _handle_flr_payment(
    request: Request,
    payment_header: str,
    settings,
    amount: str,
    recipient: str,
    func: Callable,
    args, kwargs,
) -> Any:
    from .x402_flare import FlarePaymentVerifier, parse_flare_payment, FlareNativePayment, flr_to_wei

    payment = parse_flare_payment(payment_header)
    if not isinstance(payment, FlareNativePayment):
        raise HTTPException(status_code=400, detail="invalid_flr_payment_header")

    effective_recipient = settings.x402_effective_flr_recipient
    if not effective_recipient:
        raise HTTPException(status_code=503, detail="flr_recipient_not_configured")

    expected_wei = flr_to_wei(settings.x402_flr_amount)

    verifier = FlarePaymentVerifier(
        rpc_url=settings.x402_flare_rpc_url,
        chain_id=settings.x402_flare_chain_id,
    )

    ok, err = await verifier.verify_flr_transfer(
        payment=payment,
        expected_recipient=effective_recipient,
        expected_min_wei=expected_wei,
        confirmations=settings.x402_flare_confirmations,
    )
    if not ok:
        raise HTTPException(status_code=403, detail=f"payment_verification_failed:{err}")

    # Replay protection: check tx_hash not already recorded
    await _check_tx_not_replayed(payment.tx_hash)

    await _record_flr_payment(payment, effective_recipient, expected_wei, func.__name__, settings)

    result = await func(*args, **kwargs)
    _add_payment_header(result, {"verified": True, "currency": "FLR", "tx_hash": payment.tx_hash})
    return result


# ── DB helpers ────────────────────────────────────────────────────────────────

def _get_session_factory():
    try:
        from .db import SessionLocal
        return SessionLocal
    except Exception:
        return None


async def _record_payment_best_effort(session_factory, record_fn):
    if not session_factory:
        return
    try:
        session = session_factory()
        await record_fn(session)
        session.close()
    except Exception:
        pass


async def _check_tx_not_replayed(tx_hash: str):
    """Raise 409 if this tx_hash is already recorded."""
    try:
        from .db import SessionLocal
        session = SessionLocal()
        existing = session.query(models.X402Payment).filter_by(tx_hash=tx_hash).first()
        session.close()
        if existing:
            raise HTTPException(status_code=409, detail="payment_already_used")
    except HTTPException:
        raise
    except Exception:
        pass


async def _check_nonce_not_replayed(nonce: str, token_address: str, chain_id: str):
    """Raise 409 if this EIP-3009 nonce is already recorded."""
    try:
        from .db import SessionLocal
        session = SessionLocal()
        existing = (
            session.query(models.X402Payment)
            .filter_by(eip3009_nonce=nonce, token_address=token_address, chain_id=chain_id)
            .first()
        )
        session.close()
        if existing:
            raise HTTPException(status_code=409, detail="nonce_already_used")
    except HTTPException:
        raise
    except Exception:
        pass


async def _record_usdt0_payment(
    payment: Any,
    settlement_tx_hash: Optional[str],
    facilitator_payment_id: Optional[str],
    effective_recipient: str,
    effective_token: str,
    effective_facilitator: str,
    expected_raw: int,
    endpoint: str,
    settings: Any,
):
    try:
        from .db import SessionLocal
        session = SessionLocal()
        record = models.X402Payment(
            payment_type="eip3009_facilitator",
            tx_hash=settlement_tx_hash,
            amount=Decimal(settings.x402_usdt0_amount),
            raw_amount=str(expected_raw),
            currency="USDT0",
            chain="flare",
            chain_id=str(settings.x402_flare_chain_id),
            token_address=effective_token,
            facilitator_address=effective_facilitator,
            payer_address=getattr(payment, "from_address", None),
            recipient=effective_recipient,
            eip3009_nonce=getattr(payment, "nonce", None),
            authorization_type=getattr(payment, "authorization_type", None),
            facilitator_payment_id=facilitator_payment_id,
            endpoint=endpoint,
            status="verified",
            verified_at=datetime.utcnow(),
        )
        session.add(record)
        session.commit()
        session.close()
    except Exception:
        pass


async def _record_flr_payment(
    payment: Any,
    effective_recipient: str,
    expected_wei: int,
    endpoint: str,
    settings: Any,
):
    try:
        from .db import SessionLocal
        session = SessionLocal()
        record = models.X402Payment(
            payment_type="native_transfer",
            tx_hash=payment.tx_hash,
            amount=Decimal(settings.x402_flr_amount),
            raw_amount=str(expected_wei),
            currency="FLR",
            chain="flare",
            chain_id=str(settings.x402_flare_chain_id),
            recipient=effective_recipient,
            payer_address=getattr(payment, "from_address", None),
            endpoint=endpoint,
            status="verified",
            verified_at=datetime.utcnow(),
        )
        session.add(record)
        session.commit()
        session.close()
    except Exception:
        pass


def _add_payment_header(response: Any, payload: dict):
    if isinstance(response, JSONResponse):
        response.headers["X-Payment-Response"] = json.dumps(payload)


# ── generate_payment_payload (agent helper) ───────────────────────────────────

def generate_payment_payload(
    tx_hash: str,
    amount: str,
    recipient: str,
    currency: str = "USDC",
    chain: str = "base",
) -> str:
    """Generate X-PAYMENT header value for Base USDC path."""
    return json.dumps({
        "tx_hash": tx_hash,
        "amount": amount,
        "recipient": recipient,
        "currency": currency,
        "chain": chain,
        "payment_type": "erc20_transfer",
        "timestamp": datetime.utcnow().isoformat(),
    })


def generate_usdt0_payment_payload(
    settlement_tx_hash: str,
    token: str,
    facilitator: str,
    recipient: str,
    amount: str,
    chain_id: int = 14,
) -> str:
    """Generate X-PAYMENT header value for USDT0 EIP-3009 client-settled path."""
    return json.dumps({
        "chain": "flare",
        "chain_id": chain_id,
        "currency": "USDT0",
        "payment_type": "eip3009_facilitator",
        "token": token,
        "facilitator": facilitator,
        "recipient": recipient,
        "amount": amount,
        "settlement_tx_hash": settlement_tx_hash,
    })
