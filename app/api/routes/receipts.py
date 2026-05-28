from __future__ import annotations

import base64
import json
import logging
from datetime import datetime
from typing import List, Literal, Optional

from fastapi import APIRouter, Depends, HTTPException

from app import models, schemas
from app.api.deps import get_session
from app.auth import Principal, resolve_principal
from app.errors import APIError, ErrorCode
from app.services import receipts as receipts_svc

router = APIRouter(tags=["receipts"])
logger = logging.getLogger(__name__)


@router.get("/v1/receipts", response_model=schemas.ReceiptsPage)
def list_receipts(
    status: Optional[str] = None,
    chain: Optional[str] = None,
    reference: Optional[str] = None,
    since: Optional[str] = None,
    until: Optional[str] = None,
    tags: Optional[str] = None,
    scope: Literal["mine", "all"] = "mine",
    # Cursor-based pagination (preferred for agents)
    cursor: Optional[str] = None,
    # Legacy offset-based pagination (kept for backwards compatibility)
    page: int = 1,
    page_size: int = 20,
    session=Depends(get_session),
    principal: Principal = Depends(resolve_principal),
):
    """List receipts with filtering and pagination.

    Pagination
    ----------
    Two modes are supported:
    - **Cursor-based** (recommended for agents): pass `cursor` from a previous
      response's `next_cursor` field. Stable under concurrent inserts.
    - **Offset-based** (legacy): use `page` + `page_size`. Susceptible to
      skipping or repeating rows if new receipts arrive between pages.

    Tag filtering
    -------------
    Pass `tags=tag1,tag2` to return only receipts that have ALL listed tags.
    """
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

    # Tag filter: only return receipts that contain all requested tags
    if tags:
        requested_tags = [t.strip() for t in tags.split(",") if t.strip()]
        if requested_tags:
            from sqlalchemy import func as sqlfunc
            # JSON contains check — works for both Postgres (jsonb) and SQLite (json)
            for tag in requested_tags:
                q = q.filter(
                    models.Receipt.tags.isnot(None),
                    models.Receipt.tags.contains(json.dumps(tag)),
                )

    next_cursor: Optional[str] = None

    if cursor:
        # ── Cursor-based path ─────────────────────────────────────────────────
        try:
            cur = json.loads(base64.b64decode(cursor).decode())
            after_created_at = datetime.fromisoformat(cur["created_at"])
            after_id = cur["id"]
        except Exception:
            raise APIError(ErrorCode.VALIDATION_ERROR, "Invalid cursor", 400)

        q = q.order_by(models.Receipt.created_at.desc(), models.Receipt.id.desc())
        q = q.filter(
            (models.Receipt.created_at < after_created_at)
            | (
                (models.Receipt.created_at == after_created_at)
                & (models.Receipt.id < after_id)
            )
        )
        rows = q.limit(page_size + 1).all()
        has_more = len(rows) > page_size
        rows = rows[:page_size]

        if has_more and rows:
            last = rows[-1]
            next_cursor = base64.b64encode(
                json.dumps({"created_at": last.created_at.isoformat(), "id": str(last.id)}).encode()
            ).decode()

        items = [_to_list_item(r) for r in rows]
        return schemas.ReceiptsPage(
            items=items,
            total=len(items),
            page=1,
            page_size=page_size,
            next_cursor=next_cursor,
        )

    # ── Legacy offset-based path ──────────────────────────────────────────────
    rows, total, page, page_size = receipts_svc.paginate(q, page=page, page_size=page_size)
    items = [_to_list_item(r) for r in rows]

    # Generate a cursor pointing to the last item so callers can switch modes
    if items:
        last_row = rows[-1]
        next_offset_cursor = base64.b64encode(
            json.dumps({
                "created_at": last_row.created_at.isoformat(),
                "id": str(last_row.id),
            }).encode()
        ).decode()
        # Only emit next_cursor when there are more pages
        if page * page_size < total:
            next_cursor = next_offset_cursor

    return schemas.ReceiptsPage(
        items=items, total=total, page=page, page_size=page_size, next_cursor=next_cursor
    )

