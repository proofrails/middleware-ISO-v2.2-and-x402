from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field


class Status(str, Enum):
    pending = "pending"
    awaiting_anchor = "awaiting_anchor"  # tenant must anchor on-chain
    anchored = "anchored"
    failed = "failed"


class TipRecordRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    tip_tx_hash: str = Field(..., description="Blockchain transaction hash of the tip")
    chain: str = Field(..., description="Blockchain network (EVM chain name, e.g. 'flare', 'ethereum', 'polygon')")
    amount: Decimal = Field(..., description="Tip amount (use decimal string)")
    currency: str = Field(..., description='Currency code (PoC uses "FLR")')
    sender_wallet: str = Field(..., description="Sender wallet address (0x...)")
    receiver_wallet: str = Field(..., description="Receiver wallet address (0x...)")
    reference: str = Field(..., description="External reference, e.g., capella:tip:<id>")
    callback_url: Optional[str] = Field(
        None, description="Optional: callback URL to notify when anchoring completes"
    )
    # Agentic integration fields
    metadata: Optional[dict] = Field(
        None,
        description=(
            "Free-form key-value metadata attached to this receipt. "
            "Use for correlation IDs, task IDs, workflow context, etc."
        ),
    )
    tags: Optional[List[str]] = Field(
        None,
        description="Optional string tags for filtering receipts (e.g. ['batch-1', 'refund-eligible'])",
    )


class RecordTipResponse(BaseModel):
    receipt_id: str
    status: Status
    operation_id: str = Field(
        ...,
        description=(
            "Async operation ID for status polling via GET /v1/operations/{operation_id}. "
            "Equal to receipt_id — both can be used interchangeably."
        ),
    )


class ReceiptResponse(BaseModel):
    id: str
    status: Status
    bundle_hash: Optional[str] = None
    flare_txid: Optional[str] = None
    xml_url: Optional[str] = None
    bundle_url: Optional[str] = None
    created_at: datetime
    anchored_at: Optional[datetime] = None


class VerifyRequest(BaseModel):
    bundle_url: Optional[str] = Field(None, description="URL to evidence.zip")
    bundle_hash: Optional[str] = Field(None, description="0x-prefixed sha256 of evidence.zip")


class DebugAnchorRequest(BaseModel):
    bundle_hash: str = Field(..., description="0x-prefixed sha256 (32 bytes)")


class DebugAnchorResponse(BaseModel):
    flare_txid: str
    block_number: int


class VerifyResponse(BaseModel):
    matches_onchain: bool
    bundle_hash: Optional[str] = None
    flare_txid: Optional[str] = None
    anchored_at: Optional[datetime] = None
    # Optional VC hints for verify-by-CID or when available
    vc_present: Optional[bool] = None
    vc_url: Optional[str] = None
    arweave_txid: Optional[str] = None
    issuer: Optional[str] = None
    checksums: Optional[dict] = None
    errors: List[str] = Field(default_factory=list)


class ReceiptListItem(BaseModel):
    id: str
    status: Status
    amount: Decimal
    currency: str
    chain: str
    reference: str
    created_at: datetime
    anchored_at: Optional[datetime] = None
    tags: Optional[List[str]] = None
    metadata: Optional[dict] = None


class ReceiptsPage(BaseModel):
    items: List[ReceiptListItem]
    total: int
    page: int
    page_size: int
    # Cursor pagination fields (populated when cursor parameter is used)
    next_cursor: Optional[str] = Field(
        None,
        description=(
            "Opaque cursor for the next page. Pass as ?cursor= to retrieve the next "
            "batch. Null when there are no more results. Cursor-based pagination is "
            "preferred over page/page_size for agents traversing large or live datasets."
        ),
    )


class ReceiptStatusResponse(BaseModel):
    """Lightweight receipt status — for agents polling pipeline progress."""

    id: str
    status: str
    bundle_hash: Optional[str] = None
    flare_txid: Optional[str] = None
    anchored_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class SDKBuildRequest(BaseModel):
    lang: str = Field(..., description="ts | python")
    base_url: Optional[str] = Field(None, description="Override API base URL")
    auth: Optional[str] = Field("api_key", description="api_key | jwt")
    packaging: Optional[str] = Field(None, description="npm | pypi | none")
    families: Optional[List[str]] = Field(None, description="Optional message families to include in helpers")


