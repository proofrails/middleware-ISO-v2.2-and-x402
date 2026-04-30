from __future__ import annotations

"""Flare AI Skills integration — agent-facing Flare protocol endpoints.

This module exposes three layers of Flare intelligence for agentic clients:

1. **Capabilities discovery** (`GET /v1/capabilities`)
   Returns the full API surface as OpenAI-compatible function/tool schemas.
   Any LLM agent that calls this endpoint can self-configure without
   hardcoded prompts.

2. **FTSO price feeds** (`GET /v1/flare/feeds`, `GET /v1/flare/feeds/{symbol}`)
   Live Flare FTSO v2 prices with structured metadata drawn from the
   Flare AI Skills (flare-ftso-skill). Feeds are appropriate for FX
   rate injection into ISO 20022 messages and payment verification.

3. **FDC attestation helper** (`POST /v1/flare/fdc/prepare-attestation`)
   Constructs the verifier API request body for an EVMTransaction or
   Payment attestation using the Flare Data Connector (flare-fdc-skill).
   Stronger than raw Transfer-event checking — the attestation is
   Merkle-proof-backed and verifiable on-chain.

4. **Natural language Flare explain** (`POST /v1/flare/explain`)
   Routes questions about FTSO, FDC, FAssets, and Flare architecture
   to the configured AI provider with the Flare AI Skills context injected
   into the system prompt.

Flare AI Skills reference
-------------------------
https://github.com/flare-foundation/flare-ai-skills

Skills embedded here:
  flare-general-skill  — network info, governance, tooling
  flare-ftso-skill     — price feed consumption, feed IDs, update mechanics
  flare-fdc-skill      — attestation types, verifier API, DA layer, proofs
"""

import logging
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from app.api.deps import get_session
from app.auth import Principal, resolve_principal
from app.errors import APIError, ErrorCode
from app.flare.ftso import FEED_IDS, get_ftso_rates

logger = logging.getLogger("middleware.flare_ai")

router = APIRouter(tags=["flare-ai"])


# ── Schemas ───────────────────────────────────────────────────────────────────

class FeedInfo(BaseModel):
    symbol: str
    price: Optional[str] = Field(None, description="Human-readable decimal price (e.g. '0.02150')")
    raw_value: Optional[int] = None
    raw_decimals: Optional[int] = None
    timestamp: Optional[int] = Field(None, description="Unix epoch of last on-chain update")
    age_seconds: Optional[float] = None
    source: str = "ftso_v2"
    feed_id_hex: str = Field(..., description="bytes21 feed ID as hex string")


class FeedsResponse(BaseModel):
    feeds: List[FeedInfo]
    update_frequency_seconds: int = 90
    registry_address: str
    network: str = "flare"
    note: str = (
        "Prices sourced from Flare FTSO v2. "
        "Update every ~90 s via independent data providers. "
        "Use getFeedById(bytes21) on-chain for trustless consumption."
    )


class FDCAttestationRequest(BaseModel):
    tx_hash: str = Field(..., description="Transaction hash to attest")
    chain: str = Field(
        "flare",
        description="Source chain: 'eth', 'flare', 'btc', 'xrpl', 'doge', etc.",
    )
    required_confirmations: int = Field(6, ge=1, le=100)
    provide_input: bool = Field(False, description="Include tx input data in attestation")
    list_events: bool = Field(True, description="Include event logs in attestation")


class FDCAttestationResponse(BaseModel):
    attestation_type: str
    request_body: Dict[str, Any] = Field(
        ..., description="POST body to send to the FDC verifier API"
    )
    verifier_url: str
    da_layer_url: str
    note: str


class ExplainRequest(BaseModel):
    question: str = Field(..., description="Natural language question about Flare protocol")
    context: Optional[str] = Field(
        None,
        description="Optional context (e.g. a transaction hash, feed symbol, or error message)",
    )


class ExplainResponse(BaseModel):
    answer: str
    sources: List[str] = Field(default_factory=list)


# ── Flare AI Skills knowledge base (embedded from flare-ai-skills) ────────────

