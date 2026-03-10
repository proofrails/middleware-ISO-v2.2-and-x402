from __future__ import annotations

from fastapi import APIRouter, Depends

from app import models
from app.api.deps import get_session

router = APIRouter(tags=["anchors"])


@router.get("/v1/anchors/{rid}")
def get_anchors(rid: str, session=Depends(get_session)):
    rows = session.query(models.ChainAnchor).filter(models.ChainAnchor.receipt_id == rid).all()
    return [
        {"chain": r.chain, "txid": r.txid, "anchored_at": r.anchored_at.isoformat() if r.anchored_at else None}
        for r in rows
    ]
