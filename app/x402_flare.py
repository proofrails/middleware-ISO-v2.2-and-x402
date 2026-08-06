"""Flare-specific x402 payment verification.

Handles two Flare payment paths:
  1. USDT0 via EIP-3009 facilitator (eip3009_facilitator)
  2. Native FLR transfer (native_transfer)

This module is intentionally separate from app/x402.py (Base USDC) so each
path can be tested and toggled independently.
"""
from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal, InvalidOperation
from typing import Optional

from fastapi import HTTPException
from web3 import Web3
from web3.exceptions import TransactionNotFound

# ── EIP-3009 nonce consumed event / PaymentSettled event topic ────────────────

# X402Facilitator event: X402PaymentSettled(token, payer, recipient, amount, nonce, paymentId)
_X402_SETTLED_TOPIC = Web3.keccak(
    text="X402PaymentSettled(address,address,address,uint256,bytes32,bytes32)"
).hex()

# IEIP3009: AuthorizationUsed(address authorizer, bytes32 nonce)
_AUTH_USED_TOPIC = Web3.keccak(text="AuthorizationUsed(address,bytes32)").hex()


# ── Parsed payment structs ────────────────────────────────────────────────────

@dataclass
class FlareUSDT0Payment:
    """Parsed USDT0 EIP-3009 payment from X-PAYMENT header."""
    chain: str                  # "flare"
    chain_id: int               # 14
    currency: str               # "USDT0"
    payment_type: str           # "eip3009_facilitator"
    token: str                  # USDT0 contract address
    facilitator: str            # X402Facilitator address
    # Authorization fields (present when sending unsigned auth)
    from_address: Optional[str] = None
    to: Optional[str] = None
    value: Optional[str] = None         # raw integer string
    valid_after: Optional[str] = None   # unix ts string
    valid_before: Optional[str] = None  # unix ts string
    nonce: Optional[str] = None         # 0x-prefixed bytes32
    v: Optional[int] = None
    r: Optional[str] = None
    s: Optional[str] = None
    authorization_type: str = "receiveWithAuthorization"
    # OR: client-settled mode — client already submitted to facilitator
    settlement_tx_hash: Optional[str] = None
    recipient: Optional[str] = None     # used in settlement_tx_hash mode
    amount: Optional[str] = None        # human-readable, used in settlement_tx_hash mode


@dataclass
class FlareNativePayment:
    """Parsed native FLR transfer payment."""
    chain: str = "flare"
    chain_id: int = 14
    currency: str = "FLR"
    payment_type: str = "native_transfer"
    tx_hash: str = ""
    from_address: Optional[str] = None
    to: Optional[str] = None
    value: Optional[str] = None  # raw wei string
    amount: Optional[str] = None  # human-readable FLR


# ── Parser ────────────────────────────────────────────────────────────────────

def parse_flare_payment(header: str) -> Optional[FlareUSDT0Payment | FlareNativePayment]:
    """Parse X-PAYMENT header for Flare-specific payment types."""
    try:
        data = json.loads(header)
    except Exception:
        return None

    payment_type = data.get("payment_type", "")
    chain = data.get("chain", "")

    if chain not in ("flare",) and data.get("chain_id") not in (14, "14"):
        return None

    if payment_type == "eip3009_facilitator":
        return FlareUSDT0Payment(
            chain=data.get("chain", "flare"),
            chain_id=int(data.get("chain_id", 14)),
            currency=data.get("currency", "USDT0"),
            payment_type="eip3009_facilitator",
            token=data.get("token", ""),
            facilitator=data.get("facilitator", ""),
            from_address=data.get("from"),
            to=data.get("to"),
            value=str(data["value"]) if data.get("value") is not None else None,
            valid_after=str(data["valid_after"]) if data.get("valid_after") is not None else None,
            valid_before=str(data["valid_before"]) if data.get("valid_before") is not None else None,
            nonce=data.get("nonce"),
            v=data.get("v"),
            r=data.get("r"),
            s=data.get("s"),
            authorization_type=data.get("authorization_type", "receiveWithAuthorization"),
            settlement_tx_hash=data.get("settlement_tx_hash"),
            recipient=data.get("recipient"),
            amount=str(data["amount"]) if data.get("amount") is not None else None,
        )

    if payment_type == "native_transfer":
        return FlareNativePayment(
            chain=data.get("chain", "flare"),
            chain_id=int(data.get("chain_id", 14)),
            currency=data.get("currency", "FLR"),
            payment_type="native_transfer",
            tx_hash=data.get("tx_hash", ""),
            from_address=data.get("from"),
            to=data.get("to"),
            value=str(data["value"]) if data.get("value") is not None else None,
            amount=str(data["amount"]) if data.get("amount") is not None else None,
        )

    return None


