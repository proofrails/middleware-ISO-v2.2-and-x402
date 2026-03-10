from __future__ import annotations

import os
import pathlib
import sys

import uvicorn

# Ensure project root is on sys.path so 'app' package is importable when running from scripts/
ROOT = pathlib.Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# Ensure required runtime env for local testing
os.environ.setdefault("ALLOW_ORIGINS", "http://localhost:3002,http://127.0.0.1:3002")
os.environ.setdefault("ARTIFACTS_DIR", "artifacts")
os.environ.setdefault("FLARE_RPC_URL", "https://flare-api.flare.network/ext/C/rpc")
# Fresh mainnet EvidenceAnchor (from DEPLOYMENT_PROD)
os.environ.setdefault("ANCHOR_CONTRACT_ADDR", "0x0690d8cFb1897c12B2C0b34660edBDE4E20ff4d8")
# Do NOT set a default private key; read from environment only
if not os.environ.get("ANCHOR_PRIVATE_KEY"):
    print("WARN: ANCHOR_PRIVATE_KEY not set; signing/anchoring will be disabled in this local session.")

# Local dev DB defaults to SQLite: dev.db (no Postgres required)
# DATABASE_URL may be set externally to override.

if __name__ == "__main__":
    # Make sure artifacts/ai_sessions exists
    try:
        os.makedirs(os.path.join(os.environ["ARTIFACTS_DIR"], "ai_sessions"), exist_ok=True)
    except Exception:
        pass
    # Run API on 127.0.0.1:8003 to avoid port contention
    uvicorn.run("app.main:app", host="127.0.0.1", port=8003, log_level="info")
