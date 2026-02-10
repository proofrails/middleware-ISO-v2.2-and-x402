from __future__ import annotations

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException

from app import models, schemas
from app.api.deps import get_session
from app.auth import Principal, resolve_principal

router = APIRouter(tags=["iso-write"])

ARTIFACTS_DIR = os.getenv("ARTIFACTS_DIR", "artifacts")


def _write_status_json(rec: models.Receipt) -> None:
    """Write current receipt status to status.json file.
    
    This provides an up-to-date status file that gets updated after anchoring,
    while evidence.zip remains immutable with the original snapshot.
    """
    try:
        out_dir = Path(ARTIFACTS_DIR) / str(rec.id)
        out_dir.mkdir(parents=True, exist_ok=True)
        status_file = out_dir / "status.json"
        
        status_data = {
            "receipt_id": str(rec.id),
            "status": rec.status,
            "bundle_hash": rec.bundle_hash,
            "flare_txid": rec.flare_txid,
            "anchored_at": rec.anchored_at.isoformat() if rec.anchored_at else None,
            "created_at": rec.created_at.isoformat() if rec.created_at else None,
            "last_updated": datetime.utcnow().isoformat(),
        }
        
        status_file.write_text(
            json.dumps(status_data, indent=2, separators=(",", ": "), default=str)
        )
    except Exception:
        # Best-effort; don't fail the endpoint
        pass


def _require_same_project_or_admin(principal: Principal, rec: models.Receipt) -> None:
    if principal.is_admin:
        return
    if principal.is_public:
        raise HTTPException(status_code=401, detail="Unauthorized")
    if not principal.project_id or str(rec.project_id) != str(principal.project_id):
        raise HTTPException(status_code=403, detail="forbidden")


def _load_project_chain_config(session, rec: models.Receipt, *, chain_name: Optional[str]) -> dict:
    """Resolve a chain config dict from the receipt's project config.

    Expected project config shape:
      { anchoring: { chains: [{name, contract, rpc_url?, explorer_base_url?}, ...] } }
    """

    if not rec.project_id:
        raise HTTPException(status_code=400, detail="receipt_has_no_project")

    proj = session.get(models.Project, rec.project_id)
    cfg = (proj.config or {}) if proj else {}
    anch = cfg.get("anchoring") or {}
    chains = anch.get("chains") or []
    if not isinstance(chains, list) or not chains:
        raise HTTPException(status_code=400, detail="project_missing_anchoring_chains")

    # normalize
    norm: list[dict] = [c for c in chains if isinstance(c, dict) and c.get("contract")]
    if not norm:
        raise HTTPException(status_code=400, detail="project_missing_anchoring_chains")

    if chain_name:
        for c in norm:
            if str(c.get("name") or "").lower() == str(chain_name).lower():
                return c
        raise HTTPException(status_code=400, detail="unknown_chain")

    # If only one chain is configured we can infer it.
    if len(norm) == 1:
        return norm[0]

    raise HTTPException(status_code=400, detail="chain_required")


@router.post("/v1/iso/confirm-anchor", response_model=schemas.ConfirmAnchorResponse)
def confirm_anchor(
    req: schemas.ConfirmAnchorRequest, session=Depends(get_session), principal: Principal = Depends(resolve_principal)
):
    rec: models.Receipt | None = session.get(models.Receipt, req.receipt_id)
    if not rec:
        raise HTTPException(status_code=404, detail="Receipt not found")

    _require_same_project_or_admin(principal, rec)

    # Only allowed transition: awaiting_anchor -> anchored
    if rec.status not in {"awaiting_anchor", "pending"}:
        raise HTTPException(status_code=409, detail="invalid_status_transition")

    # Receipt must have bundle hash for validation.
    if not rec.bundle_hash:
        raise HTTPException(status_code=409, detail="missing_bundle_hash")

    # Resolve chain config from project settings.
    chain_cfg = _load_project_chain_config(session, rec, chain_name=req.chain)
    chain_name = str(chain_cfg.get("name") or req.chain or rec.chain or "unknown")
    rpc_url = chain_cfg.get("rpc_url")
    contract_addr = chain_cfg.get("contract")

    # Validate tx really anchored this receipt's bundle hash on the configured contract.
    try:
        from app import anchor

        ok, _blk, anchored_at_chain = anchor.verify_anchor_tx(
            txid=req.flare_txid,
            expected_bundle_hash_hex=str(rec.bundle_hash),
            rpc_url=rpc_url,
            contract_addr=str(contract_addr) if contract_addr else None,
        )
        if not ok:
            raise HTTPException(status_code=400, detail="tx_does_not_match_bundle_hash")
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(status_code=503, detail="anchor_lookup_unavailable")

    # Upsert chain anchor row (idempotent for repeated confirms)
    existing = (
        session.query(models.ChainAnchor)
        .filter(models.ChainAnchor.receipt_id == str(rec.id), models.ChainAnchor.chain == chain_name)
        .one_or_none()
    )
    now = datetime.utcnow()
    if existing:
        existing.txid = req.flare_txid
        existing.anchored_at = anchored_at_chain or now
    else:
        session.add(
            models.ChainAnchor(
                receipt_id=str(rec.id),
                chain=str(chain_name),
                txid=req.flare_txid,
                anchored_at=anchored_at_chain or now,
            )
        )

    # Convenience fields: keep first tx in receipt.flare_txid.
    if not rec.flare_txid:
        rec.flare_txid = req.flare_txid

    # Determine whether all configured chains have been confirmed.
    proj = session.get(models.Project, rec.project_id)
    proj_cfg = (proj.config or {}) if proj else {}
    proj_anch = proj_cfg.get("anchoring") or {}
    proj_chains = proj_anch.get("chains") or []
    expected_chain_names = {
        str(c.get("name") or "").lower()
        for c in proj_chains
        if isinstance(c, dict) and c.get("contract") and c.get("name")
    }
    # If chains have no names (legacy), treat as single-chain.
    if not expected_chain_names:
        expected_chain_names = {str(chain_name).lower()}

    confirmed = session.query(models.ChainAnchor).filter(models.ChainAnchor.receipt_id == str(rec.id)).all()
    confirmed_names = {str(r.chain).lower() for r in confirmed}

    if expected_chain_names.issubset(confirmed_names):
        rec.status = "anchored"
        rec.anchored_at = anchored_at_chain or now
    else:
        # still awaiting other chains
        rec.status = "awaiting_anchor"

    session.commit()
    
    # Write current status to status.json
    _write_status_json(rec)

    return schemas.ConfirmAnchorResponse(
        receipt_id=str(rec.id),
        status=schemas.Status(rec.status),
        flare_txid=rec.flare_txid,
        anchored_at=rec.anchored_at,
    )
