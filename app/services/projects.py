from __future__ import annotations

import hashlib
import secrets

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app import models, schemas


def create_project_and_key(*, session: Session, name: str, owner_wallet: str) -> tuple[models.Project, str]:
    # Default project config
    proj_cfg = schemas.ProjectConfig().model_dump()
    proj = models.Project(name=name, owner_wallet=owner_wallet, config=proj_cfg)
    session.add(proj)
    session.commit()

    raw = secrets.token_urlsafe(48)
    h = hashlib.sha256(raw.encode()).hexdigest()
    key = models.APIKey(label=f"{name}:default", key_hash=h, project_id=proj.id, role="project_admin")
    session.add(key)
    session.commit()

    return proj, raw


def list_projects_for_principal(session: Session, principal) -> list[models.Project]:
    if principal.is_public:
        raise HTTPException(status_code=401, detail="Unauthorized")
    if principal.is_admin:
        return session.query(models.Project).all()
    if principal.project_id:
        return session.query(models.Project).filter(models.Project.id == principal.project_id).all()
    return []