class ProjectCreate(BaseModel):
    name: str = Field(..., description="Project name")


class ProjectInfo(BaseModel):
    id: str
    name: str
    owner_wallet: str
    created_at: datetime


class RegisterProjectRequest(BaseModel):
    """Self-register a project using a SIWE message/signature."""

    name: str = Field(..., description="Project name")
    message: str = Field(..., description="EIP-4361 SIWE message")
    signature: str = Field(..., description="EIP-191 signature")


class RegisterProjectResponse(BaseModel):
    project: ProjectInfo
    api_key: str = Field(..., description="API key (returned only once)")


class ProjectAnchoringChain(BaseModel):
    name: str = Field(..., description="Chain name, e.g., flare")
    contract: str = Field(..., description="EvidenceAnchor contract address")
    rpc_url: Optional[str] = Field(None, description="RPC URL override")
    explorer_base_url: Optional[str] = Field(None, description="Explorer base URL, e.g. https://flarescan.com")


DEFAULT_FLARE_CHAIN = ProjectAnchoringChain(
    name="flare",
    contract="0x0690d8cFb1897c12B2C0b34660edBDE4E20ff4d8",
    rpc_url=None,
    explorer_base_url="https://flarescan.com",
)


def _fallback_explorer_for_chain(chain_name: Optional[str]) -> Optional[str]:
    if not chain_name:
        return "https://flarescan.com"
    if str(chain_name).lower() == "flare":
        return "https://flarescan.com"
    return None


class ProjectAnchoringConfig(BaseModel):
    execution_mode: str = Field("platform", description="platform | tenant")
    chains: List[ProjectAnchoringChain] = Field(default_factory=list)


class ProjectConfig(BaseModel):
    anchoring: ProjectAnchoringConfig = ProjectAnchoringConfig()


class APIKeyCreate(BaseModel):
    label: str = Field(..., description="A human-readable label for the API key")


class APIKeyInfo(BaseModel):
    id: str
    label: str
    role: str = "project_admin"
    project_id: Optional[str] = None
    created_at: datetime
    revoked_at: Optional[datetime] = None


class VerifyCidRequest(BaseModel):
    cid: str = Field(..., description="Content ID or txid (ipfs/arweave)")
    store: Optional[str] = Field(None, description="ipfs | arweave (auto-detected if omitted)")
    receipt_id: Optional[str] = Field(None, description="Optional receipt id to check for vc.json presence")


class ISOArtifactResponse(BaseModel):
    type: str
    url: str
    sha256: Optional[str] = None
    created_at: datetime


class RefundRequest(BaseModel):
    original_receipt_id: str = Field(..., description="Receipt to refund/return")
    reason_code: Optional[str] = Field(None, description="Optional reason code")


class RefundResponse(BaseModel):
    refund_receipt_id: str
    status: Status


# Helper internal results for modules
@dataclass
class VerificationResult:
    bundle_hash: str
    errors: list[str]


@dataclass
class ChainMatch:
    matches: bool
    txid: Optional[str] = None
    anchored_at: Optional[datetime] = None


class CancelRequest(BaseModel):
    original_receipt_id: str = Field(..., description="Receipt to cancel (original pain.001)")
    reason_code: Optional[str] = Field(None, description="Optional ISO cancellation reason code (e.g., 'CUST')")


class CancelResponse(BaseModel):
    cancellation_id: str
    refund_receipt_id: str
    status: Status


class ConfirmAnchorRequest(BaseModel):
    receipt_id: str = Field(..., description="Receipt id to confirm")
    chain: Optional[str] = Field(None, description="Chain name (optional)")
    flare_txid: str = Field(..., description="Transaction hash of the anchoring tx")


class ConfirmAnchorResponse(BaseModel):
    receipt_id: str
    status: Status
    flare_txid: Optional[str] = None
    anchored_at: Optional[datetime] = None


class FIMessageRequest(BaseModel):
    reason_code: Optional[str] = Field(None, description="ISO reason code (e.g., 'CUST', 'TECH')")
    resolution_code: Optional[str] = Field(None, description="ISO resolution code (e.g., 'APPR', 'RJCT')")


