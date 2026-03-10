from __future__ import annotations

from typing import List

from fastapi import APIRouter, Depends, HTTPException, Request

from app import models, schemas
from app.api.deps import get_session
from app.auth import Principal, resolve_principal
from app.auth import siwe as siwe_mod
from app.services import projects as projects_svc

# share nonces with auth router by importing it
from .auth import _NONCES  # noqa: F401

router = APIRouter(tags=["projects"])


@router.post("/v1/projects/register", response_model=schemas.RegisterProjectResponse)
def register_project(req: schemas.RegisterProjectRequest, request: Request, session=Depends(get_session)):
    # verify SIWE
    expected = siwe_mod.expected_domain(request)
    res = siwe_mod.verify_siwe_message(req.message, req.signature, expected=expected, nonces=_NONCES, session=session)
    if not res.get("linked"):
        raise HTTPException(status_code=401, detail="siwe_verification_failed")

    proj, api_key = projects_svc.create_project_and_key(
        session=session, name=req.name, owner_wallet=str(res.get("address"))
    )

    return schemas.RegisterProjectResponse(
        project=schemas.ProjectInfo(
            id=str(proj.id), name=proj.name, owner_wallet=proj.owner_wallet, created_at=proj.created_at
        ),
        api_key=api_key,
    )


@router.get("/v1/projects", response_model=List[schemas.ProjectInfo])
def list_projects(session=Depends(get_session), principal: Principal = Depends(resolve_principal)):
    rows = projects_svc.list_projects_for_principal(session, principal)
    return [
        schemas.ProjectInfo(id=str(p.id), name=p.name, owner_wallet=p.owner_wallet, created_at=p.created_at)
        for p in rows
    ]


def _require_project_access(principal: Principal, project_id: str) -> None:
    if principal.is_public:
        raise HTTPException(status_code=401, detail="Unauthorized")
    if principal.is_admin:
        return
    if not principal.project_id or str(principal.project_id) != str(project_id):
        raise HTTPException(status_code=403, detail="forbidden")


def _require_project_admin(principal: Principal, project_id: str) -> None:
    _require_project_access(principal, project_id)
    if principal.is_admin:
        return
    if principal.role != "project_admin":
        raise HTTPException(status_code=403, detail="forbidden_requires_project_admin")


@router.get("/v1/projects/{project_id}/config", response_model=schemas.ProjectConfig)
def get_project_config(
    project_id: str, session=Depends(get_session), principal: Principal = Depends(resolve_principal)
):
    """Return project-level config (anchoring execution mode + chains).

    This is separate from org config (/v1/config).
    """

    _require_project_access(principal, project_id)

    row = session.get(models.Project, project_id)
    if not row:
        raise HTTPException(status_code=404, detail="not_found")

    try:
        cfg = row.config or {}
        return schemas.ProjectConfig(**cfg)
    except Exception:
        # If stored JSON is invalid/legacy, fall back to default.
        return schemas.ProjectConfig()


@router.put("/v1/projects/{project_id}/config", response_model=schemas.ProjectConfig)
def put_project_config(
    project_id: str,
    cfg: schemas.ProjectConfig,
    session=Depends(get_session),
    principal: Principal = Depends(resolve_principal),
):
    _require_project_admin(principal, project_id)

    row = session.get(models.Project, project_id)
    if not row:
        raise HTTPException(status_code=404, detail="not_found")

    row.config = cfg.model_dump()
    session.commit()

    return cfg
