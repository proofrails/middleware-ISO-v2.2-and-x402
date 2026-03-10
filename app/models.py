from __future__ import annotations

import uuid

from sqlalchemy import (
    JSON,
    Column,
    DateTime,
    ForeignKey,
    Numeric,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.types import CHAR, TypeDecorator

from .db import Base


class GUID(TypeDecorator):
    """
    Platform-independent GUID/UUID type.

    Uses PostgreSQL UUID when available, otherwise stores as CHAR(36) for SQLite/others.
    """

    impl = CHAR
    cache_ok = True

    def load_dialect_impl(self, dialect):
        if dialect.name == "postgresql":
            return dialect.type_descriptor(PG_UUID(as_uuid=True))
        return dialect.type_descriptor(CHAR(36))

    def process_bind_param(self, value, dialect):
        if value is None:
            return value
        if dialect.name == "postgresql":
            if isinstance(value, uuid.UUID):
                return value
            return uuid.UUID(str(value))
        # store as string
        if isinstance(value, uuid.UUID):
            return str(value)
        return str(uuid.UUID(str(value)))

    def process_result_value(self, value, dialect):
        if value is None:
            return value
        if dialect.name == "postgresql":
            return value  # already UUID
        return uuid.UUID(value)


class Receipt(Base):
    __tablename__ = "receipts"

    id = Column(GUID, primary_key=True, default=uuid.uuid4, nullable=False)

    # Ownership (multi-tenant)
    project_id = Column(GUID, ForeignKey("projects.id"), nullable=True, index=True)

    reference = Column(String, nullable=False, unique=True)
    tip_tx_hash = Column(String, nullable=False)
    chain = Column(String, nullable=False)  # e.g. "flare"

    amount = Column(Numeric(38, 18), nullable=False)
    currency = Column(String, nullable=False)  # "FLR" for PoC

    sender_wallet = Column(String, nullable=False)
    receiver_wallet = Column(String, nullable=False)

    status = Column(String, nullable=False)  # pending/anchored/failed

    bundle_hash = Column(String, nullable=True)  # 0x-prefixed sha256 of zip
    flare_txid = Column(String, nullable=True)

    xml_path = Column(String, nullable=True)
    bundle_path = Column(String, nullable=True)
    # If this receipt represents a return/refund, reference the original receipt
    refund_of = Column(GUID, ForeignKey("receipts.id"), nullable=True)

    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    anchored_at = Column(DateTime(timezone=True), nullable=True)

    __table_args__ = (UniqueConstraint("chain", "tip_tx_hash", name="uq_chain_tip"),)

    def __repr__(self) -> str:  # pragma: no cover
        return f"<Receipt id={self.id} status={self.status} tip={self.tip_tx_hash}>"


class ISOArtifact(Base):
    __tablename__ = "iso_artifacts"

    id = Column(GUID, primary_key=True, default=uuid.uuid4, nullable=False)
    receipt_id = Column(GUID, ForeignKey("receipts.id"), nullable=False, index=True)
    type = Column(String, nullable=False)  # pain.001 | pain.002 | camt.054 | pacs.004 | remt.001
    path = Column(String, nullable=False)
    sha256 = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())


class ChainAnchor(Base):
    __tablename__ = "chain_anchors"

    id = Column(GUID, primary_key=True, default=uuid.uuid4, nullable=False)
    receipt_id = Column(GUID, ForeignKey("receipts.id"), nullable=False, index=True)
    chain = Column(String, nullable=False)
    txid = Column(String, nullable=False)
    anchored_at = Column(DateTime(timezone=True), nullable=True)


class OrgConfig(Base):
    __tablename__ = "org_config"

    id = Column(GUID, primary_key=True, default=uuid.uuid4, nullable=False)
    payload = Column(JSON, nullable=False)  # JSON payload with org/ledger/mapping/anchoring/evidence/fx/etc.
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=True)


class Project(Base):
    __tablename__ = "projects"

    id = Column(GUID, primary_key=True, default=uuid.uuid4, nullable=False)
    name = Column(String, nullable=False)
    owner_wallet = Column(String, nullable=False, index=True)

    # Project-level configuration overrides (JSON):
    # - anchoring.execution_mode: platform | tenant
    # - anchoring.chains: [{name, contract, rpc_url?}, ...]
    config = Column(JSON, nullable=True)

    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=True)


