from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from . import models


# Pydantic models for OrgConfig API surface
class AssetDescriptor(BaseModel):
    symbol: str = Field(..., description="Asset ticker, e.g., FLR")
    decimals: int = Field(18, description="Decimals of the asset")
    contract_address: Optional[str] = Field(None, description="Optional address if tokenized")


class LedgerConfig(BaseModel):
    network: str = Field(..., description="e.g., flare")
    rpc_url: str = Field(..., description="RPC URL for the network")
    asset: AssetDescriptor


class AnchoringChain(BaseModel):
    name: str = Field(..., description="Chain name, e.g., flare")
    contract: str = Field(..., description="EvidenceAnchor contract address")
    rpc_url: Optional[str] = Field(None, description="RPC URL for this chain (falls back to ledger.rpc_url if absent)")
    explorer_base_url: Optional[str] = Field(None, description="Explorer base URL, e.g. https://flarescan.com")


class AnchoringConfig(BaseModel):
    chains: List[AnchoringChain] = Field(default_factory=list)
    lookback_blocks: int = 50_000
    signature_alg: str = "ed25519"


class MappingConfig(BaseModel):
    party_scheme: str = "WALLET"
    account_scheme: str = "WALLET_ACCOUNT"
    charge_bearer: str = "SLEV"
    purpose: Optional[str] = None
    category_purpose: Optional[str] = None
    use_agents: bool = False  # if True, populate BIC agents (future)
    structured_remittance: bool = False  # emit remt.001 alongside pain.001 when true
    # Optional party identifiers
    include_iban: bool = False
    include_bic: bool = False
    include_lei: bool = False
    # Defaults used if wallet mapping does not yield identifiers
    default_debtor_iban: Optional[str] = None
    default_creditor_iban: Optional[str] = None
    default_debtor_bic: Optional[str] = None
    default_creditor_bic: Optional[str] = None
    default_org_lei: Optional[str] = None


class EvidenceStore(BaseModel):
    mode: str = Field("local", description="local | ipfs | arweave")
    files_base: Optional[str] = Field(None, description="Prefix for serving artifacts")


class EvidenceConfig(BaseModel):
    include: List[str] = Field(
        default_factory=lambda: ["pain001.xml", "receipt.json", "tip.json", "manifest.json", "public_key.pem"]
    )
    sign_over: str = Field("zip_without_sig", description="Which content to sign over")
    store: EvidenceStore = EvidenceStore()


class FxPolicy(BaseModel):
    mode: str = Field("none", description="none | eqvt_amt | instd_amt_fiat")
    base_ccy: Optional[str] = Field(None, description="ISO 4217 code for fiat, e.g., EUR")
    provider: Optional[str] = Field(None, description="e.g., coingecko, chainlink")
    chainlink_feed: Optional[str] = Field(None, description="Chainlink aggregator address for quote/base")
    chainlink_rpc_url: Optional[str] = Field(
        None, description="Optional RPC URL for Chainlink feed (falls back to ledger.rpc_url)"
    )
    rounding: str = Field("bankers", description="bankers | floor | ceil")


class TxProofPolicy(BaseModel):
    min_confirmations: int = 0
    require_receipt: bool = False
    capture_block_ts: bool = False


class StatusConfig(BaseModel):
    emit_pain002: bool = True
    emit_pacs002: bool = False
    enable_cancellation: bool = True
    enable_returns: bool = True


class IntegrationConfig(BaseModel):
    openapi: bool = True
    webhook_retry: str = "exponential"
    webhook_timeout_ms: int = 15000


class SecurityConfig(BaseModel):
    auth: str = Field("api_key", description="api_key | jwt")
    rate_limit_per_minute: int = 100
    # Hosted vs self-hosted anchoring model:
    # - managed: keys held by platform (resolve via key_ref/secret store or env)
    # - self: tenant provides ANCHOR_PRIVATE_KEY in their environment
    anchor_mode: str = Field("managed", description="managed | self")
    key_ref: Optional[str] = Field(
        None, description="Opaque key reference (alias/ARN/secret id) for managed mode; no raw keys here"
    )


class ComplianceConfig(BaseModel):
    travel_rule_threshold: Optional[float] = None
    travel_rule_provider: Optional[str] = None
    sanctions_provider: Optional[str] = None
    travel_rule_enforce: bool = False
    sanctions_enforce: bool = False


class OrgSection(BaseModel):
    name: str = "Capella"
    jurisdiction: str = "SEPA"
    lei: Optional[str] = None
    default_message_families: List[str] = Field(default_factory=lambda: ["pain.001", "pain.002", "camt.054"])


class IDStrategyConfig(BaseModel):
    msg_id_strategy: str = Field("uuid", description="uuid | reference | composite")
    e2e_id_strategy: str = Field("reference", description="uuid | reference | composite")
    pmt_inf_id_strategy: str = Field("uuid", description="uuid | reference | composite")
    reqd_exctn_mode: str = Field("immediate", description="immediate | date")
    reqd_exctn_offset_days: int = 0
    timezone: str = "UTC"


class OrgConfigModel(BaseModel):
    org: OrgSection = OrgSection()
    ledger: LedgerConfig
    mapping: MappingConfig = MappingConfig()
    anchoring: AnchoringConfig = AnchoringConfig()
    evidence: EvidenceConfig = EvidenceConfig()
    fx_policy: FxPolicy = FxPolicy()
    tx_proof_policy: TxProofPolicy = TxProofPolicy()
    status: StatusConfig = StatusConfig()
    integration: IntegrationConfig = IntegrationConfig()
    security: SecurityConfig = SecurityConfig()
    id_strategy: IDStrategyConfig = IDStrategyConfig()
    compliance: ComplianceConfig = ComplianceConfig()


def get_config(session: Session) -> OrgConfigModel:
    row = session.query(models.OrgConfig).first()
    if not row:
        # Return a minimal default with placeholders
        default = OrgConfigModel(
            ledger=LedgerConfig(
                network="flare",
                rpc_url="https://flare-api.flare.network/ext/C/rpc",
                asset=AssetDescriptor(symbol="FLR", decimals=18),
            ),
            anchoring=AnchoringConfig(
                chains=[
                    AnchoringChain(
                        name="flare",
                        contract="0x0690d8cFb1897c12B2C0b34660edBDE4E20ff4d8",
                        rpc_url=None,
                        explorer_base_url="https://flarescan.com",
                    )
                ]
            ),
        )
        return default
    return OrgConfigModel.model_validate(row.payload)  # type: ignore


def save_config(session: Session, cfg: OrgConfigModel) -> OrgConfigModel:
    row = session.query(models.OrgConfig).first()
    if not row:
        row = models.OrgConfig(payload=cfg.model_dump())
        session.add(row)
    else:
        row.payload = cfg.model_dump()
    session.commit()
    return cfg