@router.get("/v1/iso/receipts/{rid}/status", response_model=schemas.ReceiptStatusResponse)
def get_receipt_status(rid: str, session=Depends(get_session)):
    """Lightweight receipt status check for polling agents.

    Returns only status, bundle_hash, flare_txid, and timestamps.
    Prefer this over `GET /v1/iso/receipts/{id}` when polling for pipeline
    completion — the full receipt payload (with ISO XML paths) is not needed
    until the receipt reaches `anchored` status.
    """
    rec: Optional[models.Receipt] = session.get(models.Receipt, rid)
    if not rec:
        raise APIError(ErrorCode.RECEIPT_NOT_FOUND, f"Receipt '{rid}' not found", 404)

    return schemas.ReceiptStatusResponse(
        id=str(rec.id),
        status=rec.status,
        bundle_hash=rec.bundle_hash,
        flare_txid=rec.flare_txid,
        anchored_at=rec.anchored_at,
        updated_at=rec.anchored_at or rec.created_at,
    )


@router.get("/v1/iso/receipts/{rid}", response_model=schemas.ReceiptResponse)
def get_receipt(rid: str, session=Depends(get_session)):
    logger.info("get_receipt_called rid=%s", rid)

    rec: Optional[models.Receipt] = session.get(models.Receipt, rid)
    if not rec:
        logger.warning("get_receipt_not_found rid=%s", rid)
        raise HTTPException(status_code=404, detail="Receipt not found")

    out = schemas.ReceiptResponse(
        id=str(rec.id),
        status=rec.status,
        bundle_hash=rec.bundle_hash,
        flare_txid=rec.flare_txid,
        xml_url=f"/files/{rid}/pain001.xml",
        bundle_url=f"/files/{rid}/evidence.zip",
        created_at=rec.created_at,
        anchored_at=rec.anchored_at,
    )

    logger.info(
        "get_receipt_return "
        "id=%s status=%s bundle_hash=%s flare_txid=%s xml_url=%s bundle_url=%s created_at=%s anchored_at=%s",
        out.id,
        out.status,
        out.bundle_hash,
        out.flare_txid,
        out.xml_url,
        out.bundle_url,
        out.created_at,
        out.anchored_at,
    )

    return out


@router.post("/v1/iso/receipts/{rid}/retry-anchor")
def retry_anchor(rid: str, session=Depends(get_session)):
    """Re-queue a failed receipt for anchoring."""
    import os
    from app.jobs import anchor_receipt_job, _project_anchoring_chains
    from app.queue import get_queue

    rec: Optional[models.Receipt] = session.get(models.Receipt, rid)
    if not rec:
        raise HTTPException(status_code=404, detail="Receipt not found")

    if rec.status != "failed":
        raise HTTPException(status_code=409, detail=f"Receipt status is '{rec.status}', not 'failed'")

    if not rec.bundle_hash:
        raise HTTPException(status_code=409, detail="Receipt has no bundle_hash")

    # Resolve chain config
    proj_chains = _project_anchoring_chains(session, rec)
    if not proj_chains:
        proj_chains = [
            {
                "name": rec.chain or "flare",
                "contract": os.getenv("ANCHOR_CONTRACT_ADDR") or "0x0690d8cFb1897c12B2C0b34660edBDE4E20ff4d8",
                "rpc_url": os.getenv("FLARE_RPC_URL"),
            }
        ]

    # Reset status and clear stale anchor tx
    rec.status = "awaiting_anchor"
    rec.flare_txid = None
    session.commit()

    # Enqueue anchor job
    anchor_q = get_queue("anchor")
    anchor_q.enqueue(
        anchor_receipt_job,
        receipt_id=str(rec.id),
        bundle_hash=rec.bundle_hash,
        chains=proj_chains,
        job_timeout=120,
    )

    logger.info("retry_anchor_enqueued rid=%s", rid)
    return {"ok": True, "id": str(rec.id), "status": "awaiting_anchor"}


# ── Helpers ───────────────────────────────────────────────────────────────────

def _to_list_item(r: models.Receipt) -> schemas.ReceiptListItem:
    return schemas.ReceiptListItem(
        id=str(r.id),
        status=schemas.Status(r.status),
        amount=r.amount,
        currency=r.currency,
        chain=r.chain,
        reference=r.reference,
        created_at=r.created_at,
        anchored_at=r.anchored_at,
        tags=r.tags,
        metadata=r.extra_metadata,
    )