from __future__ import annotations

from fastapi import APIRouter, Depends

from app.api.deps import get_session
from app.auth import resolve_principal
from app.config import OrgConfigModel
from app.config import get_config as load_config
from app.config import save_config as persist_config

router = APIRouter(tags=["config"])


@router.get("/v1/config")
def get_config(session=Depends(get_session)):
    return load_config(session)


@router.put("/v1/config")
def put_config(cfg: OrgConfigModel, session=Depends(get_session), _principal=Depends(resolve_principal)):
    return persist_config(session, cfg)
