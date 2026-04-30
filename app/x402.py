"""x402 Payment Protocol Implementation

HTTP 402 Payment Required protocol for autonomous agent payments.
Based on Coinbase's x402 specification for micro-payments.
"""
from __future__ import annotations

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


@dataclass
class PaymentDetails:
    """Payment requirement details returned in 402 response."""
    amount: str  # Amount in token units (e.g., "0.001")
    recipient: str  # Recipient wallet address
    reference: str  # Unique payment reference
    currency: str = "USDC"  # Default to USDC
    chain: str = "base"  # Default to Base network


@dataclass
class PaymentProof:
    """Parsed payment proof from X-PAYMENT header."""
    tx_hash: str
    amount: str
    recipient: str
    currency: str
    chain: str
    timestamp: Optional[str] = None


class X402PaymentVerifier:
    """Verifies x402 payments on Base/EVM chains.

    Supports two payment modes:
    - **USDC** (ERC-20 on Base): checks Transfer event logs for the USDC contract.
    - **FLR** (native token on Flare): checks the native value of the transaction itself.

    The ``chain`` field on ``PaymentProof`` selects the RPC and verification path:
    - ``chain="base"`` → USDC on Base mainnet (default)
    - ``chain="flare"`` → FLR native token on Flare C-Chain
    """

    # Chain → default RPC URL
    CHAIN_RPCS: Dict[str, str] = {
        "base": os.getenv("BASE_RPC_URL", "https://mainnet.base.org"),
        "flare": os.getenv("X402_FLARE_RPC_URL", "https://flare-api.flare.network/ext/C/rpc"),
        "coston2": "https://coston2-api.flare.network/ext/C/rpc",
    }

    def __init__(self, rpc_url: Optional[str] = None):
        self.rpc_url = rpc_url or os.getenv("BASE_RPC_URL", "https://mainnet.base.org")
        self.w3 = Web3(Web3.HTTPProvider(self.rpc_url))

        # USDC contract on Base mainnet
        self.usdc_address = os.getenv("X402_USDC_ADDRESS", "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913")

        # ERC20 Transfer event topic0
        self.transfer_topic = "0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef"

    def _w3_for_chain(self, chain: str) -> Any:
        """Return a Web3 instance connected to the correct chain RPC."""
        rpc = self.CHAIN_RPCS.get(chain.lower())
        if rpc:
            return Web3(Web3.HTTPProvider(rpc, request_kwargs={"timeout": 15}))
        return self.w3

    def parse_payment_header(self, payment_header: str) -> Optional[PaymentProof]:
        """Parse X-PAYMENT header.

        Expected format: JSON with tx_hash, amount, recipient, currency, chain.
        ``currency`` defaults to ``"USDC"``; ``chain`` defaults to ``"base"``.
        For FLR payments set ``currency="FLR"`` and ``chain="flare"``.
        """
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
        """Verify that a payment transaction exists on-chain.

        Dispatches to the correct verification path based on ``proof.currency``:
        - ``FLR`` → :meth:`_verify_flr_payment` (native token check)
        - Anything else → :meth:`_verify_erc20_payment` (ERC-20 Transfer log check)
        """
        if proof.currency.upper() == "FLR":
            return await self._verify_flr_payment(proof, expected_amount, expected_recipient)
        return await self._verify_erc20_payment(proof, expected_amount, expected_recipient)

    async def _verify_flr_payment(
        self,
        proof: PaymentProof,
        expected_amount: str,
        expected_recipient: str,
    ) -> bool:
        """Verify a native FLR transfer on Flare C-Chain.

        Checks:
        1. Transaction is confirmed (receipt status == 1).
        2. ``tx.to`` matches ``expected_recipient`` (case-insensitive).
        3. ``tx.value`` >= expected amount in wei (allows ±0.001 FLR tolerance).
        """
        try:
            w3 = self._w3_for_chain(proof.chain)
            tx_receipt = w3.eth.get_transaction_receipt(proof.tx_hash)
            if not tx_receipt or int(tx_receipt.get("status", 0)) != 1:
                return False

            tx = w3.eth.get_transaction(proof.tx_hash)
            to_addr = (tx.get("to") or "").lower()
            if to_addr != expected_recipient.lower():
                return False

            # FLR has 18 decimals (same as ETH wei)
            value_flr = Decimal(tx.get("value", 0)) / Decimal(10 ** 18)
            expected_flr = Decimal(expected_amount)
            tolerance = Decimal("0.001")
            return value_flr >= expected_flr - tolerance

        except Exception:
            return False

    async def _verify_erc20_payment(
        self,
        proof: PaymentProof,
        expected_amount: str,
        expected_recipient: str,
    ) -> bool:
        """Verify an ERC-20 (USDC) transfer via Transfer event log."""
        try:
            w3 = self._w3_for_chain(proof.chain)
            tx_receipt = w3.eth.get_transaction_receipt(proof.tx_hash)
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

                    amount_hex = log.get("data", "0x")
                    amount_wei = int(amount_hex, 16)
                    # USDC has 6 decimals
                    amount_usdc = Decimal(amount_wei) / Decimal(10 ** 6)
                    expected = Decimal(expected_amount)
                    if abs(amount_usdc - expected) < Decimal("0.0001"):
                        return True

            return False

        except Exception:
            return False

    async def record_payment(self, session, proof: PaymentProof, endpoint: str) -> models.X402Payment:
        """Record verified payment in database."""
        payment = models.X402Payment(
            tx_hash=proof.tx_hash,
            amount=Decimal(proof.amount),
            currency=proof.currency,
            chain=proof.chain,
            recipient=proof.recipient,
            endpoint=endpoint,
            verified_at=datetime.utcnow(),
        )
        session.add(payment)
        session.commit()
        session.refresh(payment)
        return payment