# ── X402Facilitator ABI (minimal, for event parsing) ─────────────────────────

_FACILITATOR_ABI = [
    {
        "name": "X402PaymentSettled",
        "type": "event",
        "inputs": [
            {"name": "token", "type": "address", "indexed": True},
            {"name": "payer", "type": "address", "indexed": True},
            {"name": "recipient", "type": "address", "indexed": True},
            {"name": "amount", "type": "uint256", "indexed": False},
            {"name": "nonce", "type": "bytes32", "indexed": False},
            {"name": "paymentId", "type": "bytes32", "indexed": False},
        ],
    },
    {
        "name": "settlePaymentAsPayee",
        "type": "function",
        "stateMutability": "nonpayable",
        "inputs": [
            {
                "name": "payload",
                "type": "tuple",
                "components": [
                    {"name": "from", "type": "address"},
                    {"name": "to", "type": "address"},
                    {"name": "token", "type": "address"},
                    {"name": "value", "type": "uint256"},
                    {"name": "validAfter", "type": "uint256"},
                    {"name": "validBefore", "type": "uint256"},
                    {"name": "nonce", "type": "bytes32"},
                    {"name": "v", "type": "uint8"},
                    {"name": "r", "type": "bytes32"},
                    {"name": "s", "type": "bytes32"},
                ],
            }
        ],
        "outputs": [{"name": "paymentId", "type": "bytes32"}],
    },
    {
        "name": "settlePayment",
        "type": "function",
        "stateMutability": "nonpayable",
        "inputs": [
            {
                "name": "payload",
                "type": "tuple",
                "components": [
                    {"name": "from", "type": "address"},
                    {"name": "to", "type": "address"},
                    {"name": "token", "type": "address"},
                    {"name": "value", "type": "uint256"},
                    {"name": "validAfter", "type": "uint256"},
                    {"name": "validBefore", "type": "uint256"},
                    {"name": "nonce", "type": "bytes32"},
                    {"name": "v", "type": "uint8"},
                    {"name": "r", "type": "bytes32"},
                    {"name": "s", "type": "bytes32"},
                ],
            }
        ],
        "outputs": [{"name": "paymentId", "type": "bytes32"}],
    },
]


# ── Verifier ──────────────────────────────────────────────────────────────────

