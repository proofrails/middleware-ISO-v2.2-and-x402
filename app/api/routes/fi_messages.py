"""Financial Institution (FI) specific ISO message generation endpoints.

Endpoints for generating FI-to-FI messages:
- camt.056 - FI-to-FI Payment Cancellation Request
- camt.029 - Resolution of Investigation
- pacs.007 - FI-to-FI Payment Reversal
- pacs.009 - Financial Institution Credit Transfer
"""
import os
from pathlib import Path
from uuid import uuid4
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app import models, schemas
from app.api.deps import get_session
from app.auth.principal import Principal
from app.auth.api_key_auth import resolve_principal
from app.iso_messages import camt056, camt029, pacs007, pacs009

router = APIRouter()


def _sha256_hex(b: bytes) -> str:
    import hashlib
    return "0x" + hashlib.sha256(b).hexdigest()


def _ensure_dir_for_receipt(rid: str) -> Path:
    artifacts_dir = os.getenv("ARTIFACTS_DIR", "artifacts")
    out = Path(artifacts_dir) / rid
    out.mkdir(parents=True, exist_ok=True)
    return out


def _write_iso_artifact(session: Session, receipt_id: str, type_str: str, filename: str, content: bytes) -> tuple[str, str]:
    """Write ISO artifact to disk and create database record."""
    out_dir = _ensure_dir_for_receipt(receipt_id)
    file_path = out_dir / filename
    try:
        file_path.write_bytes(content)
    except Exception:
        # best-effort write; proceed to DB row
        pass
    sha = _sha256_hex(content)
    art = models.ISOArtifact(receipt_id=receipt_id, type=type_str, path=str(file_path), sha256=sha)
    session.add(art)
    session.commit()
    return str(file_path), sha


@router.post("/v1/iso/camt056/{rid}", response_model=schemas.FIMessageResponse)
def generate_camt056(
    rid: str,
    req: schemas.FIMessageRequest,
    session: Session = Depends(get_session),
    principal: Principal = Depends(resolve_principal),
):
    """
    Generate a camt.056 FI-to-FI Payment Cancellation Request.
    
    This message is used by a financial institution to request cancellation of a 
    previously sent payment instruction.
    
    - Requires authentication (API key or SIWE)
    - Receipt must exist
    - Generates camt.056 ISO message
    """
    # Load original receipt
    original = session.query(models.Receipt).filter_by(id=rid).first()
    
    if not original:
        raise HTTPException(status_code=404, detail="Receipt not found")
    
    # Verify principal has access to this receipt
    if principal.project_id and original.project_id != principal.project_id:
        raise HTTPException(status_code=403, detail="Access denied to this receipt")
    
    # Convert receipt to dict format expected by generator
    original_dict = {
        "id": str(original.id),
        "reference": original.reference,
        "tip_tx_hash": original.tip_tx_hash,
        "chain": original.chain,
        "amount": original.amount,
        "currency": original.currency,
        "sender_wallet": original.sender_wallet,
        "receiver_wallet": original.receiver_wallet,
        "created_at": original.created_at or datetime.utcnow(),
    }
    
    # Generate unique message ID
    cancel_id = f"camt056-{uuid4()}"
    
    # Generate camt.056 XML
    xml_bytes = camt056.generate_camt056(original_dict, cancel_id, req.reason_code)
    
    # Save artifact
    file_path, sha = _write_iso_artifact(session, rid, "camt.056", "camt056.xml", xml_bytes)
    
    return schemas.FIMessageResponse(
        message_id=cancel_id,
        type="camt.056",
        receipt_id=rid,
        url=f"/files/{rid}/camt056.xml",
    )