def require_payment(amount: str, recipient: str, currency: str = "USDC", chain: str = "base", flr_amount: Optional[str] = None, flr_recipient: Optional[str] = None):
    """Decorator to make an endpoint x402-gated.
    
    Usage:
        @require_payment("0.001", "0xRecipientAddress")
        @router.get("/premium/data")
        async def get_premium_data():
            return {"data": "..."}
    
    Returns 402 if no payment header, verifies payment if provided.
    """
    def decorator(func: Callable):
        async def wrapper(request: Request, *args, **kwargs):
            payment_header = request.headers.get("X-PAYMENT") or request.headers.get("x-payment")
            
            # No payment provided - return 402 with payment details (all accepted options)
            if not payment_header:
                ref = f"x402:{func.__name__}:{datetime.utcnow().timestamp()}"
                options = [{"amount": amount, "recipient": recipient, "currency": currency, "chain": chain, "reference": ref}]
                if flr_amount and flr_recipient:
                    options.append({"amount": flr_amount, "recipient": flr_recipient, "currency": "FLR", "chain": "flare", "reference": ref})
                return JSONResponse(
                    status_code=402,
                    content={
                        # Primary option (USDC / configured currency)
                        "amount": amount,
                        "recipient": recipient,
                        "reference": ref,
                        "currency": currency,
                        "chain": chain,
                        # All accepted payment options
                        "accepted": options,
                    },
                    headers={
                        "X-Payment-Required": "true",
                        "X-Payment-Amount": amount,
                        "X-Payment-Currency": currency,
                    },
                )
            
            # Payment provided - verify it
            verifier = X402PaymentVerifier()
            proof = verifier.parse_payment_header(payment_header)

            if not proof:
                raise HTTPException(status_code=400, detail="invalid_payment_header")

            # Route verification to correct currency/recipient pair
            if proof.currency.upper() == "FLR" and flr_amount and flr_recipient:
                is_valid = await verifier.verify_payment(proof, flr_amount, flr_recipient)
            else:
                is_valid = await verifier.verify_payment(proof, amount, recipient)
            
            if not is_valid:
                raise HTTPException(status_code=403, detail="payment_verification_failed")
            
            # Record payment (best effort)
            try:
                from .db import SessionLocal
                session = SessionLocal()
                await verifier.record_payment(session, proof, func.__name__)
                session.close()
            except Exception:
                pass
            
            # Payment verified - execute endpoint
            result = await func(request, *args, **kwargs)
            
            # Add payment confirmation header
            if isinstance(result, JSONResponse):
                result.headers["X-Payment-Response"] = json.dumps({
                    "verified": True,
                    "tx_hash": proof.tx_hash,
                    "amount": proof.amount,
                })
            
            return result
        
        return wrapper
    return decorator


def generate_payment_payload(tx_hash: str, amount: str, recipient: str, currency: str = "USDC", chain: str = "base") -> str:
    """Generate X-PAYMENT header value.
    
    Used by agents to create payment proof.
    """
    payload = {
        "tx_hash": tx_hash,
        "amount": amount,
        "recipient": recipient,
        "currency": currency,
        "chain": chain,
        "timestamp": datetime.utcnow().isoformat(),
    }
    return json.dumps(payload)
