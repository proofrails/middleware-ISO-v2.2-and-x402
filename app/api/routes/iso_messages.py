from __future__ import annotations

from pathlib import Path
from typing import List, Optional

from fastapi import APIRouter, Depends

from app import models, schemas
from app.api.deps import get_session

router = APIRouter(tags=["iso"])


@router.get("/v1/iso/messages/{rid}", response_model=List[schemas.ISOArtifactResponse])
def list_iso_messages(rid: str, type: Optional[str] = None, session=Depends(get_session)):
    arts = session.query(models.ISOArtifact).filter(models.ISOArtifact.receipt_id == rid).all()
    out: List[schemas.ISOArtifactResponse] = []
    for a in arts:
        if type and a.type != type:
            continue
        name = Path(a.path).name if a.path else ""
        if name:
            out.append(
                schemas.ISOArtifactResponse(
                    type=a.type, url=f"/files/{rid}/{name}", sha256=a.sha256, created_at=a.created_at
                )
            )
    return out