_FLARE_SYSTEM_PROMPT = """You are a Flare blockchain protocol expert. Answer questions about:

FTSO v2 (Time Series Oracle):
- Block-latency feeds updated every ~90 seconds on Flare C-Chain
- getFeedById(bytes21 _feedId) returns (uint256 value, int8 decimals, uint64 timestamp)
- Actual price = value * 10^decimals  (decimals is typically negative, e.g. -5)
- Contract registry at 0xaD67FE66660Fb8dFE9d6b1b4240d8650e30F6019
- Resolve FtsoV2 address: registry.getContractAddressByName("FtsoV2")
- Feed ID encoding: b'\\x01' + symbol_ascii.ljust(20, b'\\x00')
- Available feeds: FLR/USD, BTC/USD, ETH/USD, XRP/USD, USDC/USD, SGB/USD, USDT/USD, ADA/USD, DOGE/USD

FDC (Flare Data Connector):
- Cryptographically attests off-chain and cross-chain data on Flare
- EVMTransaction: attests EVM tx details + event logs with Merkle proof
- Payment: confirms BTC/DOGE/XRP/XRPL payment with confirmations
- Web2Json: attests API response data (with JQ transform) on-chain
- AddressValidity: validates address format for any supported chain
- Verifier prepareRequest: POST {VERIFIER_URL}/verifier/{chain}/{type}/prepareRequest
- Auth header: X-apikey: {UUID_KEY}
- DA layer proof: POST {DA_URL}/api/v1/fdc/proof-by-request-round-raw
- On-chain verify: IFdcVerification.verifyEVMTransaction(Proof calldata)

Flare Networks:
- Mainnet: chain ID 14, RPC https://flare-api.flare.network/ext/C/rpc
- Coston2 testnet: chain ID 114, RPC https://coston2-api.flare.network/ext/C/rpc
- Songbird: chain ID 19, RPC https://songbird-api.flare.network/ext/C/rpc

FAssets:
- Wrapped non-EVM assets: FXRP, FBTC, FDOGE
- Mint via AssetManager (resolved from ContractRegistry)
- Redeem by burning fAssets back to underlying chain address

Smart Accounts (XRPL bridge):
- Links XRPL addresses to Flare EVM accounts
- MasterAccountController.getPersonalAccount(xrplAddress) → Flare address
- Enables XRPL users to interact with Flare DeFi without holding FLR

Be concise and technically precise. Include contract addresses and function signatures when relevant."""


# ── Routes ────────────────────────────────────────────────────────────────────

