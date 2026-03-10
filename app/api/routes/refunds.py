"""Refund/return endpoints for pacs.004 payment returns."""
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app import models, schemas
from app.api.deps import get_session
from app.auth.principal import Principal
from app.auth.api_key_auth import resolve_principal
from app.queue import enqueue_receipt_processing

router = APIRouter()


@router.post("/v1/iso/refund", response_model=schemas.RefundResponse)
def refund_receipt(
    req: schemas.RefundRequest,
    session: Session = Depends(get_session),
    principal: Principal = Depends(resolve_principal),
):
    """
    Initiate a refund/return for an existing receipt.
    
    This creates a new receipt that references the original, generates a pacs.004
    payment return message, and schedules it for bundling and anchoring.
    
    - Requires authentication (API key or SIWE)
    - Original receipt must exist and be in 'anchored' status
    - Creates a new receipt with refund_of foreign key
    - Generates pacs.004 ISO message
    """
    # Load original receipt
    original = session.query(models.Receipt).filter_by(id=req.original_receipt_id).first()
    
    if not original:
        raise HTTPException(status_code=404, detail="Original receipt not found")
    
    # Verify principal has access to this receipt
    # If project-scoped, check that principal's project_id matches receipt's project_id
    if principal.project_id and original.project_id != principal.project_id:
        raise HTTPException(status_code=403, detail="Access denied to this receipt")
    
    # Verify original is anchored (can only refund completed transactions)
    if original.status != "anchored":
        raise HTTPException(
            status_code=400,
            detail=f"Can only refund anchored receipts (current status: {original.status})"
        )
    
    # Create refund receipt
    refund_id = str(uuid4())
    refund_receipt = models.Receipt(
        id=refund_id,
        reference=f"refund:{original.reference}",
        tip_tx_hash=original.tip_tx_hash,  # Reference same blockchain tx
        chain=original.chain,
        amount=-abs(original.amount),  # Negative amount for return
        currency=original.currency,
        sender_wallet=original.receiver_wallet,  # Reversed
        receiver_wallet=original.sender_wallet,  # Reversed
        status="pending",
        refund_of=req.original_receipt_id,  # FK to original
        project_id=original.project_id,  # Inherit project
        callback_url=None,  # Don't inherit callback
    )
    
    session.add(refund_receipt)
    session.commit()
    session.refresh(refund_receipt)
    
    # Enqueue for processing (will generate pacs.004, bundle, anchor)
    enqueue_receipt_processing(
        receipt_id=refund_id,
        reason_code=req.reason_code,
        is_refund=True,
    )
    
    return schemas.RefundResponse(
        refund_receipt_id=refund_id,
        status=schemas.Status.pending,
    )