class FlarePaymentVerifier:
    """Verifies Flare USDT0 and native FLR x402 payments."""

    def __init__(self, rpc_url: Optional[str] = None, chain_id: int = 14):
        self.rpc_url = rpc_url or os.getenv(
            "X402_FLARE_RPC_URL", "https://flare-api.flare.network/ext/C/rpc"
        )
        self.chain_id = chain_id
        self.w3 = Web3(Web3.HTTPProvider(self.rpc_url))

    # ── USDT0 settlement_tx_hash mode ────────────────────────────────────────

    async def verify_usdt0_settlement_tx(
        self,
        payment: FlareUSDT0Payment,
        expected_token: str,
        expected_recipient: str,
        expected_raw_amount: int,
        facilitator_address: str,
        confirmations: int = 1,
    ) -> tuple[bool, Optional[str], Optional[str]]:
        """Verify a client-submitted facilitator settlement tx.

        Returns (ok, facilitator_payment_id, error_message).
        """
        if not payment.settlement_tx_hash:
            return False, None, "missing_settlement_tx_hash"

        try:
            tx_receipt = self.w3.eth.get_transaction_receipt(payment.settlement_tx_hash)
        except TransactionNotFound:
            return False, None, "transaction_not_found"
        except Exception as exc:
            return False, None, f"rpc_error:{exc}"

        if not tx_receipt:
            return False, None, "transaction_not_found"
        if tx_receipt.get("status") != 1:
            return False, None, "transaction_reverted"

        # Confirm block depth
        try:
            current_block = self.w3.eth.block_number
            tx_block = tx_receipt.get("blockNumber", 0)
            if current_block - tx_block < confirmations - 1:
                return False, None, "insufficient_confirmations"
        except Exception:
            pass  # non-fatal — proceed

        # Ensure tx was sent to the expected facilitator
        tx_to = (tx_receipt.get("to") or "").lower()
        if tx_to != facilitator_address.lower():
            return False, None, "wrong_facilitator"

        # Parse X402PaymentSettled event logs
        for log in tx_receipt.get("logs", []):
            topics = log.get("topics", [])
            if not topics:
                continue
            topic0 = topics[0].hex() if hasattr(topics[0], "hex") else topics[0]
            if topic0.lower() != _X402_SETTLED_TOPIC.lower():
                continue

            # Indexed: token(t1), payer(t2), recipient(t3)
            if len(topics) < 4:
                continue

            def _addr(topic_bytes) -> str:
                raw = topic_bytes.hex() if hasattr(topic_bytes, "hex") else topic_bytes
                return "0x" + raw[-40:]

            log_token = _addr(topics[1])
            log_recipient = _addr(topics[3])

            if log_token.lower() != expected_token.lower():
                return False, None, "token_mismatch"
            if log_recipient.lower() != expected_recipient.lower():
                return False, None, "wrong_recipient"

            # Non-indexed: amount (32 bytes), nonce (32 bytes), paymentId (32 bytes)
            data_hex = (log.get("data") or "0x").replace("0x", "")
            if len(data_hex) < 192:
                continue

            log_amount = int(data_hex[:64], 16)
            log_payment_id = "0x" + data_hex[128:192]

            if log_amount < expected_raw_amount:
                return False, None, "insufficient_amount"

            return True, log_payment_id, None

        return False, None, "facilitator_event_not_found"

    # ── USDT0 server-submitted mode ──────────────────────────────────────────

    async def submit_and_verify_usdt0(
        self,
        payment: FlareUSDT0Payment,
        expected_token: str,
        expected_recipient: str,
        expected_raw_amount: int,
        facilitator_address: str,
        settler_private_key: str,
        authorization_type: str = "receiveWithAuthorization",
    ) -> tuple[bool, Optional[str], Optional[str], Optional[str]]:
        """Server submits the EIP-3009 authorization to the facilitator.

        Returns (ok, settlement_tx_hash, facilitator_payment_id, error_message).
        """
        if not all([payment.from_address, payment.to, payment.value, payment.nonce, payment.v, payment.r, payment.s]):
            return False, None, None, "incomplete_authorization"

        if payment.token.lower() != expected_token.lower():
            return False, None, None, "token_mismatch"
        if (payment.to or "").lower() != expected_recipient.lower():
            return False, None, None, "wrong_recipient"
        if int(payment.value) < expected_raw_amount:
            return False, None, None, "insufficient_amount"

        try:
            account = self.w3.eth.account.from_key(settler_private_key)
            facilitator = self.w3.eth.contract(
                address=Web3.to_checksum_address(facilitator_address),
                abi=_FACILITATOR_ABI,
            )

            payload = (
                Web3.to_checksum_address(payment.from_address),
                Web3.to_checksum_address(payment.to),
                Web3.to_checksum_address(payment.token),
                int(payment.value),
                int(payment.valid_after or 0),
                int(payment.valid_before),
                bytes.fromhex(payment.nonce.replace("0x", "")),
                payment.v,
                bytes.fromhex(payment.r.replace("0x", "")),
                bytes.fromhex(payment.s.replace("0x", "")),
            )

            fn = (
                facilitator.functions.settlePaymentAsPayee(payload)
                if authorization_type == "receiveWithAuthorization"
                else facilitator.functions.settlePayment(payload)
            )

            tx = fn.build_transaction({
                "from": account.address,
                "nonce": self.w3.eth.get_transaction_count(account.address),
                "gas": 200_000,
            })
            signed = account.sign_transaction(tx)
            tx_hash_bytes = self.w3.eth.send_raw_transaction(signed.raw_transaction)
            receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash_bytes, timeout=60)

            if receipt.get("status") != 1:
                return False, tx_hash_bytes.hex(), None, "settlement_tx_reverted"

            # Parse paymentId from logs
            for log in receipt.get("logs", []):
                topics = log.get("topics", [])
                if not topics:
                    continue
                topic0 = topics[0].hex() if hasattr(topics[0], "hex") else topics[0]
                if topic0.lower() == _X402_SETTLED_TOPIC.lower():
                    data_hex = (log.get("data") or "0x").replace("0x", "")
                    if len(data_hex) >= 192:
                        payment_id = "0x" + data_hex[128:192]
                        return True, "0x" + tx_hash_bytes.hex().replace("0x", ""), payment_id, None

            return True, "0x" + tx_hash_bytes.hex().replace("0x", ""), None, None

        except Exception as exc:
            return False, None, None, f"settlement_error:{exc}"

    # ── Native FLR ───────────────────────────────────────────────────────────

    async def verify_flr_transfer(
        self,
        payment: FlareNativePayment,
        expected_recipient: str,
        expected_min_wei: int,
        confirmations: int = 1,
    ) -> tuple[bool, Optional[str]]:
        """Verify a native FLR transfer on Flare.

        Returns (ok, error_message).
        """
        if not payment.tx_hash:
            return False, "missing_tx_hash"

        try:
            tx = self.w3.eth.get_transaction(payment.tx_hash)
        except TransactionNotFound:
            return False, "transaction_not_found"
        except Exception as exc:
            return False, f"rpc_error:{exc}"

        if not tx:
            return False, "transaction_not_found"

        # Verify recipient
        to_addr = tx.get("to") or ""
        if to_addr.lower() != expected_recipient.lower():
            return False, "wrong_recipient"

        # Verify amount
        value_wei = tx.get("value", 0)
        if value_wei < expected_min_wei:
            return False, "insufficient_amount"

        # Verify the tx was mined and successful
        try:
            receipt = self.w3.eth.get_transaction_receipt(payment.tx_hash)
            if not receipt or receipt.get("status") != 1:
                return False, "transaction_not_confirmed"

            current_block = self.w3.eth.block_number
            tx_block = receipt.get("blockNumber", 0)
            if current_block - tx_block < confirmations - 1:
                return False, "insufficient_confirmations"
        except Exception as exc:
            return False, f"receipt_error:{exc}"

        return True, None


