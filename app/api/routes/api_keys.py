from __future__ import annotations

import hashlib
import secrets
from typing import List

from fastapi import APIRouter, Depends, HTTPException

from app import models, schemas
from app.api.deps import get_session
from app.auth import Principal, resolve_principal

router = APIRouter(tags=["api-keys"])


@router.post("/v1/auth/api-keys", response_model=schemas.APIKeyInfo)
def create_api_key(
    req: schemas.APIKeyCreate, session=Depends(get_session), principal: Principal = Depends(resolve_principal)
):
    if principal.is_public:
        raise HTTPException(status_code=401, detail="Unauthorized")

    raw = secrets.token_urlsafe(48)
    h = hashlib.sha256(raw.encode()).hexdigest()

    role = "project" if principal.role in {"project_admin", "project"} else principal.role
    row = models.APIKey(label=req.label, key_hash=h, project_id=principal.project_id, role=role)
    session.add(row)
    session.commit()

    from fastapi.responses import JSONResponse

    resp = JSONResponse(
        content={
            "id": str(row.id),
            "label": row.label,
            "role": getattr(row, "role", "project"),
            "project_id": str(getattr(row, "project_id", None)) if getattr(row, "project_id", None) else None,
            "created_at": row.created_at,
            "revoked_at": row.revoked_at,
        }
    )
    resp.headers["X-API-Key"] = raw
    return resp


@router.get("/v1/auth/api-keys", response_model=List[schemas.APIKeyInfo])
def list_api_keys(session=Depends(get_session), principal: Principal = Depends(resolve_principal)):
    if principal.is_public:
        raise HTTPException(status_code=401, detail="Unauthorized")

    q = session.query(models.APIKey)
    if not principal.is_admin:
        q = q.filter(models.APIKey.project_id == principal.project_id)

    rows = q.all()
    return [
        {
            "id": str(r.id),
            "label": r.label,
            "role": getattr(r, "role", "project"),
            "project_id": str(getattr(r, "project_id", None)) if getattr(r, "project_id", None) else None,
            "created_at": r.created_at,
            "revoked_at": r.revoked_at,
        }
        for r in rows
    ]


@router.delete("/v1/auth/api-keys/{id}")
def revoke_api_key(id: str, session=Depends(get_session), principal: Principal = Depends(resolve_principal)):
    if principal.is_public:
        raise HTTPException(status_code=401, detail="Unauthorized")

    row = session.query(models.APIKey).get(id)
    if not row:
        raise HTTPException(status_code=404, detail="not_found")

    if not principal.is_admin and str(row.project_id) != str(principal.project_id):
        raise HTTPException(status_code=403, detail="forbidden")

    if row.revoked_at is None:
        from datetime import datetime

        row.revoked_at = datetime.utcnow()
        session.commit()
    return {"status": "ok", "id": id, "revoked_at": row.revoked_at}
