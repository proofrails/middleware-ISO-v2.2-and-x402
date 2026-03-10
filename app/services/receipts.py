from __future__ import annotations

from datetime import datetime
from typing import Optional

from fastapi import HTTPException

from app import models
from app.auth import Principal


def require_write_access(principal: Principal) -> None:
    if principal.is_public:
        raise HTTPException(status_code=401, detail="Unauthorized")


def apply_receipt_scope(q, principal: Principal, scope: str):
    if scope == "all":
        if not principal.is_admin:
            raise HTTPException(status_code=403, detail="forbidden_scope_all")
        return q

    # mine
    if principal.project_id:
        return q.filter(models.Receipt.project_id == principal.project_id)
    return q


def apply_receipt_filters(
    q,
    *,
    status: Optional[str],
    chain: Optional[str],
    reference: Optional[str],
    since: Optional[datetime],
    until: Optional[datetime],
):
    if status:
        q = q.filter(models.Receipt.status == status)
    if chain:
        q = q.filter(models.Receipt.chain == chain)
    if reference:
        q = q.filter(models.Receipt.reference.like(f"%{reference}%"))
    if since:
        q = q.filter(models.Receipt.created_at >= since)
    if until:
        q = q.filter(models.Receipt.created_at <= until)
    return q


def parse_date(d: Optional[str], *, end_of_day: bool = False) -> Optional[datetime]:
    if not d:
        return None
    try:
        dt = datetime.strptime(d, "%Y-%m-%d")
        if end_of_day:
            return dt.replace(hour=23, minute=59, second=59)
        return dt
    except Exception:
        raise HTTPException(status_code=400, detail="invalid_date")


def paginate(q, *, page: int, page_size: int):
    page = max(page, 1)
    page_size = max(min(page_size, 200), 1)
    total = q.count()
    items = q.order_by(models.Receipt.created_at.desc()).offset((page - 1) * page_size).limit(page_size).all()
    return items, total, page, page_size
