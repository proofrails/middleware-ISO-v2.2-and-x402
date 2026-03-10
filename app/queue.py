from __future__ import annotations

from redis import Redis  # type: ignore
from rq import Queue  # type: ignore

from .settings import get_settings

settings = get_settings()


def _redis_url() -> str:
    return settings.redis_url


def get_redis() -> Redis:
    # decode_responses=False because RQ stores binary payloads
    return Redis.from_url(_redis_url(), decode_responses=False)


def get_queue(name: str = "default") -> Queue:
    return Queue(name, connection=get_redis())


def enqueue_receipt_processing(
    receipt_id: str,
    callback_url: str | None = None,
    reason_code: str | None = None,
    is_refund: bool = False,
) -> None:
    """Enqueue receipt processing job."""
    from .jobs import process_receipt_job
    
    q = get_queue()
    q.enqueue(
        process_receipt_job,
        receipt_id=receipt_id,
        callback_url=callback_url,
        reason_code=reason_code,
        is_refund=is_refund,
    )