class FIMessageResponse(BaseModel):
    message_id: str = Field(..., description="Generated message ID")
    type: str = Field(..., description="Message type (e.g., 'camt.056', 'pacs.009')")
    receipt_id: str = Field(..., description="Original receipt ID")
    url: str = Field(..., description="URL to download the generated XML")


# ── Agent schemas ─────────────────────────────────────────────────────────────

class AgentCreate(BaseModel):
    name: str
    wallet_address: str = Field(..., description="Agent's EVM payment wallet address")
    xmtp_address: Optional[str] = None
    pricing_rules: Optional[dict] = None
    project_id: Optional[str] = None


class AgentUpdate(BaseModel):
    name: Optional[str] = None
    wallet_address: Optional[str] = None
    xmtp_address: Optional[str] = None
    pricing_rules: Optional[dict] = None
    status: Optional[str] = None


class AgentResponse(BaseModel):
    id: str
    name: str
    wallet_address: str
    xmtp_address: Optional[str] = None
    pricing_rules: Optional[dict] = None
    status: str
    project_id: Optional[str] = None
    ai_mode: str
    created_at: datetime
    updated_at: Optional[datetime] = None


class AgentAIConfigUpdate(BaseModel):
    ai_mode: Optional[str] = Field(None, description="simple | shared | custom")
    ai_system_prompt: Optional[str] = None
    ai_provider: Optional[str] = Field(None, description="openai | anthropic | google | custom")
    ai_api_key: Optional[str] = Field(None, description="API key (write-only, stored encrypted)")
    ai_model: Optional[str] = None
    ai_endpoint: Optional[str] = None


class AgentAnchoringConfig(BaseModel):
    """Anchoring configuration for an agent. All fields are optional — pass only what you want to change."""
    auto_anchor_enabled: Optional[bool] = None
    anchor_on_payment: Optional[bool] = None
    anchor_wallet_address: Optional[str] = Field(None, description="EVM wallet address for on-chain txs")
    anchor_private_key: Optional[str] = Field(
        None,
        description="Private key for the anchor wallet (write-only, stored encrypted). "
                    "Prefer using the platform wallet via ANCHOR_PRIVATE_KEY env var instead.",
    )


class AgentAnchorDataRequest(BaseModel):
    data: dict = Field(..., description="Arbitrary JSON data to hash and optionally anchor")
    description: Optional[str] = Field(None, description="Human-readable description of this anchor")
    chain: Optional[str] = Field("flare", description="Chain to anchor on (default: flare)")
    submit_onchain: bool = Field(False, description="If true, immediately submit anchor tx on-chain")


class AgentAnchorDataResponse(BaseModel):
    id: str
    agent_id: str
    anchor_hash: str = Field(..., description="0x-prefixed SHA-256 of canonical JSON")
    chain: str
    status: str
    submit_onchain: bool
    description: Optional[str] = None
    created_at: Optional[datetime] = None


class AgentAnchorRequest(BaseModel):
    bundle_hash: str = Field(..., description="0x-prefixed 32-byte hash to anchor")
    receipt_id: Optional[str] = Field(None, description="Associate this anchor with a receipt ID")


# ── x402 premium schemas ──────────────────────────────────────────────────────

class StatementRequest(BaseModel):
    date: str = Field(..., description="Date in YYYY-MM-DD format")
    window: Optional[str] = Field(
        None,
        description="Time window for camt.052 intraday (e.g. '09:00-17:00'). "
                    "Omit or use '00:00-23:59' for a full-day camt.053.",
    )


class FXLookupRequest(BaseModel):
    base_ccy: str = Field("USD", description="Base currency code")
    quote_ccy: str = Field("FLR", description="Quote currency code")
    provider: str = Field("ftso", description="Price provider: ftso | coingecko | fallback")


class BulkVerifyRequest(BaseModel):
    bundle_urls: List[str] = Field(..., description="Up to 10 bundle URLs to verify")


class X402PaymentResponse(BaseModel):
    id: str
    tx_hash: str
    amount: str
    currency: str
    chain: str
    endpoint: str
    verified_at: datetime
    anchor_txid: Optional[str] = None
    anchor_status: Optional[str] = None