@router.get("/v1/capabilities")
def get_capabilities(
    session=Depends(get_session),
    principal: Principal = Depends(resolve_principal),
):
    """Return the full API surface as OpenAI-compatible tool schemas.

    Agentic clients call this endpoint once at startup to self-configure.
    The response includes:
    - All available operations as function/tool definitions
    - Authentication requirements
    - x402 pricing for metered endpoints
    - Flare protocol metadata (FTSO feeds, FDC, network config)

    Compatible with OpenAI function calling and Anthropic tool use formats.
    """
    from app.settings import get_settings
    settings = get_settings()
    base_url = settings.public_base_url or "http://localhost:8000"

    # Fetch live x402 pricing
    from app import models as m
    pricing: Dict[str, str] = {}
    try:
        endpoints = session.query(m.ProtectedEndpoint).all()
        pricing = {ep.path: str(ep.price) for ep in endpoints}
    except Exception:
        pass

    tools = _build_tool_schemas(pricing)

    flare_info = {
        "ftso": {
            "description": "Flare Time Series Oracle v2 — block-latency tamper-proof price feeds",
            "update_frequency_seconds": 90,
            "registry_address": settings.ftso_registry_address,
            "available_feeds": list(FEED_IDS.keys()),
            "feed_id_encoding": "b'\\x01' + symbol_ascii.ljust(20, b'\\x00')",
            "contract_method": "getFeedById(bytes21) → (uint256 value, int8 decimals, uint64 ts)",
            "live_feeds_endpoint": f"{base_url}/v1/flare/feeds",
        },
        "fdc": {
            "description": "Flare Data Connector — Merkle-proof attestation for cross-chain data",
            "attestation_types": [
                "EVMTransaction",
                "Payment",
                "Web2Json",
                "AddressValidity",
            ],
            "prepare_attestation_endpoint": f"{base_url}/v1/flare/fdc/prepare-attestation",
            "supported_chains": [
                "eth", "flare", "sgb", "btc", "doge", "xrpl",
                "testETH", "testFLR", "testSGB",
            ],
        },
        "networks": {
            "flare": {
                "chain_id": 14,
                "rpc": "https://flare-api.flare.network/ext/C/rpc",
                "explorer": "https://flarescan.com",
                "native_currency": "FLR",
            },
            "coston2": {
                "chain_id": 114,
                "rpc": "https://coston2-api.flare.network/ext/C/rpc",
                "explorer": "https://coston2.testnet.flarescan.com",
                "native_currency": "C2FLR",
            },
        },
    }

    return {
        "schema_version": "1.0",
        "service": "ISO 20022 Payment Middleware",
        "base_url": base_url,
        "authentication": {
            "methods": ["api_key", "siwe"],
            "api_key_header": "X-API-Key",
            "siwe_endpoints": [
                f"{base_url}/v1/auth/nonce",
                f"{base_url}/v1/auth/siwe-verify",
            ],
        },
        "idempotency": {
            "header": "Idempotency-Key",
            "supported_methods": ["POST", "PUT", "PATCH"],
            "ttl_hours": 24,
            "note": "Include a client-generated UUID to safely retry mutations",
        },
        "rate_limits": {
            "unauthenticated": "30 req/min",
            "api_key": "200 req/min",
            "admin": "1000 req/min",
            "headers": ["X-RateLimit-Limit", "X-RateLimit-Remaining", "X-RateLimit-Reset"],
        },
        "tools": tools,
        "flare_protocol": flare_info,
    }


@router.get("/v1/flare/feeds", response_model=FeedsResponse)
def list_feeds():
    """Return all available FTSO v2 price feeds with live values.

    Prices are sourced directly from Flare's on-chain FTSO v2 oracle,
    the same data injected into ISO 20022 messages. Results are cached
    for 90 seconds (one FTSO epoch).

    Compatible with the flare-ftso-skill from flare-foundation/flare-ai-skills.
    """
    from app.settings import get_settings
    settings = get_settings()

    if not settings.ftso_enabled:
        raise APIError(ErrorCode.FTSO_UNAVAILABLE, "FTSO feeds are disabled on this instance", 503, retryable=True)

    all_symbols = list(FEED_IDS.keys())
    rates = get_ftso_rates(all_symbols)

    feeds = []
    for sym, feed_id_bytes in FEED_IDS.items():
        rate = rates.get(sym)
        feeds.append(
            FeedInfo(
                symbol=sym,
                price=str(rate.value) if rate else None,
                raw_value=rate.raw_value if rate else None,
                raw_decimals=rate.raw_decimals if rate else None,
                timestamp=rate.timestamp if rate else None,
                age_seconds=rate.age_seconds if rate else None,
                feed_id_hex=feed_id_bytes.hex(),
            )
        )

    return FeedsResponse(
        feeds=feeds,
        registry_address=settings.ftso_registry_address,
    )


@router.get("/v1/flare/feeds/{symbol}", response_model=FeedInfo)
def get_feed(symbol: str):
    """Return a single FTSO v2 price feed by symbol (e.g. FLR/USD).

    Use URL-encoding for the slash: `/v1/flare/feeds/FLR%2FUSD`
    or pass the symbol without slash as `FLRUSD` (also accepted).
    """
    # Normalise: accept "FLRUSD" as "FLR/USD"
    normalised = symbol.upper()
    if "/" not in normalised and len(normalised) >= 6:
        normalised = f"{normalised[:3]}/{normalised[3:]}"

    if normalised not in FEED_IDS:
        raise APIError(ErrorCode.FEED_NOT_FOUND, f"Feed '{symbol}' not found. See /v1/flare/feeds for available feeds.", 404)

    from app.flare.ftso import get_ftso_rate
    rate = get_ftso_rate(normalised)

    feed_id_bytes = FEED_IDS[normalised]
    return FeedInfo(
        symbol=normalised,
        price=str(rate.value) if rate else None,
        raw_value=rate.raw_value if rate else None,
        raw_decimals=rate.raw_decimals if rate else None,
        timestamp=rate.timestamp if rate else None,
        age_seconds=rate.age_seconds if rate else None,
        feed_id_hex=feed_id_bytes.hex(),
    )


