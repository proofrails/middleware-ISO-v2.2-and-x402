"""Monitor control & observability endpoints.

These endpoints expose the state of the proactive monitoring loop and let
operators register wallets for automatic receipt creation.

Endpoints
---------
``GET  /v1/monitor/status``          – Monitor health and counters
``GET  /v1/monitor/ftso``            – Latest FTSO v2 price snapshot
``POST /v1/monitor/wallets``         – Register a wallet to watch
``GET  /v1/monitor/wallets``         – List all watched wallets
``DELETE /v1/monitor/wallets/{addr}``– Stop watching a wallet
"""
from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app import models
from app.api.deps import get_session
from app.auth.api_key_auth import resolve_principal
from app.auth.principal import Principal

router = APIRouter(tags=["monitor"])


# ── Schemas ───────────────────────────────────────────────────────────────────

class WatchWalletRequest(BaseModel):
    address: str
    label: Optional[str] = None
    project_id: Optional[str] = None


class WatchedWalletResponse(BaseModel):
    id: str
    address: str
    label: Optional[str]
    enabled: str
    last_checked_block: Optional[str]
    created_at: str


# ── Routes ────────────────────────────────────────────────────────────────────

@router.get("/v1/monitor/status")
def get_monitor_status(principal: Principal = Depends(resolve_principal)):
    """Return the monitoring service status and counters.

    Includes cycle count, stale anchor recovery stats, wallet watch stats,
    and the most recent FTSO price snapshot.
    Requires authentication.
    """
    if principal.is_public:
        raise HTTPException(401, "auth_required")
    from app.monitor import get_monitor
    mon = get_monitor()
    return {
        "running": mon.is_running(),
        **mon.status.to_dict(),
    }


@router.get("/v1/monitor/ftso")
def get_ftso_snapshot(feed: Optional[str] = None):
    """Return the latest FTSO v2 price snapshot from the monitor cache.

    Optionally filter to a single ``feed`` symbol (e.g. ``?feed=FLR/USD``).
    This endpoint is public — no auth required.

    The snapshot is refreshed every ``MONITOR_INTERVAL_SECONDS`` (default 60 s).
    For a fresh on-chain read use the ``/v1/x402/premium/fx-lookup`` endpoint with
    ``provider=ftso`` and pay the USDC or FLR fee.
    """
    from app.monitor import get_monitor
    rates = get_monitor().status.last_ftso_rates
    if feed:
        sym = feed.upper()
        if sym not in rates:
            raise HTTPException(404, f"feed_not_found: {sym}")
        return {sym: rates[sym]}
    return rates


@router.post("/v1/monitor/wallets", response_model=WatchedWalletResponse, status_code=201)
def watch_wallet(
    payload: WatchWalletRequest,
    session: Session = Depends(get_session),
    principal: Principal = Depends(resolve_principal),
):
    """Register a wallet address for proactive monitoring on Flare.

    Once registered the monitor will poll Flare C-Chain every cycle for new
    incoming FLR transfers and automatically create ISO receipts.

    Requires authentication.  Admins may specify ``project_id``; project-scoped
    keys automatically scope to their own project.
    """
    if principal.is_public:
        raise HTTPException(401, "auth_required")

    addr = payload.address.lower().strip()
    if not addr.startswith("0x") or len(addr) != 42:
        raise HTTPException(400, "invalid_address")

    existing = session.query(models.WatchedWallet).filter_by(address=addr).one_or_none()
    if existing:
        existing.enabled = "true"
        existing.label = payload.label or existing.label
        existing.updated_at = datetime.utcnow()
        session.commit()
        session.refresh(existing)
        return _wallet_response(existing)

    project_id = None
    if principal.is_admin and payload.project_id:
        project_id = payload.project_id
    elif not principal.is_admin:
        project_id = str(principal.project_id) if principal.project_id else None

    wallet = models.WatchedWallet(
        address=addr,
        label=payload.label,
        project_id=project_id,
        enabled="true",
    )
    session.add(wallet)
    session.commit()
    session.refresh(wallet)
    return _wallet_response(wallet)


@router.get("/v1/monitor/wallets")
def list_watched_wallets(
    session: Session = Depends(get_session),
    principal: Principal = Depends(resolve_principal),
):
    """List all watched wallet addresses.

    Admins see all wallets; project keys see only their project's wallets.
    Requires authentication.
    """
    if principal.is_public:
        raise HTTPException(401, "auth_required")

    q = session.query(models.WatchedWallet)
    if not principal.is_admin and principal.project_id:
        q = q.filter(models.WatchedWallet.project_id == str(principal.project_id))
    wallets = q.order_by(models.WatchedWallet.created_at.desc()).all()
    return [_wallet_response(w) for w in wallets]


@router.delete("/v1/monitor/wallets/{address}", status_code=204)
def unwatch_wallet(
    address: str,
    session: Session = Depends(get_session),
    principal: Principal = Depends(resolve_principal),
):
    """Stop monitoring a wallet address.  Sets ``enabled=false`` (soft delete)."""
    if principal.is_public:
        raise HTTPException(401, "auth_required")
    addr = address.lower().strip()
    wallet = session.query(models.WatchedWallet).filter_by(address=addr).one_or_none()
    if not wallet:
        raise HTTPException(404, "wallet_not_found")
    wallet.enabled = "false"
    wallet.updated_at = datetime.utcnow()
    session.commit()


# ── Helpers ───────────────────────────────────────────────────────────────────

def _wallet_response(w: models.WatchedWallet) -> dict:
    return {
        "id": str(w.id),
        "address": w.address,
        "label": w.label,
        "enabled": w.enabled,
        "last_checked_block": w.last_checked_block,
        "created_at": w.created_at.isoformat() if w.created_at else None,
    }
