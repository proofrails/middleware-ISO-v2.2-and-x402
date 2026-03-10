from __future__ import annotations

from typing import Optional

from fastapi import APIRouter
from starlette.responses import RedirectResponse

router = APIRouter(tags=["ui"])


@router.get("/receipt/{rid}")
def receipt_redirect(rid: str):
    return RedirectResponse(url=f"/ui/receipt.html?rid={rid}", status_code=307)


@router.get("/embed/receipt")
def embed_receipt_redirect(rid: Optional[str] = None, theme: Optional[str] = None):
    if not rid:
        return RedirectResponse(url="/", status_code=307)
    q = f"?rid={rid}"
    if theme:
        q += f"&theme={theme}"
    return RedirectResponse(url=f"/embed/receipt.html{q}", status_code=307)