class APIKey(Base):
    __tablename__ = "api_keys"

    id = Column(GUID, primary_key=True, default=uuid.uuid4, nullable=False)

    # Ownership
    project_id = Column(GUID, ForeignKey("projects.id"), nullable=True, index=True)

    # Human-readable label
    label = Column(String, nullable=False)

    # Role: admin | project_admin | project
    role = Column(String, nullable=False, server_default="project_admin")

    # Stored as sha256(key)
    key_hash = Column(String, nullable=False, unique=True, index=True)

    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    revoked_at = Column(DateTime(timezone=True), nullable=True)


class LinkedWallet(Base):
    __tablename__ = "linked_wallets"

    id = Column(GUID, primary_key=True, default=uuid.uuid4, nullable=False)
    address = Column(String, nullable=False, unique=True, index=True)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())


class X402Payment(Base):
    """Track verified x402 payments from autonomous agents."""
    __tablename__ = "x402_payments"

    id = Column(GUID, primary_key=True, default=uuid.uuid4, nullable=False)
    tx_hash = Column(String, nullable=False, unique=True, index=True)
    amount = Column(Numeric(38, 18), nullable=False)
    currency = Column(String, nullable=False, server_default="USDC")
    chain = Column(String, nullable=False, server_default="base")
    recipient = Column(String, nullable=False)
    endpoint = Column(String, nullable=False)  # Which endpoint was accessed
    agent_id = Column(GUID, ForeignKey("agent_configs.id"), nullable=True, index=True)
    verified_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())


class AgentConfig(Base):
    """Configuration for autonomous XMTP/x402 agents."""
    __tablename__ = "agent_configs"

    id = Column(GUID, primary_key=True, default=uuid.uuid4, nullable=False)
    name = Column(String, nullable=False)
    wallet_address = Column(String, nullable=False, index=True)  # Agent's payment wallet
    xmtp_address = Column(String, nullable=True)  # XMTP identity (if different)
    
    # Pricing rules (JSON): {"verify": "0.001", "statement": "0.005", ...}
    pricing_rules = Column(JSON, nullable=True)
    
    # Status: active | paused | disabled
    status = Column(String, nullable=False, server_default="active")
    
    # Owner project
    project_id = Column(GUID, ForeignKey("projects.id"), nullable=True, index=True)
    
    # AI Configuration
    ai_mode = Column(String, nullable=False, server_default="simple")
    # Values: "simple" (no AI) | "shared" (use system AI) | "custom" (user's AI)
    
    ai_system_prompt = Column(String, nullable=True)
    # Custom system prompt for shared or custom AI mode
    
    ai_provider = Column(String, nullable=True)
    # For custom mode: "openai" | "anthropic" | "google" | "custom"
    
    ai_api_key_encrypted = Column(String, nullable=True)
    # Encrypted API key for custom AI mode
    
    ai_model = Column(String, nullable=True)
    # Model name: "gpt-4o-mini" | "claude-3-haiku" | etc
    
    ai_endpoint = Column(String, nullable=True)
    # Custom AI endpoint URL (for custom provider)
    
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=True)


class ProtectedEndpoint(Base):
    """Track which endpoints are payment-gated via x402."""
    __tablename__ = "protected_endpoints"

    id = Column(GUID, primary_key=True, default=uuid.uuid4, nullable=False)
    path = Column(String, nullable=False, unique=True)  # e.g., "/v1/x402/premium/verify"
    price = Column(Numeric(38, 18), nullable=False)  # Payment amount required
    currency = Column(String, nullable=False, server_default="USDC")
    recipient = Column(String, nullable=False)  # Who receives payment
    enabled = Column(String, nullable=False, server_default="true")  # true | false
    
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=True)


class AgentAnchor(Base):
    """Track anchoring transactions initiated by autonomous agents."""
    __tablename__ = "agent_anchors"

    id = Column(GUID, primary_key=True, default=uuid.uuid4, nullable=False)
    agent_id = Column(GUID, ForeignKey("agent_configs.id"), nullable=False, index=True)
    receipt_id = Column(GUID, ForeignKey("receipts.id"), nullable=True)
    bundle_hash = Column(String, nullable=False)
    anchor_txid = Column(String, nullable=True)
    chain = Column(String, nullable=False, server_default="flare")
    status = Column(String, nullable=False, server_default="pending")  # pending | confirmed | failed
    anchored_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    
    def __repr__(self) -> str:  # pragma: no cover
        return f"<AgentAnchor id={self.id} agent_id={self.agent_id} status={self.status}>"
