from __future__ import annotations

from datetime import datetime
from typing import Optional
from uuid import uuid4

from fastapi import APIRouter, BackgroundTasks, Depends

from app import models, schemas
from app.api.deps import get_session
from app.auth import Principal, resolve_principal
from app.jobs import process_receipt_job
from app.queue import get_queue
from app.services import receipts as receipts_svc
from app.webhook_dispatcher import dispatch_receipt_event

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
            job_timeout=int(__import__("os").getenv("RQ_JOB_TIMEOUT", "120")),
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
    """Record a blockchain payment and start the ISO 20022 processing pipeline.

    Returns `receipt_id` and `operation_id` (identical values) for status
    polling. Supports `Idempotency-Key` header for safe retries — duplicate
    submissions with the same chain+tip_tx_hash or reference are detected
    and the existing receipt is returned.

    Attach `metadata` and `tags` to carry agent-specific context (correlation
    IDs, workflow state, etc.) through the processing pipeline and into
    webhook payloads.
    """
    receipts_svc.require_write_access(principal)

    chain_value = payload.chain.value if hasattr(payload.chain, "value") else str(payload.chain)

    existing = (
        session.query(models.Receipt)
        .filter(models.Receipt.chain == chain_value, models.Receipt.tip_tx_hash == payload.tip_tx_hash)
        .one_or_none()
    )
    if existing:
        return schemas.RecordTipResponse(
            receipt_id=str(existing.id),
            status=schemas.Status(existing.status),
            operation_id=str(existing.id),
        )

    existing_ref = session.query(models.Receipt).filter(models.Receipt.reference == payload.reference).one_or_none()
    if existing_ref:
        return schemas.RecordTipResponse(
            receipt_id=str(existing_ref.id),
            status=schemas.Status(existing_ref.status),
            operation_id=str(existing_ref.id),
        )

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
        extra_metadata=payload.metadata,
        tags=payload.tags,
    )
    session.add(receipt)
    session.commit()

    # Fire webhook for receipt.pending so agents can track pipeline start
    background_tasks.add_task(dispatch_receipt_event, receipt, "receipt.pending")

    _enqueue_receipt_processing(str(rid), payload.callback_url, background_tasks)

    return schemas.RecordTipResponse(
        receipt_id=str(rid),
        status=schemas.Status("pending"),
        operation_id=str(rid),
    )
