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
        None, description="Optional: Capella callback URL to notify when anchoring completes"
    )


class RecordTipResponse(BaseModel):
    receipt_id: str
    status: Status


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


class ReceiptsPage(BaseModel):
    items: List[ReceiptListItem]
    total: int
    page: int
    page_size: int


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