@router.post("/v1/flare/fdc/prepare-attestation", response_model=FDCAttestationResponse)
def prepare_fdc_attestation(body: FDCAttestationRequest):
    """Prepare an FDC attestation request body for a transaction.

    Returns the formatted request body to POST to the FDC verifier API,
    allowing you to get a Merkle-proof-backed attestation for an EVM
    transaction. This is stronger than raw Transfer-event checking.

    Flow:
    1. Call this endpoint to get the `request_body`
    2. POST `request_body` to `verifier_url` with your X-apikey header
    3. Note the `votingRoundId` from the verifier response
    4. Poll `da_layer_url` with votingRoundId + requestBytes for the proof
    5. Submit the proof to IFdcVerification.verifyEVMTransaction() on-chain

    For testnet, use verifier key "00000000-0000-0000-0000-000000000000".
    For mainnet, obtain a key from https://dev.flare.network/fdc/verifiers.
    """
    from app.settings import get_settings
    settings = get_settings()

    chain_map = {
        "flare": "flr", "ethereum": "eth", "eth": "eth",
        "btc": "btc", "bitcoin": "btc",
        "xrpl": "xrpl", "xrp": "xrpl",
        "doge": "doge",
        "sgb": "sgb", "songbird": "sgb",
    }
    chain_key = chain_map.get(body.chain.lower(), body.chain.lower())

    # Determine attestation type based on chain
    evm_chains = {"eth", "flr", "sgb", "testeth", "testflr", "testsgb"}
    if chain_key in evm_chains:
        att_type = "EVMTransaction"
        request_body: Dict[str, Any] = {
            "transactionHash": body.tx_hash,
            "requiredConfirmations": str(body.required_confirmations),
            "provideInput": body.provide_input,
            "listEvents": body.list_events,
            "logIndices": [],
        }
    else:
        att_type = "Payment"
        request_body = {
            "transactionHash": body.tx_hash,
            "requiredConfirmations": str(body.required_confirmations),
            "checkSourceAddresses": False,
        }

    # Verifier URL (configurable via FDC_VERIFIER_URL env)
    import os
    verifier_base = os.getenv(
        "FDC_VERIFIER_URL",
        "https://fdc-verifiers-testnet.aflabs.net",
    )
    da_base = os.getenv(
        "FDC_DA_LAYER_URL",
        "https://da-layer-testnet.aflabs.net",
    )

    return FDCAttestationResponse(
        attestation_type=att_type,
        request_body=request_body,
        verifier_url=f"{verifier_base}/verifier/{chain_key}/{att_type}/prepareRequest",
        da_layer_url=f"{da_base}/api/v1/fdc/proof-by-request-round-raw",
        note=(
            "POST request_body to verifier_url with header X-apikey: <your-key>. "
            "Then POST {votingRoundId, requestBytes} to da_layer_url to retrieve the Merkle proof. "
            "Submit the proof to IFdcVerification on Flare for trustless on-chain verification."
        ),
    )


