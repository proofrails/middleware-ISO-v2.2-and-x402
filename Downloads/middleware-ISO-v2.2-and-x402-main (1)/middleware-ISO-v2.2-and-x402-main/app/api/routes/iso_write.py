from __future__ import annotations

import hashlib
import os
from datetime import datetime
from pathlib import Path
from typing import Optional
from uuid import uuid4

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from sqlalchemy.orm import Session

from app import models, schemas
from app.api.deps import get_session
from app.auth import Principal, resolve_principal
from app.iso_messages.pain008 import generate_pain008
from app.jobs import process_receipt_job
from app.queue import get_queue
from app.services import receipts as receipts_svc

router = APIRouter(tags=["iso-write"])


def _enqueue_receipt_processing(
    receipt_id: str, callback_url: Optional[str], background_tasks: BackgroundTasks
) -> None:
    try:
        from rq import Retry  # type: ignore

        q = get_queue("default")
        q.enqueue(
            process_receipt_job,
            receipt_id,
            callback_url,
            job_timeout=int(__import__("os").getenv("RQ_JOB_TIMEOUT", "600")),
            retry=Retry(max=5, interval=[10, 30, 60, 120, 300]),
        )
        return
    except Exception:
        background_tasks.add_task(process_receipt_job, receipt_id, callback_url)


@router.post("/v1/iso/record-tip", response_model=schemas.RecordTipResponse)
def record_tip(
    payload: schemas.TipRecordRequest,
    background_tasks: BackgroundTasks,
    session=Depends(get_session),
    principal: Principal = Depends(resolve_principal),
):
    receipts_svc.require_write_access(principal)

    chain_value = payload.chain.value if hasattr(payload.chain, "value") else str(payload.chain)

    existing = (
        session.query(models.Receipt)
        .filter(models.Receipt.chain == chain_value, models.Receipt.tip_tx_hash == payload.tip_tx_hash)
        .one_or_none()
    )
    if existing:
        return schemas.RecordTipResponse(receipt_id=str(existing.id), status=schemas.Status(existing.status))

    existing_ref = session.query(models.Receipt).filter(models.Receipt.reference == payload.reference).one_or_none()
    if existing_ref:
        return schemas.RecordTipResponse(receipt_id=str(existing_ref.id), status=schemas.Status(existing_ref.status))

    rid = uuid4()
    created_at = datetime.utcnow()

    receipt = models.Receipt(
        id=rid,
        project_id=principal.project_id,
        reference=payload.reference,
        tip_tx_hash=payload.tip_tx_hash,
        chain=chain_value,
        amount=payload.amount,
        currency=payload.currency,
        sender_wallet=payload.sender_wallet,
        receiver_wallet=payload.receiver_wallet,
        status="pending",
        created_at=created_at,
        anchored_at=None,
    )
    session.add(receipt)
    session.commit()

    _enqueue_receipt_processing(str(rid), payload.callback_url, background_tasks)

    return schemas.RecordTipResponse(receipt_id=str(rid), status=schemas.Status("pending"))


# ---------------------------------------------------------------------------
# pain.008 – CustomerDirectDebitInitiation
# ---------------------------------------------------------------------------

def _sha256_hex(b: bytes) -> str:
    return "0x" + hashlib.sha256(b).hexdigest()


def _ensure_dir_for_receipt(rid: str) -> Path:
    artifacts_dir = os.getenv("ARTIFACTS_DIR", "artifacts")
    out = Path(artifacts_dir) / rid
    out.mkdir(parents=True, exist_ok=True)
    return out


def _write_iso_artifact(
    session: Session, receipt_id: str, type_str: str, filename: str, content: bytes
) -> tuple[str, str]:
    """Write ISO artifact to disk and create database record."""
    out_dir = _ensure_dir_for_receipt(receipt_id)
    file_path = out_dir / filename
    try:
        file_path.write_bytes(content)
    except Exception:
        pass
    sha = _sha256_hex(content)
    art = models.ISOArtifact(
        receipt_id=receipt_id, type=type_str, path=str(file_path), sha256=sha
    )
    session.add(art)
    session.commit()
    return str(file_path), sha


@router.post("/v1/iso/pain008/{rid}", response_model=schemas.FIMessageResponse)
def create_pain008(
    rid: str,
    session: Session = Depends(get_session),
    principal: Principal = Depends(resolve_principal),
):
    """
    Generate a pain.008 CustomerDirectDebitInitiation.

    - Requires authentication (API key or SIWE)
    - Receipt must exist and belong to the caller's project
    - Generates pain.008 ISO 20022 XML artifact
    """
    if principal.is_public:
        raise HTTPException(status_code=401, detail="Unauthorized")

    original = session.query(models.Receipt).filter_by(id=rid).first()
    if not original:
        raise HTTPException(status_code=404, detail="Receipt not found")

    if principal.project_id and original.project_id != principal.project_id:
        raise HTTPException(status_code=403, detail="Access denied to this receipt")

    receipt_dict = {
        "id": str(original.id),
        "reference": original.reference,
        "sender_wallet": original.sender_wallet,
        "receiver_wallet": original.receiver_wallet,
        "currency": original.currency,
        "amount": original.amount,
        "created_at": original.created_at or datetime.utcnow(),
    }

    xml_bytes = generate_pain008(receipt_dict)

    message_id = f"pain008-{uuid4()}"

    _write_iso_artifact(session, rid, "pain008", "pain008.xml", xml_bytes)

    return schemas.FIMessageResponse(
        message_id=message_id,
        type="pain.008",
        receipt_id=rid,
        url=f"/files/{rid}/pain008.xml",
    )
