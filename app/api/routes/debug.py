from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from app import schemas
from app.auth import Principal, resolve_principal

router = APIRouter(tags=["debug"])


@router.post("/v1/debug/anchor", response_model=schemas.DebugAnchorResponse)
def debug_anchor(req: schemas.DebugAnchorRequest, principal: Principal = Depends(resolve_principal)):
    if principal.is_public:
        raise HTTPException(status_code=401, detail="Unauthorized")
    try:
        from app import anchor

        txid, block_number = anchor.anchor_bundle(req.bundle_hash)
        return schemas.DebugAnchorResponse(flare_txid=txid, block_number=block_number)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"anchor_failed: {e}")