# ── Amount helpers ────────────────────────────────────────────────────────────

def usdt0_to_raw(human_amount: str, decimals: int = 6) -> int:
    """Convert human-readable USDT0 amount to raw integer units."""
    try:
        d = Decimal(human_amount) * Decimal(10 ** decimals)
        return int(d)
    except (InvalidOperation, ValueError) as exc:
        raise ValueError(f"Invalid USDT0 amount: {human_amount!r}") from exc


def flr_to_wei(human_amount: str) -> int:
    """Convert human-readable FLR amount to wei."""
    try:
        d = Decimal(human_amount) * Decimal(10 ** 18)
        return int(d)
    except (InvalidOperation, ValueError) as exc:
        raise ValueError(f"Invalid FLR amount: {human_amount!r}") from exc


def build_402_payment_options(
    usdc_enabled: bool,
    usdt0_enabled: bool,
    flr_enabled: bool,
    usdc_recipient: Optional[str],
    usdt0_recipient: Optional[str],
    flr_recipient: Optional[str],
    usdc_amount: str,
    usdt0_amount: str,
    flr_amount: str,
    usdc_token: str,
    usdt0_token: str,
    facilitator: Optional[str],
    base_chain_id: int = 8453,
    flare_chain_id: int = 14,
) -> list[dict]:
    """Build the `accepts` list returned in a 402 Payment Required response."""
    accepts = []

    if usdc_enabled and usdc_recipient:
        accepts.append({
            "scheme": "exact",
            "network": "base",
            "asset": "USDC",
            "payment_type": "erc20_transfer",
            "token": usdc_token,
            "chain_id": base_chain_id,
            "decimals": 6,
            "recipient": usdc_recipient,
            "amount": usdc_amount,
        })

    if usdt0_enabled and usdt0_recipient and facilitator:
        accepts.append({
            "scheme": "exact",
            "network": "flare",
            "asset": "USDT0",
            "payment_type": "eip3009_facilitator",
            "token": usdt0_token,
            "facilitator": facilitator,
            "chain_id": flare_chain_id,
            "decimals": 6,
            "recipient": usdt0_recipient,
            "amount": usdt0_amount,
        })

    if flr_enabled and flr_recipient:
        accepts.append({
            "scheme": "exact",
            "network": "flare",
            "asset": "FLR",
            "payment_type": "native_transfer",
            "chain_id": flare_chain_id,
            "decimals": 18,
            "recipient": flr_recipient,
            "amount": flr_amount,
        })

    return accepts
