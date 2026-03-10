from __future__ import annotations

import os
from typing import Optional

from fastapi import HTTPException, Request

from app import db, models

from .principal import Principal


def resolve_principal(request: Request) -> Principal:
    """Resolve Principal from X-API-Key.

    Behavior:
    - API_KEYS env (comma separated) => global admin keys.
    - DB keys => project-scoped.
    - If any keys exist and an invalid key is provided => 401.
    - If keys exist but no key provided => Principal(public).
    - If no keys exist at all => Principal(public) (open mode).

    NOTE: Write endpoints should explicitly forbid public principals.
    """

    token = request.headers.get("X-API-Key")

    # 1) Env keys are global admin
    env_keys = os.getenv("API_KEYS")
    allowed = {k.strip() for k in env_keys.split(",") if k.strip()} if env_keys else set()
    if token and allowed and token in allowed:
        return Principal(role="admin")

    # 2) DB-backed keys
    if token:
        try:
            import hashlib

            h = hashlib.sha256(token.encode()).hexdigest()
            s = db.SessionLocal()
            try:
                row = (
                    s.query(models.APIKey)
                    .filter(models.APIKey.key_hash == h, models.APIKey.revoked_at.is_(None))
                    .first()
                )
                if row:
                    role = getattr(row, "role", "project") or "project"
                    project_id: Optional[str] = (
                        str(getattr(row, "project_id", None)) if getattr(row, "project_id", None) else None
                    )
                    return Principal(role=role, project_id=project_id, api_key_id=str(row.id))
            finally:
                s.close()
        except Exception:
            pass

    # 3) If keys exist, invalid token => 401, no token => public
    have_env = bool(allowed)
    have_db = False
    try:
        s2 = db.SessionLocal()
        try:
            have_db = s2.query(models.APIKey).filter(models.APIKey.revoked_at.is_(None)).count() > 0
        finally:
            s2.close()
    except Exception:
        have_db = False

    if have_env or have_db:
        if token:
            raise HTTPException(status_code=401, detail="Unauthorized")
        return Principal(role="public")

    # open mode
    return Principal(role="public")