@router.post("/v1/iso/camt029/{rid}", response_model=schemas.FIMessageResponse)
def generate_camt029(
    rid: str,
    req: schemas.FIMessageRequest,
    session: Session = Depends(get_session),
    principal: Principal = Depends(resolve_principal),
):
    """
    Generate a camt.029 Resolution of Investigation.
    
    This message is used to provide the response to a cancellation request or 
    investigation query.
    
    - Requires authentication (API key or SIWE)
    - Receipt must exist
    - Generates camt.029 ISO message
    """
    # Load original receipt
    original = session.query(models.Receipt).filter_by(id=rid).first()
    
    if not original:
        raise HTTPException(status_code=404, detail="Receipt not found")
    
    # Verify principal has access to this receipt
    if principal.project_id and original.project_id != principal.project_id:
        raise HTTPException(status_code=403, detail="Access denied to this receipt")
    
    # Convert receipt to dict format expected by generator
    original_dict = {
        "id": str(original.id),
        "reference": original.reference,
        "created_at": original.created_at or datetime.utcnow(),
    }
    
    # Generate unique message ID
    resolution_id = f"camt029-{uuid4()}"
    
    # Generate camt.029 XML
    xml_bytes = camt029.generate_camt029(original_dict, resolution_id, req.resolution_code)
    
    # Save artifact
    file_path, sha = _write_iso_artifact(session, rid, "camt.029", "camt029.xml", xml_bytes)
    
    return schemas.FIMessageResponse(
        message_id=resolution_id,
        type="camt.029",
        receipt_id=rid,
        url=f"/files/{rid}/camt029.xml",
    )


@router.post("/v1/iso/pacs007/{rid}", response_model=schemas.FIMessageResponse)
def generate_pacs007(
    rid: str,
    req: schemas.FIMessageRequest,
    session: Session = Depends(get_session),
    principal: Principal = Depends(resolve_principal),
):
    """
    Generate a pacs.007 FI-to-FI Payment Reversal.
    
    This message is used by a financial institution to reverse a previously sent 
    payment instruction.
    
    - Requires authentication (API key or SIWE)
    - Receipt must exist
    - Generates pacs.007 ISO message
    """
    # Load original receipt
    original = session.query(models.Receipt).filter_by(id=rid).first()
    
    if not original:
        raise HTTPException(status_code=404, detail="Receipt not found")
    
    # Verify principal has access to this receipt
    if principal.project_id and original.project_id != principal.project_id:
        raise HTTPException(status_code=403, detail="Access denied to this receipt")
    
    # Convert receipt to dict format expected by generator
    original_dict = {
        "id": str(original.id),
        "reference": original.reference,
        "amount": original.amount,
        "currency": original.currency,
        "sender_wallet": original.sender_wallet,
        "receiver_wallet": original.receiver_wallet,
        "created_at": original.created_at or datetime.utcnow(),
    }
    
    # Generate unique message ID
    reversal_id = f"pacs007-{uuid4()}"
    
    # Generate pacs.007 XML
    xml_bytes = pacs007.generate_pacs007(original_dict, reversal_id, req.reason_code)
    
    # Save artifact
    file_path, sha = _write_iso_artifact(session, rid, "pacs.007", "pacs007.xml", xml_bytes)
    
    return schemas.FIMessageResponse(
        message_id=reversal_id,
        type="pacs.007",
        receipt_id=rid,
        url=f"/files/{rid}/pacs007.xml",
    )


@router.post("/v1/iso/pacs009/{rid}", response_model=schemas.FIMessageResponse)
def generate_pacs009(
    rid: str,
    session: Session = Depends(get_session),
    principal: Principal = Depends(resolve_principal),
):
    """
    Generate a pacs.009 Financial Institution Credit Transfer.
    
    This message is used for credit transfers between financial institutions.
    
    - Requires authentication (API key or SIWE)
    - Receipt must exist
    - Generates pacs.009 ISO message
    """
    # Load original receipt
    original = session.query(models.Receipt).filter_by(id=rid).first()
    
    if not original:
        raise HTTPException(status_code=404, detail="Receipt not found")
    
    # Verify principal has access to this receipt
    if principal.project_id and original.project_id != principal.project_id:
        raise HTTPException(status_code=403, detail="Access denied to this receipt")
    
    # Convert receipt to dict format expected by generator
    receipt_dict = {
        "id": str(original.id),
        "reference": original.reference,
        "amount": original.amount,
        "currency": original.currency,
        "sender_wallet": original.sender_wallet,
        "receiver_wallet": original.receiver_wallet,
        "created_at": original.created_at or datetime.utcnow(),
    }
    
    # Generate pacs.009 XML
    xml_bytes = pacs009.generate_pacs009(receipt_dict)
    
    # Generate unique message ID for response
    message_id = f"pacs009-{uuid4()}"
    
    # Save artifact
    file_path, sha = _write_iso_artifact(session, rid, "pacs.009", "pacs009.xml", xml_bytes)
    
    return schemas.FIMessageResponse(
        message_id=message_id,
        type="pacs.009",
        receipt_id=rid,
        url=f"/files/{rid}/pacs009.xml",
    )
