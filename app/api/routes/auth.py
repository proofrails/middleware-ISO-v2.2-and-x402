from __future__ import annotations

from datetime import datetime
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Request

from app import models
from app.api.deps import get_session
from app.auth import Principal, resolve_principal
from app.auth import siwe as siwe_mod

router = APIRouter(tags=["auth"])

_NONCES: dict[str, datetime] = {}


@router.get("/v1/auth/nonce")
def siwe_nonce(request: Request):
    nid = str(uuid4())
    _NONCES[nid] = datetime.utcnow()
    return {"nonce": nid, "domain": siwe_mod.expected_domain(request)}


@router.post("/v1/auth/siwe-verify")
def siwe_verify(payload: dict, request: Request, session=Depends(get_session)):
    """Verify SIWE.

    Backwards compatible with legacy payload {address, nonce, signature}.
    """

    message = payload.get("message")
    signature = payload.get("signature")
    if isinstance(message, str) and isinstance(signature, str):
        expected = siwe_mod.expected_domain(request)
        return siwe_mod.verify_siwe_message(message, signature, expected=expected, nonces=_NONCES, session=session)

    addr = payload.get("address")
    nonce = payload.get("nonce")
    sig = payload.get("signature")
    if isinstance(addr, str) and isinstance(nonce, str) and isinstance(sig, str):
        return siwe_mod.legacy_verify(addr, nonce, sig, nonces=_NONCES, session=session)

    raise HTTPException(status_code=400, detail="invalid_payload")


@router.get("/v1/auth/linked-wallets")
def list_linked_wallets(session=Depends(get_session), principal: Principal = Depends(resolve_principal)):
    if principal.is_public:
        raise HTTPException(status_code=401, detail="Unauthorized")
    rows = session.query(models.LinkedWallet).all()
    return [{"address": r.address, "created_at": r.created_at} for r in rows]


@router.delete("/v1/auth/linked-wallets/{address}")
def delete_linked_wallet(address: str, session=Depends(get_session), principal: Principal = Depends(resolve_principal)):
    if principal.is_public:
        raise HTTPException(status_code=401, detail="Unauthorized")
    row = session.query(models.LinkedWallet).filter(models.LinkedWallet.address == address).first()
    if not row:
        raise HTTPException(status_code=404, detail="not_found")
    session.delete(row)
    session.commit()
    return {"status": "ok", "address": address}


@router.get("/v1/auth/me")
def get_me(principal: Principal = Depends(resolve_principal)):
    """Return current principal info (role, project_id, is_admin) for UX purposes."""
    if principal.is_public:
        raise HTTPException(status_code=401, detail="Unauthorized")
    
    return {
        "role": principal.role,
        "project_id": str(principal.project_id) if principal.project_id else None,
        "is_admin": principal.is_admin,
    }


@router.post("/v1/auth/siwe-mint-key")
def siwe_mint_key(payload: dict, request: Request, session=Depends(get_session)):
    """Mint a new API key for an existing project using SIWE (wallet signature).
    
    Useful for key rotation when user lost their current key but still has wallet access.
    """
    message = payload.get("message")
    signature = payload.get("signature")
    label = payload.get("label") or "siwe-rotated-key"
    
    if not isinstance(message, str) or not isinstance(signature, str):
        raise HTTPException(status_code=400, detail="invalid_payload")
    
    expected = siwe_mod.expected_domain(request)
    res = siwe_mod.verify_siwe_message(message, signature, expected=expected, nonces=_NONCES, session=session)
    
    if not res.get("linked"):
        raise HTTPException(status_code=401, detail="siwe_verification_failed")
    
    wallet_address = str(res.get("address"))
    
    # Find project owned by this wallet
    project = session.query(models.Project).filter(models.Project.owner_wallet == wallet_address).first()
    if not project:
        raise HTTPException(status_code=404, detail="no_project_found_for_wallet")
    
    # Create new API key
    import hashlib
    import secrets
    
    raw = secrets.token_urlsafe(48)
    h = hashlib.sha256(raw.encode()).hexdigest()
    
    key = models.APIKey(
        label=label,
        key_hash=h,
        project_id=project.id,
        role="project_admin"
    )
    session.add(key)
    session.commit()
    
    from fastapi.responses import JSONResponse
    
    resp = JSONResponse(content={
        "id": str(key.id),
        "label": key.label,
        "role": key.role,
        "project_id": str(key.project_id),
        "created_at": key.created_at.isoformat() if key.created_at else None,
    })
    resp.headers["X-API-Key"] = raw
    return resp
