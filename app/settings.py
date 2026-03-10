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

    # AI
    ai_provider: Optional[str] = Field(default=None, alias="AI_PROVIDER")
    openai_api_key: Optional[str] = Field(default=None, alias="OPENAI_API_KEY")
    ai_model: str = Field(default="gpt-4o-mini", alias="AI_MODEL")
    ai_temperature: float = Field(default=0.2, alias="AI_TEMPERATURE")
    ai_max_tokens: int = Field(default=512, alias="AI_MAX_TOKENS")

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
