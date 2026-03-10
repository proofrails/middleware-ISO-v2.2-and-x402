from __future__ import annotations

from typing import List, Literal, Optional

from fastapi import APIRouter, Depends, HTTPException

from app import models, schemas
from app.api.deps import get_session
from app.auth import Principal, resolve_principal
from app.services import receipts as receipts_svc

router = APIRouter(tags=["receipts"])


@router.get("/v1/receipts", response_model=schemas.ReceiptsPage)
def list_receipts(
    status: Optional[str] = None,
    chain: Optional[str] = None,
    reference: Optional[str] = None,
    since: Optional[str] = None,
    until: Optional[str] = None,
    scope: Literal["mine", "all"] = "mine",
    page: int = 1,
    page_size: int = 20,
    session=Depends(get_session),
    principal: Principal = Depends(resolve_principal),
):
    # If any keys exist, listing requires a key.
    if principal.is_public:
        env_keys = __import__("os").getenv("API_KEYS")
        have_env = bool(env_keys and env_keys.strip())
        have_db = session.query(models.APIKey).filter(models.APIKey.revoked_at.is_(None)).count() > 0
        if have_env or have_db:
            raise HTTPException(status_code=401, detail="Unauthorized")

    q = session.query(models.Receipt)
    q = receipts_svc.apply_receipt_scope(q, principal, scope)

    since_dt = receipts_svc.parse_date(since)
    until_dt = receipts_svc.parse_date(until, end_of_day=True)

    q = receipts_svc.apply_receipt_filters(
        q, status=status, chain=chain, reference=reference, since=since_dt, until=until_dt
    )
    rows, total, page, page_size = receipts_svc.paginate(q, page=page, page_size=page_size)

    items: List[schemas.ReceiptListItem] = [
        schemas.ReceiptListItem(
            id=str(r.id),
            status=schemas.Status(r.status),
            amount=r.amount,
            currency=r.currency,
            chain=r.chain,
            reference=r.reference,
            created_at=r.created_at,
            anchored_at=r.anchored_at,
        )
        for r in rows
    ]

    return schemas.ReceiptsPage(items=items, total=total, page=page, page_size=page_size)


@router.get("/v1/iso/receipts/{rid}", response_model=schemas.ReceiptResponse)
def get_receipt(rid: str, session=Depends(get_session)):
    rec: Optional[models.Receipt] = session.get(models.Receipt, rid)
    if not rec:
        raise HTTPException(status_code=404, detail="Receipt not found")

    return schemas.ReceiptResponse(
        id=str(rec.id),
        status=rec.status,
        bundle_hash=rec.bundle_hash,
        flare_txid=rec.flare_txid,
        xml_url=f"/files/{rid}/pain001.xml",
        bundle_url=f"/files/{rid}/evidence.zip",
        created_at=rec.created_at,
        anchored_at=rec.anchored_at,
    )