@router.post("/v1/flare/explain", response_model=ExplainResponse)
def explain_flare(
    body: ExplainRequest,
    session=Depends(get_session),
    principal: Principal = Depends(resolve_principal),
):
    """Answer natural language questions about Flare protocol using AI.

    Powered by the Flare AI Skills knowledge base (flare-foundation/flare-ai-skills).
    Covers: FTSO price feeds, FDC attestations, FAssets, Smart Accounts,
    Flare network architecture, governance, and developer tooling.

    Requires AI to be configured (OPENAI_API_KEY or equivalent).
    """
    from app.settings import get_settings
    settings = get_settings()

    if not settings.openai_api_key:
        raise APIError(
            ErrorCode.INTERNAL_ERROR,
            "AI is not configured on this instance. Set OPENAI_API_KEY.",
            503,
        )

    context_addon = ""
    if body.context:
        context_addon = f"\n\nAdditional context from the user: {body.context}"

    user_message = body.question + context_addon

    try:
        import openai
        client = openai.OpenAI(api_key=settings.openai_api_key)
        completion = client.chat.completions.create(
            model=settings.ai_model,
            temperature=0.2,
            max_tokens=800,
            messages=[
                {"role": "system", "content": _FLARE_SYSTEM_PROMPT},
                {"role": "user", "content": user_message},
            ],
        )
        answer = completion.choices[0].message.content or ""
        return ExplainResponse(
            answer=answer,
            sources=["flare-ai-skills", "flare-ftso-skill", "flare-fdc-skill"],
        )
    except Exception as exc:
        logger.warning("flare_explain_ai_error: %s", exc)
        raise APIError(ErrorCode.INTERNAL_ERROR, f"AI request failed: {exc}", 500)


# ── Tool schema builder ───────────────────────────────────────────────────────

