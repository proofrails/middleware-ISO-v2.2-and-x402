from __future__ import annotations

from functools import lru_cache
from typing import List, Optional

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings (env-backed).

    Notes
    - We keep a single Settings object as the source of truth for env parsing.
    - Local/dev: sensible defaults.
    - Prod: set `APP_ENV=prod` to enable stricter validation.
    """

    model_config = SettingsConfigDict(
        env_file=(".env", ".env.production"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Environment
    app_env: str = Field(default="dev", alias="APP_ENV")  # dev | prod

    # Core URLs / paths
    public_base_url: Optional[str] = Field(default=None, alias="PUBLIC_BASE_URL")
    artifacts_dir: str = Field(default="artifacts", alias="ARTIFACTS_DIR")

    # Database
    database_url: Optional[str] = Field(default=None, alias="DATABASE_URL")
    sql_echo: bool = Field(default=False, alias="SQL_ECHO")

    # Boot behavior
    auto_create_db: bool = Field(default=True, alias="AUTO_CREATE_DB")

    # CORS
    allow_origins: str = Field(default="http://localhost:3000,http://127.0.0.1:3000", alias="ALLOW_ORIGINS")

    # Queue
    redis_url: str = Field(default="redis://localhost:6379/0", alias="REDIS_URL")

    # Auth
    api_keys: Optional[str] = Field(default=None, alias="API_KEYS")

    # Anchoring
    flare_rpc_url: str = Field(default="https://flare-api.flare.network/ext/C/rpc", alias="FLARE_RPC_URL")
    anchor_contract_addr: Optional[str] = Field(
        default="0x0690d8cFb1897c12B2C0b34660edBDE4E20ff4d8",
        alias="ANCHOR_CONTRACT_ADDR",
        description="Default EvidenceAnchor contract on Flare mainnet (override via env)",
    )
    anchor_private_key: Optional[str] = Field(default=None, alias="ANCHOR_PRIVATE_KEY")
    anchor_abi_path: str = Field(default="contracts/EvidenceAnchor.abi.json", alias="ANCHOR_ABI_PATH")
    anchor_lookback_blocks: int = Field(default=50_000, alias="ANCHOR_LOOKBACK_BLOCKS")

    # Demo
    demo_mode: bool = Field(default=False, alias="DEMO_MODE")
    demo_auto_produce: bool = Field(default=False, alias="DEMO_AUTO_PRODUCE")

    # AI
    ai_provider: Optional[str] = Field(default=None, alias="AI_PROVIDER")
    openai_api_key: Optional[str] = Field(default=None, alias="OPENAI_API_KEY")
    ai_model: str = Field(default="gpt-4o-mini", alias="AI_MODEL")
    ai_temperature: float = Field(default=0.2, alias="AI_TEMPERATURE")
    ai_max_tokens: int = Field(default=512, alias="AI_MAX_TOKENS")

    # Flare FTSO v2 — on-chain price oracle
    ftso_enabled: bool = Field(default=True, alias="FTSO_ENABLED")
    ftso_cache_ttl: int = Field(default=90, alias="FTSO_CACHE_TTL")
    ftso_registry_address: str = Field(
        default="0xaD67FE66660Fb8dFE9d6b1b4240d8650e30F6019",
        alias="FTSO_REGISTRY_ADDRESS",
    )

    # x402 — FLR native payment support
    x402_flare_rpc_url: str = Field(
        default="https://flare-api.flare.network/ext/C/rpc",
        alias="X402_FLARE_RPC_URL",
    )
    x402_flr_recipient: Optional[str] = Field(default=None, alias="X402_FLR_RECIPIENT")

    # Proactive monitor
    monitor_enabled: bool = Field(default=False, alias="MONITOR_ENABLED")
    monitor_interval_seconds: int = Field(default=60, alias="MONITOR_INTERVAL_SECONDS")
    monitor_stale_anchor_minutes: int = Field(default=10, alias="MONITOR_STALE_ANCHOR_MINUTES")
    monitor_wallet_watch_enabled: bool = Field(default=False, alias="MONITOR_WALLET_WATCH_ENABLED")
    monitor_batch_reports_enabled: bool = Field(default=False, alias="MONITOR_BATCH_REPORTS_ENABLED")

    # Agentic integration — rate limiting
    rate_limit_enabled: bool = Field(default=True, alias="RATE_LIMIT_ENABLED")

    # Agentic integration — idempotency
    idempotency_enabled: bool = Field(default=True, alias="IDEMPOTENCY_ENABLED")

    # Flare Data Connector (FDC) — for attestation-based tx verification
    fdc_verifier_url: str = Field(
        default="https://fdc-verifiers-testnet.aflabs.net",
        alias="FDC_VERIFIER_URL",
        description="FDC verifier API base URL",
    )
    fdc_da_layer_url: str = Field(
        default="https://da-layer-testnet.aflabs.net",
        alias="FDC_DA_LAYER_URL",
        description="FDC DA layer base URL for Merkle proof retrieval",
    )
    fdc_api_key: Optional[str] = Field(
        default=None,
        alias="FDC_API_KEY",
        description="X-apikey for FDC verifier API (use 00000000-0000-0000-0000-000000000000 for testnet)",
    )

    @property
    def allow_origins_list(self) -> List[str]:
        return [o.strip() for o in self.allow_origins.split(",") if o.strip()]

    @property
    def effective_database_url(self) -> str:
        # Prefer Postgres if provided; fallback to local sqlite for dev.
        if self.database_url:
            return self.database_url
        return "sqlite:///./dev.db"


@lru_cache
def get_settings() -> Settings:
    return Settings()
