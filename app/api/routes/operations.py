from __future__ import annotations

"""Operation status polling endpoint.

After `POST /v1/iso/record-tip` returns, the receipt processing pipeline
continues asynchronously. Agents can poll `GET /v1/operations/{operation_id}`
for lightweight status updates without fetching the full receipt payload.

The operation_id returned by `record-tip` is the same UUID as the receipt_id,
so both endpoints work in parallel.

Operation states
----------------
  pending         – queued, not yet picked up by a worker
  processing      – worker is generating ISO documents
  awaiting_anchor – evidence bundle ready, waiting for on-chain anchoring
  anchored        – evidence anchored on Flare; processing complete
  failed          – unrecoverable error (see error_code / error_message)

Polling guidance
----------------
- Poll at 2–5 s intervals while state is pending/processing/awaiting_anchor
- Typical end-to-end time: 10–60 s depending on chain congestion
- Anchor confirmation can take up to 5 min; use `receipt.anchored` webhook
  events instead of tight polling for production integrations
"""

from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from app import models
from app.api.deps import get_session
from app.errors import APIError, ErrorCode

router = APIRouter(tags=["operations"])


class OperationStatus(BaseModel):
    operation_id: str
    receipt_id: str
    status: str = Field(
        ...,
        description="pending | processing | awaiting_anchor | anchored | failed",
    )
    bundle_hash: Optional[str] = Field(None, description="SHA-256 of evidence bundle (set after processing)")
    flare_txid: Optional[str] = Field(None, description="On-chain anchor tx hash (set after anchoring)")
    created_at: datetime
    updated_at: Optional[datetime] = Field(None, description="Last status change timestamp")
    error_code: Optional[str] = Field(None, description="Machine-readable error code when status=failed")
    error_message: Optional[str] = Field(None, description="Human-readable error detail when status=failed")


@router.get("/v1/operations/{operation_id}", response_model=OperationStatus)
def get_operation(operation_id: str, session=Depends(get_session)):
    """Poll the status of an asynchronous receipt-processing operation.

    The `operation_id` matches the `receipt_id` returned by `POST /v1/iso/record-tip`.
    Returns a lightweight status object — use `GET /v1/iso/receipts/{id}` for
    the full receipt payload including ISO artifacts.
    """
    rec: Optional[models.Receipt] = session.get(models.Receipt, operation_id)
    if not rec:
        raise APIError(ErrorCode.OPERATION_NOT_FOUND, f"Operation '{operation_id}' not found", 404)

    error_code = None
    error_message = None
    if rec.status == "failed":
        error_code = ErrorCode.ANCHOR_FAILED.value
        error_message = "Receipt processing or on-chain anchoring failed. Use /retry-anchor to re-queue."

    return OperationStatus(
        operation_id=str(rec.id),
        receipt_id=str(rec.id),
        status=rec.status,
        bundle_hash=rec.bundle_hash,
        flare_txid=rec.flare_txid,
        created_at=rec.created_at,
        updated_at=rec.anchored_at or rec.created_at,
        error_code=error_code,
        error_message=error_message,
    )