def _build_tool_schemas(pricing: Dict[str, str]) -> List[Dict[str, Any]]:
    """Build OpenAI-compatible tool definitions for all API operations."""
    return [
        {
            "name": "record_payment",
            "description": (
                "Record a blockchain payment and generate ISO 20022 compliance documents "
                "with on-chain evidence anchoring on Flare. Returns a receipt_id and "
                "operation_id for status polling."
            ),
            "endpoint": {"method": "POST", "path": "/v1/iso/record-tip"},
            "idempotency_supported": True,
            "x402_cost": None,
            "parameters": {
                "type": "object",
                "properties": {
                    "tip_tx_hash": {
                        "type": "string",
                        "description": "Blockchain transaction hash (0x-prefixed)",
                    },
                    "chain": {
                        "type": "string",
                        "description": "Chain name: flare, ethereum, base, polygon, etc.",
                    },
                    "amount": {"type": "string", "description": "Decimal amount string"},
                    "currency": {"type": "string", "description": "Currency code: FLR, USDC, ETH, etc."},
                    "sender_wallet": {"type": "string", "description": "Sender address (0x...)"},
                    "receiver_wallet": {"type": "string", "description": "Receiver address (0x...)"},
                    "reference": {
                        "type": "string",
                        "description": "External reference, e.g. 'invoice:INV-2024-001'",
                    },
                    "metadata": {
                        "type": "object",
                        "description": "Free-form key-value metadata for agent context (correlation IDs, task IDs, etc.)",
                    },
                    "tags": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Optional string tags for filtering",
                    },
                    "callback_url": {
                        "type": "string",
                        "description": "Optional URL to receive a POST when anchoring completes",
                    },
                },
                "required": ["tip_tx_hash", "chain", "amount", "currency", "sender_wallet", "receiver_wallet", "reference"],
            },
        },
        {
            "name": "get_operation_status",
            "description": (
                "Poll the status of an asynchronous receipt-processing operation. "
                "Lightweight alternative to fetching the full receipt."
            ),
            "endpoint": {"method": "GET", "path": "/v1/operations/{operation_id}"},
            "idempotency_supported": False,
            "x402_cost": None,
            "parameters": {
                "type": "object",
                "properties": {
                    "operation_id": {"type": "string", "description": "UUID from record_payment response"},
                },
                "required": ["operation_id"],
            },
        },
        {
            "name": "get_receipt",
            "description": "Get full receipt details including ISO 20022 artifact URLs.",
            "endpoint": {"method": "GET", "path": "/v1/iso/receipts/{receipt_id}"},
            "idempotency_supported": False,
            "x402_cost": None,
            "parameters": {
                "type": "object",
                "properties": {
                    "receipt_id": {"type": "string"},
                },
                "required": ["receipt_id"],
            },
        },
        {
            "name": "get_receipt_status",
            "description": "Lightweight receipt status check — returns only status and hashes.",
            "endpoint": {"method": "GET", "path": "/v1/iso/receipts/{receipt_id}/status"},
            "idempotency_supported": False,
            "x402_cost": None,
            "parameters": {
                "type": "object",
                "properties": {
                    "receipt_id": {"type": "string"},
                },
                "required": ["receipt_id"],
            },
        },
        {
            "name": "list_receipts",
            "description": (
                "List receipts with optional filtering. Supports cursor-based pagination "
                "for reliable traversal of large datasets."
            ),
            "endpoint": {"method": "GET", "path": "/v1/receipts"},
            "idempotency_supported": False,
            "x402_cost": None,
            "parameters": {
                "type": "object",
                "properties": {
                    "cursor": {"type": "string", "description": "Opaque pagination cursor from previous response"},
                    "page_size": {"type": "integer", "default": 20},
                    "status": {"type": "string", "description": "Filter: pending|anchored|failed"},
                    "chain": {"type": "string"},
                    "tags": {"type": "string", "description": "Comma-separated tags to filter by"},
                },
                "required": [],
            },
        },
        {
            "name": "verify_bundle",
            "description": "Verify evidence bundle integrity and on-chain anchoring (metered).",
            "endpoint": {"method": "POST", "path": "/v1/x402/premium/verify-bundle"},
            "idempotency_supported": True,
            "x402_cost": pricing.get("/v1/x402/premium/verify-bundle", "0.001 USDC"),
            "parameters": {
                "type": "object",
                "properties": {
                    "bundle_url": {"type": "string"},
                    "bundle_hash": {"type": "string"},
                },
                "required": [],
            },
        },
        {
            "name": "get_ftso_feeds",
            "description": (
                "Get live FTSO v2 price feeds from Flare's on-chain oracle. "
                "Updated every ~90 seconds. Use for FX rate injection in ISO messages."
            ),
            "endpoint": {"method": "GET", "path": "/v1/flare/feeds"},
            "idempotency_supported": False,
            "x402_cost": None,
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
        {
            "name": "prepare_fdc_attestation",
            "description": (
                "Prepare a Flare Data Connector attestation request for an EVM or "
                "cross-chain transaction. Returns Merkle-proof-backed verification data."
            ),
            "endpoint": {"method": "POST", "path": "/v1/flare/fdc/prepare-attestation"},
            "idempotency_supported": False,
            "x402_cost": None,
            "parameters": {
                "type": "object",
                "properties": {
                    "tx_hash": {"type": "string"},
                    "chain": {"type": "string", "default": "flare"},
                    "required_confirmations": {"type": "integer", "default": 6},
                },
                "required": ["tx_hash"],
            },
        },
        {
            "name": "explain_flare",
            "description": (
                "Ask a natural language question about Flare protocol (FTSO, FDC, FAssets, "
                "Smart Accounts, governance). Powered by Flare AI Skills."
            ),
            "endpoint": {"method": "POST", "path": "/v1/flare/explain"},
            "idempotency_supported": False,
            "x402_cost": None,
            "parameters": {
                "type": "object",
                "properties": {
                    "question": {"type": "string"},
                    "context": {"type": "string"},
                },
                "required": ["question"],
            },
        },
        {
            "name": "register_webhook",
            "description": "Register a webhook URL to receive push events for receipt lifecycle changes.",
            "endpoint": {"method": "POST", "path": "/v1/webhooks"},
            "idempotency_supported": True,
            "x402_cost": None,
            "parameters": {
                "type": "object",
                "properties": {
                    "url": {"type": "string"},
                    "events": {
                        "type": "array",
                        "items": {"type": "string"},
                        "default": ["receipt.anchored", "receipt.failed"],
                        "description": "Topics: receipt.pending, receipt.anchored, receipt.failed, *",
                    },
                },
                "required": ["url"],
            },
        },
    ]
